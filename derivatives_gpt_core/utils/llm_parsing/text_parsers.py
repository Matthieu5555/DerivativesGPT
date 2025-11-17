"""
Pure text parsing functions for extracting values from LLM prose.

All functions are pure - no side effects, deterministic output.
"""

import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PURE TEXT PARSING FUNCTIONS
# ============================================================================

def parse_percentage_from_text(text: str) -> Optional[float]:
    """
    Extract percentage value from text like "volatility is **25.3%**".

    Tries multiple patterns:
    - **XX.X%** (bold markdown)
    - XX.X% (plain)
    - XX.X percent (word form)

    Args:
        text: Text containing percentage

    Returns:
        Decimal value (0.253 for 25.3%) or None

    Examples:
        >>> parse_percentage_from_text("volatility is **25.3%**")
        0.253

        >>> parse_percentage_from_text("The rate is 5.2%")
        0.052

        >>> parse_percentage_from_text("estimated at 10 percent")
        0.1
    """
    patterns = [
        r'\*\*(\d+\.?\d*)%\*\*',  # Bold: **25.3%**
        r'(\d+\.?\d*)%',           # Plain: 25.3%
        r'(\d+\.?\d*)\s*percent',  # Word: 25.3 percent
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 100

    logger.warning(f"Could not parse percentage from: {text[:100]}...")
    return None


def extract_price_from_message(text: str) -> Optional[float]:
    """
    Extract price from various formats.

    Handles:
    - **Price: $150.50**
    - The price is $150.50
    - Final price: $150.50
    - $150.50 (plain)
    - 150.50 (no $ sign)

    Args:
        text: Message containing price

    Returns:
        Price as float or None

    Examples:
        >>> extract_price_from_message("**Price: $150.50**")
        150.5

        >>> extract_price_from_message("The final price is $1,234.56")
        1234.56

        >>> extract_price_from_message("Total: 99.99")
        99.99
    """
    patterns = [
        r'\*\*(?:Price|Final Price|Total|Cost):\s*\$?([\d,.]+)\*\*',  # Bold label
        r'(?:price|total|final|cost)\s+(?:is\s+)?\$?([\d,.]+)',        # Prose
        r'\$\s*([\d,.]+)',                                              # Dollar sign
        r'(?:^|\s)([\d,.]+)(?:\s|$)',                                   # Plain number
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                continue

    logger.warning(f"Could not extract price from: {text[:100]}...")
    return None
