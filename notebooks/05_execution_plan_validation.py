# %% [markdown]
# # LangGraph Execution Flow
# Showcase the actual pricing agent graph execution from DerivativesGPT

# %%
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

from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent
from derivatives_gpt_core.agents.pricing.state import PricingState
from langchain_core.messages import HumanMessage

# %% [markdown]
# ## Pricing Agent Graph Structure

# %%
# Create the actual pricing agent graph
graph = create_pricing_agent()

# Visualize the graph (requires Jupyter with graphviz)
from derivatives_gpt_core.utils.graph_visualization import display_graph_in_notebook
display_graph_in_notebook(graph)

# %% [markdown]
# ## Node Execution Flow

# %%
# The pricing agent has these nodes:
nodes = [
    "extract_parameters",     # Extract option parameters from query
    "check_missing_params",   # Check what's missing
    "fetch_market_data",      # Get spot price from Yahoo Finance
    "fetch_volatility",       # Calculate historical volatility
    "fetch_risk_free_rate",   # Get risk-free rate
    "create_execution_plan",  # Plan parallel execution
    "validate_parameters",    # Validate all parameters
    "price_instrument",       # Price the option
    "generate_response",      # Format the response
    "should_continue",        # Conditional edge
    "router"                  # Route based on state
]

# %% [markdown]
# ## Conditional Routing Example

# %%
async def trace_execution(query: str):
    """Trace the execution path through the graph"""
    state = PricingState(messages=[HumanMessage(content=query)])

    # The graph will execute nodes based on conditional edges
    # Path depends on what parameters are provided vs missing

    # Example paths:
    # 1. Full params provided: extract → validate → price → response
    # 2. Missing spot: extract → check → fetch_market → validate → price → response
    # 3. Complex query: extract → check → create_plan → parallel_fetch → price → response

    result = await graph.ainvoke(state)
    return result

# %% [markdown]
# ## Parallel Execution Plan

# %%
from derivatives_gpt_core.agents.pricing.nodes.create_execution_plan import create_execution_plan

async def show_execution_plan(query: str):
    """Show how the agent creates an execution plan"""
    state = PricingState(messages=[HumanMessage(content=query)])

    # Extract parameters first
    from derivatives_gpt_core.agents.pricing.nodes.extract_parameters import extract_parameters
    state = await extract_parameters(state)

    # Create execution plan
    state = await create_execution_plan(state)

    # The plan shows which tasks can run in parallel
    return state.get("execution_plan")

# %% [markdown]
# ## State Management Pattern

# %%
# PricingState is a TypedDict that flows through the graph
from typing import get_type_hints

# Show the state structure
state_fields = get_type_hints(PricingState)
# Display: {field: type_hint for field, type_hint in state_fields.items()}

# %% [markdown]
# ## Error Handling and Retries

# %%
async def test_error_handling():
    """Test how the graph handles errors"""
    # Invalid query
    state = PricingState(messages=[HumanMessage(content="Price something")])

    # The graph has built-in error handling
    # Missing parameters trigger specific nodes
    # API failures trigger retries

    result = await graph.ainvoke(state)
    return result

# %% [markdown]
# ## Complete Execution Example

# %%
import asyncio

async def full_execution_demo():
    """Complete execution from query to response"""
    query = "Price a European call option on AAPL with strike $150, expiring in 30 days"

    state = PricingState(messages=[HumanMessage(content=query)])

    # Execute the full graph
    result = await graph.ainvoke(state)

    # The result contains:
    # - Extracted parameters
    # - Fetched market data
    # - Calculated price
    # - Formatted response

    return result