"""
Market data providers for task execution.

Provides interfaces and implementations for fetching real-time market data
from external sources (Yahoo Finance, etc.) during option pricing execution.
"""

from typing import Protocol
import yfinance as yf
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


class MarketDataProvider(Protocol):
    """
    Protocol for market data providers (dependency injection).

    Defines the interface for fetching real-time market data during execution.
    Implementations can use different data sources (Yahoo Finance, Bloomberg, etc.).
    """

    def get_spot_price(self, ticker: str) -> float:
        """
        Fetch current spot price for ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            float: Spot price

        Raises:
            ValueError: If no data available
        """
        ...


class YFinanceProvider:
    """
    Yahoo Finance market data provider with retry logic.

    Implements MarketDataProvider protocol using yfinance library.
    Includes exponential backoff retry for network errors.
    """

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def get_spot_price(self, ticker: str) -> float:
        """
        Fetch spot price from Yahoo Finance with retry logic.

        Retry Strategy:
        - Up to 3 attempts
        - Exponential backoff (1s, 2s, 4s...)
        - Retries on network errors only
        - Does NOT retry on data errors (invalid ticker, bad format)

        Args:
            ticker: Stock symbol

        Returns:
            float: Current spot price

        Raises:
            ValueError: If ticker invalid or no data available
            ConnectionError: If all network retry attempts fail
        """
        try:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="1d")

            if hist.empty:
                # Don't retry - ticker likely invalid
                raise ValueError(
                    f"No market data for {ticker}. Ticker may be invalid or delisted."
                )

            return float(hist['Close'].iloc[-1])

        except (KeyError, IndexError, TypeError) as e:
            # Don't retry parsing errors - indicates bad data format
            raise ValueError(
                f"Failed to parse market data for {ticker}: {str(e)}"
            ) from e
