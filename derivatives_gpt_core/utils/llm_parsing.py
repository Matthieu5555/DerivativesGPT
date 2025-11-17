"""
Robust parsing utilities for LLM outputs.

BACKWARD COMPATIBILITY WRAPPER
This module re-exports from derivatives_gpt_core.utils.llm_parsing for backward compatibility.
All implementation has been split into focused modules by concern.

This module provides utilities to parse LLM responses that may contain:
- JSON in markdown code blocks
- Percentages in various formats
- Prices in various formats
- Extra prose before/after structured data

All functions are defensive and use multiple fallback strategies.

Module structure:
- llm_parsing/json_extraction.py: Pure JSON extraction
- llm_parsing/text_parsers.py: Pure text parsing (%, $)
- llm_parsing/validation.py: Pydantic validation
"""

# Re-export all public API from llm_parsing subpackage
from .llm_parsing import (
    extract_json_from_markdown,
    is_valid_json,
    parse_percentage_from_text,
    extract_price_from_message,
    extract_and_validate,
    extract_and_validate_with_retry,
)

__all__ = [
    "extract_json_from_markdown",
    "is_valid_json",
    "parse_percentage_from_text",
    "extract_price_from_message",
    "extract_and_validate",
    "extract_and_validate_with_retry",
]
