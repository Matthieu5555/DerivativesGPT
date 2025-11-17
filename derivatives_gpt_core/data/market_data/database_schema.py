"""
Database schema initialization for market data.

This module handles creation and initialization of the SQLite database schema
following the QuantStart provider-agnostic pattern.
"""

import sqlite3
from pathlib import Path


def initialize_database_schema(db_path: Path) -> None:
    """
    Initialize database schema for market data storage.

    Creates tables following provider-agnostic design:
    - data_vendor: Data source providers (yfinance, Alpha Vantage, etc.)
    - exchange: Stock exchanges (NYSE, NASDAQ, etc.)
    - symbol: Ticker symbols with exchange relationships
    - daily_price: OHLCV price data

    Args:
        db_path: Path to SQLite database file
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Data vendor table (yfinance, alpha_vantage, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_vendor (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            website_url TEXT
        )
    """)

    # Exchange table (NYSE, NASDAQ, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exchange (
            id INTEGER PRIMARY KEY,
            abbrev TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            currency TEXT NOT NULL
        )
    """)

    # Symbol table (provider-agnostic ticker identification)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symbol (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            instrument TEXT NOT NULL,
            name TEXT,
            currency TEXT NOT NULL,
            FOREIGN KEY (exchange_id) REFERENCES exchange(id),
            UNIQUE(exchange_id, ticker)
        )
    """)

    # Daily price table (OHLCV data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_price (
            symbol_id INTEGER NOT NULL,
            price_date TEXT NOT NULL,
            close_price REAL NOT NULL,
            adj_close_price REAL NOT NULL,
            volume INTEGER,
            data_vendor_id INTEGER NOT NULL,
            last_updated TEXT NOT NULL,
            FOREIGN KEY (symbol_id) REFERENCES symbol(id),
            FOREIGN KEY (data_vendor_id) REFERENCES data_vendor(id),
            PRIMARY KEY (symbol_id, price_date, data_vendor_id)
        )
    """)

    # Index for fast price lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_lookup
        ON daily_price(symbol_id, price_date DESC)
    """)

    # Insert default data vendor (yfinance)
    cursor.execute("""
        INSERT OR IGNORE INTO data_vendor (id, name, website_url)
        VALUES (1, 'yfinance', 'https://finance.yahoo.com')
    """)

    # Insert default exchanges
    exchanges = [
        (1, 'NYSE', 'New York Stock Exchange', 'USA', 'USD'),
        (2, 'NASDAQ', 'NASDAQ Stock Market', 'USA', 'USD'),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO exchange (id, abbrev, name, country, currency)
        VALUES (?, ?, ?, ?, ?)
    """, exchanges)

    conn.commit()
    conn.close()
