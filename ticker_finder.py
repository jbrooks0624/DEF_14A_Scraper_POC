import requests
import json
import yfinance as yf
from difflib import SequenceMatcher


def get_ticker_from_sec(company_name):
    """Use SEC EDGAR to find ticker with fuzzy matching"""
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {'User-Agent': 'brooks.joshua03@gmail.com'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        companies = response.json()
        
        # Normalize search term - remove common suffixes
        company_name_lower = company_name.lower().strip()
        company_name_clean = company_name_lower.replace("inc.", "").replace("inc", "").replace("corp.", "").replace("corp", "").replace("ltd.", "").replace("ltd", "").replace(",", "").strip()
        
        best_match = None
        best_ratio = 0
        
        # Search through companies with fuzzy matching
        for key, company in companies.items():
            company_title = company['title'].lower()
            company_title_clean = company_title.replace("inc.", "").replace("inc", "").replace("corp.", "").replace("corp", "").replace("ltd.", "").replace("ltd", "").replace(",", "").strip()
            
            # Check for exact substring match first
            if company_name_clean in company_title_clean or company_title_clean in company_name_clean:
                return company['ticker']
            
            # Calculate similarity ratio using SequenceMatcher
            ratio = SequenceMatcher(None, company_name_clean, company_title_clean).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = company
        
        # Return best match if similarity is above threshold (70%)
        if best_ratio > 0.7 and best_match:
            return best_match['ticker']
            
    except Exception as e:
        print(f"SEC lookup failed: {e}")
    
    return None


def get_ticker_yahoo_search(company_name):
    """Search Yahoo Finance for ticker symbol"""
    try:
        # Try direct ticker lookup first
        ticker = yf.Ticker(company_name)
        info = ticker.info
        
        if info and 'symbol' in info and info.get('regularMarketPrice'):
            return info['symbol']
    except:
        pass
    
    # Try with common suffixes removed
    clean_name = company_name.replace(" Inc.", "").replace(" Inc", "").replace(" Corp.", "").replace(" Corp", "").replace(" Ltd.", "").replace(" Ltd", "").strip()
    try:
        ticker = yf.Ticker(clean_name)
        info = ticker.info
        if info and 'symbol' in info and info.get('regularMarketPrice'):
            return info['symbol']
    except:
        pass
    
    return None


def find_ticker(company_name, verbose=False):
    """Find ticker using multiple methods with fallback"""
    if verbose:
        print(f"Searching for: {company_name}")
    
    # Method 1: Try SEC lookup (most reliable for US companies)
    if verbose:
        print("Trying SEC lookup...")
    ticker = get_ticker_from_sec(company_name)
    if ticker:
        if verbose:
            print(f"✓ Found via SEC: {ticker}")
        return ticker
    
    # Method 2: Try Yahoo Finance
    if verbose:
        print("Trying Yahoo Finance...")
    ticker = get_ticker_yahoo_search(company_name)
    if ticker:
        if verbose:
            print(f"✓ Found via Yahoo: {ticker}")
        return ticker
    
    if verbose:
        print("✗ No ticker found")
    return None


def get_market_cap(ticker_symbol, verbose=False):
    """Get market cap for a company by ticker symbol"""
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        market_cap = info.get('marketCap')
        
        if market_cap:
            return market_cap
        else:
            if verbose:
                print(f"Market cap not available for {ticker_symbol}")
            return None
    except Exception as e:
        if verbose:
            print(f"Error getting market cap: {e}")
        return None


def company_to_market_cap(company_name):
    """Complete workflow: company name -> ticker -> market cap"""
    ticker = find_ticker(company_name)
    
    if not ticker:
        return None
    
    print(f"\nFetching market cap for {ticker}...")
    market_cap = get_market_cap(ticker)
    
    if market_cap:
        print(f"Market Cap: ${market_cap:,}")
        return market_cap
    
    return None


if __name__ == "__main__":
    # Test with different company names
    company_to_market_cap("Mesa Laboratorty")
