import streamlit as st
import asyncio
import pandas as pd
import io
from ticker_finder import find_ticker, get_market_cap
from scraper import scrape_html, extract_context_around_phrases
from bs4 import BeautifulSoup
from analyze_14a import analyze
from edgar_api import find_def14a_url
from database import save_analysis_result, get_top_companies
import json
from typing import Dict, Optional, List
import time
from datetime import datetime


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
    .status-pending {
        color: #666;
        font-size: 0.9rem;
    }
    .status-processing {
        color: #2c5cc5;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .status-success {
        color: #28a745;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .status-error {
        color: #dc3545;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .summary-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }
    .summary-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2c5cc5;
    }
    .summary-label {
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    /* Selector styling */
    div[data-testid="stSelectbox"] {
        background: white;
        border-radius: 8px;
        padding: 0.25rem;
    }
    div[data-testid="stSelectbox"] > div {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        border: 2px solid #2c5cc5;
        border-radius: 6px;
    }
    /* Download button styling */
    .download-btn {
        display: inline-block;
        padding: 0.5rem 1rem;
        background: linear-gradient(135deg, #2c5cc5 0%, #1e3a8a 100%);
        color: white;
        text-decoration: none;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        transition: transform 0.2s;
    }
    .download-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(44, 92, 197, 0.3);
    }
    /* Stop button styling */
    button[kind="secondary"] {
        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
    }
    button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #c82333 0%, #bd2130 100%) !important;
        box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3) !important;
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
if 'batch_running' not in st.session_state:
    st.session_state.batch_running = False
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = []
if 'batch_progress' not in st.session_state:
    st.session_state.batch_progress = {}
if 'uploaded_df' not in st.session_state:
    st.session_state.uploaded_df = None
if 'stop_requested' not in st.session_state:
    st.session_state.stop_requested = False


def log_error(company_name: str, stage: str, error_message: str, details: str = ""):
    """Log detailed error information to terminal"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "=" * 80
    print(f"\n{separator}")
    print(f"❌ ERROR | {timestamp}")
    print(f"Company: {company_name}")
    print(f"Stage: {stage}")
    print(f"Error: {error_message}")
    if details:
        print(f"Details: {details}")
    print(separator)


def log_success(company_name: str, ticker: str, percentage: float):
    """Log successful processing to terminal"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"✅ SUCCESS | {timestamp} | {company_name} ({ticker}) → {percentage:.4f}%")


async def process_company(company_name: str, status_placeholder=None) -> Dict:
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
        if status_placeholder:
            status_placeholder.info("🔄 Searching for DEF 14A filing...")
        
        filing_info = find_def14a_url(company_name, verbose=False)
        
        # Check if there was an error
        if filing_info and 'error' in filing_info:
            result['error'] = filing_info.get('error_detail', 'Could not find DEF 14A filing')
            result['company_name'] = filing_info.get('company_name', company_name)
            result['ticker'] = filing_info.get('ticker')
            if status_placeholder:
                status_placeholder.error(f"❌ {result['error']}")
            return result
        
        if not filing_info:
            result['error'] = "Could not find DEF 14A filing for this company"
            if status_placeholder:
                status_placeholder.error(f"❌ {result['error']}")
            return result
        
        result['ticker'] = filing_info['ticker']
        result['filing_date'] = filing_info['filing_date']
        result['def14a_url'] = filing_info['url']
        sec_url = filing_info['url']
        
        if status_placeholder:
            status_placeholder.success(f"✅ Found DEF 14A (Filed: {filing_info['filing_date']})")
            await asyncio.sleep(0.1)  # Brief pause for visual feedback
        
        # Step 2: Get market cap
        result['stage'] = 'fetching_market_cap'
        if status_placeholder:
            status_placeholder.info("🔄 Fetching market cap...")
        
        market_cap = get_market_cap(result['ticker'])
        if not market_cap:
            result['error'] = "Could not fetch market cap"
            if status_placeholder:
                status_placeholder.error(f"❌ {result['error']}")
            return result
        result['market_cap'] = market_cap
        
        # Show market cap
        if status_placeholder:
            status_placeholder.success(f"✅ Market Cap: ${market_cap:,}")
            await asyncio.sleep(0.1)  # Brief pause for visual feedback
        
        # Step 3: Scrape and analyze
        result['stage'] = 'fetching_coc'
        if status_placeholder:
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
                if status_placeholder:
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
            
            if status_placeholder:
                status_placeholder.success(f"✅ Analysis complete!")
        
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as parse_error:
            # Failed to parse or calculate from the analysis result
            result['error'] = "Failed to find change of control values from DEF 14A document"
            if status_placeholder:
                status_placeholder.error(f"❌ {result['error']}")
            return result
        
    except Exception as e:
        result['error'] = str(e)
        if status_placeholder:
            status_placeholder.error(f"❌ Error: {str(e)}")
    
    return result


async def process_batch_companies(company_names: List[str], progress_container, status_table_container):
    """Process companies in small batches and update progress"""
    results = []
    batch_size = 3  # Process 3 companies at a time
    total = len(company_names)
    
    # Create status tracking
    status_dict = {name: {'status': 'Pending', 'stage': '', 'percentage': None} for name in company_names}
    
    # Progress bar
    progress_bar = progress_container.progress(0)
    progress_text = progress_container.empty()
    
    for i in range(0, total, batch_size):
        # Check if stop was requested
        if st.session_state.stop_requested:
            # Mark remaining companies as cancelled
            for j in range(i, total):
                company_name = company_names[j]
                if status_dict[company_name]['status'] == 'Pending':
                    status_dict[company_name]['status'] = 'Cancelled'
                    status_dict[company_name]['stage'] = 'Stopped by user'
            
            update_status_table(status_table_container, status_dict, company_names)
            completed = len([r for r in results if r.get('percentage') is not None or r.get('error') is not None])
            progress_text.markdown(f"**⏸️ Stopped: {completed} / {total} companies completed before stop**")
            break
        
        batch = company_names[i:i+batch_size]
        batch_results = []
        
        # Update status to processing for current batch
        for company in batch:
            status_dict[company]['status'] = 'Processing'
            status_dict[company]['stage'] = 'Starting...'
        
        # Update status table
        update_status_table(status_table_container, status_dict, company_names)
        
        # Process batch concurrently
        tasks = []
        for company in batch:
            tasks.append(process_company_with_status_update(company, status_dict, status_table_container, company_names))
        
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)
        
        # Update progress
        completed = min(i + batch_size, total)
        progress = completed / total
        progress_bar.progress(progress)
        progress_text.markdown(f"**Processing: {completed} / {total} companies ({progress*100:.0f}%)**")
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < total:
            await asyncio.sleep(1)
    
    if not st.session_state.stop_requested:
        progress_text.markdown(f"**✅ Complete: {total} / {total} companies (100%)**")
    
    return results


async def process_company_with_status_update(company_name: str, status_dict: dict, status_table_container, all_companies: List[str]):
    """Process a company and update status in real-time"""
    
    # Log start of processing
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔵 START | {timestamp} | Processing: {company_name}")
    
    # Store original company name
    original_company_name = company_name
    
    # Update stages as we go
    stages = {
        'finding_def14a': 'Finding DEF 14A...',
        'fetching_market_cap': 'Fetching market cap...',
        'fetching_coc': 'Analyzing CoC...',
        'complete': 'Complete',
        'error': 'Error'
    }
    
    result = {
        'company_name': original_company_name,  # Always use the original input name
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
        status_dict[company_name]['stage'] = stages['finding_def14a']
        update_status_table(status_table_container, status_dict, all_companies)
        
        filing_info = find_def14a_url(company_name, verbose=False)
        
        if filing_info and 'error' in filing_info:
            result['error'] = filing_info.get('error_detail', 'Could not find DEF 14A filing')
            # Keep original company name, don't overwrite
            result['ticker'] = filing_info.get('ticker')
            status_dict[company_name]['status'] = 'Error'
            status_dict[company_name]['stage'] = result['error'][:50]
            update_status_table(status_table_container, status_dict, all_companies)
            
            # Log detailed error
            log_error(
                original_company_name,
                "DEF 14A Filing Search",
                result['error'],
                f"Ticker: {result['ticker'] or 'Not found'} | Error Type: {filing_info.get('error', 'Unknown')}"
            )
            return result
        
        if not filing_info:
            result['error'] = "Could not find DEF 14A filing"
            status_dict[company_name]['status'] = 'Error'
            status_dict[company_name]['stage'] = 'No DEF 14A found'
            update_status_table(status_table_container, status_dict, all_companies)
            
            log_error(
                original_company_name,
                "DEF 14A Filing Search",
                "No filing information returned",
                "The SEC EDGAR API returned no results for this company"
            )
            return result
        
        result['ticker'] = filing_info['ticker']
        result['filing_date'] = filing_info['filing_date']
        result['def14a_url'] = filing_info['url']
        sec_url = filing_info['url']
        
        # Step 2: Get market cap
        result['stage'] = 'fetching_market_cap'
        status_dict[company_name]['stage'] = stages['fetching_market_cap']
        update_status_table(status_table_container, status_dict, all_companies)
        
        market_cap = get_market_cap(result['ticker'])
        if not market_cap:
            result['error'] = "Could not fetch market cap"
            status_dict[company_name]['status'] = 'Error'
            status_dict[company_name]['stage'] = 'No market cap'
            update_status_table(status_table_container, status_dict, all_companies)
            
            log_error(
                original_company_name,
                "Market Cap Fetch",
                "Failed to retrieve market cap from Yahoo Finance",
                f"Ticker: {result['ticker']} | Filing Date: {result['filing_date']} | This could be due to: delisted stock, incorrect ticker, or API issues"
            )
            return result
        result['market_cap'] = market_cap
        
        # Step 3: Scrape and analyze
        result['stage'] = 'fetching_coc'
        status_dict[company_name]['stage'] = stages['fetching_coc']
        update_status_table(status_table_container, status_dict, all_companies)
        
        try:
            html = scrape_html(sec_url)
            if not html or len(html) < 100:
                raise ValueError("Empty or invalid HTML content received")
        except Exception as scrape_error:
            result['error'] = "Failed to scrape SEC filing"
            status_dict[company_name]['status'] = 'Error'
            status_dict[company_name]['stage'] = 'Scraping failed'
            update_status_table(status_table_container, status_dict, all_companies)
            
            log_error(
                original_company_name,
                "HTML Scraping",
                f"Failed to download or parse SEC filing: {str(scrape_error)}",
                f"URL: {sec_url} | Ticker: {result['ticker']} | This could be network issues or SEC server problems"
            )
            return result
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            for script in soup(['script', 'style']):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            text = '\n'.join(line for line in lines if line)
            
            if len(text) < 1000:
                raise ValueError(f"Document too short ({len(text)} chars), likely parsing error")
            
            search_phrases = ['change in control', 'change of control']
            text_blocks = extract_context_around_phrases(text, search_phrases, context_chars=1000)
            relevant_text = '\n\n'.join(text_blocks)
            
            if not relevant_text or len(relevant_text) < 100:
                raise ValueError(f"No 'change of control' text found in document. Document length: {len(text)} chars")
                
        except Exception as parse_error:
            result['error'] = "Failed to extract text from SEC filing"
            status_dict[company_name]['status'] = 'Error'
            status_dict[company_name]['stage'] = 'Text extraction failed'
            update_status_table(status_table_container, status_dict, all_companies)
            
            log_error(
                original_company_name,
                "Text Extraction",
                f"Failed to parse document or find CoC phrases: {str(parse_error)}",
                f"URL: {sec_url} | Ticker: {result['ticker']} | Document may not contain change of control provisions"
            )
            return result
        
        try:
            analysis_result = await analyze(relevant_text)
        except Exception as openai_error:
            result['error'] = "OpenAI analysis failed"
            status_dict[company_name]['status'] = 'Error'
            status_dict[company_name]['stage'] = 'AI analysis failed'
            update_status_table(status_table_container, status_dict, all_companies)
            
            log_error(
                original_company_name,
                "OpenAI Analysis",
                f"AI analysis failed: {str(openai_error)}",
                f"Ticker: {result['ticker']} | Relevant text length: {len(relevant_text)} chars | Check API key and rate limits"
            )
            return result
        
        try:
            json_str = analysis_result
            original_response = analysis_result[:500]  # Store first 500 chars for error logging
            
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
            
            try:
                payouts = json.loads(json_str)
            except json.JSONDecodeError as json_err:
                raise ValueError(f"JSON parsing failed: {str(json_err)}. Parsed string: {json_str[:200]}")
            
            if isinstance(payouts, dict):
                payouts = [payouts]
            
            total_payments = 0
            for payout in payouts:
                amount = payout.get('amount', 0)
                if isinstance(amount, str):
                    try:
                        amount = float(amount.replace(',', '').replace('$', ''))
                    except (ValueError, AttributeError) as amt_err:
                        log_error(
                            original_company_name,
                            "Amount Conversion",
                            f"Failed to convert amount '{amount}' to float",
                            f"Ticker: {result['ticker']} | Payout: {payout}"
                        )
                        continue
                total_payments += float(amount) if amount else 0
            
            if total_payments == 0:
                result['error'] = "Failed to find CoC values"
                status_dict[company_name]['status'] = 'Error'
                status_dict[company_name]['stage'] = 'No CoC values found'
                update_status_table(status_table_container, status_dict, all_companies)
                
                log_error(
                    original_company_name,
                    "CoC Value Extraction",
                    "Total payments calculated as $0",
                    f"Ticker: {result['ticker']} | Payouts parsed: {len(payouts)} | AI Response: {original_response}... | This could mean no payments or parsing failure"
                )
                return result
            
            percentage = (total_payments / market_cap) * 100
            
            result['total_payments'] = total_payments
            result['percentage'] = percentage
            result['payouts'] = payouts
            result['stage'] = 'complete'
            
            # Save to database
            try:
                if percentage > 0:
                    save_analysis_result(result)
                    log_success(original_company_name, result['ticker'], percentage)
            except Exception as db_error:
                log_error(
                    original_company_name,
                    "Database Save",
                    f"Failed to save to MongoDB: {str(db_error)}",
                    f"Ticker: {result['ticker']} | Percentage: {percentage:.4f}% | Check MongoDB connection"
                )
                # Don't fail the whole process, just log the error
            
            status_dict[company_name]['status'] = 'Complete'
            status_dict[company_name]['stage'] = f'{percentage:.4f}%'
            status_dict[company_name]['percentage'] = percentage
            update_status_table(status_table_container, status_dict, all_companies)
        
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as parse_error:
            result['error'] = "Failed to parse CoC values"
            status_dict[company_name]['status'] = 'Error'
            status_dict[company_name]['stage'] = 'Parse error'
            update_status_table(status_table_container, status_dict, all_companies)
            
            log_error(
                original_company_name,
                "JSON Parsing & Calculation",
                f"Failed to parse AI response or calculate values: {str(parse_error)}",
                f"Ticker: {result['ticker']} | AI Response: {original_response if 'original_response' in locals() else 'N/A'}... | Error type: {type(parse_error).__name__}"
            )
            return result
        
    except Exception as e:
        result['error'] = str(e)
        status_dict[company_name]['status'] = 'Error'
        status_dict[company_name]['stage'] = str(e)[:50]
        update_status_table(status_table_container, status_dict, all_companies)
        
        # Log unexpected errors
        log_error(
            original_company_name,
            "Unexpected Error",
            f"Unhandled exception during processing: {str(e)}",
            f"Exception type: {type(e).__name__} | Stage: {result.get('stage', 'unknown')} | Ticker: {result.get('ticker', 'N/A')}"
        )
    
    return result


def update_status_table(container, status_dict: dict, company_order: List[str]):
    """Update the status table display"""
    
    rows = []
    for company in company_order:
        status_info = status_dict[company]
        status = status_info['status']
        stage = status_info['stage']
        
        # Style based on status
        if status == 'Complete':
            status_html = f'<span class="status-success">✅ {status}</span>'
            stage_html = f'<span class="status-success">{stage}</span>'
        elif status == 'Error':
            status_html = f'<span class="status-error">❌ {status}</span>'
            stage_html = f'<span class="status-error">{stage}</span>'
        elif status == 'Processing':
            status_html = f'<span class="status-processing">🔄 {status}</span>'
            stage_html = f'<span class="status-processing">{stage}</span>'
        elif status == 'Cancelled':
            status_html = f'<span class="status-pending">⏸️ {status}</span>'
            stage_html = f'<span class="status-pending">{stage}</span>'
        else:
            status_html = f'<span class="status-pending">⏳ {status}</span>'
            stage_html = f'<span class="status-pending">-</span>'
        
        rows.append(f"<tr><td>{company}</td><td>{status_html}</td><td>{stage_html}</td></tr>")
    
    table_html = f"""
    <table class="leaderboard-table">
        <thead>
            <tr>
                <th>Company Name</th>
                <th>Status</th>
                <th>Progress</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """
    
    container.markdown(table_html, unsafe_allow_html=True)


def create_csv_from_results(successful_results: List[Dict]) -> str:
    """Create CSV content from successful results"""
    import io
    
    # Create DataFrame
    csv_data = []
    for result in successful_results:
        csv_data.append({
            'Company Name': result.get('company_name', 'N/A'),
            'Ticker': result.get('ticker', 'N/A'),
            'Percentage of Market Cap': f"{result.get('percentage', 0):.4f}%",
            'Percentage (Numeric)': result.get('percentage', 0),
            'Market Cap ($)': result.get('market_cap', 0),
            'Total CoC Payments ($)': result.get('total_payments', 0),
            'Filing Date': result.get('filing_date', 'N/A'),
            'DEF 14A URL': result.get('def14a_url', 'N/A')
        })
    
    df = pd.DataFrame(csv_data)
    
    # Sort by percentage descending
    df = df.sort_values('Percentage (Numeric)', ascending=False)
    
    # Convert to CSV
    return df.to_csv(index=False)


def display_batch_results_summary(results: List[Dict]):
    """Display summary and top N results from batch processing"""
    
    # Calculate statistics
    successful = [r for r in results if r.get('percentage') is not None]
    failed = [r for r in results if r.get('error') is not None]
    
    total = len(results)
    success_count = len(successful)
    failed_count = len(failed)
    avg_percentage = sum(r['percentage'] for r in successful) / success_count if success_count > 0 else 0
    
    # Check if processing was stopped early
    was_stopped = st.session_state.get('stop_requested', False) or (success_count + failed_count < total)
    
    # Display summary header with download button
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        if was_stopped:
            st.markdown("### 📊 Batch Processing Summary (Stopped)")
        else:
            st.markdown("### 📊 Batch Processing Summary")
    
    with header_col2:
        if successful:
            csv_content = create_csv_from_results(successful)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Export CSV",
                data=csv_content,
                file_name=f"coc_analysis_{timestamp}.csv",
                mime="text/csv",
                width='stretch',
                type="primary"
            )
    
    if was_stopped:
        st.info("⏸️ **Processing was stopped.** Results shown are for completed companies only.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    cols = st.columns(4)
    
    with cols[0]:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value">{total}</div>
            <div class="summary-label">Total</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value" style="color: #28a745;">{success_count}</div>
            <div class="summary-label">Successful</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value" style="color: #dc3545;">{failed_count}</div>
            <div class="summary-label">Failed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-value">{avg_percentage:.4f}%</div>
            <div class="summary-label">Average</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display top N results
    if successful:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # Header with selector
        header_col1, header_col2, header_col3 = st.columns([2, 1, 2])
        
        with header_col1:
            st.markdown('<div class="leaderboard-header" style="text-align: left; margin: 0;">🏆 Top Results</div>', unsafe_allow_html=True)
        
        with header_col2:
            # Selector for top N
            top_n_options = [10, 20, 50]
            # Limit options based on actual successful results
            available_options = [n for n in top_n_options if n <= success_count]
            if not available_options:
                available_options = [success_count]
            elif success_count not in available_options and success_count < 50:
                available_options.append(success_count)
                available_options.sort()
            
            top_n = st.selectbox(
                "Show top:",
                options=available_options,
                index=0,
                key="top_n_selector",
                label_visibility="collapsed"
            )
        
        with header_col3:
            st.markdown(f'<div style="text-align: right; color: #666; font-size: 0.9rem; padding-top: 0.5rem;">Showing {min(top_n, success_count)} of {success_count} successful</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Sort by percentage and get top N
        sorted_results = sorted(successful, key=lambda x: x['percentage'], reverse=True)
        top_results = sorted_results[:top_n]
        
        rows = []
        for idx, company in enumerate(top_results, 1):
            rank_class = f"rank-{idx}" if idx <= 3 else "rank-other"
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else ""
            
            company_name = company.get('company_name', 'N/A')
            ticker = company.get('ticker', 'N/A')
            percentage = company.get('percentage', 0)
            market_cap = company.get('market_cap', 0)
            doc_url = company.get('def14a_url', '')
            
            # Truncate long company names
            if len(company_name) > 45:
                company_name = company_name[:42] + "..."
            
            rows.append(f"""
            <tr>
                <td><span class="rank-badge {rank_class}">{medal if medal else idx}</span></td>
                <td><strong>{company_name}</strong></td>
                <td><span class="ticker-badge">{ticker}</span></td>
                <td><span class="percent-badge">{percentage:.4f}%</span></td>
                <td>${market_cap:,}</td>
                <td>{'<a href="' + doc_url + '" target="_blank" style="color: #2c5cc5; text-decoration: none; font-weight: 500;">📄 View Filing</a>' if doc_url else '-'}</td>
            </tr>
            """)
        
        table_html = f"""
        <div class="leaderboard-container">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th style="width: 60px;">#</th>
                        <th style="width: 35%;">Company Name</th>
                        <th style="width: 10%;">Ticker</th>
                        <th style="width: 15%;">Percentage</th>
                        <th style="width: 20%;">Market Cap</th>
                        <th style="width: 15%;">Filing</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
        
        st.markdown(table_html, unsafe_allow_html=True)
    
    # Show failed companies if any
    if failed:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(f"⚠️ View Failed Companies ({failed_count})"):
            for company in failed:
                st.text(f"• {company['company_name']}: {company.get('error', 'Unknown error')}")


def display_leaderboard():
    """Display top N companies leaderboard in compact sidebar format"""
    try:
        # Initialize session state for sidebar leaderboard count
        if 'sidebar_top_n' not in st.session_state:
            st.session_state.sidebar_top_n = 10
        
        # Selector for top N
        top_n = st.selectbox(
            "Show top:",
            options=[10, 20, 50],
            index=[10, 20, 50].index(st.session_state.sidebar_top_n) if st.session_state.sidebar_top_n in [10, 20, 50] else 0,
            key="sidebar_leaderboard_selector",
            help="Select how many companies to display"
        )
        
        st.session_state.sidebar_top_n = top_n
        
        # Fetch top N companies
        top_companies = get_top_companies(top_n)
        
        if not top_companies:
            st.caption("No companies analyzed yet.")
            return
        
        st.caption(f"Showing top {len(top_companies)} companies")
        st.markdown("---")
        
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


def manual_input_tab():
    """Display the manual input interface"""
    
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
        if st.button("🔍 Analyze", disabled=st.session_state.running, width='stretch', type="primary", key="manual_analyze"):
            # Filter out empty names
            valid_names = [name for name in company_names if name.strip()]
            
            if not valid_names:
                st.error("Please enter at least one company name")
            else:
                st.session_state.running = True
                st.session_state.results = {}
                st.rerun()
    
    with button_cols[1]:
        if st.button("🗑️ Clear", disabled=not st.session_state.results, width='stretch', key="manual_clear"):
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


def batch_upload_tab():
    """Display the batch upload interface"""
    
    st.markdown("### 📁 Batch Upload")
    st.markdown("Upload an Excel or CSV file containing company names for batch analysis.")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['xlsx', 'xls', 'csv'],
        disabled=st.session_state.batch_running,
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        try:
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.session_state.uploaded_df = df
            
            # Show preview
            st.success(f"✅ File loaded successfully! Found {len(df)} rows.")
            
            with st.expander("📋 Preview Data", expanded=True):
                st.dataframe(df.head(), width='stretch')
            
            # Column name input
            st.markdown("---")
            st.markdown("### ⚙️ Configuration")
            
            # Check if "Company Name" column exists
            default_column = "Company Name" if "Company Name" in df.columns else ""
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                column_name = st.text_input(
                    "Enter the column name containing company names:",
                    value=default_column,
                    disabled=st.session_state.batch_running,
                    placeholder="e.g., Company Name, Company, Name",
                    key="column_input"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Show Available Columns", disabled=st.session_state.batch_running):
                    st.info(f"Available columns: {', '.join(df.columns.tolist())}")
            
            if column_name:
                if column_name in df.columns:
                    # Get company names from column
                    company_names = df[column_name].dropna().astype(str).tolist()
                    company_names = [name.strip() for name in company_names if name.strip()]
                    
                    # Limit to 1298
                    if len(company_names) > 1298:
                        st.warning(f"⚠️ Found {len(company_names)} companies. Limiting to first 1298.")
                        company_names = company_names[:1298]
                    
                    st.success(f"✅ Found {len(company_names)} companies to analyze")
                    
                    # Show preview of companies
                    with st.expander("👁️ Preview Companies", expanded=False):
                        preview_cols = st.columns(3)
                        for idx, name in enumerate(company_names[:15]):
                            with preview_cols[idx % 3]:
                                st.text(f"• {name}")
                        if len(company_names) > 15:
                            st.caption(f"... and {len(company_names) - 15} more")
                    
                    # Action buttons
                    st.markdown("---")
                    button_cols = st.columns([1, 1, 3])
                    
                    with button_cols[0]:
                        if st.button(
                            "🔍 Analyze All Companies",
                            disabled=st.session_state.batch_running,
                            width='stretch',
                            type="primary",
                            key="batch_analyze"
                        ):
                            st.session_state.batch_running = True
                            st.session_state.batch_results = []
                            st.session_state.stop_requested = False  # Reset stop flag
                            st.rerun()
                    
                    with button_cols[1]:
                        if st.button(
                            "🗑️ Clear Results",
                            disabled=not st.session_state.batch_results,
                            width='stretch',
                            key="batch_clear"
                        ):
                            st.session_state.batch_running = False
                            st.session_state.batch_results = []
                            st.session_state.uploaded_df = None
                            st.rerun()
                    
                    # Process batch
                    if st.session_state.batch_running:
                        st.markdown("---")
                        
                        # Header with Stop button
                        header_col1, header_col2 = st.columns([3, 1])
                        with header_col1:
                            st.markdown("### 🔄 Processing Batch")
                        with header_col2:
                            if st.button("⏹️ Stop", type="secondary", width='stretch', key="stop_batch"):
                                st.session_state.stop_requested = True
                                st.rerun()
                        
                        progress_container = st.container()
                        st.markdown("<br>", unsafe_allow_html=True)
                        status_table_container = st.empty()
                        
                        async def run_batch():
                            results = await process_batch_companies(
                                company_names,
                                progress_container,
                                status_table_container
                            )
                            return results
                        
                        results = asyncio.run(run_batch())
                        st.session_state.batch_results = results
                        st.session_state.batch_running = False
                        st.session_state.stop_requested = False  # Reset stop flag
                        st.rerun()
                    
                    # Display results
                    if st.session_state.batch_results and not st.session_state.batch_running:
                        st.markdown("---")
                        display_batch_results_summary(st.session_state.batch_results)
                
                else:
                    st.error(f"❌ Column '{column_name}' not found in the file.")
                    st.info(f"Available columns: {', '.join(df.columns.tolist())}")
        
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
    
    else:
        # Instructions when no file is uploaded
        st.info("""
        **📝 Instructions:**
        1. Upload an Excel (.xlsx, .xls) or CSV file
        2. Enter the column name containing company names
        3. Click "Analyze All Companies" to start batch processing
        4. View results and top performers when complete
        
        **⚠️ Note:** Maximum 1298 companies per batch
        """)


def main():
    # Sidebar with leaderboard
    with st.sidebar:
        st.markdown("### 🏆 Leaderboard")
        st.markdown("---")
        display_leaderboard()
    
    # Title
    st.markdown('<h1 class="main-title">Change of Control Analyzer</h1>', unsafe_allow_html=True)
    
    # Tabs for Manual vs Batch
    tab1, tab2 = st.tabs(["✍️ Manual Input", "📁 Batch Upload"])
    
    with tab1:
        manual_input_tab()
    
    with tab2:
        batch_upload_tab()


if __name__ == "__main__":
    main()
