
# %%
import sys
from pathlib import Path
import os
import getpass
from dotenv import load_dotenv

# Add parent directory to path to import from main codebase
# Works in both .py scripts and .ipynb Jupyter notebooks
if '__file__' in globals():
    # Running as a .py script
    notebook_dir = Path(__file__).parent
    project_root = notebook_dir.parent
else:
    # Running in Jupyter notebook
    # Find project root by looking for pyproject.toml
    current = Path(os.getcwd())
    project_root = current if (current / 'pyproject.toml').exists() else current.parent

sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Load environment variables from .env file
load_dotenv()

# %%
def _set_env(var: str):
    """Helper function to set environment variable if not already set"""
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

# GEMINI_API_KEY is required for embeddings in FAISS vector search
_set_env("GEMINI_API_KEY")

from derivatives_gpt_core.rag.hybrid_retriever import get_rag_retriever

# %%
# The hybrid retriever combines BM25 (keyword search) with FAISS (semantic search)
try:
    retriever = get_rag_retriever()
    print(f"✓ FAISS index loaded: {retriever.index.ntotal} vectors, {len(retriever.metadata)} documents\n")
except Exception as e:
    print(f"⚠ FAISS index not available. Skipping RAG examples.\n")
    retriever = None

# %%
if retriever:
    query = "What are the assumptions of the Black-Scholes model?"

    # Retrieve relevant sources
    results = retriever.retrieve(query)

    print(f"Query: {query}\n")
    print(f"Found {len(results)} relevant sources:\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. Book: {result['book']}")
        print(f"   Location: {result['page']}")
        print(f"   Score: {result['score']:.3f}")
        print(f"   Text: {result['text'][:200]}...")
        print()
else:
    print("Skipping - FAISS index not available")

# %%
if retriever:
    # Test different types of queries
    test_queries = [
        "Explain delta hedging",
        "What is the volatility smile?",
        "How do barrier options work?",
        "What is put-call parity?"
    ]

    print("Testing RAG Retrieval on Multiple Queries:\n")
    for query in test_queries:
        results = retriever.retrieve(query)
        print(f"Query: {query}")
        print(f"  → Found {len(results)} sources")
        if results:
            print(f"  → Top result from: {results[0]['book']} ({results[0]['page']})")
        print()
else:
    print("Skipping - FAISS index not available")
