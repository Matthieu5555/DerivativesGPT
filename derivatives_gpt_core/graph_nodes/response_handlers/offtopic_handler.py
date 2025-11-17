"""
Handler for off-topic requests.

Pure function - deterministic output from state.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from typing import Dict, Any

from .helpers import build_message_response, format_list_items


# ============================================================================
# OFF-TOPIC HANDLER
# ============================================================================

def handle_off_topic(state: BaseAgentState) -> Dict[str, Any]:
    """
    Handle off-topic requests.

    Pure function - takes state, returns dict.

    Politely redirects user to options pricing queries.

    Args:
        state: Current option pricing state

    Returns:
        dict: Updated messages with redirect
    """
    capabilities = [
        "Price European options using Black-Scholes",
        "Estimate volatility from Yahoo Finance data",
        "Explain option pricing concepts"
    ]

    response_text = (
        "I'm an options pricing specialist focused on European call and put options.\n\n"
        "I can help you:\n"
        f"{format_list_items(capabilities)}\n\n"
        "For other questions, please consult a general-purpose assistant.\n\n"
        "Would you like to price an option?"
    )

    return build_message_response(response_text)
