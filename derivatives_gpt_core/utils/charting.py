"""
Professional dark mode charting for DerivativesGPT.

BACKWARD COMPATIBILITY WRAPPER
This module re-exports from derivatives_gpt_core.utils.charting for backward compatibility.
All implementation has been split into focused modules using function composition.

Key features:
- Dark mode optimized color palette
- yfinance data caching to avoid rate limits (429 errors)
- Candlestick charts with volume bars
- Moving averages (SMA 20, SMA 50)
- Responsive design for mobile and desktop

Module structure:
- charting/config.py: Theme and color configuration
- charting/data_fetch.py: yfinance caching layer
- charting/indicators.py: Pure technical calculations
- charting/traces.py: Plotly trace builders
- charting/layout.py: Figure layout configuration
- charting/chart_builder.py: Main composition function

Called by: chainlit_application_launcher.py, chart_manager.py
"""

# Re-export all public API from charting subpackage
from .charting import (
    create_price_chart,
    get_cache_info,
    clear_all_cache,
    invalidate_cache_for_ticker,
)

# Alias for backward compatibility (some code might use this name)
_invalidate_cache_for_ticker = invalidate_cache_for_ticker

__all__ = [
    "create_price_chart",
    "get_cache_info",
    "clear_all_cache",
    "invalidate_cache_for_ticker",
]
