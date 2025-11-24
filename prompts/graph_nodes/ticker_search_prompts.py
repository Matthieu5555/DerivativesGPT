"""
Ticker Search Prompts

Used by search_ticker node to decide if web search is needed and to extract ticker from search results.
"""

TICKER_SEARCH_DECISION_PROMPT = """You decide if we need to search for a ticker symbol.

User query: {query}

Current state:
- Ticker extracted: {ticker}
- Asset mentioned: Check if query mentions a company/asset name

Output ONLY valid JSON:
{
    "needs_search": boolean,
    "asset_name": string | null,
    "reasoning": string
}

Examples:

Query: "Price a call on Apple"
{
    "needs_search": true,
    "asset_name": "Apple",
    "reasoning": "User mentioned 'Apple' but no ticker was extracted"
}

Query: "Price a call on AAPL"
{
    "needs_search": false,
    "asset_name": null,
    "reasoning": "Ticker 'AAPL' is already present"
}

Query: "What is an option?"
{
    "needs_search": false,
    "asset_name": null,
    "reasoning": "This is an educational query, no ticker needed"
}"""

TICKER_EXTRACTION_PROMPT = """Extract the Yahoo Finance ticker symbol from web search results.

Asset name: {asset_name}

Web search results:
{search_results}

Output ONLY valid JSON:
{
    "ticker": string | null,
    "confidence": "high" | "medium" | "low",
    "reasoning": string
}

Examples:

Asset: "Apple"
Results: "Apple Inc. (NASDAQ: AAPL) is a technology company..."
{
    "ticker": "AAPL",
    "confidence": "high",
    "reasoning": "Found clear ticker symbol AAPL for Apple Inc. on NASDAQ"
}

Asset: "Tesla"
Results: "Tesla, Inc. trades on Nasdaq under ticker TSLA"
{
    "ticker": "TSLA",
    "confidence": "high",
    "reasoning": "Found ticker TSLA for Tesla on Nasdaq"
}

Asset: "Berkshire Hathaway"
Results: "Berkshire Hathaway Class A (BRK.A) and Class B (BRK.B) shares..."
{
    "ticker": "BRK.B",
    "confidence": "medium",
    "reasoning": "Found two tickers, defaulting to more liquid Class B shares"
}"""
