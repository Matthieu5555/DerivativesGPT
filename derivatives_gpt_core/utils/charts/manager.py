"""
ChartManager - Centralized chart lifecycle management.

Handles chart creation and display with async-safe operations,
caching, and comprehensive error handling.
"""

from typing import Optional, Tuple
import logging
import asyncio
from functools import lru_cache
from datetime import datetime, timedelta
import chainlit as cl

from .exceptions import ChartDataError, ChartRenderError, ChartDisplayError
from .result import ChartResult

logger = logging.getLogger(__name__)


# ============================================================================
# Lazy Dependency Loading
# ============================================================================

_plotly_loaded = False
_yfinance_loaded = False
_plotly_go = None
_yfinance = None


def _ensure_plotly():
    """Lazy load Plotly with error handling."""
    global _plotly_loaded, _plotly_go

    if _plotly_loaded:
        return _plotly_go

    try:
        import plotly.graph_objects as go
        _plotly_go = go
        _plotly_loaded = True
        logger.info("Plotly loaded successfully")
        return _plotly_go
    except ImportError as e:
        raise ChartRenderError("Plotly not installed. Install with: pip install plotly") from e


def _ensure_yfinance():
    """Lazy load yfinance with error handling."""
    global _yfinance_loaded, _yfinance

    if _yfinance_loaded:
        return _yfinance

    try:
        import yfinance as yf
        _yfinance = yf
        _yfinance_loaded = True
        logger.info("yfinance loaded successfully")
        return _yfinance
    except ImportError as e:
        raise ChartDataError("yfinance not installed. Install with: pip install yfinance") from e


# ============================================================================
# ChartManager - Singleton for chart lifecycle management
# ============================================================================

class ChartManager:
    """
    Chart manager with comprehensive error handling.

    Features:
    - Async-safe (runs blocking ops in thread pool)
    - Explicit error handling (no silent failures)
    - Cached data (LRU cache prevents rate limits)
    - Graceful degradation (chart fails → user still gets pricing)
    - Centralized logic (one place to maintain)

    Singleton pattern ensures consistent behavior across codebase.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._cache_max_size = 100
        self._failure_cache = {}  # Track recent failures for cooldown
        self._cooldown_minutes = 1  # Wait 1 minute before retrying failed tickers
        logger.info("ChartManager initialized")

    @lru_cache(maxsize=100)
    def _fetch_market_data_cached(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Tuple[Optional[object], Optional[float]]:
        """
        Fetch and cache market data from yfinance.

        Runs synchronously - must be called from thread pool in async context.

        Args:
            ticker: Stock symbol (e.g., "AAPL")
            start_date: ISO format date string
            end_date: ISO format date string

        Returns:
            (data_frame, spot_price) or (None, None) on failure

        Raises:
            ChartDataError: If data fetch fails
        """
        yf = _ensure_yfinance()

        try:
            logger.info(f"Fetching market data for {ticker} from {start_date} to {end_date}")

            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                timeout=10
            )

            if data is None or data.empty:
                raise ChartDataError(f"No data returned for {ticker}. Ticker may be invalid.")

            # Extract spot price (most recent close)
            spot_price = float(data['Close'].iloc[-1])

            logger.info(f"Successfully fetched data for {ticker}, spot price: ${spot_price:.2f}")
            return data, spot_price

        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                raise ChartDataError(f"Rate limited by Yahoo Finance for {ticker}") from e
            elif "No data found" in str(e) or "invalid" in str(e).lower():
                raise ChartDataError(f"Invalid ticker symbol: {ticker}") from e
            else:
                raise ChartDataError(f"Failed to fetch data for {ticker}: {str(e)}") from e

    def _create_chart_figure_professional(
        self,
        ticker: str,
        lookback_days: int = 252,
        include_volume: bool = True,
        include_sma: bool = True
    ) -> Tuple[object, float]:
        """
        Create professional chart using charting.py implementation.

        Args:
            ticker: Stock symbol
            lookback_days: Days of historical data
            include_volume: Add volume bars
            include_sma: Add moving averages

        Returns:
            (figure, spot_price) tuple

        Raises:
            ChartRenderError: If chart creation fails
        """
        try:
            # Import the professional charting module
            from derivatives_gpt_core.utils.charting import create_price_chart

            figure, spot_price, spot_date = create_price_chart(
                ticker=ticker,
                lookback_days=lookback_days,
                include_volume=include_volume,
                include_sma=include_sma
            )

            if figure is None or spot_price is None or spot_date is None:
                raise ChartRenderError(f"create_price_chart returned None for {ticker}")

            logger.info(f"Successfully created professional chart for {ticker}")
            return figure, spot_price, spot_date

        except Exception as e:
            raise ChartRenderError(f"Failed to create professional chart for {ticker}: {str(e)}") from e

    async def _create_chart_async(
        self,
        ticker: str,
        lookback_days: int = 252,
        include_volume: bool = True,
        include_sma: bool = True
    ) -> Tuple[object, float]:
        """
        Create chart asynchronously using professional charting.py implementation.

        Args:
            ticker: Stock symbol
            lookback_days: Days of historical data
            include_volume: Add volume bars
            include_sma: Add moving averages

        Returns:
            (figure, spot_price)

        Raises:
            ChartDataError: Data fetch failed
            ChartRenderError: Chart creation failed
        """
        # Create professional chart in thread pool (blocking operation)
        loop = asyncio.get_event_loop()
        figure, spot_price, spot_date = await loop.run_in_executor(
            None,  # Use default ThreadPoolExecutor
            self._create_chart_figure_professional,
            ticker.upper(),
            lookback_days,
            include_volume,
            include_sma
        )

        return figure, spot_price, spot_date

    async def display_chart_async(
        self,
        ticker: str,
        lookback_days: int = 252,
        include_volume: bool = True,
        include_sma: bool = True
    ) -> ChartResult:
        """
        Create and display chart in Chainlit UI (async, non-blocking).

        This is the main entry point for displaying charts with safety guardrails:
        - Ticker validation (basic format check)
        - Cooldown period after failures (prevent hammering failed tickers)
        - Timeout protection (5 seconds max)

        Args:
            ticker: Stock symbol (e.g., "AAPL")
            lookback_days: Days of historical data (default: 252 = 1 year)
            include_volume: Add volume bars (default: True)
            include_sma: Add moving averages (default: True)

        Returns:
            ChartResult with success status and spot price (or error)
        """
        ticker = ticker.upper()

        try:
            # 1. Basic ticker validation
            if not ticker or not ticker.isalnum() or len(ticker) > 5:
                raise ChartDataError(f"Invalid ticker format: {ticker}")

            # 2. Check cooldown period for recently failed tickers
            if ticker in self._failure_cache:
                last_failure = self._failure_cache[ticker]
                time_since_failure = datetime.now() - last_failure
                if time_since_failure.total_seconds() < (self._cooldown_minutes * 60):
                    logger.warning(f"Skipping {ticker} - in cooldown period after recent failure")
                    return ChartResult.failure_result(
                        ChartDataError(f"{ticker} in cooldown"),
                        f"Skipping {ticker} - recent failure"
                    )

            # 3. Create and display chart with timeout
            try:
                figure, spot_price, spot_date = await asyncio.wait_for(
                    self._create_chart_async(ticker, lookback_days, include_volume, include_sma),
                    timeout=5.0
                )

                # Display in Chainlit
                fig_element = cl.Plotly(name=f"{ticker}_chart", figure=figure, display="inline")
                await cl.Message(
                    content=f"{ticker} {spot_date} ${spot_price:.2f}",
                    elements=[fig_element]
                ).send()

                # Remove from failure cache on success
                self._failure_cache.pop(ticker, None)

                return ChartResult.success_result(spot_price)

            except asyncio.TimeoutError:
                raise ChartDataError(f"Timeout fetching data for {ticker} (5s limit)")

        except ChartDataError as e:
            # Track failure for cooldown
            self._failure_cache[ticker] = datetime.now()
            logger.warning(f"Chart data error for {ticker}: {e}")
            return ChartResult.failure_result(e, f"Could not fetch data for {ticker}")

        except ChartRenderError as e:
            logger.warning(f"Chart render error for {ticker}: {e}")
            return ChartResult.failure_result(e, f"Could not create chart for {ticker}")

        except ChartDisplayError as e:
            logger.warning(f"Chart display error for {ticker}: {e}")
            return ChartResult.failure_result(e, f"Could not display chart for {ticker}")

        except Exception as e:
            # Unexpected error - log full traceback
            logger.error(f"Unexpected chart error for {ticker}: {e}", exc_info=True)
            return ChartResult.failure_result(e, f"Unexpected error displaying chart for {ticker}")

    async def get_spot_price_async(self, ticker: str) -> Optional[float]:
        """
        Get spot price without displaying chart (lightweight).

        Args:
            ticker: Stock symbol

        Returns:
            Spot price (float) or None if failed
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)  # Just need recent data

            loop = asyncio.get_event_loop()
            _, spot_price = await loop.run_in_executor(
                None,
                self._fetch_market_data_cached,
                ticker.upper(),
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            return spot_price

        except Exception as e:
            logger.warning(f"Failed to fetch spot price for {ticker}: {e}")
            return None
