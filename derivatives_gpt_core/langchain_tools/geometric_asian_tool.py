"""Geometric Asian option pricing tool."""

from langchain_core.tools import tool
from derivatives_gpt_core.features.asian.pricing import (
    calculate_geometric_asian_option_price,
    convert_days_to_years,
    InvalidParameterError
)
from derivatives_gpt_core.config import get_settings
from derivatives_gpt_core.constants import PRICE_DECIMAL_PLACES
from typing import Literal


@tool
def price_geometric_asian_option(
    spot_price: float,
    strike_price: float,
    time_to_expiry_days: float,
    volatility: float,
    risk_free_rate: float,
    option_type: Literal["call", "put"],
    num_observations: int = 252
) -> float | str:
    """
    Calculate geometric Asian option price using analytical formula.

    Asian options are path-dependent - the payoff depends on the AVERAGE price
    of the underlying over the option's life, not just the final price.

    WHEN TO USE:
    - After you have ALL parameters
    - CALL ORDER: estimate_risk_free_rate -> estimate_annualized_volatility -> this tool
    - ONLY for GEOMETRIC Asian options (user says "geometric average" or "geometric Asian")

    WHAT ARE GEOMETRIC ASIAN OPTIONS:
    - Payoff based on geometric mean: (S_1 * S_2 * ... * S_n)^(1/n)
    - Less volatile than regular options (averaging reduces risk)
    - Cheaper than vanilla options (lower volatility = lower price)
    - Used in commodity markets and for hedging average exposure

    DIFFERENCE FROM ARITHMETIC ASIAN:
    - Geometric: (S_1 * S_2 * S_3)^(1/3) - has closed-form solution (this tool)
    - Arithmetic: (S_1 + S_2 + S_3) / 3 - requires Monte Carlo (not implemented yet)
    - Geometric is always <= Arithmetic
    - If user just says "Asian", clarify which type or assume arithmetic

    PARAMETERS:
    - spot_price: Current stock price in $
    - strike_price: Strike price in $ (user must provide)
    - time_to_expiry_days: Days to expiration (30, 60, 90, etc.)
    - volatility: From estimate_annualized_volatility or user (decimal like 0.25)
    - risk_free_rate: From estimate_risk_free_rate (decimal like 0.05)
    - option_type: "call" or "put"
    - num_observations: Number of averaging points (default 252 = daily for 1 year)

    RETURNS:
    - Option price in $ (2 decimals)
    - OR error string if parameters invalid

    METHODOLOGY:
    - Exact analytical formula (not an approximation!)
    - Uses adjusted Black-Scholes with modified volatility and drift
    - Volatility adjustment: σ_adj = σ * sqrt((2n+1)/(6(n+1)))
    - More observations -> lower adjusted volatility -> lower price

    EXAMPLE for "price geometric Asian call AAPL strike 270, 90 days":
    Step 1: risk_free_rate = estimate_risk_free_rate(90) -> extract rate
    Step 2: volatility = estimate_annualized_volatility("AAPL") -> extract vol
    Step 3: Call this tool:
        spot_price=268.47
        strike_price=270.0
        time_to_expiry_days=90.0
        volatility=0.25
        risk_free_rate=0.0525
        option_type="call"
        num_observations=252

    IMPORTANT:
    - If returns error, explain problem to user clearly
    - Always call estimate_risk_free_rate and estimate_annualized_volatility first
    - Geometric Asian options are CHEAPER than vanilla options
    - num_observations: daily=252, weekly=52, monthly=12
    - If user doesn't specify observation frequency, use 252 (daily)
    """
    settings = get_settings()

    try:
        # Convert days to years
        time_years = convert_days_to_years(
            time_to_expiry_days,
            settings.days_per_year
        )

        # Calculate price (can raise InvalidParameterError)
        price = calculate_geometric_asian_option_price(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry_years=time_years,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            option_type=option_type,
            num_observations=num_observations
        )

        return round(price, PRICE_DECIMAL_PLACES)

    except InvalidParameterError as e:
        # User-friendly error for parameter validation
        return f"[ERROR] Invalid parameters: {str(e)}"

    except Exception as e:
        # Unexpected error - still return gracefully
        return f"[ERROR] Unexpected error during pricing: {str(e)}"
