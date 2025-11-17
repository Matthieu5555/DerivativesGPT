"""
yfinance data fetching with LRU caching.

Isolated I/O layer - all external data fetching goes through here.
"""

import pandas as pd
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# YFINANCE CACHING - Avoid 429 Rate Limit Errors
# ============================================================================

@lru_cache(maxsize=100)
def fetch_market_data_cached(
    ticker: str,
    start_date: str,
    end_date: str
) -> Optional[pd.DataFrame]:
    """
    Fetch and cache market data from yfinance.

    Why caching matters:
    - yfinance is NOT an official API (scrapes Yahoo Finance)
    - Making too many requests causes 429 "Too Many Requests" errors
    - Yahoo may temporarily ban your IP after repeated violations
    - LRU cache stores last 100 unique (ticker, date range) requests

    Cache key: (ticker, start_date, end_date)
    Cache duration: Until Python process restarts (acceptable for development)

    For production: Consider redis cache with TTL or yfinance_cache library

    Args:
        ticker: Stock symbol (e.g., "AAPL")
        start_date: ISO format date string (e.g., "2025-10-01")
        end_date: ISO format date string (e.g., "2025-10-23")

    Returns:
        DataFrame with OHLCV data or None if fetch fails
    """
    try:
        import yfinance as yf

        logger.info(f"Fetching market data for {ticker} (not from cache)")
        data = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False,  # Suppress progress bar
            timeout=10  # Don't hang forever
        )

        if data.empty:
            logger.warning(f"No data returned for {ticker}")
            return None

        return data

    except Exception as e:
        logger.error(f"yfinance error for {ticker}: {str(e)}")

        # Check for rate limiting
        if "429" in str(e) or "Too Many Requests" in str(e):
            logger.error(
                "WARNING: RATE LIMITED by Yahoo Finance. "
                "Wait 5-10 minutes before trying again. "
                "Consider implementing longer-term caching."
            )

        return None


def invalidate_cache_for_ticker(ticker: str) -> None:
    """
    Invalidate all cached data for a specific ticker.

    Use case: When you know data is stale and needs refresh.
    Note: Current implementation clears entire cache (LRU doesn't support partial clear).
    """
    fetch_market_data_cached.cache_clear()
    logger.info(f"Cache cleared for all tickers (requested for {ticker})")


def get_cache_info() -> dict:
    """
    Get information about the current cache state.

    Useful for debugging and monitoring cache performance.

    Returns:
        Dictionary with cache statistics
    """
    cache_info = fetch_market_data_cached.cache_info()
    return {
        "hits": cache_info.hits,
        "misses": cache_info.misses,
        "size": cache_info.currsize,
        "max_size": cache_info.maxsize,
        "hit_rate": cache_info.hits / (cache_info.hits + cache_info.misses)
                    if (cache_info.hits + cache_info.misses) > 0 else 0
    }


def clear_all_cache() -> None:
    """Clear all cached market data."""
    fetch_market_data_cached.cache_clear()
    logger.info("All market data cache cleared")
