"""Web search node using Tavily API."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.config import get_settings
from langchain_core.messages import SystemMessage, HumanMessage
from tavily import TavilyClient
from typing import Dict, Any
import logging

# Import prompts from centralized location
from prompts.graph_nodes.web_search_prompts import SEARCH_QUERY_PROMPT

logger = logging.getLogger(__name__)


async def web_search(state: BaseAgentState) -> Dict[str, Any]:
    """
    Perform web search using Tavily to augment RAG context.

    Steps:
    1. LLM formulates search query based on RAG gaps
    2. Execute Tavily search (if enabled in .env)
    3. Store results

    Args:
        state: Current graph state with reformulated_rag

    Returns:
        dict: {"web_search_results": list, "web_search_query": str}
    """
    settings = get_settings()

    # Check if web search enabled
    if not settings.enable_web_search:
        logger.info("Web search disabled in config")
        return {"web_search_results": [], "web_search_query": ""}

    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured")
        return {"web_search_results": [], "web_search_query": ""}

    try:
        # Extract user query
        user_query = ""
        if state.messages:
            from langchain_core.messages import HumanMessage as HM
            for msg in reversed(state.messages):
                if isinstance(msg, HM):
                    user_query = msg.content
                    break

        # Skip web search for simple vanilla options (optimization)
        vanilla_keywords = ["vanilla", "european call", "european put", "american call", "american put"]
        user_query_lower = user_query.lower()
        if any(kw in user_query_lower for kw in vanilla_keywords):
            logger.info("Query mentions vanilla options, skipping web search")
            return {"web_search_results": [], "web_search_query": ""}

        # Skip if no RAG content
        if not state.reformulated_rag:
            logger.info("No RAG content to base search on, skipping web search")
            return {"web_search_results": [], "web_search_query": ""}

        # LLM formulates search query
        llm = get_classification_llm()
        response = llm.invoke([
            SystemMessage(content=SEARCH_QUERY_PROMPT.format(
                rag_content=state.reformulated_rag[:500],  # First 500 chars
                user_query=user_query
            ))
        ])

        search_query = response.content.strip()

        if search_query == "NONE" or not search_query:
            logger.info("LLM determined no web search needed")
            return {"web_search_results": [], "web_search_query": ""}

        # Execute Tavily search (max 1 search)
        client = TavilyClient(api_key=settings.tavily_api_key)
        search_response = client.search(
            query=search_query,
            max_results=3,  # Top 3 results
            search_depth="basic"
        )

        results = []
        for result in search_response.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0.0)
            })

        logger.info(f"Web search for '{search_query}' returned {len(results)} results")

        return {
            "web_search_results": results,
            "web_search_query": search_query
        }

    except Exception as e:
        logger.error(f"Web search failed: {e}", exc_info=True)
        return {"web_search_results": [], "web_search_query": ""}
