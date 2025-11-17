"""
Response handlers for different classification outcomes.

BACKWARD COMPATIBILITY WRAPPER
This module re-exports from derivatives_gpt_core.graph_nodes.response_handlers for backward compatibility.
All implementation has been split into focused modules by handler type.

Module structure:
- response_handlers/helpers.py: Pure helper functions
- response_handlers/exotic_handler.py: Exotic options handler
- response_handlers/clarify_handler.py: Parameter clarification handler
- response_handlers/offtopic_handler.py: Off-topic redirect handler
- response_handlers/educational_handler.py: Educational concept handler
"""

# Re-export all public API from response_handlers subpackage
from .response_handlers import (
    build_message_response,
    format_list_items,
    handle_recognize_but_refuse,
    handle_clarify_parameters,
    handle_clarify,
    handle_off_topic,
    handle_explain_concept,
)

__all__ = [
    "build_message_response",
    "format_list_items",
    "handle_recognize_but_refuse",
    "handle_clarify_parameters",
    "handle_clarify",
    "handle_off_topic",
    "handle_explain_concept",
]
