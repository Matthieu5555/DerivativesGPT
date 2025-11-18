# %% [markdown]
# # Multi-Agent Orchestration and Parallel Execution
# Showcase the actual orchestrator and parallel execution from DerivativesGPT

# %%
import asyncio
import time
import sys
from pathlib import Path
import os

# Add parent directory to path to import from main codebase
# Works in both notebooks and scripts
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

from derivatives_gpt_core.core.graph.orchestrator_graph import create_orchestrator_graph
from derivatives_gpt_core.core.state.orchestrator import OrchestratorState
from langchain_core.messages import HumanMessage

# %% [markdown]
# ## Multi-Agent Orchestrator

# %%
# The orchestrator routes between pricing and educational agents
import asyncio
orchestrator = asyncio.run(create_orchestrator_graph())

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

# %%
from derivatives_gpt_core.agents.pricing.nodes.fetch_market_data import fetch_market_data
from derivatives_gpt_core.agents.pricing.nodes.fetch_volatility import fetch_volatility
from derivatives_gpt_core.agents.pricing.nodes.fetch_risk_free_rate import fetch_risk_free_rate

async def parallel_data_fetch():
    """Demonstrate parallel fetching of market data"""
    from derivatives_gpt_core.agents.pricing.state import PricingState

    state = PricingState(ticker="AAPL")

    start = time.time()

    # Parallel fetch (as done in the actual agent)
    tasks = [
        fetch_market_data(state),
        fetch_volatility(state),
        fetch_risk_free_rate(state)
    ]

    results = await asyncio.gather(*tasks)
    parallel_time = time.time() - start

    # Sequential comparison
    start = time.time()
    await fetch_market_data(state)
    await fetch_volatility(state)
    await fetch_risk_free_rate(state)
    sequential_time = time.time() - start

    return {
        "parallel_time": parallel_time,
        "sequential_time": sequential_time,
        "speedup": sequential_time / parallel_time
    }

# %% [markdown]
# ## Async State Persistence

# %%
from derivatives_gpt_core.core.state_persistence.async_state_saver import AsyncSQLiteSaver

async def test_state_persistence():
    """Show how state is persisted asynchronously"""
    saver = AsyncSQLiteSaver()

    # Save state asynchronously (non-blocking)
    thread_id = "test-thread-123"
    checkpoint = {
        "messages": ["test message"],
        "agent": "pricing",
        "timestamp": time.time()
    }

    await saver.aput(thread_id, checkpoint)

    # Retrieve state
    retrieved = await saver.aget(thread_id)
    return retrieved

# %% [markdown]
# ## Parallel Option Pricing

# %%
async def price_option_portfolio():
    """Price multiple options in parallel using the pricing agent"""
    from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent_graph

    graph = create_pricing_agent_graph()

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

# %%
from derivatives_gpt_core.core.router.agent_detector import AgentDetector

detector = AgentDetector()

# Test confidence-based routing
test_queries = [
    "Price a European call option",  # High confidence -> Pricing
    "What is gamma hedging?",  # High confidence -> Educational
    "Calculate the implied volatility",  # Medium confidence
    "Show me financial stuff"  # Low confidence -> needs LLM
]

for query in test_queries:
    agent, confidence = detector.detect_agent_with_confidence(query)

# %% [markdown]
# ## Complete Multi-Agent Flow

# %%
async def complete_flow_demo():
    """Demonstrate complete multi-agent orchestration"""
    orchestrator = create_orchestrator_graph()

    # Mixed queries that route to different agents
    queries = [
        "Explain what delta means in options",
        "Price a call option on AAPL at strike 150",
        "How does volatility affect option prices?",
        "Calculate a put option price for TSLA"
    ]

    for query in queries:
        state = OrchestratorState(messages=[HumanMessage(content=query)])

        # Orchestrator routes to appropriate agent
        result = await orchestrator.ainvoke(state)

        # Extract agent used
        agent_used = result.get("agent_used", "unknown")

# %% [markdown]
# ## Performance Comparison

# %%
async def benchmark_execution_modes():
    """Compare different execution modes"""
    from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent_graph

    graph = create_pricing_agent_graph()
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