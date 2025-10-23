# Change of Control Analyzer

A Streamlit application that automatically analyzes DEF 14A filings to calculate change of control payments as a percentage of market capitalization.

## Features

✅ **No Excel Required** - Just enter a company name  
✅ **Automatic DEF 14A Discovery** - Uses SEC EDGAR API to find the most recent filing  
✅ **Market Cap Lookup** - Fetches current market capitalization  
✅ **AI-Powered Analysis** - Uses OpenAI to extract change of control payment information  
✅ **Multi-Company Support** - Analyze multiple companies simultaneously  
✅ **Real-Time Processing** - See progress as the app searches and analyzes

## How It Works

1. **Company Search**: Enter a company name (e.g., "TreeHouse Foods")
2. **DEF 14A Discovery**: The app searches SEC EDGAR for the most recent DEF 14A filing
3. **Market Cap Fetch**: Retrieves current market capitalization from Yahoo Finance
4. **Document Scraping**: Downloads and parses the DEF 14A HTML document
5. **AI Analysis**: Extracts change of control payments for executives using OpenAI
6. **Calculation**: Computes total payments as a percentage of market cap

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
# Create a .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

## Usage

### Run the Streamlit App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### Using the Interface

1. Enter one or more company names in the input boxes
2. Click the ➕ button to add more companies
3. Click 🔍 **Analyze** to start processing
4. View results showing:
   - Market capitalization
   - Total change of control payments
   - Individual executive payouts (expandable)
   - **Final percentage** of market cap

### Example Companies to Try

- TreeHouse Foods
- Apple Inc
- Microsoft Corporation
- Tesla Inc

## File Structure

```
scraper/
├── app.py              # Main Streamlit application
├── edgar_api.py        # SEC EDGAR API integration
├── ticker_finder.py    # Company ticker and market cap lookup
├── scraper.py          # HTML scraping utilities
├── analyze_14a.py      # OpenAI analysis logic
├── main.py            # Legacy CLI script
├── requirements.txt    # Python dependencies
└── .env               # Environment variables (create this)
```

## Module Details

### edgar_api.py

- `search_company_cik(company_name)` - Find company CIK from name
- `get_company_filings(cik)` - Retrieve all company filings
- `find_latest_def14a(filings_data)` - Locate most recent DEF 14A
- `construct_document_url(cik, filing)` - Build URL to document
- `find_def14a_url(company_name)` - Complete workflow function

### ticker_finder.py

- `find_ticker(company_name)` - Get ticker symbol
- `get_market_cap(ticker_symbol)` - Fetch market capitalization

### scraper.py

- `scrape_html(url)` - Download HTML content
- `extract_context_around_phrases(text, phrases)` - Find relevant text blocks

### analyze_14a.py

- `analyze(text)` - Use OpenAI to extract payment information

## API Usage & Compliance

### SEC EDGAR API

- Rate limit: 10 requests per second (automatically throttled)
- User-Agent: Includes contact email
- No API key required

### Yahoo Finance (via yfinance)

- Used for market cap data
- No API key required

### OpenAI API

- Requires API key (set in .env)
- Model: gpt-5-mini
- Used for text analysis

## Error Handling

The app handles common errors gracefully:

- Company not found in SEC database
- No DEF 14A filings available
- Market cap unavailable
- Network timeouts
- API rate limiting

## Notes

- The app searches for **DEF 14A** (Definitive Proxy Statement) filings specifically
- Only analyzes change of control provisions
- Results show the most recent filing available
- Payment amounts are extracted using AI and may require manual verification

## License

This project is for educational and research purposes.

## Support

For issues or questions, please refer to the code comments or contact the developer.
