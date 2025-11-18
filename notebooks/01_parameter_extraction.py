# %% [markdown]
# # Parameter Extraction from Natural Language
# Showcase the actual parameter extraction node from DerivativesGPT pricing agent

# %%
import asyncio
import sys
from pathlib import Path
import os
import getpass
from dotenv import load_dotenv

# Add parent directory to path to import from main codebase
# Works in both notebooks and scripts
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv()

# %% [markdown]
# ## API Key Setup
# This notebook requires API keys based on your LLM_PROVIDER setting:
# - openrouter → OPENROUTER_API_KEY (default)
# - openai → OPENAI_API_KEY
# - gemini → GEMINI_API_KEY
#
# If you have a .env file, it will be loaded automatically.
# Otherwise, you'll be prompted to enter the required API key.

# %%
def _set_env(var: str):
    """Helper function to set environment variable if not already set"""
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

# Determine which API key to request based on LLM_PROVIDER (defaults to openrouter)
llm_provider = os.environ.get("LLM_PROVIDER", "openrouter")

if llm_provider == "openai":
    _set_env("OPENAI_API_KEY")
elif llm_provider in ("gemini", "gemini_finetuned"):
    _set_env("GEMINI_API_KEY")
else:  # openrouter is default
    _set_env("OPENROUTER_API_KEY")

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