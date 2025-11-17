"""
Response handlers for different classification outcomes.

Pure functions that take state and return response dicts.
Each handler corresponds to a specific classification outcome.

Public API:
- build_message_response(): Helper to build response dicts
- format_list_items(): Helper to format markdown lists
- handle_recognize_but_refuse(): Exotic options we can't price
- handle_clarify_parameters(): Ask for missing parameters
- handle_clarify: Legacy alias for handle_clarify_parameters
- handle_off_topic(): Redirect off-topic queries
- handle_explain_concept(): Educational concept explanations

Module structure:
- helpers.py: Pure helper functions
- exotic_handler.py: Recognize but refuse handler
- clarify_handler.py: Parameter clarification handler
- offtopic_handler.py: Off-topic redirect handler
- educational_handler.py: Concept explanation handler
"""

# Helper functions
from .helpers import (
    build_message_response,
    format_list_items,
)

# Handler functions
from .exotic_handler import handle_recognize_but_refuse
from .clarify_handler import handle_clarify_parameters, handle_clarify
from .offtopic_handler import handle_off_topic
from .educational_handler import handle_explain_concept

__all__ = [
    "build_message_response",
    "format_list_items",
    "handle_recognize_but_refuse",
    "handle_clarify_parameters",
    "handle_clarify",
    "handle_off_topic",
    "handle_explain_concept",
]
