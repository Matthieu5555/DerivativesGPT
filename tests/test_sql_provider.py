"""Test SQL data provider."""

import pytest
import sqlite3
from pathlib import Path
from derivatives_gpt_core.market_data.sql_data_provider import SQLDataProvider, create_sql_provider


@pytest.fixture
def test_db_path(tmp_path):
    """Create temporary database path."""
    return str(tmp_path / "test_market_data.db")


@pytest.fixture
def provider(test_db_path):
    """Create provider with test database."""
    return SQLDataProvider(test_db_path)


def test_schema_initialization(provider, test_db_path):
    """Test that schema is created correctly."""
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert 'data_vendor' in tables
    assert 'exchange' in tables
    assert 'symbol' in tables
    assert 'daily_price' in tables

    # Check vendor exists
    cursor.execute("SELECT COUNT(*) FROM data_vendor WHERE name = 'yfinance'")
    assert cursor.fetchone()[0] == 1

    # Check exchanges exist
    cursor.execute("SELECT COUNT(*) FROM exchange")
    assert cursor.fetchone()[0] >= 2  # NYSE and NASDAQ

    conn.close()


def test_get_current_price_no_data(provider):
    """Test get_current_price with no data."""
    with pytest.raises(ValueError, match="not found"):
        provider.get_current_price("AAPL")


def test_get_historical_volatility_no_data(provider):
    """Test get_historical_volatility with no data."""
    with pytest.raises(ValueError, match="not found"):
        provider.get_historical_volatility("AAPL")


def test_get_available_tickers_empty(provider):
    """Test get_available_tickers with empty database."""
    tickers = provider.get_available_tickers()
    assert tickers == []


def test_factory_function(test_db_path):
    """Test factory function creates provider."""
    provider = create_sql_provider(test_db_path)
    assert isinstance(provider, SQLDataProvider)


def test_populated_database():
    """
    Test with actual populated database (integration test).

    This test requires running populate_market_data.py first.
    """
    try:
        provider = create_sql_provider("data/market_data.db")

        # Test get_available_tickers
        tickers = provider.get_available_tickers()
        assert len(tickers) > 0
        assert 'AAPL' in tickers

        # Test get_current_price
        price = provider.get_current_price('AAPL')
        assert price > 0
        assert price < 1000  # Sanity check

        # Test get_historical_volatility
        vol = provider.get_historical_volatility('AAPL', lookback_days=30)
        assert 0.01 < vol < 2.0  # Reasonable volatility range

        # Test get_price_history
        history = provider.get_price_history('AAPL', days=30)
        assert len(history) > 0
        assert 'date' in history.columns
        assert 'close' in history.columns

        print(f"✓ Integration test passed with {len(tickers)} tickers")

    except FileNotFoundError:
        pytest.skip("Database not populated. Run populate_market_data.py first.")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
