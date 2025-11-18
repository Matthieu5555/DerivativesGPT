# %% [markdown]
# # Option Pricing with LangChain Tools
# Showcase the actual pricing tools from DerivativesGPT
#
# **Note:** This notebook demonstrates direct tool invocation which doesn't require API keys.
# The pricing calculations are done using mathematical formulas (Black-Scholes, Binomial Trees, etc.)

# %%
import sys
from pathlib import Path
import os

# Add parent directory to path to import from main codebase
# Works in both notebooks and scripts
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

# Import ACTUAL pricing tools from the codebase
from derivatives_gpt_core.langchain_tools.black_scholes_tool import price_european_option
from derivatives_gpt_core.langchain_tools.american_option_tool import price_american_option
from derivatives_gpt_core.langchain_tools.geometric_asian_tool import price_geometric_asian_option
from derivatives_gpt_core.langchain_tools.digital_option_tool import price_digital_option

# %% [markdown]
# ## LangChain Tool Integration Pattern

# %%
# These are actual @tool decorated functions that can be bound to LLMs
import inspect
# inspect.getsource(price_european_option)  # View tool implementation

# %% [markdown]
# ## European Option Pricing (Black-Scholes)

# %%
# Direct tool invocation
result = price_european_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,  # 3 months
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "call"
})
print(f"European Call Price: ${result}")

# %% [markdown]
# ## American Option Pricing (Binomial Tree)

# %%
# American options can be exercised early
american_result = price_american_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "put",  # Put option
    "dividend_yield": 0.0
})
print(f"American Put Price: ${american_result}")

# %% [markdown]
# ## Exotic Options: Asian and Digital

# %%
# Asian option (path-dependent)
asian_result = price_geometric_asian_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "call",
    "num_observations": 252  # Daily observations
})
print(f"Geometric Asian Call Price: ${asian_result}")

# Digital/Binary option
digital_result = price_digital_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "call",
    "payout": 1.0
})
print(f"Digital Call Price: ${digital_result}")

# %% [markdown]
# ## Tool Binding with LangChain

# %%
# from langchain_openai import ChatOpenAI

# # Bind tools to LLM (this is how the pricing agent uses them)
# tools = [
#     price_european_option,
#     price_american_option,
#     price_geometric_asian_option,
#     price_digital_option
# ]
# llm = ChatOpenAI(model="gpt-4o-mini")
# llm_with_tools = llm.bind_tools(tools)
# print(f"Bound {len(tools)} pricing tools to LLM")

# Note: Tool binding requires OPENAI_API_KEY to be set
# These tools are automatically bound to the pricing agent's LLM
print("Tools can be bound to LLMs using llm.bind_tools() - see pricing agent implementation")

# %% [markdown]
# ## Parallel Pricing with Async

# %%
import asyncio

async def price_portfolio():
    """Price multiple options in parallel using the pricing tools"""
    # Price multiple strikes in parallel
    tasks = []
    for strike in [95, 100, 105, 110]:
        task = asyncio.to_thread(
            price_european_option.invoke,
            {
                "spot_price": 100,
                "strike_price": strike,
                "time_to_expiry_days": 30,
                "risk_free_rate": 0.05,
                "volatility": 0.2,
                "option_type": "call"
            }
        )
        tasks.append(task)

    # Execute in parallel
    results = await asyncio.gather(*tasks)
    return results

# Run the parallel pricing
results = asyncio.run(price_portfolio())
print("\nPortfolio Pricing Results (different strikes):")
for strike, price in zip([95, 100, 105, 110], results):
    print(f"  Strike ${strike}: ${price}")