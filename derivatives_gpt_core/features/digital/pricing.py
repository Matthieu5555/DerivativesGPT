"""
Digital (Binary) option pricing formula.

Pure math - no LangChain dependencies. Can be tested independently.

Digital options pay a fixed amount if the option expires in-the-money, nothing otherwise:
- Digital Call: Pays $1 if S_T > K, $0 otherwise
- Digital Put: Pays $1 if S_T < K, $0 otherwise

These are also called "binary options" or "cash-or-nothing options".
"""

import numpy as np
from scipy.stats import norm
from typing import Literal


class InvalidParameterError(Exception):
    """Raised when pricing parameters are invalid."""
    pass


def calculate_digital_option_price(
    spot_price: float,
    strike_price: float,
    time_to_expiry_years: float,
    volatility: float,
    risk_free_rate: float,
    option_type: Literal["call", "put"],
    payout: float = 1.0,
    dividend_yield: float = 0.0
) -> float:
    """
    Calculate digital/binary option price using analytical formula.

    Digital options have discontinuous payoffs:
    - Digital Call: max(0, 1) if S_T > K
    - Digital Put: max(0, 1) if S_T < K

    The formula is derived from Black-Scholes by differentiating with respect
    to the strike price. The value is the present value of the probability
    of finishing in-the-money.

    Args:
        spot_price: Current asset price (must be > 0)
        strike_price: Strike price (must be > 0)
        time_to_expiry_years: Time to expiry in years (must be > 0)
        volatility: Annualized volatility as decimal (0.25 = 25%)
        risk_free_rate: Risk-free rate as decimal (0.05 = 5%)
        option_type: "call" or "put"
        payout: Fixed payout if ITM (default $1.00)
        dividend_yield: Continuous dividend yield (default 0.0)

    Returns:
        Option price (present value of expected payout)

    Raises:
        InvalidParameterError: If parameters invalid

    References:
        - Hull, J. (2018). Options, Futures, and Other Derivatives, 10th ed.
        - Reiner, E. and Rubinstein, M. (1991). Breaking down the barriers.
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
    if payout <= 0:
        raise InvalidParameterError(f"Payout must be positive, got {payout}")

    # Calculate d2 from Black-Scholes (this is the risk-neutral probability)
    d2 = (
        np.log(spot_price / strike_price)
        + (risk_free_rate - dividend_yield - 0.5 * volatility ** 2) * time_to_expiry_years
    ) / (volatility * np.sqrt(time_to_expiry_years))

    # Discount factor
    discount_factor = np.exp(-risk_free_rate * time_to_expiry_years)

    # Calculate price based on option type
    if option_type == "call":
        # Digital call: PV(payout * P(S_T > K))
        # P(S_T > K) = N(d2)
        price = payout * discount_factor * norm.cdf(d2)
    else:  # put
        # Digital put: PV(payout * P(S_T < K))
        # P(S_T < K) = N(-d2) = 1 - N(d2)
        price = payout * discount_factor * norm.cdf(-d2)

    return float(price)


def convert_days_to_years(days: float, days_per_year: int = 365) -> float:
    """Convert days to years."""
    return days / days_per_year
