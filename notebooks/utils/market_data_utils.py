"""Utilities for market data fetching."""

from typing import Dict
from derivatives_gpt_core.data.market_data.price_provider import SQLPriceProvider
from derivatives_gpt_core.langchain_tools.volatility_tool import VolatilityCalculator

def fetch_spot_price(ticker: str) -> Dict:
    """Fetch current market data from Yahoo Finance."""
    provider = SQLPriceProvider()
    data = provider.get_current_price(ticker)

    return {
        'ticker': ticker,
        'spot': data['regularMarketPrice'],
        'prev_close': data['regularMarketPreviousClose'],
        'volume': data['regularMarketVolume'],
        'change': data['regularMarketPrice'] - data['regularMarketPreviousClose'],
        'change_pct': ((data['regularMarketPrice'] / data['regularMarketPreviousClose']) - 1) * 100,
        'timestamp': data.get('regularMarketTime', 'N/A')
    }

def fetch_volatility(ticker: str, lookback_days: int = 30) -> Dict:
    """Calculate historical volatility."""
    calc = VolatilityCalculator()

    # Historical volatility
    hist_vol = calc._calculate_historical_volatility(ticker, lookback_days)

    # Mock implied volatility (typically higher)
    implied_vol = hist_vol * 1.15

    return {
        'ticker': ticker,
        'historical_vol': hist_vol,
        'implied_vol': implied_vol,
        'lookback_days': lookback_days,
        'vol_spread': implied_vol - hist_vol
    }

def fetch_risk_free_rate() -> float:
    """Get current risk-free rate."""
    # Simplified - using 10Y Treasury approximate
    return 0.045  # 4.5%