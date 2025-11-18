# %% [markdown]
# # Option Pricing with LangChain Tools
# Showcase the actual pricing tools from DerivativesGPT

# %%
import sys
from pathlib import Path

# Add parent directory to path to import from main codebase
sys.path.append(str(Path(__file__).parent.parent))

# Import ACTUAL pricing tools from the codebase
from derivatives_gpt_core.langchain_tools.black_scholes_pricer_tool import price_european_option_tool
from derivatives_gpt_core.langchain_tools.american_option_pricer_tool import price_american_option_tool
from derivatives_gpt_core.langchain_tools.asian_option_pricer_tool import price_asian_option_tool
from derivatives_gpt_core.langchain_tools.digital_option_pricer_tool import price_digital_option_tool

# %% [markdown]
# ## LangChain Tool Integration Pattern

# %%
# These are actual @tool decorated functions that can be bound to LLMs
import inspect
# inspect.getsource(price_european_option_tool)  # View tool implementation

# %% [markdown]
# ## European Option Pricing (Black-Scholes)

# %%
# Direct tool invocation
result = price_european_option_tool.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,  # 3 months
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "is_call": True
})

# %% [markdown]
# ## American Option Pricing (Binomial Tree)

# %%
# American options can be exercised early
american_result = price_american_option_tool.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "is_call": False,  # Put option
    "n_steps": 100
})

# %% [markdown]
# ## Exotic Options: Asian and Digital

# %%
# Asian option (path-dependent)
asian_result = price_asian_option_tool.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "is_call": True,
    "n_simulations": 10000,
    "n_steps": 252  # Daily observations
})

# Digital/Binary option
digital_result = price_digital_option_tool.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry": 0.25,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "is_call": True,
    "payout": 1.0
})

# %% [markdown]
# ## Tool Binding with LangChain

# %%
from langchain_openai import ChatOpenAI

# Bind tools to LLM (this is how the pricing agent uses them)
tools = [
    price_european_option_tool,
    price_american_option_tool,
    price_asian_option_tool,
    price_digital_option_tool
]

# %% [markdown]
# ## Greeks Calculation

# %%
from derivatives_gpt_core.features.vanilla.greeks import calculate_greeks

greeks = calculate_greeks(
    spot_price=100,
    strike_price=105,
    time_to_expiry=0.25,
    risk_free_rate=0.05,
    volatility=0.2,
    is_call=True
)

# %% [markdown]
# ## Parallel Pricing with Async

# %%
import asyncio

async def price_portfolio():
    """Price multiple options in parallel"""
    from derivatives_gpt_core.agents.pricing.nodes.price_instrument import price_instrument
    from derivatives_gpt_core.agents.pricing.state import PricingState

    # Create multiple pricing tasks
    tasks = []
    for strike in [95, 100, 105, 110]:
        state = PricingState(
            ticker="AAPL",
            spot_price=100,
            strike_price=strike,
            time_to_expiry_days=30,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type="call"
        )
        tasks.append(price_instrument(state))

    # Execute in parallel
    results = await asyncio.gather(*tasks)
    return results