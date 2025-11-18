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

notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

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
#
# Test how the pricing agent extracts parameters from natural language queries

# %%
async def test_extraction(query: str):
    """Test the actual parameter extraction node from pricing agent"""
    print(f"\nQuery: {query}")
    print("-" * 80)

    state = PricingState(messages=[HumanMessage(content=query)])
    result = await extract_parameters(state)

    print(f"Extraction Successful: {result.get('extraction_successful', False)}")
    print(f"Ticker: {result.get('ticker', 'N/A')}")
    print(f"Strike Price: {result.get('strike_price', 'N/A')}")
    print(f"Time to Expiry: {result.get('time_to_expiry_days', 'N/A')} days")
    print(f"Option Type: {result.get('option_type', 'N/A')}")
    print(f"Product Type: {result.get('product_type', 'N/A')}")

    if result.get('missing_info'):
        print(f"Missing Info: {result['missing_info']}")

    return result

# Example 1: Simple vanilla option
print("=" * 80)
print("Example 1: Simple Vanilla Call Option")
print("=" * 80)
query1 = "Price a call option on AAPL with strike 150, expiring in 30 days"
await test_extraction(query1)

# %% [markdown]
# ## Complex Query with Context

# %%
print("\n" + "=" * 80)
print("Example 2: Protective Put with Implied Parameters")
print("=" * 80)
query2 = "I want to buy a protective put on Tesla, strike around $250, 3 months out, assuming 45% vol"
await test_extraction(query2)

# %% [markdown]
# ## Exotic Option Query

# %%
print("\n" + "=" * 80)
print("Example 3: Exotic Barrier Option")
print("=" * 80)
query3 = "Price a down-and-out call on SPY, strike $450, barrier at $420, expiring in 60 days"
await test_extraction(query3)

# %% [markdown]
# ## Multi-Leg Strategy Query

# %%
print("\n" + "=" * 80)
print("Example 4: Multi-Leg Iron Condor Strategy")
print("=" * 80)
query4 = "Create an iron condor on Microsoft with strikes 340/345/355/360, all expiring next month"
await test_extraction(query4)

# %% [markdown]
# ## Ambiguous Query Handling

# %%
print("\n" + "=" * 80)
print("Example 5: Ambiguous Query (should request clarification)")
print("=" * 80)
query5 = "What's the price of an option?"
await test_extraction(query5)

# %% [markdown]
# ## Key Insights
#
# The parameter extraction node demonstrates:
# 1. **Structured Output Parsing**: Converts natural language to structured parameters
# 2. **Context Understanding**: Infers implicit parameters (e.g., "protective put" → put option)
# 3. **Relative Strike Resolution**: Handles "around $250" appropriately
# 4. **Missing Information Detection**: Identifies what needs clarification
# 5. **Product Type Classification**: Maps to specific pricing models (vanilla, barrier, etc.)
