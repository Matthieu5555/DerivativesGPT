"""Utility functions for response formatting."""

from typing import Any


def format_pricing_response(result: dict[str, Any]) -> str:
    """
    Format graph result into user-facing response.

    Args:
        result: Graph execution result containing query_type, messages, etc.

    Returns:
        Formatted response string
    """
    if result.get("query_type") == "refuse":
        return result.get("refusal_reason", "Cannot process this request")

    # Get LLM's final message
    last_message = result["messages"][-1]
    response_text = last_message.content

    # Append price if available
    if result.get("option_price"):
        response_text += f"\n\nPrice: ${result['option_price']:.2f}"

    return response_text
