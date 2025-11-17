"""RAG retrieval with LLM reformulation for context augmentation."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.rag.hybrid_retriever import get_rag_retriever
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.config import get_settings
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any
import logging

# Import prompts from centralized location
from prompts.graph_nodes.context_reformulation_prompts import REFORMULATION_PROMPT

logger = logging.getLogger(__name__)


async def augment_with_context(state: BaseAgentState) -> Dict[str, Any]:
    """
    Retrieve and reformulate RAG context.

    Steps:
    1. Retrieve RAG chunks using hybrid search
    2. LLM reformulates to extract only relevant content
    3. Stores both raw and reformulated results

    Args:
        state: Current graph state with user query

    Returns:
        dict: {"rag_sources": list, "rag_query": str, "reformulated_rag": str}
    """
    settings = get_settings()

    # Check if RAG enabled
    if not settings.rag_enabled:
        logger.info("RAG disabled in config, skipping retrieval")
        return {"rag_sources": [], "rag_query": "", "reformulated_rag": ""}

    try:
        # Extract user query
        query = ""
        if state.messages:
            from langchain_core.messages import HumanMessage as HM
            for msg in reversed(state.messages):
                if isinstance(msg, HM):
                    query = msg.content
                    break

        if not query:
            logger.warning("No user query found")
            return {"rag_sources": [], "rag_query": "", "reformulated_rag": ""}

        # Retrieve RAG sources
        retriever = get_rag_retriever()
        sources = retriever.retrieve(query)

        if not sources:
            logger.info("No RAG sources retrieved")
            return {"rag_sources": [], "rag_query": query, "reformulated_rag": ""}

        # Reformulate RAG content with LLM
        chunks_text = "\n\n".join([
            f"Chunk {i+1} (from {src.get('book', 'Unknown')}, page {src.get('page', '?')}):\n{src['text']}"
            for i, src in enumerate(sources[:3])  # Top 3 chunks
        ])

        llm = get_classification_llm()
        response = llm.invoke([
            SystemMessage(content=REFORMULATION_PROMPT.format(query=query, chunks=chunks_text))
        ])

        reformulated = response.content.strip()

        logger.info(f"RAG retrieved {len(sources)} sources, reformulated to {len(reformulated)} chars")

        return {
            "rag_sources": sources,
            "rag_query": query,
            "reformulated_rag": reformulated
        }

    except FileNotFoundError as e:
        logger.warning(f"RAG vectorstore not found: {e}")
        return {"rag_sources": [], "rag_query": "", "reformulated_rag": ""}

    except Exception as e:
        logger.error(f"RAG retrieval/reformulation failed: {e}", exc_info=True)
        return {"rag_sources": [], "rag_query": "", "reformulated_rag": ""}
