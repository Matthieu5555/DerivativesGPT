"""
Main chart building function using function composition.

This module composes all the smaller functions to create the final chart.
Maintains exact same behavior as original create_price_chart().
"""

import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional
import logging

from .data_fetch import fetch_market_data_cached
from .indicators import (
    fix_multiindex_columns,
    add_technical_indicators,
    extract_spot_price,
    truncate_to_lookback,
)
from .traces import (
    create_candlestick_trace,
    create_sma_20_trace,
    create_sma_50_trace,
    create_volume_trace,
)
from .layout import (
    create_subplot_structure,
    configure_layout,
    configure_axes,
)

logger = logging.getLogger(__name__)


# ============================================================================
# MAIN CHART BUILDING FUNCTION (Function Composition)
# ============================================================================

def create_price_chart(
    ticker: str,
    lookback_days: int = 30,
    include_volume: bool = True,
    include_sma: bool = True
) -> tuple[Optional[go.Figure], Optional[float]]:
    """
    Create a professional dark mode price chart for Chainlit display.

    This function creates a candlestick chart with optional volume bars
    and moving averages, optimized for financial analysis.

    Features:
    - Candlestick price chart (OHLC data)
    - Volume bars with color matching price direction
    - Simple Moving Averages (20-day and 50-day)
    - Responsive design (works on mobile and desktop)
    - Professional dark mode color scheme

    Edge cases handled:
    - Ticker not found: Returns (None, None) (graceful failure)
    - Insufficient data for SMA: Skips SMA 50, keeps SMA 20
    - yfinance rate limit (429): Returns (None, None), logs error
    - Empty data: Returns (None, None)

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
        lookback_days: Number of days of history (default 30)
        include_volume: Whether to show volume subplot (default True)
        include_sma: Whether to show moving averages (default True)

    Returns:
        Tuple of (Plotly Figure object, current spot price) or (None, None) on error
        - Figure: ready for cl.Plotly() display
        - Spot price: Most recent closing price (float)

    Example usage:
        fig, spot_price = create_price_chart("AAPL", lookback_days=60)
        if fig:
            await cl.Message(
                elements=[cl.Plotly(name="chart", figure=fig)]
            ).send()
        if spot_price:
            print(f"Current price: ${spot_price:.2f}")
    """
    try:
        # Step 1: Calculate date range with buffer for SMA calculation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 60)  # Extra buffer for SMA

        # Step 2: Fetch data with caching (isolated I/O)
        data = fetch_market_data_cached(
            ticker=ticker,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )

        if data is None or data.empty:
            logger.warning(f"No data available for {ticker}")
            return None, None

        # Step 3: Pure transformations pipeline
        data = fix_multiindex_columns(data)

        # Extract spot price and date BEFORE truncating (most recent close in full dataset)
        current_spot_price = extract_spot_price(data)
        current_spot_date = data.index[-1].strftime('%Y-%m-%d')
        logger.info(f"Extracted spot price for {ticker}: ${current_spot_price:.2f}")

        # Truncate to display window
        data = truncate_to_lookback(data, lookback_days)

        # Calculate technical indicators
        data = add_technical_indicators(data, include_sma=include_sma)

        # Step 4: Create figure structure
        fig = create_subplot_structure(include_volume=include_volume)

        # Step 5: Add price candlestick trace (row 1)
        candlestick_trace = create_candlestick_trace(data)
        fig.add_trace(candlestick_trace, row=1, col=1)

        # Step 6: Add SMA traces if requested (row 1)
        if include_sma:
            sma_20_trace = create_sma_20_trace(data)
            if sma_20_trace:
                fig.add_trace(sma_20_trace, row=1, col=1)

            sma_50_trace = create_sma_50_trace(data)
            if sma_50_trace:
                fig.add_trace(sma_50_trace, row=1, col=1)

        # Step 7: Add volume trace if requested (row 2)
        if include_volume:
            volume_trace = create_volume_trace(data)
            fig.add_trace(volume_trace, row=2, col=1)

        # Step 8: Configure layout and axes
        configure_layout(fig, ticker, lookback_days, include_volume)
        configure_axes(fig, include_volume)

        logger.info(f"Successfully created chart for {ticker} with spot price ${current_spot_price:.2f}")
        return fig, current_spot_price, current_spot_date

    except Exception as e:
        logger.error(f"Chart creation error for {ticker}: {str(e)}", exc_info=True)
        return None, None, None
