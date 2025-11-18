# %% [markdown]
# # Market Data Fetching from Yahoo Finance
# Real-time market data retrieval

# %%
import sys
from pathlib import Path

# Add parent directory to path to import from main codebase
sys.path.append(str(Path(__file__).parent.parent))

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