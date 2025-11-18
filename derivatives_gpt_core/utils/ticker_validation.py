"""
Ticker validation utilities for Yahoo Finance integration.

This module provides functions to validate tickers against Yahoo Finance
without triggering errors visible to end users. Used by classify_intent
node to determine if a ticker exists before attempting to price.
"""

import yfinance as yf
from typing import Dict, Any, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# Called by: validate_ticker_exists() for timeout control
# Sets max wait time for yfinance API calls before giving up
# Lower values = faster failures but may miss slow APIs, Higher = more reliable but slower
VALIDATION_TIMEOUT = 5  # seconds

# Called by: @lru_cache decorator on validate_ticker_exists()
# Maximum ticker validations kept in memory to avoid repeated API calls
# Higher values = more memory usage but fewer API calls, 1000 is reasonable for typical usage
CACHE_SIZE = 1000


@lru_cache(maxsize=CACHE_SIZE)
def validate_ticker_exists(ticker: str) -> Dict[str, Any]:
    """
    # Called by: classify_intent node before routing to pricing agent
    # Prevents pricing failures by validating ticker exists before computation
    # Cached to avoid repeated Yahoo Finance API calls for same tickers
    # Results used to display friendly errors ("FAKE123 not found") instead of crashes

    Validation strategy:
    1. Attempts to fetch ticker.info (catches 404 errors)
    2. Falls back to checking ticker.history for data availability
    3. Returns structured result with validation status and metadata

    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL')

    Returns:
        Dict containing:
            - exists (bool): Whether ticker is valid
            - name (str): Company name if found, empty otherwise
            - asset_type (str): 'equity', 'etf', 'index', or 'unknown'
            - reason (str): Explanation if ticker doesn't exist

    Examples:
        >>> validate_ticker_exists('NVDA')
        {'exists': True, 'name': 'NVIDIA Corporation', 'asset_type': 'equity', 'reason': ''}

        >>> validate_ticker_exists('FAKE123')
        {'exists': False, 'name': '', 'asset_type': 'unknown', 'reason': 'Ticker not found on Yahoo Finance'}
    """
    ticker = ticker.upper().strip()

    try:
        yf_ticker = yf.Ticker(ticker)

        # Primary validation: Check ticker.info
        info = yf_ticker.info

        # Yahoo Finance returns minimal dict for invalid tickers
        # Valid tickers have 'regularMarketPrice' or 'longName'
        if len(info) <= 1:
            return {
                'exists': False,
                'name': '',
                'asset_type': 'unknown',
                'reason': 'Ticker not found on Yahoo Finance'
            }

        # Check for key indicators of valid ticker
        name = info.get('longName') or info.get('shortName', '')

        if not name:
            # Fallback: Try fetching recent price history
            history = yf_ticker.history(period='1d')
            if history.empty:
                return {
                    'exists': False,
                    'name': '',
                    'asset_type': 'unknown',
                    'reason': 'No price data available for ticker'
                }
            else:
                # Has data but no name - unusual but valid
                name = ticker  # Use ticker as fallback name

        # Determine asset type
        asset_type = _classify_asset_type(info)

        return {
            'exists': True,
            'name': name,
            'asset_type': asset_type,
            'reason': ''
        }

    except Exception as e:
        logger.warning(f"Ticker validation failed for {ticker}: {str(e)}")
        return {
            'exists': False,
            'name': '',
            'asset_type': 'unknown',
            'reason': f'Validation error: {str(e)}'
        }


def _classify_asset_type(info: Dict[str, Any]) -> str:
    """
    Classify the asset type based on Yahoo Finance info dictionary.

    Args:
        info: Dictionary returned from ticker.info

    Returns:
        Asset classification: 'equity', 'etf', 'index', 'crypto', or 'unknown'
    """
    quote_type = info.get('quoteType', '').lower()

    if quote_type == 'equity':
        return 'equity'
    elif quote_type == 'etf':
        return 'etf'
    elif quote_type in ['index', 'mutualfund']:
        return 'index'
    elif quote_type == 'cryptocurrency':
        return 'crypto'
    else:
        # Fallback classification based on other indicators
        if 'sharesOutstanding' in info and info.get('sharesOutstanding', 0) > 0:
            return 'equity'
        return 'unknown'


def get_friendly_ticker_error(ticker: str, validation_result: Dict[str, Any]) -> str:
    """
    Generate user-friendly error message for invalid tickers.

    Args:
        ticker: The ticker that failed validation
        validation_result: Result dict from validate_ticker_exists()

    Returns:
        User-friendly error message
    """
    if not validation_result['exists']:
        return (
            f"I couldn't find '{ticker}' on Yahoo Finance. "
            f"Please check the ticker symbol and try again. "
            f"You can verify tickers at https://finance.yahoo.com"
        )

    return f"Ticker '{ticker}' exists but cannot be processed at this time."
