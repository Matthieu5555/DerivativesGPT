# %% [markdown]
# # Market Data Fetching from Yahoo Finance
# Real-time market data retrieval
#
# **Note:** This notebook uses Yahoo Finance which does not require API keys.
# All data is fetched through the yfinance library.

# %%
import sys
from pathlib import Path
import os

# Add parent directory to path to import from main codebase
# Works in both notebooks and scripts
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

from notebooks.utils.market_data_utils import fetch_spot_price, fetch_volatility, fetch_risk_free_rate
from notebooks.utils.common import timer
import pandas as pd

# %% [markdown]
# ## Fetch Single Stock Data

# %%
@timer
def get_stock_data(ticker):
    return fetch_spot_price(ticker)

# %% [markdown]
# ## Batch Fetch Multiple Tickers

# %%
tickers = ['AAPL', 'TSLA', 'SPY', 'NVDA', 'MSFT']

@timer
def batch_fetch(tickers):
    return [fetch_spot_price(t) for t in tickers]

# %% [markdown]
# ## Fetch Volatility Data

# %%

# %% [markdown]
# ## Complete Option Pricing Parameters

# %%
ticker = 'SPY'

# %% [markdown]
# ## Error Handling Demo

# %%
# Try invalid ticker
try:
    invalid_data = fetch_spot_price('INVALID123')
except Exception as e:
    pass  # Error handling demonstration