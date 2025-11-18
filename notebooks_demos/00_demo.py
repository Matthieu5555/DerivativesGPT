# %%
import sys
from pathlib import Path
import os

# Works in both .py scripts and .ipynb Jupyter notebooks
if '__file__' in globals():
    notebook_dir = Path(__file__).parent
    project_root = notebook_dir.parent
else:
    # Running in Jupyter - find project root by marker file
    current = Path(os.getcwd())
    project_root = current if (current / 'pyproject.toml').exists() else current.parent

sys.path.insert(0, str(project_root))
os.chdir(project_root)

from notebooks.utils.market_data_utils import fetch_spot_price, fetch_volatility, fetch_risk_free_rate
from derivatives_gpt_core.langchain_tools.black_scholes_tool import price_european_option
from derivatives_gpt_core.rag.hybrid_retriever import get_rag_retriever

# %%
print("MARKET DATA FETCHING")

ticker = "AAPL"
spot = fetch_spot_price(ticker)
vol = fetch_volatility(ticker, period=30)
rfr = fetch_risk_free_rate()

print(f"\n{ticker} Market Data:")
print(f"  Spot Price: ${spot:.2f}")
print(f"  Volatility: {vol:.2%}")
print(f"  Risk-Free Rate: {rfr:.2%}")

# %%
print("OPTION PRICING")

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

# %%
print("RAG RETRIEVAL")

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
