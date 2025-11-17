"""
Chart-related exceptions for explicit error handling.

All chart errors are categorized by failure type to enable
specific error handling strategies.
"""


class ChartError(Exception):
    """Base exception for all chart-related errors."""
    pass


class ChartDataError(ChartError):
    """Failed to fetch market data (network, API, invalid ticker)."""
    pass


class ChartRenderError(ChartError):
    """Failed to render chart (Plotly issue, data format)."""
    pass


class ChartDisplayError(ChartError):
    """Failed to display chart in UI (Chainlit issue)."""
    pass
