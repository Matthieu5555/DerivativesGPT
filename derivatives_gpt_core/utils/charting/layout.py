"""
Plotly figure layout configuration.

Pure functions for configuring chart appearance.
"""

from plotly.subplots import make_subplots
import plotly.graph_objects as go


# ============================================================================
# LAYOUT BUILDERS (Pure Functions)
# ============================================================================

def create_subplot_structure(include_volume: bool) -> go.Figure:
    """
    Create subplot structure for price chart with optional volume.

    Args:
        include_volume: Whether to include volume subplot

    Returns:
        Plotly Figure with subplots configured
    """
    subplot_specs = [[{"secondary_y": False}]]
    if include_volume:
        subplot_specs.append([{"secondary_y": False}])

    row_heights = [0.7, 0.3] if include_volume else [1.0]
    subplot_titles = ("Price", "Volume") if include_volume else ("Price",)

    fig = make_subplots(
        rows=len(subplot_specs),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=row_heights,
        subplot_titles=subplot_titles
    )

    return fig


def configure_layout(
    fig: go.Figure,
    ticker: str,
    lookback_days: int,
    include_volume: bool
) -> None:
    """
    Configure figure layout for dark mode display.

    Mutates fig in place (Plotly API limitation).

    Args:
        fig: Plotly figure to configure
        ticker: Stock ticker symbol
        lookback_days: Number of days displayed
        include_volume: Whether volume subplot is included
    """
    fig.update_layout(
        template='chainlit_dark',
        title=dict(
            text=f"{ticker} - {lookback_days} Day History",
            x=0.5,
            xanchor='center',
            font=dict(size=18, color='#FFFFFF')
        ),
        xaxis_rangeslider_visible=False,  # Hide range slider for cleaner look
        height=600 if include_volume else 500,
        hovermode='x unified',  # Single hover tooltip for all traces
        showlegend=False,
        margin=dict(l=60, r=30, t=80, b=40)
    )


def configure_axes(fig: go.Figure, include_volume: bool) -> None:
    """
    Configure x-axis and y-axis styling.

    Mutates fig in place (Plotly API limitation).

    Args:
        fig: Plotly figure to configure
        include_volume: Whether volume subplot is included
    """
    # X-axis (time) - show grid on bottom subplot
    fig.update_xaxes(
        showgrid=True,
        gridwidth=0.5,
        row=2 if include_volume else 1,
        col=1
    )

    # Y-axis for price chart
    fig.update_yaxes(
        showgrid=True,
        gridwidth=0.5,
        row=1,
        col=1
    )

    # Y-axis for volume (if included) - less clutter
    if include_volume:
        fig.update_yaxes(
            showgrid=False,
            row=2,
            col=1
        )
