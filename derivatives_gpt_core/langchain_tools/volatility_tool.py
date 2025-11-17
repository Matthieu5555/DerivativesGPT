"""Volatility estimation tool with SQL data provider."""

from langchain_core.tools import tool
from derivatives_gpt_core.constants import MOCK_VOLATILITIES, DATABASE_HISTORICAL_LOOKBACK_DAYS
from derivatives_gpt_core.market_data.sql_data_provider import create_sql_provider
from derivatives_gpt_core.exceptions import DataNotFoundError, DataFetchError


@tool
def estimate_annualized_volatility(ticker: str, lookback_days: int = 30) -> str:
    """
    Estimate annualized volatility for a stock ticker using historical price data.

    THEORETICAL CONTEXT: For options pricing, implied volatility (IV) is generally
    preferred over historical volatility because it is forward-looking and reflects
    the market's consensus expectation of future volatility. Implied volatility is
    derived by reversing the Black-Scholes model on actual traded option prices.

    However, since we currently lack option chain data, we cannot extract implied
    volatility. As a fallback, we calculate historical volatility from past stock
    returns using the standard deviation method. While historical volatility is
    backward-looking, research suggests it provides reasonable price estimates
    for practical purposes.

    When explaining to users, acknowledge that market-derived implied volatility
    would be theoretically preferred, but historical volatility serves as a solid
    empirical substitute given our data constraints.

    WHEN TO USE:
    - After estimating the risk-free rate
    - User doesn't provide volatility in their request
    - Most users don't know volatility, so estimate it
    - Call BEFORE price_european_option if volatility not provided
    - Do NOT call if user explicitly gives volatility

    PARAMETERS:
    - ticker: Stock symbol (any valid ticker from Yahoo Finance)
    - lookback_days: Historical period for calculation (default: 30)

    RETURNS:
    - Dictionary with volatility, method, and data source

    DATA SOURCE:
    - Primary: SQL database with historical prices
    - Fallback: Mock volatility constants if database unavailable

    EXAMPLE:
    User: "price call on AAPL strike 150, 30 days"
    Step 1: estimate_risk_free_rate(30) -> explain
    Step 2: estimate_annualized_volatility("AAPL") -> explain
    Step 3: Use both in price_european_option

    IMPORTANT: The system validates tickers upfront, so this tool should only receive valid tickers.
    """
    ticker_upper = ticker.upper()

    # Try SQL provider first
    try:
        market_data_repository = create_sql_provider()
        vol = market_data_repository.get_historical_volatility(ticker_upper, lookback_days)
        return f"Volatility: {vol:.2%} ({lookback_days}-day historical realized volatility from Yahoo Finance)"

    except ValueError as e:
        # Ticker not in database - try to fetch from yfinance
        market_data_repository = create_sql_provider()
        success, message = market_data_repository.fetch_and_store_ticker(ticker_upper, lookback_days=DATABASE_HISTORICAL_LOOKBACK_DAYS)

        if success:
            # Retry volatility calculation with newly fetched data
            try:
                vol = market_data_repository.get_historical_volatility(ticker_upper, lookback_days)
                return f"Volatility: {vol:.2%} ({lookback_days}-day historical realized volatility from Yahoo Finance, newly fetched)"
            except Exception as retry_error:
                # Failed even after fetching - try mock fallback
                pass

        # If fetch failed or retry failed, try mock data
        if ticker_upper in MOCK_VOLATILITIES:
            vol = MOCK_VOLATILITIES[ticker_upper]
            return f"Volatility: {vol:.2%} (fallback estimate from mock data)"
        else:
            # Not in database, fetch failed, and not in fallback
            raise DataNotFoundError(
                f"No volatility data available for {ticker_upper}",
                details={"ticker": ticker_upper, "lookback_days": lookback_days}
            )

    except Exception as e:
        # Unexpected error - fall back to mocks
        if ticker_upper in MOCK_VOLATILITIES:
            vol = MOCK_VOLATILITIES[ticker_upper]
            return f"Volatility: {vol:.2%} (fallback estimate from mock data)"
        else:
            raise DataFetchError(
                f"Error estimating volatility for {ticker}",
                details={"ticker": ticker_upper, "error": str(e), "lookback_days": lookback_days}
            ) from e
