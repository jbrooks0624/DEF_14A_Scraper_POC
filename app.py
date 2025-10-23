import streamlit as st
import asyncio
from ticker_finder import find_ticker, get_market_cap
from scraper import scrape_html, extract_context_around_phrases
from bs4 import BeautifulSoup
from analyze_14a import analyze
from edgar_api import find_def14a_url
import json
from typing import Dict, Optional


# Page config
st.set_page_config(
    page_title="Change of Control Analyzer",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 600;
        margin-bottom: 2rem;
        color: #1f1f1f;
    }
    .stTextInput input {
        font-size: 0.85rem;
        height: 40px;
    }
    .result-card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #f0f7ff;
        border: 2px solid #2c5cc5;
        margin-bottom: 1rem;
        text-align: center;
    }
    .result-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .result-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2c5cc5;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .company-header {
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #1f1f1f;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)


# Initialize session state
if 'num_inputs' not in st.session_state:
    st.session_state.num_inputs = 1
if 'running' not in st.session_state:
    st.session_state.running = False
if 'results' not in st.session_state:
    st.session_state.results = {}


async def process_company(company_name: str, status_placeholder) -> Dict:
    """Process a single company and return results"""
    result = {
        'company_name': company_name,
        'ticker': None,
        'market_cap': None,
        'total_payments': None,
        'percentage': None,
        'error': None,
        'stage': 'init',
        'filing_date': None
    }
    
    try:
        # Step 1: Find DEF 14A filing
        result['stage'] = 'finding_def14a'
        status_placeholder.info("🔄 Searching for DEF 14A filing...")
        
        filing_info = find_def14a_url(company_name, verbose=False)
        
        # Check if there was an error
        if filing_info and 'error' in filing_info:
            result['error'] = filing_info.get('error_detail', 'Could not find DEF 14A filing')
            result['company_name'] = filing_info.get('company_name', company_name)
            result['ticker'] = filing_info.get('ticker')
            status_placeholder.error(f"❌ {result['error']}")
            return result
        
        if not filing_info:
            result['error'] = "Could not find DEF 14A filing for this company"
            status_placeholder.error(f"❌ {result['error']}")
            return result
        
        result['ticker'] = filing_info['ticker']
        result['filing_date'] = filing_info['filing_date']
        sec_url = filing_info['url']
        
        status_placeholder.success(f"✅ Found DEF 14A (Filed: {filing_info['filing_date']})")
        await asyncio.sleep(0.1)  # Brief pause for visual feedback
        
        # Step 2: Get market cap
        result['stage'] = 'fetching_market_cap'
        status_placeholder.info("🔄 Fetching market cap...")
        
        market_cap = get_market_cap(result['ticker'])
        if not market_cap:
            result['error'] = "Could not fetch market cap"
            status_placeholder.error(f"❌ {result['error']}")
            return result
        result['market_cap'] = market_cap
        
        # Show market cap
        status_placeholder.success(f"✅ Market Cap: ${market_cap:,}")
        await asyncio.sleep(0.1)  # Brief pause for visual feedback
        
        # Step 3: Scrape and analyze
        result['stage'] = 'fetching_coc'
        status_placeholder.info("🔄 Analyzing change in control information...")
        
        # Scrape SEC filing
        html = scrape_html(sec_url)
        soup = BeautifulSoup(html, 'html.parser')
        
        for script in soup(['script', 'style']):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
        
        search_phrases = ['change in control', 'change of control']
        text_blocks = extract_context_around_phrases(text, search_phrases, context_chars=1000)
        relevant_text = '\n\n'.join(text_blocks)
        
        # Analyze with OpenAI
        analysis_result = await analyze(relevant_text)
        
        # Parse and calculate
        try:
            json_str = analysis_result
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0].strip()
            
            json_str = json_str.strip()
            if json_str.startswith('{') and not json_str.startswith('['):
                if '}\n{' in json_str or '},\n{' in json_str:
                    json_str = '[' + json_str.replace('}\n{', '},\n{').replace('},\n{', '},\n{') + ']'
                else:
                    json_str = '[' + json_str + ']'
            
            payouts = json.loads(json_str)
            if isinstance(payouts, dict):
                payouts = [payouts]
            
            # Ensure all amounts are numeric and handle potential string values
            total_payments = 0
            for payout in payouts:
                amount = payout.get('amount', 0)
                # Convert to float if it's a string or int
                if isinstance(amount, str):
                    amount = float(amount.replace(',', '').replace('$', ''))
                total_payments += float(amount) if amount else 0
            
            percentage = (total_payments / market_cap) * 100
            
            result['total_payments'] = total_payments
            result['percentage'] = percentage
            result['payouts'] = payouts
            result['stage'] = 'complete'
            
            status_placeholder.success(f"✅ Analysis complete!")
        
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as parse_error:
            # Failed to parse or calculate from the analysis result
            result['error'] = "Failed to find change of control values from DEF 14A document"
            status_placeholder.error(f"❌ {result['error']}")
            return result
        
    except Exception as e:
        result['error'] = str(e)
        status_placeholder.error(f"❌ Error: {str(e)}")
    
    return result


def display_result(company_name: str, result: Dict):
    """Display results for a single company"""
    # Company header
    display_name = result.get('company_name', company_name)
    st.markdown(f'<div class="company-header">{display_name}</div>', unsafe_allow_html=True)
    
    if result.get('error'):
        st.error(f"❌ {result['error']}")
        
        # Show helpful suggestions based on error type
        if 'not found' in result['error'].lower():
            st.info("💡 **Tip:** Try using the full legal name with 'Inc.', 'Corp.', or 'Corporation'")
        elif 'no def 14a' in result['error'].lower():
            st.info("💡 **Note:** This company may be private, foreign, or hasn't filed a proxy statement recently.")
        
        return
    
    # Ticker and filing date
    if result.get('ticker'):
        ticker_info = f"**Ticker:** {result['ticker']}"
        if result.get('filing_date'):
            ticker_info += f" | **DEF 14A Filed:** {result['filing_date']}"
        st.caption(ticker_info)
    
    # Market Cap
    if result.get('market_cap'):
        st.metric("Market Cap", f"${result['market_cap']:,}")
    
    # Change of Control Info
    if result.get('total_payments'):
        st.metric("Total CoC Payments", f"${result['total_payments']:,}")
        
        # Show individual payouts in expander
        if result.get('payouts'):
            with st.expander("View Payment Details"):
                for payout in result['payouts']:
                    if payout.get('amount', 0) > 0:
                        st.text(f"• {payout.get('name', 'Unknown')}: ${payout.get('amount', 0):,}")
    
    # Final Result - Big and prominent
    if result.get('percentage') is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
            <div class="result-card">
                <div class="result-value">{result['percentage']:.4f}%</div>
                <div class="metric-label">of Market Cap</div>
            </div>
        """, unsafe_allow_html=True)


async def process_all_companies(company_names, status_placeholders):
    """Process all companies concurrently"""
    tasks = [process_company(name, placeholder) 
             for name, placeholder in zip(company_names, status_placeholders) 
             if name.strip()]
    results = await asyncio.gather(*tasks)
    return {name: result for name, result in zip(company_names, results) if name.strip()}


def main():
    # Title
    st.markdown('<h1 class="main-title">Change of Control Analyzer</h1>', unsafe_allow_html=True)
    
    # Help section
    with st.expander("💡 How to use this tool", expanded=False):
        st.markdown("""
        **Enter a company name** to analyze their most recent DEF 14A proxy statement.
        
        **What this tool does:**
        1. 🔍 Searches SEC EDGAR for the company's most recent DEF 14A filing
        2. 💰 Fetches the current market capitalization
        3. 📄 Analyzes change of control provisions for executives
        4. 📊 Calculates total payments as a % of market cap
        """)
    
    # Input section
    st.markdown("---")
    
    # Create input boxes with plus and delete buttons
    company_names = []
    for i in range(st.session_state.num_inputs):
        cols = st.columns([10, 1, 1])
        
        with cols[0]:
            company_name = st.text_input(
                f"Company {i+1}",
                key=f"company_input_{i}",
                placeholder="Enter company name",
                label_visibility="collapsed",
                disabled=st.session_state.running
            )
            company_names.append(company_name)
        
        with cols[1]:
            if i == st.session_state.num_inputs - 1:  # Only show plus on last input
                if st.button("➕", key=f"add_{i}", disabled=st.session_state.running, help="Add another company"):
                    st.session_state.num_inputs += 1
                    st.rerun()
        
        with cols[2]:
            if st.session_state.num_inputs > 1:  # Only show delete if more than one input
                if st.button("🗑️", key=f"delete_{i}", disabled=st.session_state.running, help="Remove this company"):
                    # Remove this input by decreasing count
                    st.session_state.num_inputs -= 1
                    st.rerun()
    
    # Action buttons
    st.markdown("<br>", unsafe_allow_html=True)
    button_cols = st.columns([1, 1, 3])
    
    with button_cols[0]:
        if st.button("🔍 Analyze", disabled=st.session_state.running, use_container_width=True, type="primary"):
            # Filter out empty names
            valid_names = [name for name in company_names if name.strip()]
            
            if not valid_names:
                st.error("Please enter at least one company name")
            else:
                st.session_state.running = True
                st.session_state.results = {}
                st.rerun()
    
    with button_cols[1]:
        if st.button("🗑️ Clear", disabled=not st.session_state.results, use_container_width=True):
            st.session_state.num_inputs = 1
            st.session_state.running = False
            st.session_state.results = {}
            st.rerun()
    
    # Process and display results
    if st.session_state.running:
        valid_names = [name for name in company_names if name.strip()]
        
        # Create columns for side-by-side display
        st.markdown("---")
        st.markdown("### 📊 Processing...")
        
        cols = st.columns(len(valid_names))
        
        # Create placeholders for each company
        company_containers = []
        status_placeholders = []
        
        for col, name in zip(cols, valid_names):
            with col:
                st.markdown(f'<div class="company-header">{name}</div>', unsafe_allow_html=True)
                status_placeholder = st.empty()
                status_placeholders.append(status_placeholder)
                result_container = st.container()
                company_containers.append(result_container)
        
        # Process all companies concurrently
        async def run_processing():
            results = await process_all_companies(valid_names, status_placeholders)
            return results
        
        # Run async processing
        results = asyncio.run(run_processing())
        st.session_state.results = results
        st.session_state.running = False
        st.rerun()
    
    # Display final results if available
    if st.session_state.results and not st.session_state.running:
        st.markdown("---")
        st.markdown("### 📊 Results")
        
        cols = st.columns(len(st.session_state.results))
        
        for col, (company_name, result) in zip(cols, st.session_state.results.items()):
            with col:
                display_result(company_name, result)


if __name__ == "__main__":
    main()

