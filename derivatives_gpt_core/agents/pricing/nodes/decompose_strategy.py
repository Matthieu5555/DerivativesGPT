"""Extract mathematical features from multi-leg strategies."""

from derivatives_gpt_core.agents.pricing.state import PricingState
from derivatives_gpt_core.llm_provider import get_decomposer_llm
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import StrategyDecomposition
from derivatives_gpt_core.pricing_capabilities import get_tool_list_for_llm
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any
import json
import logging

# Import prompts from centralized location
from prompts.graph_nodes.strategy_decomposition_prompts import DECOMPOSER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def decompose_strategy(state: PricingState) -> Dict[str, Any]:
    """
    Decompose strategy into mathematical components.

    Purpose:
    - Identify legs for multi-leg strategies (straddle -> call + put)
    - Validate system can handle this strategy
    - Prepare for planning

    Called after: Classification and RAG retrieval
    Triggers only for: response_type="can_price"

    Args:
        state: Current state with classification results

    Returns:
        dict: Updated state with decomposition or error

    Examples:
        Single vanilla -> {"can_execute": True} (skip decomposition)
        Straddle -> {"legs": [{"type": "call", ...}, {"type": "put", ...}], "can_execute": True}
        Exotic barrier -> {"can_execute": False, "reasoning": "Barrier monitoring not supported"}
    """
    # Skip if not pricing
    if state.response_type != "can_price":
        logger.info("Not a pricing request, skipping decomposition")
        # BUG FIX: For vanilla options in pricing agent, we CAN execute even without explicit response_type
        # Don't return empty dict - this causes can_execute to be None/False, routing to exotic handler
        return {"can_execute": True}

    # Skip if already decomposed (single vanilla without multi-leg flag)
    if state.strategy_type == "single" and not state.multi_leg:
        logger.info("Single vanilla option, skipping decomposition")
        return {"can_execute": True}

    # If legs already populated by classifier, validate and pass through
    if state.legs and len(state.legs) > 0:
        logger.info(f"Legs already populated by classifier: {state.legs}")
        return {"can_execute": True}

    decomposer_model = get_decomposer_llm()
    user_query = state.messages[-1].content
    rag_context = state.reformulated_rag or ""

    # Get tool list to ground decomposer's can_decompose decision
    tool_capabilities = get_tool_list_for_llm()

    prompt = f"""## AVAILABLE PRICING TOOLS (use this to set can_decompose):
{tool_capabilities}

## RAG Context:
{rag_context}

## User Query:
{user_query}

## Classification:
Strategy Type: {state.strategy_type}
Product Type: {state.product_type}

Extract mathematical features. Set can_decompose=true ONLY if ALL legs can be priced with available tools."""

    try:
        response = await decomposer_model.ainvoke([
            SystemMessage(content=DECOMPOSER_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])

        # Parse and validate JSON response using Pydantic schema
        response_text = response.content.strip()
        validated_decomposition = extract_and_validate_with_retry(response_text, StrategyDecomposition, max_attempts=3, strict=False)

        if validated_decomposition is None:
            logger.error("Failed to extract or validate JSON from decomposer response")
            logger.error(f"Raw response (first 500 chars): {response_text[:500]}")
            # This is a TECHNICAL error (parsing failure), not a business logic error
            # Return clarify instead of refuse, with better error message
            return {
                "can_execute": False,
                "response_type": "clarify_parameters",
                "reasoning": "I encountered a technical issue analyzing this strategy. Could you rephrase your request?",
                "legs": None
            }

        if not validated_decomposition.can_decompose:
            reason = validated_decomposition.reason or "Strategy too complex"
            logger.warning(f"Cannot decompose: {reason}")
            return {
                "can_execute": False,
                "response_type": "recognize_but_refuse",
                "reasoning": reason,
                "legs": None
            }

        num_legs = len(validated_decomposition.legs) if validated_decomposition.legs else 0
        logger.info(f"Decomposition successful: {validated_decomposition.strategy_type} with {num_legs} legs")

        # Convert legs to dict format for state storage
        legs_dict = [leg.model_dump() for leg in validated_decomposition.legs] if validated_decomposition.legs else None

        return {
            "legs": legs_dict,
            "can_execute": True
        }

    except json.JSONDecodeError as e:
        logger.error(f"Decomposition JSON parsing failed: {e}")
        return {
            "can_execute": False,
            "reasoning": f"Decomposition parsing error: {str(e)}",
            "legs": None
        }

    except Exception as e:
        logger.error(f"Decomposition failed: {e}")
        return {
            "can_execute": False,
            "reasoning": f"Decomposition error: {str(e)}",
            "legs": None
        }
