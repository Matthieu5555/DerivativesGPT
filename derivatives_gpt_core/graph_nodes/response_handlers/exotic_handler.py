"""
Handler for exotic options that we recognize but cannot price.

Pure function - deterministic output from state.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.pricing_capabilities import PRICING_TOOLS
from typing import Dict, Any

from .helpers import build_message_response


# ============================================================================
# EXOTIC OPTIONS HANDLER
# ============================================================================

def handle_recognize_but_refuse(state: BaseAgentState) -> Dict[str, Any]:
    """
    Handle exotic options with simple, honest explanation (response formatting).

    Pure function - takes state, returns dict.

    Called by: graph routing when response_type is "recognize_but_refuse"

    Purpose: Explain why we can't price exotic derivatives and what we can do instead.

    Edge cases handled:
    - Unknown product type: Generic exotic explanation
    - Missing ticker: Still provide helpful response
    - Multiple exotic features: Mention all detected features

    Args:
        state: Current option pricing state

    Returns:
        dict: Updated messages with explanation
    """
    product_type = (state.product_type or "exotic derivative").lower()
    ticker = state.extracted_ticker or state.ticker
    features = state.features_detected or []

    # Product-specific explanations for why we can't price them (response formatting)
    # NOTE: American, Digital, Geometric Asian are now priceable and should NOT be in this list
    pricing_method_required = {
        "asian": "Monte Carlo simulation to calculate average price across random paths",
        "asian_option": "Monte Carlo simulation to calculate average price across random paths",
        "barrier": "path-dependent simulation with continuous barrier monitoring",
        "barrier_option": "path-dependent simulation with continuous barrier monitoring",
        "lookback": "path-dependent simulation tracking maximum/minimum prices",
        "lookback_option": "path-dependent simulation tracking maximum/minimum prices",
        "rainbow": "multi-dimensional Monte Carlo with correlation matrix for multiple assets",
        "rainbow_option": "multi-dimensional Monte Carlo with correlation matrix",
        "variance_swap": "variance replication using option strips and volatility modeling",
        "compound": "nested Black-Scholes with recursive valuation",
        "compound_option": "nested Black-Scholes with recursive valuation",
    }

    # Get method or use generic
    method = pricing_method_required.get(
        product_type.replace(" ", "_"),
        "advanced numerical methods not currently implemented"
    )

    # Build clean explanation (response formatting: No numbered lists!)
    response_parts = []

    # Header
    response_parts.append(
        f"I recognize this as an **{product_type.replace('_', ' ')}**."
    )

    # Why we can't price it
    response_parts.append(
        f"\n\n**Why I can't price this:**\n"
        f"This product requires {method}."
    )

    # Mention detected exotic features if any
    if features:
        feature_str = ", ".join(features)
        response_parts.append(
            f" Detected features: {feature_str}."
        )

    # What we can do instead (response formatting: Generate from actual capabilities)
    ticker_part = f" on {ticker}" if ticker else ""

    # Build list of what we CAN price from PRICING_TOOLS
    capability_lines = []
    for tool_name, tool_info in PRICING_TOOLS.items():
        if tool_info.get("can_price"):
            option_types = tool_info.get("option_types", [])
            description = tool_info.get("description", "")
            # Format nicely: "European options (vanilla_call, vanilla_put)"
            types_str = ", ".join(option_types[:3])  # Show first 3
            if len(option_types) > 3:
                types_str += f", and {len(option_types)-3} more"
            capability_lines.append(f"- {description}: {types_str}")

    capabilities_text = "\n".join(capability_lines) if capability_lines else "European call/put options"

    response_parts.append(
        f"\n\n**What I can do:**\n"
        f"I can price these option types{ticker_part}:\n{capabilities_text}"
    )

    # Friendly closing
    response_parts.append(
        "\n\nWould you like me to price a vanilla option instead?"
    )

    response = "".join(response_parts)

    return build_message_response(response, option_price=None)
