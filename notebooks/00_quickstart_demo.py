# %% [markdown]
# # DerivativesGPT Quickstart Demo
# End-to-end demonstration of the multi-agent derivatives pricing system
#
# This notebook showcases:
# - Multi-agent orchestration (Pricing + Educational agents)
# - Parameter extraction from natural language
# - Real-time market data fetching
# - Option pricing with multiple models
# - RAG-augmented educational responses

# %%
import asyncio
import sys
from pathlib import Path
import os
import getpass
from dotenv import load_dotenv

# Setup project paths
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

# Change to project root for correct file paths
original_cwd = os.getcwd()
os.chdir(project_root)

load_dotenv()

# %% [markdown]
# ## API Key Setup
# Required keys (at minimum one of):
# - **OPENROUTER_API_KEY** (recommended, default)
# - **OPENAI_API_KEY** (if using OpenAI)
# - **GEMINI_API_KEY** (if using Gemini, also needed for RAG embeddings)
#
# Optional for enhanced features:
# - **LANGSMITH_API_KEY** (for tracing and observability)

# %%
def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

# Set up based on LLM provider
llm_provider = os.environ.get("LLM_PROVIDER", "openrouter")

if llm_provider == "openai":
    _set_env("OPENAI_API_KEY")
elif llm_provider in ("gemini", "gemini_finetuned"):
    _set_env("GEMINI_API_KEY")
else:
    _set_env("OPENROUTER_API_KEY")

# Import core components
from derivatives_gpt_core.core.graph.orchestrator_graph import create_orchestrator
from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent
from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph
from langchain_core.messages import HumanMessage

# %% [markdown]
# ## System Architecture Overview
#
# DerivativesGPT uses a **multi-agent architecture** with LangGraph:
#
# 1. **Orchestrator**: Routes queries to specialized agents
# 2. **Pricing Agent**: Handles option pricing requests
# 3. **Educational Agent**: Explains financial concepts with RAG
#
# Each agent is a compiled LangGraph with nodes, edges, and state management.

# %%
# Create the orchestrator (coordinates all agents)
print("Building multi-agent orchestrator...")
graph = create_orchestrator()
print("✓ Orchestrator ready with Pricing and Educational agents\n")

# %% [markdown]
# ## Example 1: Simple Option Pricing Request

# %%
print("=" * 80)
print("EXAMPLE 1: Vanilla Option Pricing")
print("=" * 80)

query1 = "Price a call option on AAPL, strike $150, expiring in 30 days"
print(f"\nUser Query: {query1}\n")

config = {"configurable": {"thread_id": "demo_pricing"}}
result1 = graph.invoke({"messages": [HumanMessage(content=query1)]}, config)

# Display final response
final_message = result1["messages"][-1]
print("Agent Response:")
print(final_message.content)

# %% [markdown]
# ## Example 2: Educational Query with RAG

# %%
print("\n" + "=" * 80)
print("EXAMPLE 2: Educational Query (RAG-Augmented)")
print("=" * 80)

query2 = "Explain the Black-Scholes model assumptions"
print(f"\nUser Query: {query2}\n")

config2 = {"configurable": {"thread_id": "demo_education"}}
result2 = graph.invoke({"messages": [HumanMessage(content=query2)]}, config2)

final_message2 = result2["messages"][-1]
print("Agent Response:")
print(final_message2.content)

# %% [markdown]
# ## Example 3: Exotic Option (Barrier Option)

# %%
print("\n" + "=" * 80)
print("EXAMPLE 3: Exotic Barrier Option")
print("=" * 80)

query3 = "Price a down-and-out call on SPY, strike $450, barrier at $420, 60 days to expiry"
print(f"\nUser Query: {query3}\n")

config3 = {"configurable": {"thread_id": "demo_exotic"}}
result3 = graph.invoke({"messages": [HumanMessage(content=query3)]}, config3)

final_message3 = result3["messages"][-1]
print("Agent Response:")
print(final_message3.content)

# %% [markdown]
# ## Example 4: Multi-Leg Strategy

# %%
print("\n" + "=" * 80)
print("EXAMPLE 4: Iron Condor Strategy")
print("=" * 80)

query4 = "Create an iron condor on NVDA with strikes 140/145/160/165, expiring in 45 days"
print(f"\nUser Query: {query4}\n")

config4 = {"configurable": {"thread_id": "demo_strategy"}}
result4 = graph.invoke({"messages": [HumanMessage(content=query4)]}, config4)

final_message4 = result4["messages"][-1]
print("Agent Response:")
print(final_message4.content)

# %% [markdown]
# ## Example 5: Follow-up Conversation

# %%
print("\n" + "=" * 80)
print("EXAMPLE 5: Follow-up Conversation with Memory")
print("=" * 80)

# First query
query5a = "What is delta hedging?"
print(f"\nUser: {query5a}")

config5 = {"configurable": {"thread_id": "demo_followup"}}
result5a = graph.invoke({"messages": [HumanMessage(content=query5a)]}, config5)
print(f"Agent: {result5a['messages'][-1].content[:200]}...\n")

# Follow-up query (uses same thread_id for memory)
query5b = "Can you give me an example with actual numbers?"
print(f"User: {query5b}")

result5b = graph.invoke({"messages": [HumanMessage(content=query5b)]}, config5)
print(f"Agent: {result5b['messages'][-1].content}")

# %% [markdown]
# ## Key Features Demonstrated
#
# ### 1. Intelligent Agent Routing
# - The orchestrator automatically detects intent (pricing vs educational)
# - Routes to the appropriate specialized agent
#
# ### 2. Natural Language Understanding
# - Extracts parameters from conversational queries
# - Handles relative strikes, date descriptions, strategy names
#
# ### 3. Real-Time Market Data
# - Fetches spot prices from Yahoo Finance
# - Calculates implied volatility
# - Uses current risk-free rates
#
# ### 4. Multiple Pricing Models
# - **Black-Scholes**: European options
# - **Binomial Trees**: American options
# - **Closed-form**: Exotic options (barrier, Asian, digital)
# - **Portfolio**: Multi-leg strategies
#
# ### 5. RAG-Augmented Education
# - Retrieves from 11 derivatives textbooks
# - Hybrid BM25 + FAISS semantic search
# - Cites sources with book names and chapters
#
# ### 6. Conversation Memory
# - Checkpointed state across turns
# - Context-aware follow-ups
# - Thread-based conversation tracking
#
# ## Next Steps
#
# Explore individual components in detail:
# - **01_parameter_extraction.py**: Deep dive on NLP parameter extraction
# - **02_rag_vs_llm.py**: Compare RAG vs pure LLM responses
# - **03_market_data_fetching.py**: Market data providers and caching
# - **04_option_pricing_showcase.py**: All pricing models side-by-side
# - **07_graph_visualization.py**: Visualize agent graphs and routing
