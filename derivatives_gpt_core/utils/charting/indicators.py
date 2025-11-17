"""
Pure technical indicator calculations.

All functions are pure - same input always produces same output.
No side effects, no I/O, no mutations.
"""

import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PURE DATA TRANSFORMATIONS
# ============================================================================

def fix_multiindex_columns(data: pd.DataFrame) -> pd.DataFrame:
    """
    Fix MultiIndex columns that yfinance sometimes returns.

    Args:
        data: DataFrame that might have MultiIndex columns

    Returns:
        DataFrame with single-level column index
    """
    if isinstance(data.columns, pd.MultiIndex):
        data = data.copy()
        data.columns = data.columns.droplevel(1)
    return data


def calculate_sma(data: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculate Simple Moving Average.

    Pure function - no mutations.

    Args:
        data: DataFrame with 'Close' column
        window: Window size for rolling average

    Returns:
        Series with SMA values
    """
    return data['Close'].rolling(window=window).mean()


def add_technical_indicators(data: pd.DataFrame, include_sma: bool = True) -> pd.DataFrame:
    """
    Add technical indicators to data (SMA 20, SMA 50).

    Pure function - returns new DataFrame, doesn't mutate input.

    Args:
        data: DataFrame with OHLCV columns
        include_sma: Whether to calculate SMAs

    Returns:
        New DataFrame with added indicator columns
    """
    data = data.copy()

    if include_sma:
        data['SMA_20'] = calculate_sma(data, window=20)

        # Only calculate SMA 50 if we have enough data
        if len(data) >= 50:
            data['SMA_50'] = calculate_sma(data, window=50)

    return data


def extract_spot_price(data: pd.DataFrame) -> float:
    """
    Extract current spot price (most recent close).

    Pure function.

    Args:
        data: DataFrame with 'Close' column

    Returns:
        Most recent closing price as float
    """
    return float(data['Close'].iloc[-1])


def truncate_to_lookback(data: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    """
    Keep only the most recent N days of data.

    Pure function - returns new DataFrame.

    Args:
        data: Full historical DataFrame
        lookback_days: Number of recent days to keep

    Returns:
        Truncated DataFrame
    """
    if len(data) > lookback_days:
        return data.iloc[-lookback_days:].copy()
    return data.copy()


def generate_volume_colors(data: pd.DataFrame, bullish_color: str, bearish_color: str) -> list[str]:
    """
    Generate volume bar colors based on price direction.

    Pure function - deterministic output.

    Args:
        data: DataFrame with 'Open' and 'Close' columns
        bullish_color: Color for bullish (close >= open) bars
        bearish_color: Color for bearish (close < open) bars

    Returns:
        List of color strings matching DataFrame length
    """
    colors = [
        bullish_color if row['Close'] >= row['Open'] else bearish_color
        for _, row in data.iterrows()
    ]
    return colors
