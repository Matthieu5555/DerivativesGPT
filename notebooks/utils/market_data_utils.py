"""Utilities for market data fetching."""

from typing import Dict
from derivatives_gpt_core.data.market_data.price_provider import SQLPriceProvider
from derivatives_gpt_core.langchain_tools.volatility_tool import estimate_annualized_volatility
from derivatives_gpt_core.langchain_tools.risk_free_rate_tool import get_risk_free_rate_tool
import yfinance as yf
import numpy as np

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
    """Calculate historical volatility using actual tool."""
    # Use the actual volatility tool
    vol_str = estimate_annualized_volatility(ticker, lookback_days)

    # Parse the volatility from the string result
    # The tool returns a string like "Annualized volatility: 0.2342"
    try:
        hist_vol = float(vol_str.split(":")[-1].strip())
    except:
        # Fallback calculation
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period=f"{lookback_days}d")
        returns = np.log(hist['Close'] / hist['Close'].shift(1))
        hist_vol = returns.std() * np.sqrt(252)

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
    """Get current risk-free rate using actual tool."""
    # Use the actual risk-free rate tool
    result = get_risk_free_rate_tool.invoke({})

    # Parse the rate from the result
    try:
        rate = float(result.split(":")[-1].strip().replace("%", "")) / 100
    except:
        rate = 0.045  # Fallback

    return rate