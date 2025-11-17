"""Centralized strike resolution utility.

This module provides a single source of truth for resolving relative strike
specifications (ATM, OTM, ITM, percentage-based) to absolute strike prices.

Eliminates code duplication across validate_inputs.py and execute_parallel_tasks.py.
"""

import re
import logging
from typing import Union, Literal

logger = logging.getLogger(__name__)


def resolve_strike(
    strike: Union[str, float, int],
    spot_price: float,
    option_type: Literal["call", "put"] = "call"
) -> float:
    """
    Resolve relative strike specifications to absolute values.

    Single source of truth for strike resolution - used in both validation
    and execution phases to ensure consistent behavior.

    Args:
        strike: Strike price specification
            - Absolute: numeric value (e.g., 150.0)
            - Relative: string specification (e.g., "ATM", "5% above", "OTM")
        spot_price: Current spot price of the underlying asset
        option_type: "call" or "put" (used for OTM/ITM resolution)

    Returns:
        float: Absolute strike price

    Raises:
        ValueError: If spot_price is invalid (<=0)

    Examples:
        >>> resolve_strike(150.0, 100.0)
        150.0

        >>> resolve_strike("ATM", 100.0)
        100.0

        >>> resolve_strike("5% above", 100.0)
        105.0

        >>> resolve_strike("10% below", 100.0)
        90.0

        >>> resolve_strike("OTM", 100.0, "call")
        105.0

        >>> resolve_strike("OTM", 100.0, "put")
        95.0

        >>> resolve_strike("ITM", 100.0, "call")
        95.0

        >>> resolve_strike("ITM", 100.0, "put")
        105.0
    """
    # Validate spot_price
    if spot_price <= 0:
        raise ValueError(f"Spot price must be positive, got {spot_price}")

    # If already numeric, return as-is
    if isinstance(strike, (int, float)):
        return float(strike)

    # Parse relative strike specification
    strike_lower = str(strike).lower().strip()

    # ATM (at-the-money)
    if strike_lower == "atm" or "at the money" in strike_lower:
        return spot_price

    # Percentage above
    if "% above" in strike_lower or "%above" in strike_lower:
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', strike_lower)
        if match:
            percentage = float(match.group(1)) / 100
            return spot_price * (1 + percentage)

    # Percentage below
    if "% below" in strike_lower or "%below" in strike_lower:
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', strike_lower)
        if match:
            percentage = float(match.group(1)) / 100
            return spot_price * (1 - percentage)

    # OTM (out-of-the-money) - strike makes option OTM
    if "otm" in strike_lower or "out of the money" in strike_lower:
        # Call OTM: strike > spot (5% above)
        # Put OTM: strike < spot (5% below)
        return spot_price * 1.05 if option_type == "call" else spot_price * 0.95

    # ITM (in-the-money) - strike makes option ITM
    if "itm" in strike_lower or "in the money" in strike_lower:
        # Call ITM: strike < spot (5% below)
        # Put ITM: strike > spot (5% above)
        return spot_price * 0.95 if option_type == "call" else spot_price * 1.05

    # Fallback: unable to parse, default to ATM
    logger.warning(
        f"Unable to parse relative strike '{strike}', defaulting to ATM (${spot_price:.2f})"
    )
    return spot_price
