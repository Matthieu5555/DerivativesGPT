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

# Works in both .py scripts and .ipynb Jupyter notebooks
if '__file__' in globals():
    notebook_dir = Path(__file__).parent
    project_root = notebook_dir.parent
else:
    # Running in Jupyter - find project root by marker file
    current = Path(os.getcwd())
    project_root = current if (current / 'pyproject.toml').exists() else current.parent

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
# ## Multi-Leg Strategies: Straddle

# %%
print("\n" + "=" * 80)
print("Example 6: Straddle (Long Call + Long Put)")
print("=" * 80)
query6 = "Price a straddle on NVDA at strike $180, expiring in 45 days"
result6 = await test_extraction(query6)

if result6.get('multi_leg'):
    print("\n📊 Multi-Leg Strategy Detected:")
    print(f"  Strategy Type: {result6.get('strategy_type', 'N/A')}")
    print(f"  Number of Legs: {len(result6.get('legs', []))}")

    if result6.get('legs'):
        print("\n  Individual Legs:")
        for i, leg in enumerate(result6['legs'], 1):
            print(f"    Leg {i}: {leg.get('option_type', 'N/A').upper()} @ ${leg.get('strike_price', 'N/A')}")

# %% [markdown]
# ## Multi-Leg Strategies: Iron Condor

# %%
print("\n" + "=" * 80)
print("Example 7: Iron Condor (4 Legs)")
print("=" * 80)
query7 = "Price an iron condor on SPY: buy 440 put, sell 445 put, sell 460 call, buy 465 call, 30 days"
result7 = await test_extraction(query7)

if result7.get('multi_leg'):
    print("\n📊 Multi-Leg Strategy Detected:")
    print(f"  Strategy Type: {result7.get('strategy_type', 'iron_condor')}")

    if result7.get('legs'):
        print(f"\n  {len(result7['legs'])} Legs:")
        for i, leg in enumerate(result7['legs'], 1):
            position = leg.get('position', 'long')
            opt_type = leg.get('option_type', 'N/A')
            strike = leg.get('strike_price', 'N/A')
            print(f"    {i}. {position.upper()} {opt_type.upper()} @ ${strike}")

# %% [markdown]
# ## Multi-Leg Strategies: Bull Call Spread

# %%
print("\n" + "=" * 80)
print("Example 8: Bull Call Spread")
print("=" * 80)
query8 = "Create a bull call spread on AAPL: buy 265 call, sell 275 call, 60 days"
result8 = await test_extraction(query8)

if result8.get('multi_leg'):
    print("\n📊 Spread Strategy:")
    legs = result8.get('legs', [])

    long_leg = next((l for l in legs if l.get('position') == 'long'), None)
    short_leg = next((l for l in legs if l.get('position') == 'short'), None)

    if long_leg and short_leg:
        print(f"  Long:  {long_leg['option_type'].upper()} @ ${long_leg['strike_price']}")
        print(f"  Short: {short_leg['option_type'].upper()} @ ${short_leg['strike_price']}")
        print(f"  Max Profit: ${short_leg['strike_price'] - long_leg['strike_price']} (at expiry if > ${short_leg['strike_price']})")
        print(f"  Max Loss: Premium paid (if < ${long_leg['strike_price']})")
