"""
Pure JSON extraction functions for LLM outputs.

All functions are pure - no side effects, deterministic output.
"""

import re
import json
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PURE JSON EXTRACTION FUNCTIONS
# ============================================================================

def extract_json_from_markdown(text: str) -> Optional[dict]:
    """
    Extract JSON from LLM response that may contain markdown and prose.

    Tries multiple strategies in order:
    1. Direct JSON parsing (no markdown)
    2. Extract from markdown code blocks (all blocks, prefer later ones)
    3. Find JSON object with regex (outermost braces)

    Args:
        text: LLM response text

    Returns:
        Parsed JSON dict or None if all strategies fail

    Examples:
        >>> extract_json_from_markdown('{"key": "value"}')
        {'key': 'value'}

        >>> extract_json_from_markdown('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}

        >>> extract_json_from_markdown('Here is the result:\\n```\\n{"key": "value"}\\n```')
        {'key': 'value'}
    """
    text = text.strip()

    # Preprocess: Strip duplicated outer braces (LLM edge case)
    # Some LLMs output {{ }} instead of { } when confused about templating
    if text.startswith('{{') and text.endswith('}}'):
        # Check if removing outer layer would still be valid JSON structure
        inner_text = text[1:-1].strip()
        if inner_text.startswith('{') and inner_text.endswith('}'):
            text = inner_text
            logger.debug("Removed duplicate outer braces from LLM response")

    # Strategy 1: Direct parse (no markdown)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    if "```" in text:
        # Find all code blocks (handle both ```json and ``` variants)
        blocks = re.findall(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        # Try each block in reverse order (LLM usually puts final output last)
        for block in reversed(blocks):
            try:
                return json.loads(block.strip())
            except json.JSONDecodeError:
                continue

    # Strategy 3: Find JSON object with bracket counting (handles arbitrary nesting)
    # Handles cases where JSON is embedded in prose without code blocks
    first_brace = text.find('{')
    if first_brace != -1:
        brace_count = 0
        for i in range(first_brace, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    try:
                        return json.loads(text[first_brace:i+1])
                    except json.JSONDecodeError:
                        pass
                    break

    logger.error("Could not extract JSON from LLM response")
    logger.debug(f"Response text (first 500 chars): {text[:500]}...")
    return None


def is_valid_json(text: str) -> bool:
    """
    Check if text contains valid JSON.

    This is a quick sanity check that can be used before attempting full parsing.

    Args:
        text: Text to check

    Returns:
        True if text contains valid JSON, False otherwise

    Examples:
        >>> is_valid_json('{"key": "value"}')
        True

        >>> is_valid_json('Not JSON')
        False

        >>> is_valid_json('```json\\n{"key": "value"}\\n```')
        True
    """
    # Try direct parse first
    try:
        json.loads(text.strip())
        return True
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown
    if extract_json_from_markdown(text) is not None:
        return True

    return False
