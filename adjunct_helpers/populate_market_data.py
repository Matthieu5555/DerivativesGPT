"""Populate market data database with yfinance data."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import pandas as pd
from typing import Literal


# Initial ticker universe (can be expanded later)
INITIAL_TICKERS = {
    'AAPL': ('Apple Inc.', 'stock'),
    'TSLA': ('Tesla, Inc.', 'stock'),
    'SPY': ('SPDR S&P 500 ETF', 'etf'),
    'GOOGL': ('Alphabet Inc.', 'stock'),
    'MSFT': ('Microsoft Corporation', 'stock'),
    'AMZN': ('Amazon.com, Inc.', 'stock'),
}


def populate_database(
    db_path: str = "data/market_data.db",
    lookback_days: int = 365,
    tickers: dict[str, tuple[str, Literal['stock', 'etf']]] = INITIAL_TICKERS
) -> None:
    """
    Populate database with historical market data.

    Args:
        db_path: Path to SQLite database
        lookback_days: Days of historical data to fetch
        tickers: Dict of {ticker: (name, instrument)}
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}. Run SQLDataProvider.__init__() first.")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get vendor ID for yfinance
    cursor.execute("SELECT id FROM data_vendor WHERE name = 'yfinance'")
    vendor_id = cursor.fetchone()[0]

    # Get default exchange ID (NYSE/NASDAQ)
    cursor.execute("SELECT id FROM exchange WHERE abbrev = 'NASDAQ'")
    exchange_id = cursor.fetchone()[0]

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    print(f"Fetching {lookback_days} days of data for {len(tickers)} tickers...")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print()

    for ticker, (name, instrument) in tickers.items():
        print(f"Processing {ticker} ({name})...")

        try:
            # Fetch data from yfinance
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(start=start_date, end=end_date)

            if hist.empty:
                print(f"  WARNING:  No data returned for {ticker}")
                continue

            # Insert symbol if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO symbol (exchange_id, ticker, instrument, name, currency)
                VALUES (?, ?, ?, ?, 'USD')
            """, (exchange_id, ticker, instrument, name))

            # Get symbol ID
            cursor.execute("SELECT id FROM symbol WHERE ticker = ?", (ticker,))
            symbol_id = cursor.fetchone()[0]

            # Insert price data
            rows_inserted = 0
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
                        float(row['Close']),  # yfinance already provides adjusted close
                        int(row['Volume']) if not pd.isna(row['Volume']) else 0,
                        vendor_id,
                        datetime.now().isoformat()
                    ))
                    rows_inserted += 1
                except Exception as e:
                    print(f"  WARNING:  Error inserting row for {date}: {e}")
                    continue

            conn.commit()
            print(f"  ✓ Inserted {rows_inserted} price observations")

        except Exception as e:
            print(f"  [ERROR] Error processing {ticker}: {e}")
            continue

    conn.close()
    print("\n[OK] Database population complete!")


def verify_data(db_path: str = "data/market_data.db") -> None:
    """
    Verify database contains expected data.

    Args:
        db_path: Path to SQLite database
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "="*50)
    print("DATABASE VERIFICATION")
    print("="*50 + "\n")

    # Check symbols
    cursor.execute("SELECT COUNT(*) FROM symbol")
    symbol_count = cursor.fetchone()[0]
    print(f"Symbols: {symbol_count}")

    # Check prices
    cursor.execute("SELECT COUNT(*) FROM daily_price")
    price_count = cursor.fetchone()[0]
    print(f"Price observations: {price_count}")

    # Check per ticker
    cursor.execute("""
        SELECT s.ticker, s.name, COUNT(dp.price_date) as obs_count,
               MIN(dp.price_date) as earliest, MAX(dp.price_date) as latest
        FROM symbol s
        LEFT JOIN daily_price dp ON s.id = dp.symbol_id
        GROUP BY s.ticker, s.name
        ORDER BY s.ticker
    """)

    print("\nPer-ticker breakdown:")
    print(f"{'Ticker':<10} {'Observations':<15} {'Date Range':<30}")
    print("-" * 55)

    for row in cursor.fetchall():
        ticker, name, count, earliest, latest = row
        date_range = f"{earliest} to {latest}" if earliest and latest else "No data"
        print(f"{ticker:<10} {count:<15} {date_range:<30}")

    conn.close()


if __name__ == "__main__":
    # Ensure database exists (initialize schema)
    from derivatives_gpt_core.market_data.sql_data_provider import SQLDataProvider
    provider = SQLDataProvider()

    # Populate with 1 year of data
    populate_database(lookback_days=365)

    # Verify
    verify_data()
