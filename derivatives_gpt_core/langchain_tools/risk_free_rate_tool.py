"""Risk-free rate estimation tool with live Treasury yield fetching."""

from langchain_core.tools import tool
from datetime import date
from derivatives_gpt_core.config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import yfinance as yf
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Treasury yield symbols from Yahoo Finance
# Yields are returned as percentages (e.g., 5.25 for 5.25%)
# Note: ^IRX, ^FVX, ^TNX, ^TYX are yield indices (most reliable)
TREASURY_SYMBOLS = {
    "3month": "^IRX",   # 3-month T-bill (13-week) - CBOE Interest Rate 10 Year T No
    "1year": "^IRX",    # Use 3-month as proxy (1-year not available)
    "5year": "^FVX",    # 5-year Treasury Note
    "10year": "^TNX",   # 10-year Treasury Note
    "30year": "^TYX"    # 30-year Treasury Bond
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def _fetch_treasury_yield(symbol: str, tenor_name: str) -> float:
    """
    Fetch current Treasury yield from Yahoo Finance with retry logic.

    Args:
        symbol: Yahoo Finance symbol (e.g., ^IRX for 3-month T-bill)
        tenor_name: Human-readable name (e.g., "3-month T-bill")

    Returns:
        float: Yield as decimal (e.g., 0.0525 for 5.25%)

    Raises:
        ValueError: If data unavailable or parsing fails
        ConnectionError: If all retry attempts fail
    """
    try:
        ticker = yf.Ticker(symbol)

        # Get most recent price (yield is in the price field, as percentage)
        hist = ticker.history(period="5d")  # Get last 5 days to ensure we have data

        if hist.empty:
            raise ValueError(f"No data available for {tenor_name} ({symbol})")

        # Get most recent closing price (yield as percentage)
        latest_yield_pct = float(hist['Close'].iloc[-1])

        # Convert from percentage to decimal (5.25 → 0.0525)
        yield_decimal = latest_yield_pct / 100.0

        logger.info(f"Fetched {tenor_name} yield: {yield_decimal:.4f} ({latest_yield_pct:.2f}%)")
        return yield_decimal

    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(
            f"Failed to parse yield data for {tenor_name}: {str(e)}"
        ) from e


def _get_treasury_symbol_for_horizon(time_horizon_days: float) -> Tuple[str, str, str]:
    """
    Select appropriate Treasury symbol based on option time horizon.

    Maps option maturity to closest available Treasury yield on Yahoo Finance.
    Uses yield curve matching principle: match option duration to Treasury duration.

    Args:
        time_horizon_days: Days to option expiration

    Returns:
        Tuple of (yahoo_symbol, tenor_name, fallback_config_field)
    """
    if time_horizon_days <= 90:
        # Short-term options: Use 3-month T-bill
        return TREASURY_SYMBOLS["3month"], "3-month T-bill", "risk_free_rate_3month"
    elif time_horizon_days <= 730:  # ~2 years
        # Medium-term: Use 3-month as best available proxy (2-year not on Yahoo)
        return TREASURY_SYMBOLS["1year"], "1-year T-bill (proxy)", "risk_free_rate_1year"
    elif time_horizon_days <= 2737:  # ~7.5 years (midpoint between 5 and 10)
        # 2-7.5 years: Use 5-year Note
        return TREASURY_SYMBOLS["5year"], "5-year Treasury Note", "risk_free_rate_1year"
    elif time_horizon_days <= 5475:  # ~15 years (midpoint between 10 and 30)
        # 7.5-15 years: Use 10-year Note
        return TREASURY_SYMBOLS["10year"], "10-year Treasury Note", "risk_free_rate_default"
    else:
        # Very long-term: Use 30-year Bond
        return TREASURY_SYMBOLS["30year"], "30-year Treasury Bond", "risk_free_rate_default"


@tool
def estimate_risk_free_rate(time_horizon_days: float) -> str:
    """
    Estimate risk-free rate by fetching live US Treasury yields from Yahoo Finance.

    Dynamically fetches current Treasury yields matching the option's maturity:
    - ≤ 90 days: 3-month T-bill (^IRX)
    - 90-730 days: 1-year proxy (^IRX)
    - 730-2737 days: 5-year Note (^FVX)
    - 2737-5475 days: 10-year Note (^TNX)
    - > 5475 days: 30-year Bond (^TYX)

    Includes comprehensive error handling with fallback to config values.

    WHEN TO USE:
    - ALWAYS call this FIRST before pricing any option
    - The rate must match the option's time to expiration

    PARAMETERS:
    - time_horizon_days: Days to expiration (e.g., 30, 60, 90)

    RETURNS:
    - String with risk-free rate, tenor, and data source

    EXAMPLE:
    estimate_risk_free_rate(60) ->
    "Risk-free rate: 5.25% (live 3-month T-bill yield from Yahoo Finance, 60 days)"
    """
    # Input validation
    if time_horizon_days <= 0:
        raise ValueError(
            f"Error: Invalid time horizon ({time_horizon_days} days). "
            f"Time horizon must be positive."
        )

    if time_horizon_days > 10950:  # 30 years
        logger.warning(
            f"Very long time horizon ({time_horizon_days:.0f} days = {time_horizon_days/365:.1f} years). "
            f"Using 30-year Treasury as proxy."
        )

    # Get appropriate Treasury symbol for this time horizon
    symbol, tenor_name, fallback_field = _get_treasury_symbol_for_horizon(time_horizon_days)

    # Try to fetch live rate from Yahoo Finance
    try:
        live_rate = _fetch_treasury_yield(symbol, tenor_name)

        return (
            f"Risk-free rate: {live_rate:.4f} ({live_rate*100:.2f}%) "
            f"(live {tenor_name} yield from Yahoo Finance for {time_horizon_days:.0f}-day horizon)"
        )

    except Exception as e:
        # Log technical error for debugging
        logger.warning(
            f"Failed to fetch live Treasury yield for {tenor_name}: {e}. "
            f"Using fallback config value."
        )

        settings = get_settings()
        fallback_rate = getattr(settings, fallback_field)

        # Return user-friendly message that explains the situation
        # The LLM will use this to communicate with the user
        return (
            f"API Error: Unable to fetch live {tenor_name} yield from Yahoo Finance. "
            f"Using fallback rate: {fallback_rate:.4f} ({fallback_rate*100:.2f}%) "
            f"for {time_horizon_days:.0f}-day horizon. "
            f"\n\n"
            f"Note: This is a recent Treasury rate from our fallback data. "
            f"If you have a preferred risk-free rate for your calculation, "
            f"please let me know and I'll use that instead. "
            f"For example, you could say: 'Use 4.5% as the risk-free rate'"
        )
