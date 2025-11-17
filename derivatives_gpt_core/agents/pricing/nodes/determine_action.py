"""Determine action based on classified asset and option type."""

from derivatives_gpt_core.agents.pricing.state import PricingState
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def determine_action(state: PricingState) -> Dict[str, Any]:
    """
    Determine response_type by TRUSTING the LLM's classification.

    The LLM (classify_option_type) already told us:
    - can_price: boolean (whether we can price this)
    - option_type: string (what kind of option it is)
    - response_type: string (can be set by classifier for educational queries)

    We just use that information instead of re-implementing hardcoded rules.

    Args:
        state: State with classifications from LLM

    Returns:
        dict: {"response_type": str, "can_price": bool, ...}
    """
    option_type = state.option_type_classified
    can_price = state.can_price  # LLM already determined this!

    # Check if user forgot to specify call vs put
    if state.clarification_context == "missing_direction":
        logger.info("User did not specify call or put direction, requesting clarification")
        return {
            "response_type": "clarify_option",
            "can_price": False,
            "clarification_context": "missing_direction"
        }

    # Check if classifier already determined response_type (e.g., explain_concept)
    if state.response_type == "explain_concept":
        logger.info(f"Classifier set response_type=explain_concept, using that")
        return {
            "response_type": "explain_concept",
            "can_price": False
        }

    # Trust the LLM's classification
    if can_price:
        logger.info(f"LLM says we can price {option_type}")
        return {
            "response_type": "can_price",
            "can_price": True
        }

    # Unknown option type - ask for clarification
    if option_type == "unknown":
        logger.info("Option type unknown, requesting clarification")
        return {
            "response_type": "clarify_option",
            "can_price": False
        }

    # LLM recognized it but says we can't price it (exotic, unsupported, etc.)
    # Return "recognize_but_refuse" which shows "I can't price this but here's what I can price"
    # This is DIFFERENT from "explain_concept" which is for educational queries
    logger.info(f"LLM says we cannot price {option_type}, showing what we CAN price")
    return {
        "response_type": "recognize_but_refuse",
        "can_price": False,
        "reasoning": f"Recognized as {option_type} but cannot price"
    }
