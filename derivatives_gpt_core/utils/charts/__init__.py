"""
Chart utilities - Modular chart lifecycle management.

Public API:
- ChartManager: Singleton for chart creation and display
- ChartResult: Immutable result structure
- ChartError, ChartDataError, ChartRenderError, ChartDisplayError: Exceptions

Usage:
    from derivatives_gpt_core.utils.charts import ChartManager

    manager = ChartManager()
    result = await manager.display_chart_async("AAPL")

    if result.success:
        print(f"Spot price: ${result.spot_price:.2f}")
    else:
        print(f"Error: {result.error_message}")
"""

from .exceptions import (
    ChartError,
    ChartDataError,
    ChartRenderError,
    ChartDisplayError
)
from .result import ChartResult
from .manager import ChartManager

__all__ = [
    "ChartManager",
    "ChartResult",
    "ChartError",
    "ChartDataError",
    "ChartRenderError",
    "ChartDisplayError",
]
