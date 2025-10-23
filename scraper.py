import requests
from bs4 import BeautifulSoup


def scrape_html(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    return response.text


def extract_context_around_phrases(text, phrases, context_chars=100):

    results = []
    text_lower = text.lower()
    
    for phrase in phrases:
        phrase_lower = phrase.lower()
        start_pos = 0
        
        # Find all occurrences of the phrase
        while True:
            pos = text_lower.find(phrase_lower, start_pos)
            if pos == -1:
                break
            
            # Extract context before and after
            start = max(0, pos - context_chars)
            end = min(len(text), pos + len(phrase) + context_chars)
            
            context_block = text[start:end]
            results.append(context_block)
            
            # Move to next potential occurrence
            start_pos = pos + 1
    
    return results


def main():
    url = "https://www.sec.gov/Archives/edgar/data/1320695/000132069525000014/ths-20250301.htm"
    
    # Scrape the HTML
    html = scrape_html(url)
    
    # Parse HTML and extract text only
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up text (remove extra whitespace)
    lines = (line.strip() for line in text.splitlines())
    text = '\n'.join(line for line in lines if line)
    
    # Define phrases to search for
    search_phrases = ['change in control',]
    
    # Extract context around phrases
    text_blocks = extract_context_around_phrases(text, search_phrases, context_chars=1000)
    
    # Write to result.txt
    with open('result.txt', 'w', encoding='utf-8') as f:
        for block in text_blocks:
            f.write(block)
            f.write("\n\n")
    
    print(f"Found {len(text_blocks)} matches. Results saved to result.txt")


if __name__ == "__main__":
    main()
