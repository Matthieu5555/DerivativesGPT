"""
Black-Scholes option pricing formula.

Pure math - no LangChain dependencies. Can be tested independently.
"""

import numpy as np
from scipy.stats import norm
from typing import Literal


class InvalidParameterError(Exception):
    """Raised when pricing parameters are invalid."""
    pass


def black_scholes_call(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float
) -> float:
    """
    Calculate Black-Scholes call option price.

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility

    Returns:
        Call option price
    """
    return calculate_black_scholes_price(S, K, T, sigma, r, "call")


def black_scholes_put(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float
) -> float:
    """
    Calculate Black-Scholes put option price.

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        sigma: Volatility

    Returns:
        Put option price
    """
    return calculate_black_scholes_price(S, K, T, sigma, r, "put")


def calculate_black_scholes_price(
    spot_price: float,
    strike_price: float,
    time_to_expiry_years: float,
    volatility: float,
    risk_free_rate: float,
    option_type: Literal["call", "put"]
) -> float:
    """
    Calculate European option price using Black-Scholes.

    Args:
        spot_price: Current asset price (must be > 0)
        strike_price: Strike price (must be > 0)
        time_to_expiry_years: Time to expiry in years (must be > 0)
        volatility: Annualized volatility as decimal (0.25 = 25%)
        risk_free_rate: Risk-free rate as decimal (0.05 = 5%)
        option_type: "call" or "put"

    Returns:
        Option price

    Raises:
        InvalidParameterError: If parameters invalid
    """
    # Validate
    if spot_price <= 0:
        raise InvalidParameterError(f"Spot price must be positive, got {spot_price}")
    if strike_price <= 0:
        raise InvalidParameterError(f"Strike price must be positive, got {strike_price}")
    if time_to_expiry_years <= 0:
        raise InvalidParameterError(f"Time must be positive, got {time_to_expiry_years}")
    if volatility < 0:
        raise InvalidParameterError(f"Volatility cannot be negative, got {volatility}")
    if volatility > 2.0:
        raise InvalidParameterError(f"Volatility unreasonably high (>200%), got {volatility}")
    if option_type not in ("call", "put"):
        raise InvalidParameterError(f"Option type must be call/put, got {option_type}")

    # Edge case: Zero volatility - option converges to intrinsic value
    if volatility < 0.0001:  # Effectively zero
        discount_factor = np.exp(-risk_free_rate * time_to_expiry_years)
        if option_type == "call":
            intrinsic = max(0.0, spot_price - strike_price)
        else:  # put
            intrinsic = max(0.0, strike_price - spot_price)
        # For European options, discount the intrinsic value
        return float(intrinsic * discount_factor)

    # Edge case: Very small time to expiry - option converges to intrinsic value
    if time_to_expiry_years < 0.001 / 365:  # Less than ~8 hours
        if option_type == "call":
            return float(max(0.0, spot_price - strike_price))
        else:  # put
            return float(max(0.0, strike_price - spot_price))

    # Calculate d1 and d2
    d1 = (
        np.log(spot_price / strike_price)
        + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry_years
    ) / (volatility * np.sqrt(time_to_expiry_years))

    d2 = d1 - volatility * np.sqrt(time_to_expiry_years)

    # Calculate price
    if option_type == "call":
        price = (
            spot_price * norm.cdf(d1)
            - strike_price * np.exp(-risk_free_rate * time_to_expiry_years) * norm.cdf(d2)
        )
    else:  # put
        price = (
            strike_price * np.exp(-risk_free_rate * time_to_expiry_years) * norm.cdf(-d2)
            - spot_price * norm.cdf(-d1)
        )

    return float(price)


def convert_days_to_years(days: float, days_per_year: int = 365) -> float:
    """Convert days to years."""
    return days / days_per_year
