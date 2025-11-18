"""
Moneyness calculation utilities for options.

Moneyness determines whether an option has intrinsic value:
- ITM (In-The-Money): Option has intrinsic value if exercised now
- ATM (At-The-Money): Strike ≈ Spot price
- OTM (Out-The-Money): Option has no intrinsic value, only time value
"""

from typing import Literal
from derivatives_gpt_core.constants import AT_THE_MONEY_THRESHOLD
from derivatives_gpt_core.exceptions import ParameterValidationError


def calculate_moneyness(
    spot_price: float,
    strike_price: float,
    option_type: Literal["call", "put"]
) -> str:
    """
    # Called by: Pricing validation, strategy decomposition, risk analysis modules
    # Determines if option has intrinsic value (affects pricing and exercise decisions)
    # Changing AT_THE_MONEY_THRESHOLD in constants.py affects boundary classification

    Args:
        spot_price: Current asset price
        strike_price: Option strike price
        option_type: "call" or "put"

    Returns:
        "in-the-money", "at-the-money", or "out-of-the-money"

    Examples:
        >>> calculate_moneyness(100, 110, "call")
        'out-of-the-money'  # Call with strike above spot

        >>> calculate_moneyness(100, 90, "call")
        'in-the-money'  # Call with strike below spot

        >>> calculate_moneyness(100, 110, "put")
        'in-the-money'  # Put with strike above spot

        >>> calculate_moneyness(100, 90, "put")
        'out-of-the-money'  # Put with strike below spot
    """
    if spot_price <= 0 or strike_price <= 0:
        raise ParameterValidationError(
            "Prices must be positive",
            details={"spot_price": spot_price, "strike_price": strike_price}
        )

    if option_type not in ("call", "put"):
        raise ParameterValidationError(
            f"Option type must be 'call' or 'put', got '{option_type}'",
            details={"option_type": option_type, "valid_types": ["call", "put"]}
        )

    # Calculate moneyness ratio
    spot_strike_ratio = spot_price / strike_price

    if abs(spot_strike_ratio - 1.0) < AT_THE_MONEY_THRESHOLD:
        return "at-the-money"

    # Determine ITM/OTM based on option type
    if option_type == "call":
        # Call: ITM when spot > strike, OTM when spot < strike
        return "in-the-money" if spot_price > strike_price else "out-of-the-money"
    else:  # put
        # Put: ITM when spot < strike, OTM when spot > strike
        return "in-the-money" if spot_price < strike_price else "out-of-the-money"


def get_moneyness_ratio(spot_price: float, strike_price: float) -> float:
    """
    # Called by: Greeks calculation, implied volatility solvers, risk metrics
    # Provides numerical measure of how far ITM/OTM an option is
    # Used in volatility smile analysis and delta calculations

    Args:
        spot_price: Current asset price
        strike_price: Option strike price

    Returns:
        Ratio of spot to strike (e.g., 1.1 means 10% in-the-money for call)
    """
    if strike_price <= 0:
        raise ParameterValidationError(
            "Strike price must be positive",
            details={"strike_price": strike_price}
        )

    return spot_price / strike_price


def explain_moneyness(
    spot_price: float,
    strike_price: float,
    option_type: Literal["call", "put"]
) -> str:
    """
    Generate user-friendly explanation of moneyness.

    Returns:
        Human-readable explanation string
    """
    moneyness = calculate_moneyness(spot_price, strike_price, option_type)
    ratio = get_moneyness_ratio(spot_price, strike_price)

    if moneyness == "at-the-money":
        return (
            f"This option is **at-the-money** (spot ${spot_price:.2f} ≈ strike ${strike_price:.2f}). "
            f"It has minimal intrinsic value and is primarily time value."
        )

    percentage_diff = abs(ratio - 1.0) * 100

    if moneyness == "in-the-money":
        intrinsic_value = abs(spot_price - strike_price)
        return (
            f"This option is **in-the-money** by {percentage_diff:.1f}% "
            f"(spot ${spot_price:.2f} vs strike ${strike_price:.2f}). "
            f"It has ${intrinsic_value:.2f} of intrinsic value plus time value."
        )
    else:  # OTM
        return (
            f"This option is **out-of-the-money** by {percentage_diff:.1f}% "
            f"(spot ${spot_price:.2f} vs strike ${strike_price:.2f}). "
            f"It has no intrinsic value, only time value. The stock would need to move "
            f"${abs(strike_price - spot_price):.2f} for this option to be profitable at expiration."
        )
