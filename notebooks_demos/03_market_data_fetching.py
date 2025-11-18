
# %%
import sys
from pathlib import Path
import os

if '__file__' in globals():
    notebook_dir = Path(__file__).parent
    project_root = notebook_dir.parent
else:
    # Running in Jupyter - find project root by marker file
    current = Path(os.getcwd())
    project_root = current if (current / 'pyproject.toml').exists() else current.parent

sys.path.insert(0, str(project_root))

from notebooks.utils.market_data_utils import fetch_spot_price, fetch_volatility, fetch_risk_free_rate
from notebooks.utils.common import timer
import pandas as pd


# %%
ticker = 'AAPL'
print(f"Fetching current price for {ticker}...")

price = fetch_spot_price(ticker)
print(f"\n✓ {ticker} Current Price: ${price:.2f}")

# %%
tickers = ['AAPL', 'TSLA', 'SPY', 'NVDA', 'MSFT']
print(f"Fetching prices for {len(tickers)} tickers...\n")

prices = {}
for ticker in tickers:
    try:
        prices[ticker] = fetch_spot_price(ticker)
        print(f"  {ticker:6s}: ${prices[ticker]:>8.2f}")
    except Exception as e:
        print(f"  {ticker:6s}: Error - {e}")


# %%
ticker = 'SPY'
print(f"Calculating 30-day historical volatility for {ticker}...")

vol = fetch_volatility(ticker, period=30)
print(f"\n✓ {ticker} 30-Day Volatility: {vol:.2%}")

# %%
ticker = 'AAPL'
print(f"Fetching complete pricing parameters for {ticker}...\n")

# Fetch all required parameters
spot = fetch_spot_price(ticker)
vol = fetch_volatility(ticker, period=30)
rfr = fetch_risk_free_rate()

print(f"Complete Parameters for {ticker} Option Pricing:")
print(f"  Spot Price:        ${spot:.2f}")
print(f"  Volatility (30d):  {vol:.2%}")
print(f"  Risk-Free Rate:    {rfr:.2%}")
print(f"\n✓ Ready for option pricing calculations!")