"""
SEC EDGAR API Module
Handles company search and DEF 14A filing discovery
"""

import requests
import time
import yfinance as yf
from typing import Optional, Dict, List


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for better matching by removing punctuation and extra spaces.
    
    Args:
        name: Company name to normalize
        
    Returns:
        Normalized company name (lowercase, no punctuation, single spaces)
    """
    import re
    # Convert to lowercase
    name = name.lower()
    # Remove punctuation (commas, periods, etc.)
    name = re.sub(r'[^\w\s]', ' ', name)
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    # Strip leading/trailing spaces
    name = name.strip()
    return name


def search_company_by_ticker(ticker: str) -> Optional[Dict]:
    """
    Search for company in SEC database by ticker symbol.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "ASPN")
        
    Returns:
        Dict with 'title', 'ticker', 'cik' or None if not found
    """
    headers = {
        'User-Agent': 'Change of Control Analyzer brooks.joshua03@gmail.com',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'www.sec.gov'
    }
    
    url = "https://www.sec.gov/files/company_tickers.json"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        companies = response.json()
        
        # Search by ticker (exact match, case-insensitive)
        ticker_upper = ticker.upper().strip()
        
        for key, company in companies.items():
            if company['ticker'].upper() == ticker_upper:
                return {
                    'title': company['title'],
                    'ticker': company['ticker'],
                    'cik': str(company['cik_str']).zfill(10)
                }
        
        return None
            
    except Exception as e:
        print(f"Error searching by ticker: {e}")
        return None


def search_yahoo_finance(search_term: str) -> Optional[Dict]:
    """
    Search Yahoo Finance for company information.
    Returns ticker and official company name.
    
    Args:
        search_term: Company name, ticker, or variation
        
    Returns:
        Dict with 'ticker' and 'name' or None if not found
    """
    try:
        # Try as ticker first
        ticker = yf.Ticker(search_term)
        info = ticker.info
        
        # Check if we got valid data
        if info and 'symbol' in info and info.get('regularMarketPrice'):
            return {
                'ticker': info['symbol'],
                'name': info.get('longName') or info.get('shortName', '')
            }
    except:
        pass
    
    # Try common variations
    variations = [
        search_term,
        search_term.upper(),  # For tickers
        f"{search_term} Inc",
        f"{search_term} Inc.",
        f"{search_term} Corporation",
        f"{search_term} Corp",
    ]
    
    for variation in variations:
        try:
            ticker = yf.Ticker(variation)
            info = ticker.info
            
            if info and 'symbol' in info and info.get('regularMarketPrice'):
                return {
                    'ticker': info['symbol'],
                    'name': info.get('longName') or info.get('shortName', '')
                }
        except:
            continue
    
    return None


def search_company_cik(company_name: str, return_all_matches: bool = False) -> Optional[Dict]:
    """
    Search for company CIK using SEC's company tickers JSON file.
    
    Args:
        company_name: Name of the company to search for
        return_all_matches: If True, return all matches instead of just the first
        
    Returns:
        Dict with 'title', 'ticker', 'cik' and optionally 'all_matches' or None if not found
    """
    headers = {
        'User-Agent': 'Change of Control Analyzer brooks.joshua03@gmail.com',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'www.sec.gov'
    }
    
    url = "https://www.sec.gov/files/company_tickers.json"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        companies = response.json()
        
        # Normalize search term for better matching
        normalized_search = normalize_company_name(company_name)
        matches = []
        
        for key, company in companies.items():
            normalized_title = normalize_company_name(company['title'])
            
            # Check if normalized search is in normalized title or vice versa
            if normalized_search in normalized_title or normalized_title in normalized_search:
                matches.append({
                    'title': company['title'],
                    'ticker': company['ticker'],
                    'cik': str(company['cik_str']).zfill(10)  # Pad with zeros to 10 digits
                })
        
        if matches:
            if return_all_matches:
                return {
                    'title': matches[0]['title'],
                    'ticker': matches[0]['ticker'],
                    'cik': matches[0]['cik'],
                    'all_matches': matches
                }
            else:
                # Return the first match (usually most relevant)
                return matches[0]
        else:
            return None
            
    except Exception as e:
        print(f"Error searching for company: {e}")
        return None


def get_company_filings(cik: str) -> Optional[Dict]:
    """
    Get company filings from SEC submissions API.
    
    Args:
        cik: Company's CIK number (10 digits with leading zeros)
        
    Returns:
        Dict with company filings data or None if error
    """
    headers = {
        'User-Agent': 'Change of Control Analyzer brooks.joshua03@gmail.com',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'data.sec.gov'
    }
    
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    
    try:
        # Add delay to respect SEC rate limits (10 requests per second max)
        time.sleep(0.2)
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        print(f"Error fetching filings: {e}")
        return None


def find_latest_def14a(filings_data: Dict) -> Optional[Dict[str, str]]:
    """
    Find the most recent DEF 14A filing from the filings data.
    
    Args:
        filings_data: Company filings data from get_company_filings()
        
    Returns:
        Dict with 'filing_date', 'accession_number', and 'primary_document' or None
    """
    try:
        recent_filings = filings_data.get('filings', {}).get('recent', {})
        
        forms = recent_filings.get('form', [])
        filing_dates = recent_filings.get('filingDate', [])
        accession_numbers = recent_filings.get('accessionNumber', [])
        primary_documents = recent_filings.get('primaryDocument', [])
        
        # Find all DEF 14A filings
        def14a_filings = []
        for i, form in enumerate(forms):
            if form == 'DEF 14A':
                def14a_filings.append({
                    'filing_date': filing_dates[i],
                    'accession_number': accession_numbers[i],
                    'primary_document': primary_documents[i]
                })
        
        if def14a_filings:
            # Sort by date (most recent first)
            def14a_filings.sort(key=lambda x: x['filing_date'], reverse=True)
            return def14a_filings[0]
        else:
            return None
            
    except Exception as e:
        print(f"Error searching for DEF 14A: {e}")
        return None


def construct_document_url(cik: str, filing: Dict[str, str]) -> str:
    """
    Construct the URL to the actual DEF 14A document.
    
    Args:
        cik: Company's CIK number (10 digits)
        filing: Filing dict with 'accession_number' and 'primary_document'
        
    Returns:
        Full URL to the DEF 14A document
    """
    # Remove dashes from accession number for the URL path
    accession_no_dashes = filing['accession_number'].replace('-', '')
    
    # Remove leading zeros from CIK for URL
    cik_no_leading_zeros = cik.lstrip('0')
    
    # URL format: https://www.sec.gov/Archives/edgar/data/CIK/ACCESSIONNUMBER/PRIMARYDOCUMENT
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_no_dashes}/{filing['primary_document']}"
    
    return url


def find_def14a_url(company_name: str, verbose: bool = False) -> Optional[Dict[str, str]]:
    """
    Complete workflow: company name -> DEF 14A URL
    Uses multi-stage search:
    1. Try SEC database directly (fast)
    2. Fall back to Yahoo Finance search (handles tickers, nicknames)
    3. Use ticker to find in SEC database
    
    Args:
        company_name: Name of the company, ticker symbol, or variation
        verbose: Print progress messages
        
    Returns:
        Dict with 'url', 'company_name', 'ticker', 'filing_date', and optionally 'error_detail' 
        or None if not found
    """
    if verbose:
        print(f"Searching for DEF 14A filing for: {company_name}")
    
    # Stage 1: Try SEC database directly (fast path)
    if verbose:
        print("  Stage 1: Trying SEC database...")
    company_info = search_company_cik(company_name, return_all_matches=True)
    
    # Stage 2: If not found, try Yahoo Finance as fallback
    if not company_info:
        if verbose:
            print("  Stage 1: Not found in SEC database")
            print("  Stage 2: Trying Yahoo Finance search...")
        
        yahoo_result = search_yahoo_finance(company_name)
        
        if yahoo_result:
            if verbose:
                print(f"  Stage 2: Found on Yahoo Finance - {yahoo_result['name']} ({yahoo_result['ticker']})")
                print(f"  Stage 3: Looking up ticker {yahoo_result['ticker']} in SEC database...")
            
            # Stage 3: Use ticker to find in SEC
            company_info = search_company_by_ticker(yahoo_result['ticker'])
            
            if company_info:
                if verbose:
                    print(f"  Stage 3: Found in SEC database via ticker!")
        else:
            if verbose:
                print("  Stage 2: Not found on Yahoo Finance either")
    else:
        if verbose:
            print(f"  Stage 1: Found in SEC database!")
    
    # If still not found after all stages
    if not company_info:
        if verbose:
            print(f"❌ Company not found: {company_name}")
        return {
            'error': 'company_not_found',
            'error_detail': f'No company found matching "{company_name}". Try using the full legal name (e.g., "Apple Inc." instead of "Apple")'
        }
    
    if verbose:
        print(f"✓ Found: {company_info['title']} (Ticker: {company_info['ticker']}, CIK: {company_info['cik']})")
    
    # Step 2: Get filings
    filings_data = get_company_filings(company_info['cik'])
    if not filings_data:
        if verbose:
            print(f"❌ Could not retrieve filings")
        return {
            'error': 'filings_not_retrieved',
            'error_detail': f'Could not retrieve filings for {company_info["title"]}. The SEC API may be temporarily unavailable.',
            'company_name': company_info['title'],
            'ticker': company_info['ticker']
        }
    
    if verbose:
        print(f"✓ Retrieved filings for {filings_data.get('name', 'company')}")
    
    # Step 3: Find latest DEF 14A
    latest_def14a = find_latest_def14a(filings_data)
    if not latest_def14a:
        if verbose:
            print(f"❌ No DEF 14A filings found")
        return {
            'error': 'no_def14a',
            'error_detail': f'{company_info["title"]} has no DEF 14A filings. This could mean the company is private, foreign, or has not filed a proxy statement recently.',
            'company_name': company_info['title'],
            'ticker': company_info['ticker']
        }
    
    if verbose:
        print(f"✓ Found DEF 14A filed on {latest_def14a['filing_date']}")
    
    # Step 4: Construct URL
    document_url = construct_document_url(company_info['cik'], latest_def14a)
    
    if verbose:
        print(f"✓ Document URL: {document_url}")
    
    return {
        'url': document_url,
        'company_name': company_info['title'],
        'ticker': company_info['ticker'],
        'filing_date': latest_def14a['filing_date']
    }


if __name__ == "__main__":
    # Test with TreeHouse Foods
    result = find_def14a_url("TreeHouse Foods", verbose=True)
    if result:
        print(f"\n{'='*70}")
        print(f"SUCCESS!")
        print(f"Company: {result['company_name']}")
        print(f"Ticker: {result['ticker']}")
        print(f"Filing Date: {result['filing_date']}")
        print(f"URL: {result['url']}")
        print(f"{'='*70}")

