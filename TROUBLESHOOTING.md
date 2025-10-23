# Troubleshooting Guide

## "Could not find DEF 14A filing for this company"

This error has three possible causes, each now with a specific error message:

### 1. ❌ Company Not Found

**Error message:**

> No company found matching "[company name]". Try using the full legal name (e.g., "Apple Inc." instead of "Apple")

**What it means:**
The company name you entered doesn't match any company in the SEC database.

**Solutions:**

- ✅ Use the full legal name: "Apple Inc." not "Apple"
- ✅ Add corporate suffixes: "Microsoft Corporation" not "Microsoft"
- ✅ Check spelling carefully
- ✅ Try variations: "Meta Platforms, Inc." instead of "Meta" or "Facebook"

**Examples:**
| ❌ Won't Work | ✅ Will Work |
|--------------|-------------|
| Apple | Apple Inc. |
| Meta | Meta Platforms, Inc. |
| Google | Alphabet Inc. |
| Tesla | Tesla, Inc. |

---

### 2. ❌ No DEF 14A Filings

**Error message:**

> [Company Name] has no DEF 14A filings. This could mean the company is private, foreign, or has not filed a proxy statement recently.

**What it means:**
The company was found in the SEC database, but doesn't have any DEF 14A proxy statements on file.

**Common reasons:**

- **Private company** - Only public companies file DEF 14A
- **Foreign company** - Non-US companies may not file DEF 14A
- **Recently IPO'd** - May not have filed their first proxy yet
- **Special corporate structure** - Some companies use different filing types

**Examples of companies that won't work:**

- SpaceX (private)
- Saudi Aramco (foreign)
- Companies listed only on foreign exchanges

---

### 3. ❌ Could Not Retrieve Filings

**Error message:**

> Could not retrieve filings for [Company Name]. The SEC API may be temporarily unavailable.

**What it means:**
Network or SEC API issue.

**Solutions:**

- Wait a few seconds and try again
- Check your internet connection
- The SEC API may be under maintenance

---

## Company Search Tips

### Best Practices

✅ **DO:**

- Search for: "TreeHouse Foods"
- Search for: "Costco Wholesale"
- Search for: "Target Corporation"
- Include common suffixes like Inc., Corp., Corporation

❌ **DON'T:**

- Search for: "AAPL" (ticker symbols - use company name)
- Search for: "Apple" (too generic)
- Use abbreviations unless that's the official name

### Finding the Official Company Name

1. **Google it**: Search "[company] SEC filings"
2. **Check their website**: Look at the footer or "About" page
3. **Yahoo Finance**: The company name at the top of the page
4. **SEC.gov**: Search manually at https://www.sec.gov/edgar/search/

---

## Understanding DEF 14A

**What is DEF 14A?**

- DEF 14A = Definitive Proxy Statement
- Filed annually by public companies
- Contains executive compensation details
- Includes change of control provisions

**When are they filed?**

- Typically filed before annual shareholder meetings
- Usually once per year (April-June for most companies)
- Some companies file more frequently

**Who files DEF 14A?**

- US public companies listed on NYSE, NASDAQ, etc.
- Required by SEC for companies with registered securities
- NOT filed by:
  - Private companies
  - Foreign companies (unless also US-listed)
  - Small reporting companies (sometimes exempt)

---

## Still Having Issues?

### Quick Diagnostic

Try searching for these known working companies:

1. **TreeHouse Foods** - Should work perfectly
2. **Costco Wholesale** - Should work
3. **Target Corporation** - Should work
4. **Apple Inc.** - Should work

If these work but your company doesn't:

- Your company might be private or foreign
- Check if the company actually files with the SEC
- Visit sec.gov/edgar/search to verify manually

### Example Search Flow

```
User enters: "walmart"
❌ Not found

User enters: "Walmart"
❌ Not found

User enters: "Walmart Inc"
✅ Found! Walmart Inc.
   Ticker: WMT
   Latest DEF 14A found
```

---

## Technical Details

### How the Search Works

1. App queries SEC's company_tickers.json
2. Does case-insensitive substring match
3. Returns first match found
4. Retrieves all company filings via CIK
5. Filters for DEF 14A form type
6. Selects most recent by filing date

### Rate Limits

- SEC allows 10 requests per second
- App automatically throttles to 5 req/sec (200ms delay)
- No API key required

### Search Algorithm

```python
# Searches for substring match
"TreeHouse" matches "TreeHouse Foods, Inc." ✅
"Apple" matches "Apple Inc." ✅
"Apple" also matches "Applebee's" ⚠️ (returns first match)
```

---

## Contact & Support

If you continue having issues:

1. Check the company exists on sec.gov/edgar/search
2. Try the exact name from the SEC website
3. Verify it's a US public company
4. Check if they've filed a DEF 14A in the last 2 years
