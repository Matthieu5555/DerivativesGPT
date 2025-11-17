"""
Plotly theme and color configuration for dark mode charts.

Pure data structures - no logic, no side effects.
"""

import plotly.io as pio


# ============================================================================
# DARK MODE THEME CONFIGURATION
# ============================================================================

def setup_chainlit_dark_theme():
    """
    Configure custom Chainlit-optimized dark theme for Plotly.

    This is idempotent - safe to call multiple times.
    Modifies global plotly.io.templates registry.
    """
    # Define custom Chainlit-optimized dark theme
    pio.templates["chainlit_dark"] = pio.templates["plotly_dark"]

    # Customize for better visibility and Chainlit integration
    pio.templates["chainlit_dark"].layout.update({
        # Transparent to inherit Chainlit's background
        'paper_bgcolor': 'rgba(0,0,0,0)',

        # Subtle dark blue-gray for plot area
        'plot_bgcolor': 'rgba(17,25,40,0.7)',

        # Font styling
        'font': {
            'color': '#E0E0E0',
            'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
            'size': 12
        },

        # Title styling
        'title': {
            'font': {'size': 16, 'color': '#FFFFFF', 'family': 'Inter'}
        },

        # X-axis styling (subtle gridlines)
        'xaxis': {
            'gridcolor': 'rgba(99, 110, 123, 0.3)',
            'linecolor': 'rgba(99, 110, 123, 0.5)',
            'zerolinecolor': 'rgba(99, 110, 123, 0.5)',
        },

        # Y-axis styling (subtle gridlines)
        'yaxis': {
            'gridcolor': 'rgba(99, 110, 123, 0.3)',
            'linecolor': 'rgba(99, 110, 123, 0.5)',
            'zerolinecolor': 'rgba(99, 110, 123, 0.5)',
        }
    })


# ============================================================================
# COLOR SCHEME - Financial Industry Standard
# ============================================================================

CHART_COLORS = {
    # Candlestick colors (colorblind-friendly)
    'bullish_candle': '#00D9A3',      # Cyan-green (increasing)
    'bearish_candle': '#FF6B9D',      # Coral-pink (decreasing)

    # Volume colors (50% opacity for subtlety)
    'volume_bullish': 'rgba(0, 217, 163, 0.5)',
    'volume_bearish': 'rgba(255, 107, 157, 0.5)',

    # Moving averages
    'sma_20': '#3B82F6',              # Blue
    'sma_50': '#F59E0B',              # Amber

    # Accent colors
    'current_price': '#10B981',       # Green
    'reference_line': '#6B7280',      # Gray
}


# Auto-initialize theme on import (side effect, but safe and idempotent)
setup_chainlit_dark_theme()
