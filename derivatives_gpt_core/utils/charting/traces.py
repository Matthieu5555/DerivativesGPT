"""
Plotly trace creation functions.

Pure functions that create Plotly trace objects.
Each function is focused on one trace type.
"""

import plotly.graph_objects as go
import pandas as pd
from typing import Optional

from .config import CHART_COLORS
from .indicators import generate_volume_colors


# ============================================================================
# TRACE BUILDERS (Pure Functions)
# ============================================================================

def create_candlestick_trace(data: pd.DataFrame) -> go.Candlestick:
    """
    Create candlestick trace for price chart.

    Pure function - deterministic output.

    Args:
        data: DataFrame with OHLC columns and DatetimeIndex

    Returns:
        Plotly Candlestick trace object
    """
    return go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price',
        increasing_line_color=CHART_COLORS['bullish_candle'],
        decreasing_line_color=CHART_COLORS['bearish_candle'],
        increasing_fillcolor=CHART_COLORS['bullish_candle'],
        decreasing_fillcolor=CHART_COLORS['bearish_candle'],
        line=dict(width=1),
    )


def create_sma_20_trace(data: pd.DataFrame) -> Optional[go.Scatter]:
    """
    Create SMA 20 trace if data is available.

    Args:
        data: DataFrame with 'SMA_20' column

    Returns:
        Plotly Scatter trace or None if no valid data
    """
    if 'SMA_20' not in data.columns or data['SMA_20'].isna().all():
        return None

    return go.Scatter(
        x=data.index,
        y=data['SMA_20'],
        name='SMA 20',
        line=dict(color=CHART_COLORS['sma_20'], width=1.5, dash='dot'),
        opacity=0.7,
        hovertemplate='SMA 20: $%{y:.2f}<extra></extra>'
    )


def create_sma_50_trace(data: pd.DataFrame) -> Optional[go.Scatter]:
    """
    Create SMA 50 trace if data is available.

    Args:
        data: DataFrame with 'SMA_50' column

    Returns:
        Plotly Scatter trace or None if no valid data
    """
    if 'SMA_50' not in data.columns or data['SMA_50'].isna().all():
        return None

    return go.Scatter(
        x=data.index,
        y=data['SMA_50'],
        name='SMA 50',
        line=dict(color=CHART_COLORS['sma_50'], width=1.5, dash='dash'),
        opacity=0.7,
        hovertemplate='SMA 50: $%{y:.2f}<extra></extra>'
    )


def create_volume_trace(data: pd.DataFrame) -> go.Bar:
    """
    Create volume bar trace with directional coloring.

    Args:
        data: DataFrame with 'Volume', 'Open', 'Close' columns

    Returns:
        Plotly Bar trace object
    """
    colors = generate_volume_colors(
        data,
        bullish_color=CHART_COLORS['volume_bullish'],
        bearish_color=CHART_COLORS['volume_bearish']
    )

    return go.Bar(
        x=data.index,
        y=data['Volume'],
        name='Volume',
        marker=dict(color=colors, line=dict(width=0)),
        showlegend=False,
        hovertemplate='Volume: %{y:,.0f}<extra></extra>'
    )
