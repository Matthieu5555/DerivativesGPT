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

from derivatives_gpt_core.agents.pricing.nodes.extract_parameters import extract_parameters
from derivatives_gpt_core.agents.pricing.state import PricingState
from langchain_core.messages import HumanMessage

# %%
async def test_extraction(query: str):
    """Test the actual parameter extraction node from pricing agent"""
    print(f"\nQuery: {query}")

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
print("Example 1: Simple Vanilla Call Option")
query1 = "Price a call option on AAPL with strike 150, expiring in 30 days"
await test_extraction(query1)

# %%
print("Example 2: Protective Put with Implied Parameters")
query2 = "I want to buy a protective put on Tesla, strike around $250, 3 months out, assuming 45% vol"
await test_extraction(query2)

