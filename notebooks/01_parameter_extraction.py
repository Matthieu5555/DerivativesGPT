# %% [markdown]
# # Parameter Extraction from Natural Language
# Showcase the actual parameter extraction node from DerivativesGPT pricing agent

# %%
import asyncio
import sys
from pathlib import Path
import os

# Add parent directory to path to import from main codebase
# Works in both notebooks and scripts
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

# Import the ACTUAL parameter extraction from the codebase
from derivatives_gpt_core.agents.pricing.nodes.extract_parameters import extract_parameters
from derivatives_gpt_core.agents.pricing.state import PricingState
from langchain_core.messages import HumanMessage

# %% [markdown]
# ## Direct Parameter Extraction using Pricing Agent Node

# %%
async def test_extraction(query: str):
    """Test the actual parameter extraction node from pricing agent"""
    state = PricingState(messages=[HumanMessage(content=query)])
    result = await extract_parameters(state)
    return result

# Example 1: Simple vanilla option
query1 = "Price a call option on AAPL with strike 150, expiring in 30 days"

# %% [markdown]
# ## Complex Query with Context

# %%
query2 = "I want to buy a protective put on Tesla, strike around $250, 3 months out, assuming 45% vol"

# %% [markdown]
# ## Exotic Option Query

# %%
query3 = "Price a down-and-out call on SPY, strike $450, barrier at $420, expiring in 60 days"

# %% [markdown]
# ## Multi-Leg Strategy Query

# %%
query4 = "Create an iron condor on Microsoft with strikes 340/345/355/360, all expiring next month"

# %% [markdown]
# ## Ambiguous Query Handling

# %%
query5 = "What's the price of an option?"