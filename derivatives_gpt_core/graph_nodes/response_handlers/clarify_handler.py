"""
Handler for parameter clarification requests.

Pure function - deterministic output from state.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from typing import Dict, Any

from .helpers import build_message_response


# ============================================================================
# CLARIFICATION HANDLER
# ============================================================================

def handle_clarify_parameters(state: BaseAgentState) -> Dict[str, Any]:
    """
    Handle requests with missing pricing parameters.

    Pure function - takes state, returns dict.

    Asks for specific missing information needed for pricing.
    Shows any API errors or data issues that occurred.

    Loop protection:
    - Tracks clarification_attempts
    - Fails gracefully after max_clarification_attempts

    Args:
        state: Current option pricing state

    Returns:
        dict: Updated messages with clarification questions
    """
    # Check loop protection - increment counter
    clarification_attempts = state.clarification_attempts + 1

    # If we've reached or exceeded max attempts, show final message
    if clarification_attempts >= state.max_clarification_attempts:
        return build_message_response(
            f"I've asked for clarification {state.max_clarification_attempts} times but "
            f"still don't have enough information to proceed.\n\n"
            f"Please provide a complete pricing request like:\n"
            f'"Price a call on AAPL strike $150, expiring in 30 days"\n\n'
            f"Or type 'help' for examples.",
            clarification_attempts=clarification_attempts
        )

    # Use the LLM's reasoning from parameter extraction
    reasoning = getattr(state, 'reasoning', None) or "I need more information to price this option"

    # Build parameter status dynamically based on what's in state
    # Use getattr with None default for pricing-specific fields
    has_ticker = bool(getattr(state, 'ticker', None) or getattr(state, 'extracted_ticker', None))
    has_option_type = bool(getattr(state, 'option_type', None))
    has_strike = getattr(state, 'strike_price', None) is not None
    has_expiry = getattr(state, 'time_to_expiry_days', None) is not None

    params_status = []
    if has_ticker:
        ticker = getattr(state, 'ticker', None) or getattr(state, 'extracted_ticker', None)
        params_status.append(f"[OK] Ticker: **{ticker}**")
    if has_option_type:
        option_type = getattr(state, 'option_type', None)
        params_status.append(f"[OK] Option type: **{option_type}**")
    if has_strike:
        strike = getattr(state, 'strike_price', None)
        params_status.append(f"[OK] Strike: **{strike}**")
    if has_expiry:
        expiry = getattr(state, 'time_to_expiry_days', None)
        params_status.append(f"[OK] Expiry: **{expiry:.0f} days**")

    response_parts = [f"{reasoning}\n\n"]

    if params_status:
        response_parts.append("What I have:\n")
        response_parts.append("\n".join(params_status))
        response_parts.append("\n\n")

    response_parts.append("Please provide the missing information.")

    # Check for validation errors (which may include API errors)
    validation_errors = getattr(state, 'validation_errors', None)
    if validation_errors:
        api_warnings = []
        for error in validation_errors:
            if "API Error" in error or "unavailable" in error.lower():
                api_warnings.append(error)

        if api_warnings:
            response_parts.append("\n\n**Note:** ")
            response_parts.append("\n".join(api_warnings))

    response_text = "".join(response_parts)
    return build_message_response(response_text, clarification_attempts=clarification_attempts)


# Legacy alias for backward compatibility
handle_clarify = handle_clarify_parameters
