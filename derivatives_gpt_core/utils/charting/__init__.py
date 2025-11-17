"""
Professional dark mode charting for DerivativesGPT.

This module creates Plotly charts optimized for Chainlit's dark theme using
function composition for maintainability.

Public API:
- create_price_chart(): Main function (same signature as before)
- get_cache_info(): Cache statistics
- clear_all_cache(): Clear market data cache

Usage:
    from derivatives_gpt_core.utils.charting import create_price_chart

    fig, spot_price = create_price_chart("AAPL", lookback_days=60)
    if fig:
        await cl.Message(elements=[cl.Plotly(name="chart", figure=fig)]).send()
"""

# Public API - backward compatible
from .chart_builder import create_price_chart
from .data_fetch import get_cache_info, clear_all_cache, invalidate_cache_for_ticker

# Internal modules (not exported)
# - config: Theme and colors
# - data_fetch: yfinance caching
# - indicators: Pure technical calculations
# - traces: Plotly trace builders
# - layout: Figure layout configuration

__all__ = [
    "create_price_chart",
    "get_cache_info",
    "clear_all_cache",
    "invalidate_cache_for_ticker",
]
