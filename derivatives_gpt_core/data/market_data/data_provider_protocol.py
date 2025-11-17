"""
Market data provider protocol.

Defines the interface that all market data providers must implement.
"""

from typing import Protocol
import pandas as pd


class MarketDataProvider(Protocol):
    """
    Protocol for market data providers.

    Defines the interface for accessing market data from any source
    (SQL database, API, mock data, etc.).
    """

    def get_current_price(self, ticker: str) -> float:
        """
        Get most recent close price for ticker.

        Args:
            ticker: Ticker symbol (e.g., 'AAPL')

        Returns:
            Most recent adjusted close price

        Raises:
            ValueError: If ticker not found or no data available
        """
        ...

    def get_historical_volatility(self, ticker: str, lookback_days: int = 30) -> float:
        """
        Get annualized historical volatility.

        Args:
            ticker: Ticker symbol
            lookback_days: Number of days to look back for volatility calculation

        Returns:
            Annualized volatility as decimal (e.g., 0.25 for 25%)

        Raises:
            ValueError: If ticker not found or insufficient data
        """
        ...

    def get_price_history(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get historical price data for charting.

        Args:
            ticker: Ticker symbol
            days: Number of days to retrieve

        Returns:
            DataFrame with columns: date, close, volume

        Raises:
            ValueError: If ticker not found
        """
        ...

    def get_available_tickers(self) -> list[str]:
        """
        Get list of tickers with data.

        Returns:
            List of ticker symbols
        """
        ...
