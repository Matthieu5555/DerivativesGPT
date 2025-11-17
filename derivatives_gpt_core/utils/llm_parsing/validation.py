"""
Pydantic validation functions for LLM outputs.

Pure functions that combine JSON extraction with schema validation.
"""

import re
import json
from typing import Optional, TypeVar, Type
from pydantic import BaseModel, ValidationError
import logging

from .json_extraction import extract_json_from_markdown

logger = logging.getLogger(__name__)

# Generic type for Pydantic models
T = TypeVar('T', bound=BaseModel)


# ============================================================================
# PURE VALIDATION FUNCTIONS
# ============================================================================

def extract_and_validate(
    text: str,
    model: Type[T],
    strict: bool = True
) -> Optional[T]:
    """
    Extract JSON from LLM response and validate against Pydantic model.

    This is the primary function to use for parsing LLM outputs with schema validation.
    It combines JSON extraction with Pydantic validation to catch LLM drift immediately.

    Args:
        text: LLM response text (may contain markdown, prose, etc.)
        model: Pydantic model class to validate against
        strict: If True, raises ValidationError on schema mismatch.
                If False, logs error and returns None.

    Returns:
        Validated Pydantic model instance or None if extraction/validation fails

    Raises:
        ValidationError: If strict=True and validation fails

    Examples:
        >>> from pydantic import BaseModel
        >>> class PriceResult(BaseModel):
        ...     ticker: str
        ...     price: float
        ...
        >>> text = '```json\\n{"ticker": "AAPL", "price": 150.5}\\n```'
        >>> result = extract_and_validate(text, PriceResult)
        >>> result.ticker
        'AAPL'
        >>> result.price
        150.5

        >>> # Invalid schema - missing required field
        >>> text = '```json\\n{"ticker": "AAPL"}\\n```'
        >>> result = extract_and_validate(text, PriceResult, strict=False)
        >>> result is None
        True

    Benefits:
        1. **Catches LLM drift**: If the LLM changes output format, validation fails immediately
        2. **Type safety**: Guarantees the returned object matches expected schema
        3. **Single source of truth**: Schema defined once in Pydantic model
        4. **Better error messages**: Pydantic provides detailed validation errors
    """
    # Step 1: Extract JSON from markdown/prose
    raw_dict = extract_json_from_markdown(text)

    if raw_dict is None:
        logger.error(f"Failed to extract JSON from LLM response for {model.__name__}")
        if strict:
            raise ValueError(f"Could not extract JSON from LLM response")
        return None

    # Step 2: Validate against Pydantic schema
    try:
        validated_instance = model.model_validate(raw_dict)
        logger.debug(f"Successfully validated {model.__name__} from LLM response")
        return validated_instance

    except ValidationError as e:
        logger.error(
            f"Pydantic validation failed for {model.__name__}: {e}\n"
            f"Raw dict: {raw_dict}"
        )
        if strict:
            raise
        return None


def extract_and_validate_with_retry(
    text: str,
    model: Type[T],
    max_attempts: int = 3,
    strict: bool = False
) -> Optional[T]:
    """
    Extract and validate JSON with multiple parsing strategies.

    This enhanced version tries multiple strategies:
    1. Direct JSON parsing
    2. Extract from markdown code blocks
    3. Find JSON with bracket counting
    4. Retry with different strategies on each attempt

    Args:
        text: LLM response text
        model: Pydantic model to validate against
        max_attempts: Maximum parsing attempts (default: 3)
        strict: If True, raises on failure; if False, returns None

    Returns:
        Validated Pydantic model instance or None

    Example:
        >>> result = extract_and_validate_with_retry(response_text, MySchema)
    """
    for attempt in range(max_attempts):
        result = extract_and_validate(text, model, strict=False)

        if result is not None:
            if attempt > 0:
                logger.info(f"JSON validation succeeded on attempt {attempt + 1} for {model.__name__}")
            return result

        # Log failure details
        if attempt == 0:
            logger.warning(
                f"JSON validation failed for {model.__name__} on first attempt. "
                f"Response preview: {text[:300]}..."
            )

            # Try to extract just JSON objects from the text
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)

            for json_match in matches:
                try:
                    raw_dict = json.loads(json_match)
                    validated = model.model_validate(raw_dict)
                    logger.info(f"Successfully extracted JSON using regex pattern for {model.__name__}")
                    return validated
                except (json.JSONDecodeError, ValidationError):
                    continue

    # All attempts exhausted
    logger.error(
        f"JSON validation failed after {max_attempts} attempts for {model.__name__}. "
        f"Response: {text}"
    )

    if strict:
        raise ValueError(f"Failed to extract valid JSON from LLM response after {max_attempts} attempts")
    return None
