"""Utilities for market data fetching."""

from typing import Dict
from derivatives_gpt_core.data.market_data.price_provider import SQLPriceProvider
from derivatives_gpt_core.langchain_tools.volatility_tool import estimate_annualized_volatility
from derivatives_gpt_core.langchain_tools.risk_free_rate_tool import estimate_risk_free_rate
import yfinance as yf
import numpy as np

def fetch_spot_price(ticker: str) -> float:
    """Fetch current spot price from Yahoo Finance."""
    try:
        ticker_obj = yf.Ticker(ticker)
        # Get the most recent close price
        hist = ticker_obj.history(period="1d")
        if hist.empty:
            raise ValueError(f"No data available for ticker {ticker}")
        price = hist['Close'].iloc[-1]
        return float(price)
    except Exception as e:
        raise ValueError(f"Failed to fetch price for {ticker}: {str(e)}")

def fetch_volatility(ticker: str, period: int = 30) -> float:
    """Calculate historical volatility."""
    try:
        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(period=f"{period}d")
        returns = np.log(hist['Close'] / hist['Close'].shift(1))
        vol = returns.std() * np.sqrt(252)
        return vol
    except:
        return 0.25  # Fallback

def fetch_risk_free_rate() -> float:
    """Get current risk-free rate using actual tool."""
    # Use the actual risk-free rate tool (requires time horizon in days)
    result = estimate_risk_free_rate.invoke({"time_horizon_days": 30})

    # Parse the rate from the result
    try:
        rate = float(result.split(":")[-1].strip().replace("%", "")) / 100
    except:
        rate = 0.045  # Fallback

    return rate