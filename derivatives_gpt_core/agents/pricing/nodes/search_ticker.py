"""Optional web search to find ticker symbol for asset name."""

from derivatives_gpt_core.agents.pricing.state import PricingState
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.utils.llm_parsing import extract_json_from_markdown
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any
import logging

# Import prompts from centralized location
from prompts.graph_nodes.ticker_search_prompts import (
    TICKER_SEARCH_DECISION_PROMPT,
    TICKER_EXTRACTION_PROMPT
)

logger = logging.getLogger(__name__)


async def search_for_ticker(state: PricingState) -> Dict[str, Any]:
    """
    Optional web search to find ticker symbol if asset name mentioned but no ticker.

    Flow:
    1. Check if we need to search (asset name but no ticker)
    2. If yes, perform web search for "[asset name] ticker symbol yahoo finance"
    3. Extract ticker from search results using LLM
    4. Update state with found ticker

    Args:
        state: State after parameter extraction

    Returns:
        dict: Updated ticker if found, or skip_ticker_search flag
    """
    ticker = state.ticker or state.extracted_ticker

    # Already have ticker? Skip search
    if ticker:
        logger.info(f"Ticker already present: {ticker}, skipping search")
        return {"skip_ticker_search": True}

    # Get user query
    user_query = state.messages[-1].content

    # Use LLM to decide if we need to search
    llm = get_classification_llm()

    decision_prompt = TICKER_SEARCH_DECISION_PROMPT.format(
        query=user_query,
        ticker=ticker or "None"
    )

    try:
        response = llm.invoke([SystemMessage(content=decision_prompt)])
        decision = extract_json_from_markdown(response.content.strip())

        if not decision or not decision.get("needs_search"):
            logger.info(f"No ticker search needed: {decision.get('reasoning') if decision else 'parsing failed'}")
            return {"skip_ticker_search": True}

        asset_name = decision.get("asset_name")
        logger.info(f"Need to search for ticker: asset_name={asset_name}")

        # Perform web search
        from tavily import TavilyClient
        from derivatives_gpt_core.config import get_settings

        settings = get_settings()
        if not settings.tavily_api_key:
            logger.warning("Tavily API key not configured, skipping ticker search")
            return {"skip_ticker_search": True}

        tavily_client = TavilyClient(api_key=settings.tavily_api_key)
        search_query = f"{asset_name} stock ticker symbol yahoo finance"

        logger.info(f"Searching: {search_query}")
        search_results = tavily_client.search(query=search_query, max_results=3)

        # Format results for LLM
        results_text = "\n\n".join([
            f"Source: {r.get('title', 'Unknown')}\n{r.get('content', '')}"
            for r in search_results.get("results", [])
        ])

        # Extract ticker using LLM
        extraction_prompt = TICKER_EXTRACTION_PROMPT.format(
            asset_name=asset_name,
            search_results=results_text[:2000]  # Limit context
        )

        response = llm.invoke([SystemMessage(content=extraction_prompt)])
        extraction = extract_json_from_markdown(response.content.strip())

        if not extraction:
            logger.error("Failed to parse ticker extraction response")
            return {"skip_ticker_search": True}

        found_ticker = extraction.get("ticker")
        confidence = extraction.get("confidence", "low")
        reasoning = extraction.get("reasoning", "")

        if found_ticker and confidence in ["high", "medium"]:
            logger.info(f"Found ticker: {found_ticker} (confidence: {confidence})")
            return {
                "extracted_ticker": found_ticker,
                "skip_ticker_search": False
            }
        else:
            logger.warning(f"Could not find ticker: {reasoning}")
            return {"skip_ticker_search": True}

    except (ValueError, KeyError, ConnectionError, TimeoutError) as e:
        # Expected errors - gracefully skip ticker search
        logger.warning(f"Ticker search unavailable: {e}")
        return {"skip_ticker_search": True}
    except Exception as e:
        # Unexpected errors - log and re-raise to surface bugs
        logger.error(f"Unexpected error in ticker search: {e}", exc_info=True)
        raise
