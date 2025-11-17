"""
Pure helper functions for response building.

All functions are pure - no side effects, deterministic output.
"""

from langchain_core.messages import AIMessage
from typing import Dict, List, Any


# ============================================================================
# PURE HELPER FUNCTIONS
# ============================================================================

def build_message_response(content: str, **kwargs) -> Dict[str, Any]:
    """
    Build a standard message response dict (DRY helper).

    Pure function - same inputs always produce same output.

    Args:
        content: Message content text
        **kwargs: Additional fields to include in response

    Returns:
        dict: Response with messages and optional fields

    Example:
        >>> build_message_response("Hello", option_price=None)
        {"messages": [AIMessage(content="Hello")], "option_price": None}
    """
    response = {"messages": [AIMessage(content=content)]}
    response.update(kwargs)
    return response


def format_list_items(items: List[str], prefix: str = "-") -> str:
    """
    Format list of items as markdown list.

    Pure function - deterministic output.

    Args:
        items: List of items to format
        prefix: List prefix character (default "-")

    Returns:
        str: Formatted list as string

    Example:
        >>> format_list_items(["Item 1", "Item 2"])
        "- Item 1\n- Item 2"
    """
    return "\n".join(f"{prefix} {item}" for item in items)
