"""
Completion and failure handlers for pricing workflow.

This module contains handlers that generate final responses
after validation failures or successful pricing completion.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from langchain_core.messages import AIMessage
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def handle_validation_failure(state: BaseAgentState) -> Dict[str, Any]:
    """
    Handle validation failures by explaining errors to user.

    Separates critical errors from warnings and formats them
    into a user-friendly message.

    Args:
        state: Current state with validation_errors

    Returns:
        dict: Updated messages with error explanation
    """
    errors = state.validation_errors or []

    # Separate critical errors from warnings
    critical_errors = [e for e in errors if not e.startswith(('WARNING:', 'INFO:'))]
    warnings = [e for e in errors if e.startswith(('WARNING:', 'INFO:'))]

    response_parts = ["I found some issues with the pricing parameters:\n"]

    if critical_errors:
        response_parts.append("**Errors:**")
        for error in critical_errors:
            response_parts.append(f"- {error}")

    if warnings:
        response_parts.append("\n**Warnings:**")
        for warning in warnings:
            response_parts.append(f"- {warning}")

    response_parts.append("\nPlease correct these issues and try again.")

    response_text = "\n".join(response_parts)

    return {
        "messages": [AIMessage(content=response_text)]
    }


def handle_pricing_complete(state: BaseAgentState) -> Dict[str, Any]:
    """
    Generate final pricing response for single options.

    Called after successful execution and validation.
    Formats the pricing result with all relevant details.

    Args:
        state: Current state with pricing results

    Returns:
        dict: Updated messages with pricing result
    """
    price = state.option_price
    option_type = state.option_type
    ticker = state.ticker or state.extracted_ticker or "the underlying"
    strike = state.strike_price
    expiry = state.time_to_expiry_days

    if price is None:
        return {
            "messages": [AIMessage(content="Pricing calculation completed but no price was generated.")]
        }

    response = (
        f"The {option_type} option on {ticker} "
        f"(strike ${strike:.2f}, {expiry:.0f} days to expiry) "
        f"is priced at **${price:.2f}**"
    )

    # Add warnings if any
    if state.validation_warnings:
        response += "\n\n**Notes:**"
        for warning in state.validation_warnings:
            response += f"\n- {warning}"

    return {
        "messages": [AIMessage(content=response)]
    }
