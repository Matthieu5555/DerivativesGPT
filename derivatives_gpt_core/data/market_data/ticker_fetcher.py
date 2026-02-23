"""
Ticker data fetcher.

Handles fetching ticker data from external sources (yfinance)
and storing it in the database.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def fetch_and_store_ticker_data(
    db_path: Path,
    ticker: str,
    lookback_days: int = 730
) -> tuple[bool, str]:
    """
    Fetch ticker data from yfinance and store in database.

    This function is called when a ticker is requested but not found in the database.
    It fetches historical data and populates the database for future use.

    Args:
        db_path: Path to SQLite database
        ticker: Ticker symbol (e.g., 'NVDA')
        lookback_days: Days of history to fetch (default: 730 = 2 years)

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = fetch_and_store_ticker_data(
            Path("data/market_data.db"),
            "NVDA",
            730
        )
    """
    import yfinance as yf

    try:
        ticker_upper = ticker.upper()

        # Fetch data from yfinance
        ticker_obj = yf.Ticker(ticker_upper)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        hist = ticker_obj.history(start=start_date, end=end_date)

        if hist.empty:
            return False, f"No data available for {ticker_upper} from yfinance"

        # Get database connection using context manager to prevent leaks
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Get vendor and exchange IDs
            cursor.execute("SELECT id FROM data_vendor WHERE name = 'yfinance'")
            vendor_result = cursor.fetchone()
            if not vendor_result:
                return False, "Database configuration error: yfinance vendor not found"
            vendor_id = vendor_result[0]

            cursor.execute("SELECT id FROM exchange WHERE abbrev = 'NASDAQ'")
            exchange_result = cursor.fetchone()
            if not exchange_result:
                return False, "Database configuration error: NASDAQ exchange not found"
            exchange_id = exchange_result[0]

            # Insert symbol if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO symbol (exchange_id, ticker, instrument, name, currency)
                VALUES (?, ?, 'stock', ?, 'USD')
            """, (exchange_id, ticker_upper, ticker_upper))

            # Get symbol ID
            cursor.execute("SELECT id FROM symbol WHERE ticker = ?", (ticker_upper,))
            symbol_result = cursor.fetchone()
            if not symbol_result:
                return False, f"Failed to create symbol entry for {ticker_upper}"
            symbol_id = symbol_result[0]

            # Insert price data
            rows_inserted = 0
            rows_failed = 0
            for date, row in hist.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_price
                        (symbol_id, price_date, close_price, adj_close_price, volume, data_vendor_id, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol_id,
                        date.strftime('%Y-%m-%d'),
                        float(row['Close']),
                        float(row['Close']),
                        int(row['Volume']) if not pd.isna(row['Volume']) else 0,
                        vendor_id,
                        datetime.now().isoformat()
                    ))
                    rows_inserted += 1
                except Exception as e:
                    rows_failed += 1
                    logger.warning(f"Failed to insert row for {ticker_upper} on {date}: {e}")
                    continue

            conn.commit()

        if rows_inserted > 0:
            return True, f"Successfully fetched {rows_inserted} days of data for {ticker_upper}"
        else:
            return False, f"No valid price data found for {ticker_upper}"

    except Exception as e:
        return False, f"Error fetching {ticker}: {str(e)}"
