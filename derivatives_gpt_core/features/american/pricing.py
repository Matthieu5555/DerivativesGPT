"""
American option pricing using Bjerksund-Stensland (2002) approximation.

Pure math - no LangChain dependencies. Can be tested independently.

American options can be exercised at any time before expiration, which makes
them more valuable than European options. The Bjerksund-Stensland method provides
a fast analytical approximation that is accurate to within a few cents for most cases.
"""

import numpy as np
from scipy.stats import norm
from typing import Literal

from derivatives_gpt_core.utils.time_conversion import convert_days_to_years


class InvalidParameterError(Exception):
    """Raised when pricing parameters are invalid."""
    pass


def calculate_american_option_price(
    spot_price: float,
    strike_price: float,
    time_to_expiry_years: float,
    volatility: float,
    risk_free_rate: float,
    option_type: Literal["call", "put"],
    dividend_yield: float = 0.0
) -> float:
    """
    Calculate American option price using Bjerksund-Stensland (2002) approximation.

    This is an analytical approximation that is fast and accurate. It works by
    finding the optimal exercise boundary and calculating the value of waiting
    vs exercising early.

    Args:
        spot_price: Current asset price (must be > 0)
        strike_price: Strike price (must be > 0)
        time_to_expiry_years: Time to expiry in years (must be > 0)
        volatility: Annualized volatility as decimal (0.25 = 25%)
        risk_free_rate: Risk-free rate as decimal (0.05 = 5%)
        option_type: "call" or "put"
        dividend_yield: Continuous dividend yield (default 0.0)

    Returns:
        American option price

    Raises:
        InvalidParameterError: If parameters invalid

    References:
        - Bjerksund, P. and Stensland, G. (2002). "Closed-form valuation of
          American options." Scandinavian Working Paper in Business Administration.
        - Hull, J. (2018). Options, Futures, and Other Derivatives, 10th ed.

    Notes:
        - For American calls with no dividends, returns European call price
          (early exercise is never optimal)
        - For American puts or calls with dividends, uses the approximation formula
        - Accuracy is typically within $0.01-0.05 of binomial tree prices
    """
    # Validate
    if spot_price <= 0:
        raise InvalidParameterError(f"Spot price must be positive, got {spot_price}")
    if strike_price <= 0:
        raise InvalidParameterError(f"Strike price must be positive, got {strike_price}")
    if time_to_expiry_years <= 0:
        raise InvalidParameterError(f"Time must be positive, got {time_to_expiry_years}")
    if not (0.01 <= volatility <= 2.0):
        raise InvalidParameterError(f"Volatility must be 0.01-2.0, got {volatility}")
    if option_type not in ("call", "put"):
        raise InvalidParameterError(f"Option type must be call/put, got {option_type}")

    # For American put, use put-call symmetry: P(S,K,r,q) = C(K,S,q,r)
    if option_type == "put":
        return calculate_american_option_price(
            spot_price=strike_price,
            strike_price=spot_price,
            time_to_expiry_years=time_to_expiry_years,
            volatility=volatility,
            risk_free_rate=dividend_yield,
            option_type="call",
            dividend_yield=risk_free_rate
        )

    # For American call with no dividends, early exercise is never optimal
    if dividend_yield == 0:
        from derivatives_gpt_core.features.vanilla.pricing import calculate_black_scholes_price
        return calculate_black_scholes_price(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry_years=time_to_expiry_years,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            option_type="call"
        )

    # Bjerksund-Stensland approximation for American call with dividends
    sqrt_t = np.sqrt(time_to_expiry_years)
    sigma_sqrt_t = volatility * sqrt_t

    # Calculate beta (with edge case protection)
    if volatility < 0.001:  # Protect against division by very small volatility
        # For very low volatility, option approaches intrinsic value
        return max(0.0, spot_price - strike_price)

    beta = (
        (0.5 - dividend_yield / volatility ** 2)
        + np.sqrt(
            (dividend_yield / volatility ** 2 - 0.5) ** 2
            + 2 * risk_free_rate / volatility ** 2
        )
    )

    # Calculate B_infinity and B_0 (with edge case protection)
    B_inf = beta / (beta - 1) * strike_price

    # Handle edge case when r ≈ q (avoid division by zero)
    if abs(risk_free_rate - dividend_yield) < 1e-10:
        # When r = q, use limiting case
        B_0 = strike_price
    else:
        B_0 = max(strike_price, risk_free_rate / (risk_free_rate - dividend_yield) * strike_price)

    # Calculate h(T)
    h_t = -(dividend_yield * time_to_expiry_years + 2 * sigma_sqrt_t) * B_0 / (B_inf - B_0)

    # Calculate critical stock price I
    I = B_0 + (B_inf - B_0) * (1 - np.exp(h_t))

    # If spot >= I, exercise immediately (but ensure non-negative)
    if spot_price >= I:
        return max(0.0, spot_price - strike_price)

    # Calculate alpha
    alpha = (I - strike_price) * I ** (-beta)

    # Calculate d1 terms (using correct drift: r - q, not just q)
    d1_I = (
        np.log(spot_price / I)
        + (risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * time_to_expiry_years
    ) / sigma_sqrt_t

    d1_K = (
        np.log(spot_price / strike_price)
        + (risk_free_rate - dividend_yield + 0.5 * volatility ** 2) * time_to_expiry_years
    ) / sigma_sqrt_t

    # Calculate option price
    price = (
        alpha * (spot_price ** beta)
        - alpha * norm.cdf(d1_I) * (spot_price ** beta) / (I ** beta)
        + norm.cdf(d1_K) * spot_price * np.exp(-dividend_yield * time_to_expiry_years)
        - norm.cdf(d1_K - sigma_sqrt_t) * strike_price * np.exp(-risk_free_rate * time_to_expiry_years)
    )

    return float(price)
