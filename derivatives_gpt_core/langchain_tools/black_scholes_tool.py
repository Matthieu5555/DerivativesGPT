"""Black-Scholes pricing tool."""

from langchain_core.tools import tool
from derivatives_gpt_core.features.vanilla.pricing import (
    calculate_black_scholes_price,
    convert_days_to_years,
    InvalidParameterError
)
from derivatives_gpt_core.config import get_settings
from derivatives_gpt_core.constants import PRICE_DECIMAL_PLACES
from typing import Literal


@tool
def price_european_option(
    spot_price: float,
    strike_price: float,
    time_to_expiry_days: float,
    volatility: float,
    risk_free_rate: float,
    option_type: Literal["call", "put"]
) -> float | str:
    """
    Calculate European option price using Black-Scholes.

    European options can only be exercised at expiration.

    WHEN TO USE:
    - After you have ALL parameters
    - CALL ORDER: estimate_risk_free_rate -> estimate_annualized_volatility -> this tool
    - ONLY for European call/put (not American or exotic)

    PARAMETERS:
    - spot_price: Current stock price in $ (use 100 if not specified)
    - strike_price: Strike price in $ (user must provide)
    - time_to_expiry_days: Days to expiration (30, 60, 90, etc.)
    - volatility: From estimate_annualized_volatility or user (decimal like 0.25)
    - risk_free_rate: From estimate_risk_free_rate (decimal like 0.05)
    - option_type: "call" or "put"

    RETURNS:
    - Option price in $ (2 decimals)
    - OR error string if parameters invalid

    ASSUMPTIONS:
    - European exercise only
    - No dividends
    - Constant volatility

    EXAMPLE for "price call AAPL strike 150, 30 days":
    Step 1: risk_free_rate = estimate_risk_free_rate(30) -> extract rate
    Step 2: volatility = estimate_annualized_volatility("AAPL") -> extract vol
    Step 3: Call this tool:
        spot_price=100.0
        strike_price=150.0
        time_to_expiry_days=30.0
        volatility=0.25
        risk_free_rate=0.0525
        option_type="call"

    IMPORTANT:
    - If returns error, explain problem to user clearly
    - Always call estimate_risk_free_rate and estimate_annualized_volatility first
    - Use spot_price=100 as default assumption
    """
    settings = get_settings()

    try:
        # Convert days to years
        time_years = convert_days_to_years(
            time_to_expiry_days,
            settings.days_per_year
        )

        # Calculate price (can raise InvalidParameterError)
        price = calculate_black_scholes_price(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry_years=time_years,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            option_type=option_type
        )

        return round(price, PRICE_DECIMAL_PLACES)

    except InvalidParameterError as e:
        # User-friendly error for parameter validation
        return f"[ERROR] Invalid parameters: {str(e)}"

    except Exception as e:
        # Unexpected error - still return gracefully
        return f"[ERROR] Unexpected error during pricing: {str(e)}"
