"""Classify option type based on asset and augmented context."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import OptionTypeClassification
from derivatives_gpt_core.pricing_capabilities import get_tool_list_for_llm
from prompts.classification import OPTION_CLASSIFICATION_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


async def classify_option_type(state: BaseAgentState) -> Dict[str, Any]:
    """
    Classify option type using asset type + augmented context.
    
    Args:
        state: State with asset_type_classified and context
    
    Returns:
        dict: {"option_type_classified": str, ...}
    """
    try:
        # Build context
        context_parts = []
        
        if state.reformulated_rag:
            context_parts.append(f"RAG Context:\n{state.reformulated_rag}")
        
        if state.web_search_results:
            web_content = "\n".join([
                f"- {r['title']}: {r['content'][:200]}"
                for r in state.web_search_results[:2]
            ])
            context_parts.append(f"Web Search:\n{web_content}")
        
        context = "\n\n".join(context_parts) if context_parts else "No context"
        
        # Get user query
        user_query = ""
        if state.messages:
            from langchain_core.messages import HumanMessage as HM
            for msg in reversed(state.messages):
                if isinstance(msg, HM):
                    user_query = msg.content
                    break
        
        asset_type = state.asset_type_classified or "equity"

        # LLM classification
        llm = get_classification_llm()

        # Get tool list to ground LLM's can_price decision in reality
        tool_capabilities = get_tool_list_for_llm()

        prompt = f"""{OPTION_CLASSIFICATION_PROMPT}

## AVAILABLE PRICING TOOLS (use this to determine can_price):
{tool_capabilities}

## User Query
{user_query}

## Asset Type
{asset_type}

## Additional Context
{context[:1500]}

Classify the option type and return ONLY valid JSON. Use the AVAILABLE PRICING TOOLS list above to accurately set can_price=true ONLY if we have a tool for this option type."""

        response = llm.invoke([SystemMessage(content=prompt)])

        validated_result = extract_and_validate_with_retry(response.content.strip(), OptionTypeClassification, max_attempts=3, strict=False)

        if not validated_result:
            raise ValueError("Failed to parse or validate option type classification JSON")

        logger.info(f"Option type classified as: {validated_result.option_type}, reasoning: {validated_result.reasoning}, can_price: {validated_result.can_price}, missing_direction: {validated_result.missing_direction}")

        # Map option_type to strategy_type for decomposer routing
        option_type_lower = validated_result.option_type.lower()
        if "straddle" in option_type_lower:
            strategy_type = "straddle"
        elif "strangle" in option_type_lower:
            strategy_type = "strangle"
        elif "spread" in option_type_lower:
            strategy_type = "spread"
        elif "butterfly" in option_type_lower:
            strategy_type = "butterfly"
        else:
            # Vanilla calls/puts and all other single-asset options
            strategy_type = "single"

        result = {
            "option_type_classified": validated_result.option_type,
            "product_type": validated_result.option_type,  # Also update legacy field
            "strategy_type": strategy_type,  # CRITICAL: Set strategy_type for decomposer routing
            "features_detected": validated_result.features_detected,
            "can_price": validated_result.can_price,
            "clarification_context": "missing_direction" if validated_result.missing_direction else None
        }

        # Pass through response_type if set (e.g., "explain_concept" for educational queries)
        if validated_result.response_type:
            result["response_type"] = validated_result.response_type
            logger.info(f"Setting response_type={validated_result.response_type}")

        return result
    
    except Exception as e:
        logger.error(f"Option type classification failed: {e}")
        return {
            "option_type_classified": "unknown",
            "product_type": "unknown"
        }
