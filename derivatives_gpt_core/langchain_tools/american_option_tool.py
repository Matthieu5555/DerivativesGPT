"""American option pricing tool using Bjerksund-Stensland approximation."""

from langchain_core.tools import tool
from derivatives_gpt_core.features.american.pricing import (
    calculate_american_option_price,
    convert_days_to_years,
    InvalidParameterError
)
from derivatives_gpt_core.config import get_settings
from derivatives_gpt_core.constants import PRICE_DECIMAL_PLACES
from typing import Literal


@tool
def price_american_option(
    spot_price: float,
    strike_price: float,
    time_to_expiry_days: float,
    volatility: float,
    risk_free_rate: float,
    option_type: Literal["call", "put"],
    dividend_yield: float = 0.0
) -> float | str:
    """
    Calculate American option price using Bjerksund-Stensland approximation.

    American options can be exercised at ANY time before expiration, which
    makes them more valuable than European options (since you have more flexibility).

    WHEN TO USE:
    - After you have ALL parameters
    - CALL ORDER: estimate_risk_free_rate -> estimate_annualized_volatility -> this tool
    - ONLY for American-style options (user explicitly says "American")

    WHAT ARE AMERICAN OPTIONS:
    - Can be exercised at any time before expiration
    - More valuable than European options (flexibility premium)
    - Common in US equity markets (most exchange-traded options are American)
    - Early exercise is optimal for:
      * Deep ITM puts (time value < intrinsic value)
      * Calls on dividend-paying stocks (capture dividend)

    PARAMETERS:
    - spot_price: Current stock price in $
    - strike_price: Strike price in $ (user must provide)
    - time_to_expiry_days: Days to expiration (30, 60, 90, etc.)
    - volatility: From estimate_annualized_volatility or user (decimal like 0.25)
    - risk_free_rate: From estimate_risk_free_rate (decimal like 0.05)
    - option_type: "call" or "put"
    - dividend_yield: Annual dividend yield (default 0.0)

    RETURNS:
    - Option price in $ (2 decimals)
    - OR error string if parameters invalid

    METHODOLOGY:
    - Uses Bjerksund-Stensland (2002) analytical approximation
    - Fast (no tree required) and accurate (within $0.01-0.05 of binomial)
    - Finds optimal exercise boundary
    - For calls with no dividends, returns European call price (early exercise never optimal)

    EXAMPLE for "price American put AAPL strike 270, 90 days":
    Step 1: risk_free_rate = estimate_risk_free_rate(90) -> extract rate
    Step 2: volatility = estimate_annualized_volatility("AAPL") -> extract vol
    Step 3: Call this tool:
        spot_price=268.47
        strike_price=270.0
        time_to_expiry_days=90.0
        volatility=0.25
        risk_free_rate=0.0525
        option_type="put"
        dividend_yield=0.0

    IMPORTANT:
    - If returns error, explain problem to user clearly
    - Always call estimate_risk_free_rate and estimate_annualized_volatility first
    - American options are MORE expensive than European options
    - If user doesn't specify "American", assume European (use price_european_option)
    - Price includes the "early exercise premium"
    """
    settings = get_settings()

    try:
        # Convert days to years
        time_years = convert_days_to_years(
            time_to_expiry_days,
            settings.days_per_year
        )

        # Calculate price (can raise InvalidParameterError)
        price = calculate_american_option_price(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry_years=time_years,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            option_type=option_type,
            dividend_yield=dividend_yield
        )

        return round(price, PRICE_DECIMAL_PLACES)

    except InvalidParameterError as e:
        # User-friendly error for parameter validation
        return f"[ERROR] Invalid parameters: {str(e)}"

    except Exception as e:
        # Unexpected error - still return gracefully
        return f"[ERROR] Unexpected error during pricing: {str(e)}"
