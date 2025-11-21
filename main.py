import pandas as pd
import asyncio
from ticker_finder import company_to_market_cap
from scraper import scrape_html, extract_context_around_phrases
from bs4 import BeautifulSoup
from analyze_14a import analyze
import json


async def process_first_row():
    """
    Process the first row of the Excel file:
    1. Load the Excel file
    2. Get company name and fetch market cap
    3. Scrape SEC proxy filing
    4. Analyze with OpenAI
    5. Calculate total payments / market cap
    """
    
    # Load Excel file
    print("Loading Excel file...")
    df = pd.read_excel('Proxy Ticker Segment.xlsx')
    
    # Get first row
    first_row = df.iloc[0]
    
    company_name = first_row['Company Name']
    sec_url = first_row['SEC Proxy Filing URL']
    
    print(f"\nProcessing: {company_name}")
    print(f"SEC URL: {sec_url}")
    
    # Step 1: Get market cap
    print("\n=== STEP 1: Getting Market Cap ===")
    market_cap = company_to_market_cap(company_name)
    
    if not market_cap:
        print(f"Error: Could not get market cap for {company_name}")
        return
    
    print(f"Market Cap: ${market_cap:,}")
    
    # Step 2: Scrape SEC filing
    print("\n=== STEP 2: Scraping SEC Filing ===")
    try:
        html = scrape_html(sec_url)
        
        # Parse HTML and extract text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
        
        # Extract context around "change in control" phrases
        search_phrases = ['change in control', 'change of control']
        text_blocks = extract_context_around_phrases(text, search_phrases, context_chars=1000)
        
        # Combine text blocks
        relevant_text = '\n\n'.join(text_blocks)
        
        print(f"Found {len(text_blocks)} relevant text blocks")
        print(f"Total text length: {len(relevant_text)} characters")
        
    except Exception as e:
        print(f"Error scraping SEC filing: {e}")
        return
    
    # Step 3: Analyze with OpenAI
    print("\n=== STEP 3: Analyzing with OpenAI ===")
    try:
        analysis_result = await analyze(relevant_text)
        print("Analysis result:")
        print(analysis_result)
        
    except Exception as e:
        print(f"Error analyzing text: {e}")
        return
    
    # Step 4: Parse JSON and calculate total payments
    print("\n=== STEP 4: Calculating Total Payments ===")
    try:
        # Extract JSON from response (handling markdown code blocks)
        json_str = analysis_result
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0].strip()
        
        # Parse JSON - handle both single object and array
        json_str = json_str.strip()
        
        # If it's comma-separated objects without array brackets, wrap in array
        if json_str.startswith('{') and not json_str.startswith('['):
            # Check if there are multiple JSON objects
            if '}\n{' in json_str or '},\n{' in json_str:
                json_str = '[' + json_str.replace('}\n{', '},\n{').replace('},\n{', '},\n{') + ']'
            else:
                json_str = '[' + json_str + ']'
        
        payouts = json.loads(json_str)
        
        # Calculate total
        if isinstance(payouts, dict):
            payouts = [payouts]
        
        total_payments = sum(payout.get('amount', 0) for payout in payouts)
        
        print(f"\nTotal Payments: ${total_payments:,}")
        print(f"Market Cap: ${market_cap:,}")
        
        # Calculate percentage
        percentage = (total_payments / market_cap) * 100
        
        print(f"\n{'='*60}")
        print(f"RESULT: {percentage:.4f}%")
        print(f"{'='*60}")
        print(f"\nTotal Change of Control Payments: ${total_payments:,}")
        print(f"As percentage of Market Cap: {percentage:.4f}%")
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Response was: {analysis_result}")
        return
    except Exception as e:
        print(f"Error calculating payments: {e}")
        return


if __name__ == "__main__":
    asyncio.run(process_first_row())

