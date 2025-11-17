"""
Web Search Prompts

Used by web_search node to formulate search queries for exotic derivatives.
"""

SEARCH_QUERY_PROMPT = """Based on the RAG content below, formulate ONE web search query to clarify EXOTIC or COMPLEX derivative concepts that need clarification.

IMPORTANT:
- ONLY search for exotic/complex derivatives (Asian, barrier, quanto, lookback, compound, rainbow, etc.)
- DO NOT search for vanilla options (simple European/American calls/puts)
- DO NOT search for standard strategies (straddle, strangle, spread, butterfly)
- If the query is about a vanilla option, return "NONE"

RAG Content:
{rag_content}

User Query:
{user_query}

Return ONLY the search query, no explanation. If no search needed or query is about vanilla options, return "NONE"."""
