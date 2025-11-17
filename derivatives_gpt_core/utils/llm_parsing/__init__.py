"""
Robust parsing utilities for LLM outputs.

This module provides utilities to parse LLM responses that may contain:
- JSON in markdown code blocks
- Percentages in various formats
- Prices in various formats
- Extra prose before/after structured data

All functions are defensive and use multiple fallback strategies.

Public API:
- extract_json_from_markdown(): Extract JSON from markdown/prose
- is_valid_json(): Quick sanity check for JSON
- parse_percentage_from_text(): Extract percentage values
- extract_price_from_message(): Extract price values
- extract_and_validate(): Extract + validate against Pydantic model
- extract_and_validate_with_retry(): Extract + validate with retry logic

Module structure:
- json_extraction.py: Pure JSON extraction functions
- text_parsers.py: Pure text parsing functions (%, $)
- validation.py: Pydantic validation functions
"""

# JSON extraction functions
from .json_extraction import (
    extract_json_from_markdown,
    is_valid_json,
)

# Text parsing functions
from .text_parsers import (
    parse_percentage_from_text,
    extract_price_from_message,
)

# Validation functions
from .validation import (
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
