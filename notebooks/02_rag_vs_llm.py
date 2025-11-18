# %% [markdown]
# # Hybrid RAG System: BM25 + FAISS
# Showcase the actual hybrid retriever from DerivativesGPT

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

# IMPORTANT: Change working directory to project root for RAG paths to resolve correctly
original_cwd = os.getcwd()
os.chdir(project_root)

# Load environment variables from .env file
load_dotenv()

# %% [markdown]
# ## API Key Setup
# This notebook requires:
# - GEMINI_API_KEY: For text embeddings (Google text-embedding-004 model) used in RAG
#
# If you have a .env file, it will be loaded automatically.
# Otherwise, you'll be prompted to enter the required API key.

# %%
def _set_env(var: str):
    """Helper function to set environment variable if not already set"""
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

# GEMINI_API_KEY is required for embeddings in FAISS vector search
_set_env("GEMINI_API_KEY")

from derivatives_gpt_core.rag.hybrid_retriever import HybridRAGRetriever, get_rag_retriever

# %% [markdown]
# ## Initialize the Hybrid Retriever

# %%
# The hybrid retriever combines BM25 (keyword search) with FAISS (semantic search)
try:
    retriever = get_rag_retriever()
    print(f"✓ FAISS index loaded: {retriever.index.ntotal} vectors, {len(retriever.metadata)} documents\n")
except Exception as e:
    print(f"⚠ FAISS index not available. Skipping RAG examples.\n")
    retriever = None

# %% [markdown]
# ## Test Query: Black-Scholes Model

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

# %% [markdown]
# ## Multiple Test Queries

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

# %% [markdown]
# ## Hybrid Retrieval Architecture

# %%
# The hybrid retriever uses a two-stage process:
print("""
Hybrid RAG Architecture:
========================

Stage 1: BM25 Keyword Search
  - Fast lexical matching on all documents
  - Returns top 20 candidates based on term frequency
  - Good for exact keyword matches

Stage 2: FAISS Vector Reranking
  - Embeds query using Google text-embedding-004
  - Computes cosine similarity with BM25 candidates
  - Returns top 3 most semantically relevant

Advantages:
  - Fast: BM25 narrows search space first
  - Accurate: Vector similarity captures semantic meaning
  - Best of both: Keyword precision + semantic understanding
""")