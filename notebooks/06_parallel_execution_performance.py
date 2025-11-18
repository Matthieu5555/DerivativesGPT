# %% [markdown]
# # Multi-Agent Orchestration and Parallel Execution
# Showcase the actual orchestrator and parallel execution from DerivativesGPT

# %%
import asyncio
import time
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

from derivatives_gpt_core.core.graph.orchestrator_graph import create_orchestrator
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from langchain_core.messages import HumanMessage

# %% [markdown]
# ## Multi-Agent Orchestrator

# %%
# The orchestrator routes between pricing and educational agents
import asyncio
orchestrator = create_orchestrator()

# Visualize the multi-agent orchestration
from derivatives_gpt_core.utils.graph_visualization import display_graph_in_notebook
display_graph_in_notebook(orchestrator)

# It uses both keyword and LLM-based detection for routing
routing_examples = [
    "Price a call option on AAPL",  # -> Pricing Agent
    "Explain the Black-Scholes model",  # -> Educational Agent
    "What are the Greeks?",  # -> Educational Agent
    "Calculate the price of a put option"  # -> Pricing Agent
]

# %% [markdown]
# ## Parallel Market Data Fetching
#
# Note: The pricing agent fetches market data (spot price, volatility, risk-free rate) in parallel.
# This section would demonstrate the performance benefits but requires API keys to run live.

# %%
# Example pattern for parallel data fetching (requires API keys):
# from derivatives_gpt_core.agents.pricing.nodes.fetch_market_data import fetch_market_data
# from derivatives_gpt_core.agents.pricing.nodes.fetch_volatility import fetch_volatility
# from derivatives_gpt_core.agents.pricing.nodes.fetch_risk_free_rate import fetch_risk_free_rate
#
# async def parallel_data_fetch():
#     """Demonstrate parallel fetching of market data"""
#     from derivatives_gpt_core.agents.pricing.state import PricingState
#     state = PricingState(ticker="AAPL")
#
#     # Parallel fetch (as done in the actual agent)
#     tasks = [fetch_market_data(state), fetch_volatility(state), fetch_risk_free_rate(state)]
#     results = await asyncio.gather(*tasks)
#     return results

print("Parallel data fetching pattern: Market data nodes execute concurrently using asyncio.gather()")

# %% [markdown]
# ## Async State Persistence
#
# **Note:** State persistence is handled by LangGraph's built-in checkpointing system.
# The codebase uses standard LangGraph checkpointing patterns.

# %%
print("State persistence is managed by LangGraph's checkpointing system")
print("See .env for CHECKPOINT_DB_PATH configuration")

# %% [markdown]
# ## Parallel Option Pricing

# %%
async def price_option_portfolio():
    """Price multiple options in parallel using the pricing agent"""
    from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent

    graph = create_pricing_agent()

    # Create multiple pricing requests
    queries = [
        "Price a call option on AAPL, strike 150, 30 days",
        "Price a put option on TSLA, strike 200, 60 days",
        "Price an Asian call on SPY, strike 450, 45 days",
        "Price a digital put on MSFT, strike 350, 90 days"
    ]

    start = time.time()

    # Execute all queries in parallel
    tasks = []
    for query in queries:
        state = {"messages": [HumanMessage(content=query)]}
        tasks.append(graph.ainvoke(state))

    results = await asyncio.gather(*tasks)
    total_time = time.time() - start

    return {
        "queries": len(queries),
        "total_time": total_time,
        "avg_time": total_time / len(queries)
    }

# %% [markdown]
# ## Agent Confidence Routing
#
# **Note:** Agent routing is handled internally by the orchestrator.
# It uses both keyword matching and LLM-based classification to route queries.

# %%
print("Agent routing examples:")
print("- 'Price a European call option' → Pricing Agent")
print("- 'What is gamma hedging?' → Educational Agent")
print("- 'Calculate implied volatility' → Pricing Agent")
print("\nRouting uses keyword patterns + LLM classification for ambiguous cases")

# %% [markdown]
# ## Complete Multi-Agent Flow

# %%
async def complete_flow_demo():
    """Demonstrate complete multi-agent orchestration"""
    orchestrator = create_orchestrator()

    # Mixed queries that route to different agents
    queries = [
        "Explain what delta means in options",
        "Price a call option on AAPL at strike 150",
        "How does volatility affect option prices?",
        "Calculate a put option price for TSLA"
    ]

    for query in queries:
        state = BaseAgentState(messages=[HumanMessage(content=query)])

        # Orchestrator routes to appropriate agent
        result = await orchestrator.ainvoke(state)

        # Extract agent used
        agent_used = result.get("agent_used", "unknown")

# %% [markdown]
# ## Performance Comparison

# %%
async def benchmark_execution_modes():
    """Compare different execution modes"""
    from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent

    graph = create_pricing_agent()
    query = "Price a call option on AAPL, strike 150, 30 days"

    # Single execution
    start = time.time()
    state = {"messages": [HumanMessage(content=query)]}
    await graph.ainvoke(state)
    single_time = time.time() - start

    # Batch execution (4 options)
    start = time.time()
    tasks = [graph.ainvoke({"messages": [HumanMessage(content=query)]}) for _ in range(4)]
    await asyncio.gather(*tasks)
    batch_time = time.time() - start

    return {
        "single_execution": single_time,
        "batch_4_parallel": batch_time,
        "batch_avg_time": batch_time / 4,
        "efficiency": (single_time * 4) / batch_time
    }