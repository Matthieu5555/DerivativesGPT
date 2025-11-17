"""
Chart display manager with comprehensive error handling.

BACKWARD COMPATIBILITY WRAPPER
This module re-exports from derivatives_gpt_core.utils.charts for backward compatibility.
All implementation has been moved to the charts/ subpackage.

Responsibilities:
- Fetch market data via yfinance (with LRU caching)
- Generate Plotly charts using charting.py
- Display charts in Chainlit UI
- Handle errors with typed exceptions

Architecture:
- ChartManager: Singleton managing chart lifecycle
- Async operations: Runs yfinance in ThreadPoolExecutor (non-blocking)
- Error types: ChartDataError, ChartRenderError, ChartDisplayError
- Graceful degradation: Chart failures don't break pricing workflow

Usage:
    from derivatives_gpt_core.utils.chart_manager import chart_manager

    # In async context (e.g., LangGraph nodes)
    result = await chart_manager.display_chart_async("AAPL")
    if result.success:
        print(f"Spot price: ${result.spot_price:.2f}")
"""

from typing import Optional, Tuple

# Re-export all public API from charts subpackage
from .charts import (
    ChartManager,
    ChartResult,
    ChartError,
    ChartDataError,
    ChartRenderError,
    ChartDisplayError,
)

# Global singleton instance (for backward compatibility)
chart_manager = ChartManager()


# ============================================================================
# Backward compatibility - Drop-in replacement for old create_price_chart
# ============================================================================

async def create_and_display_chart(
    ticker: str,
    lookback_days: int = 252,
    include_volume: bool = True,
    include_sma: bool = True
) -> Tuple[Optional[float], Optional[str]]:
    """
    Backward compatible wrapper for old code.

    Returns:
        (spot_price, error_message) - spot_price is None if failed
    """
    result = await chart_manager.display_chart_async(
        ticker=ticker,
        lookback_days=lookback_days,
        include_volume=include_volume,
        include_sma=include_sma
    )

    if result.success:
        return result.spot_price, None
    else:
        return None, result.error_message


__all__ = [
    "ChartManager",
    "ChartResult",
    "ChartError",
    "ChartDataError",
    "ChartRenderError",
    "ChartDisplayError",
    "chart_manager",
    "create_and_display_chart",
]
