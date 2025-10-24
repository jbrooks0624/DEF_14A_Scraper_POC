import streamlit as st
import asyncio
from ticker_finder import find_ticker, get_market_cap
from scraper import scrape_html, extract_context_around_phrases
from bs4 import BeautifulSoup
from analyze_14a import analyze
from edgar_api import find_def14a_url
from database import save_analysis_result, get_top_companies
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
    .leaderboard-table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .leaderboard-table th {
        background: linear-gradient(135deg, #2c5cc5 0%, #1e3a8a 100%);
        color: white;
        padding: 1rem;
        text-align: left;
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .leaderboard-table td {
        padding: 0.9rem 1rem;
        border-bottom: 1px solid #f0f0f0;
        font-size: 0.95rem;
    }
    .leaderboard-table tr:hover {
        background-color: #f8f9fa;
    }
    .leaderboard-table tr:last-child td {
        border-bottom: none;
    }
    .rank-badge {
        display: inline-block;
        width: 32px;
        height: 32px;
        line-height: 32px;
        text-align: center;
        border-radius: 50%;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .rank-1 { background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%); color: #000; }
    .rank-2 { background: linear-gradient(135deg, #c0c0c0 0%, #e8e8e8 100%); color: #000; }
    .rank-3 { background: linear-gradient(135deg, #cd7f32 0%, #e8b687 100%); color: #fff; }
    .rank-other { background: #e9ecef; color: #495057; }
    .percent-badge {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .ticker-badge {
        display: inline-block;
        background: #f3e5f5;
        color: #6a1b9a;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
        font-family: monospace;
    }
    .leaderboard-header {
        text-align: center;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        color: #1f1f1f;
    }
    .leaderboard-container {
        background: #fafafa;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
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
        'filing_date': None,
        'def14a_url': None
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
        result['def14a_url'] = filing_info['url']
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
            
            # If we got 0 total, the analysis likely failed to extract values
            if total_payments == 0:
                result['error'] = "Failed to find change of control values from DEF 14A document"
                status_placeholder.error(f"❌ {result['error']}")
                return result
            
            percentage = (total_payments / market_cap) * 100
            
            result['total_payments'] = total_payments
            result['percentage'] = percentage
            result['payouts'] = payouts
            result['stage'] = 'complete'
            
            # Save to MongoDB if percentage is non-zero
            if percentage > 0:
                save_analysis_result(result)
            
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


def display_leaderboard():
    """Display top 10 companies leaderboard in compact sidebar format"""
    try:
        top_companies = get_top_companies(10)
        
        if not top_companies:
            st.caption("No companies analyzed yet.")
            return
        
        # Compact list view for sidebar
        for idx, company in enumerate(top_companies, 1):
            rank_class = f"rank-{idx}" if idx <= 3 else "rank-other"
            percent = company.get("percentage", 0)
            ticker = company.get("ticker", "N/A")
            company_name = company.get("company_name", "N/A")
            doc_url = company.get("def14a_url", "")
            
            # Shorten company name if too long
            if len(company_name) > 30:
                company_name = company_name[:27] + "..."
            
            # Create compact card
            card_html = f'''
            <div style="background: white; padding: 0.75rem; margin-bottom: 0.5rem; border-radius: 8px; border-left: 4px solid {'#ffd700' if idx == 1 else '#c0c0c0' if idx == 2 else '#cd7f32' if idx == 3 else '#e9ecef'}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                    <span class="rank-badge {rank_class}" style="font-size: 0.75rem; width: 24px; height: 24px; line-height: 24px;">{idx}</span>
                    <span style="font-size: 0.85rem; font-weight: 600; color: #1565c0;">{percent:.4f}%</span>
                </div>
                <div style="font-size: 0.8rem; font-weight: 600; color: #1f1f1f; margin-bottom: 0.2rem;">{company_name}</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="ticker-badge" style="font-size: 0.7rem; padding: 0.2rem 0.4rem;">{ticker}</span>
                    {'<a href="' + doc_url + '" target="_blank" style="color: #2c5cc5; text-decoration: none; font-size: 0.75rem;">📄 View</a>' if doc_url else ''}
                </div>
            </div>
            '''
            st.markdown(card_html, unsafe_allow_html=True)
        
    except Exception as e:
        st.caption(f"⚠️ Could not load leaderboard")


def display_result(company_name: str, result: Dict):
    """Display results for a single company"""
    # Company header
    display_name = result.get('company_name', company_name)
    st.markdown(f'<div class="company-header">{display_name}</div>', unsafe_allow_html=True)
    
    # Display DEF 14A link if available (show even if there's an error)
    if result.get('def14a_url'):
        st.markdown(f"""
            <div style="padding: 0.75rem; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #2c5cc5; margin-bottom: 1rem;">
                <div style="font-size: 0.85rem; color: #666; margin-bottom: 0.25rem;">📄 DEF 14A Proxy Statement</div>
                <a href="{result['def14a_url']}" target="_blank" style="font-size: 0.9rem; text-decoration: none; color: #2c5cc5; font-weight: 500;">
                    View SEC Filing →
                </a>
                {f'<div style="font-size: 0.8rem; color: #888; margin-top: 0.25rem;">Filed: {result["filing_date"]}</div>' if result.get('filing_date') else ''}
            </div>
        """, unsafe_allow_html=True)
    
    if result.get('error'):
        st.error(f"❌ {result['error']}")
        
        # Show helpful suggestions based on error type
        if 'not found' in result['error'].lower():
            st.info("💡 **Tip:** Try using the full legal name with 'Inc.', 'Corp.', or 'Corporation'")
        elif 'no def 14a' in result['error'].lower():
            st.info("💡 **Note:** This company may be private, foreign, or hasn't filed a proxy statement recently.")
        elif 'failed to find change of control' in result['error'].lower():
            st.info("💡 **Note:** The document was found but change of control values couldn't be extracted. You can review the document manually using the link above.")
        
        return
    
    # Ticker info
    if result.get('ticker'):
        st.caption(f"**Ticker:** {result['ticker']}")
    
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
    # Sidebar with leaderboard
    with st.sidebar:
        st.markdown("### 🏆 Top 10 Leaderboard")
        st.markdown("---")
        display_leaderboard()
    
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

