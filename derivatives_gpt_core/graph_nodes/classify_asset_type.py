"""Classify asset type based on augmented context."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import AssetTypeClassification
from prompts.classification import ASSET_CLASSIFICATION_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


async def classify_asset_type(state: BaseAgentState) -> Dict[str, Any]:
    """
    Classify asset type using augmented context.
    
    Args:
        state: State with RAG + web search context
    
    Returns:
        dict: {"asset_type_classified": str, ...}
    """
    try:
        # Build context from RAG + web search
        context_parts = []
        
        if state.reformulated_rag:
            context_parts.append(f"RAG Context:\n{state.reformulated_rag}")
        
        if state.web_search_results:
            web_content = "\n".join([
                f"- {r['title']}: {r['content'][:200]}"
                for r in state.web_search_results[:2]
            ])
            context_parts.append(f"Web Search:\n{web_content}")
        
        context = "\n\n".join(context_parts) if context_parts else "No context available"
        
        # Get user query
        user_query = ""
        if state.messages:
            from langchain_core.messages import HumanMessage as HM
            for msg in reversed(state.messages):
                if isinstance(msg, HM):
                    user_query = msg.content
                    break
        
        # LLM classification
        llm = get_classification_llm()

        prompt = f"""{ASSET_CLASSIFICATION_PROMPT}

## User Query
{user_query}

## Additional Context
{context[:1500]}

Classify the asset type and return ONLY valid JSON."""

        response = llm.invoke([SystemMessage(content=prompt)])

        validated_result = extract_and_validate_with_retry(response.content.strip(), AssetTypeClassification, max_attempts=3, strict=False)

        if not validated_result:
            raise ValueError("Failed to parse or validate asset classification JSON")

        logger.info(f"Asset type classified as: {validated_result.asset_type}, reasoning: {validated_result.reasoning}")

        return {
            "asset_type_classified": validated_result.asset_type,
            "asset_class": validated_result.asset_type  # Also update legacy field
        }
    
    except Exception as e:
        logger.error(f"Asset classification failed: {e}")
        return {
            "asset_type_classified": "unknown",
            "asset_class": "unknown"
        }
