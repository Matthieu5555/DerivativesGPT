# %% [markdown]
# # DerivativesGPT Component Showcase
# Demonstrates individual components without the full orchestrator
#
# This notebook showcases:
# - Direct pricing agent usage
# - Market data fetching
# - RAG retrieval
# - Option pricing calculations
#
# **For full multi-agent orchestration**: Use the Chainlit UI application

# %%
import sys
from pathlib import Path
import os

notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from notebooks.utils.market_data_utils import fetch_spot_price, fetch_volatility, fetch_risk_free_rate
from derivatives_gpt_core.langchain_tools.black_scholes_tool import price_european_option
from derivatives_gpt_core.rag.hybrid_retriever import get_rag_retriever

# %% [markdown]
# ## Component 1: Market Data Fetching

# %%
print("=" * 80)
print("MARKET DATA FETCHING")
print("=" * 80)

ticker = "AAPL"
spot = fetch_spot_price(ticker)
vol = fetch_volatility(ticker, period=30)
rfr = fetch_risk_free_rate()

print(f"\n{ticker} Market Data:")
print(f"  Spot Price: ${spot:.2f}")
print(f"  Volatility: {vol:.2%}")
print(f"  Risk-Free Rate: {rfr:.2%}")

# %% [markdown]
# ## Component 2: Option Pricing

# %%
print("\n" + "=" * 80)
print("OPTION PRICING")
print("=" * 80)

price = price_european_option.invoke({
    "spot_price": spot,
    "strike_price": spot * 1.05,  # 5% OTM
    "time_to_expiry_days": 30,
    "risk_free_rate": rfr,
    "volatility": vol,
    "option_type": "call"
})

print(f"\nEuropean Call Option (30 days, 5% OTM):")
print(f"  Premium: ${price:.2f}")

# %% [markdown]
# ## Component 3: RAG Retrieval

# %%
print("\n" + "=" * 80)
print("RAG RETRIEVAL")
print("=" * 80)

try:
    retriever = get_rag_retriever()
    results = retriever.retrieve("What are the Black-Scholes assumptions?")

    print(f"\nRetrieved {len(results)} sources:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['book']} ({result['page']})")
        print(f"   Score: {result['score']:.3f}")
        print(f"   Text: {result['text'][:150]}...")
except Exception as e:
    print(f"\nRAG not available: {e}")

# %% [markdown]
# ## Key Insights
#
# ### Individual Components Work Independently
# - Market data from Yahoo Finance
# - Pricing calculations using mathematical models
# - RAG retrieval from quantitative finance textbooks
#
# ### Full System Integration
# For the complete multi-agent system with:
# - Intent classification
# - Agent routing
# - Conversation memory
# - Natural language understanding
#
# **Run the Chainlit UI**: `chainlit run chainlit_application_launcher.py`
#
# ### Other Focused Notebooks
# - **01_parameter_extraction.py**: NLP → structured parameters
# - **02_rag_vs_llm.py**: Hybrid retrieval deep dive
# - **03_market_data_fetching.py**: Data provider patterns
# - **04_option_pricing_showcase.py**: All pricing models
# - **07_graph_visualization.py**: Agent graph architecture
