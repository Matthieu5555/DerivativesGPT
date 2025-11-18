"""
Geometric Asian option pricing using analytical formula.

Pure math - no LangChain dependencies. Can be tested independently.

Asian options are path-dependent - the payoff depends on the average price of
the underlying asset over the option's life. There are two types:
- Arithmetic Asian: Average = (S_1 + S_2 + ... + S_n) / n
- Geometric Asian: Average = (S_1 * S_2 * ... * S_n) ^ (1/n)

Geometric Asian options have a closed-form solution (this file).
Arithmetic Asian options require Monte Carlo simulation (not implemented yet).
"""

import numpy as np
from scipy.stats import norm
from typing import Literal

from derivatives_gpt_core.utils.time_conversion import convert_days_to_years


class InvalidParameterError(Exception):
    """Raised when pricing parameters are invalid."""
    pass


def calculate_geometric_asian_option_price(
    spot_price: float,
    strike_price: float,
    time_to_expiry_years: float,
    volatility: float,
    risk_free_rate: float,
    option_type: Literal["call", "put"],
    num_observations: int = 252,
    dividend_yield: float = 0.0
) -> float:
    """
    Calculate geometric Asian option price using analytical formula.

    Geometric Asian options use the geometric mean of prices over the averaging period.
    The key insight is that the geometric mean of log-normal random variables is
    also log-normal, which allows us to use a modified Black-Scholes formula.

    Args:
        spot_price: Current asset price (must be > 0)
        strike_price: Strike price (must be > 0)
        time_to_expiry_years: Time to expiry in years (must be > 0)
        volatility: Annualized volatility as decimal (0.25 = 25%)
        risk_free_rate: Risk-free rate as decimal (0.05 = 5%)
        option_type: "call" or "put"
        num_observations: Number of averaging points (default 252 = daily for 1 year)
        dividend_yield: Continuous dividend yield (default 0.0)

    Returns:
        Geometric Asian option price

    Raises:
        InvalidParameterError: If parameters invalid

    References:
        - Kemna, A. and Vorst, T. (1990). "A pricing method for options based
          on average asset values." Journal of Banking and Finance, 14(1), 113-129.
        - Hull, J. (2018). Options, Futures, and Other Derivatives, 10th ed.

    Notes:
        - This is an exact analytical formula (not an approximation)
        - Geometric Asian options are less valuable than arithmetic Asian options
        - The formula uses adjusted volatility and drift parameters
        - More averaging points -> lower volatility -> lower option price
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
    if num_observations < 2:
        raise InvalidParameterError(f"Need at least 2 observations, got {num_observations}")

    # Edge case: Zero volatility - deterministic average
    if volatility < 0.0001:  # Effectively zero
        # With zero volatility, the average is the forward price
        forward_price = spot_price * np.exp((risk_free_rate - dividend_yield) * time_to_expiry_years)
        discount_factor = np.exp(-risk_free_rate * time_to_expiry_years)

        if option_type == "call":
            return float(max(0.0, forward_price - strike_price) * discount_factor)
        else:  # put
            return float(max(0.0, strike_price - forward_price) * discount_factor)

    # Edge case: Very small time to expiry - average converges to spot
    if time_to_expiry_years < 0.001 / 365:  # Less than ~8 hours
        if option_type == "call":
            return float(max(0.0, spot_price - strike_price))
        else:  # put
            return float(max(0.0, strike_price - spot_price))

    # Adjust volatility for geometric averaging
    # The geometric mean has lower volatility than individual observations
    # For discrete averaging with n observations (Kemna-Vorst formula)
    n = num_observations
    sigma_adj = volatility * np.sqrt((n + 1) * (2 * n + 1) / (6 * n * n))

    # Adjust drift (expected return) for discrete geometric averaging
    mu = risk_free_rate - dividend_yield
    # Adjusted drift for geometric average (Kemna-Vorst)
    mu_adj = ((n + 1) / (2 * n)) * (mu - 0.5 * volatility ** 2) + 0.5 * sigma_adj ** 2

    # Calculate modified d1 and d2
    sqrt_t = np.sqrt(time_to_expiry_years)

    # Note: mu_adj already includes the 0.5 * sigma_adj^2 term
    d1 = (
        np.log(spot_price / strike_price)
        + mu_adj * time_to_expiry_years
    ) / (sigma_adj * sqrt_t)

    d2 = d1 - sigma_adj * sqrt_t

    # Calculate price based on option type (using correct discounting)
    # The discount is already embedded in the Black-Scholes framework
    if option_type == "call":
        price = (
            spot_price * np.exp((mu_adj - risk_free_rate) * time_to_expiry_years) * norm.cdf(d1)
            - strike_price * np.exp(-risk_free_rate * time_to_expiry_years) * norm.cdf(d2)
        )
    else:  # put
        price = (
            strike_price * np.exp(-risk_free_rate * time_to_expiry_years) * norm.cdf(-d2)
            - spot_price * np.exp((mu_adj - risk_free_rate) * time_to_expiry_years) * norm.cdf(-d1)
        )

    return float(price)
