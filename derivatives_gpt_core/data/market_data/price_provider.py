"""
Price and volatility data provider.

SQLite-based implementation of MarketDataProvider protocol.
Provides current prices, historical volatility, and price history.
"""

import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
from derivatives_gpt_core.data.market_data.data_provider_protocol import MarketDataProvider
from derivatives_gpt_core.data.market_data.database_schema import initialize_database_schema
from derivatives_gpt_core.data.market_data.ticker_fetcher import fetch_and_store_ticker_data


class SQLPriceProvider:
    """
    SQLite-based market data provider.

    Implements MarketDataProvider protocol with SQLite backend.
    Follows QuantStart schema pattern for flexibility and provider-agnostic design.
    """

    def __init__(self, db_path: str | Path = "data/market_data.db") -> None:
        """
        Initialize SQL price provider.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema if database doesn't exist
        if not self.db_path.exists():
            initialize_database_schema(self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(str(self.db_path))

    def get_symbol_id(self, ticker: str) -> int | None:
        """
        Get symbol ID for ticker.

        Args:
            ticker: Ticker symbol (e.g., 'AAPL')

        Returns:
            Symbol ID or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM symbol WHERE ticker = ?
        """, (ticker.upper(),))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def fetch_and_store_ticker(
        self,
        ticker: str,
        lookback_days: int = 730
    ) -> tuple[bool, str]:
        """
        Fetch ticker data from yfinance and store in database.

        This is a convenience wrapper around ticker_fetcher.fetch_and_store_ticker_data.

        Args:
            ticker: Ticker symbol (e.g., 'NVDA')
            lookback_days: Days of history to fetch (default: 730 = 2 years)

        Returns:
            (success: bool, message: str)
        """
        return fetch_and_store_ticker_data(self.db_path, ticker, lookback_days)

    def get_current_price(self, ticker: str) -> float:
        """
        Get most recent close price for ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            Most recent adjusted close price

        Raises:
            ValueError: If ticker not found or no data available
        """
        symbol_id = self.get_symbol_id(ticker)
        if symbol_id is None:
            raise ValueError(f"Ticker {ticker} not found in database")

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT adj_close_price, price_date
            FROM daily_price
            WHERE symbol_id = ?
            ORDER BY price_date DESC
            LIMIT 1
        """, (symbol_id,))

        result = cursor.fetchone()
        conn.close()

        if result is None:
            raise ValueError(f"No price data available for {ticker}")

        return float(result[0])

    def get_historical_volatility(self, ticker: str, lookback_days: int = 30) -> float:
        """
        Calculate annualized historical volatility from daily returns.

        Uses standard deviation of logarithmic returns:
        vol_annual = std(log(P_t / P_{t-1})) * sqrt(252)

        Args:
            ticker: Ticker symbol
            lookback_days: Number of days to look back

        Returns:
            Annualized volatility as decimal (e.g., 0.25 for 25%)

        Raises:
            ValueError: If ticker not found or insufficient data
        """
        symbol_id = self.get_symbol_id(ticker)
        if symbol_id is None:
            raise ValueError(f"Ticker {ticker} not found in database")

        conn = self._get_connection()

        # Get price history
        query = """
            SELECT price_date, adj_close_price
            FROM daily_price
            WHERE symbol_id = ?
            ORDER BY price_date DESC
            LIMIT ?
        """

        df = pd.read_sql_query(query, conn, params=(symbol_id, lookback_days + 1))
        conn.close()

        if len(df) < 2:
            raise ValueError(f"Insufficient data for {ticker} (need at least 2 days)")

        # Calculate log returns
        df = df.sort_values('price_date')
        df['log_return'] = np.log(df['adj_close_price'] / df['adj_close_price'].shift(1))

        # Remove NaN from first row
        log_returns = df['log_return'].dropna()

        if len(log_returns) < 2:
            raise ValueError(f"Insufficient returns data for {ticker}")

        # Calculate annualized volatility (252 trading days per year)
        daily_vol = log_returns.std()
        annualized_vol = daily_vol * np.sqrt(252)

        return float(annualized_vol)

    def get_price_history(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get historical price data for charting.

        Args:
            ticker: Ticker symbol
            days: Number of days to retrieve

        Returns:
            DataFrame with columns: date, close, adj_close, volume

        Raises:
            ValueError: If ticker not found
        """
        symbol_id = self.get_symbol_id(ticker)
        if symbol_id is None:
            raise ValueError(f"Ticker {ticker} not found in database")

        conn = self._get_connection()

        query = """
            SELECT price_date as date,
                   close_price as close,
                   adj_close_price as adj_close,
                   volume
            FROM daily_price
            WHERE symbol_id = ?
            ORDER BY price_date DESC
            LIMIT ?
        """

        df = pd.read_sql_query(query, conn, params=(symbol_id, days))
        conn.close()

        # Sort chronologically for charting
        df = df.sort_values('date')

        return df

    def get_available_tickers(self) -> list[str]:
        """
        Get list of all tickers with price data.

        Returns:
            List of ticker symbols
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT s.ticker
            FROM symbol s
            INNER JOIN daily_price dp ON s.id = dp.symbol_id
            ORDER BY s.ticker
        """)

        tickers = [row[0] for row in cursor.fetchall()]
        conn.close()

        return tickers


def create_price_provider(db_path: str = "data/market_data.db") -> MarketDataProvider:
    """
    Factory function to create SQL price provider.

    Args:
        db_path: Path to SQLite database

    Returns:
        SQLPriceProvider instance conforming to MarketDataProvider protocol
    """
    return SQLPriceProvider(db_path)
