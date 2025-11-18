# %% [markdown]
# # Hybrid RAG System: BM25 + FAISS
# Showcase the actual hybrid retriever from DerivativesGPT

# %%
import sys
from pathlib import Path
import os

# Add parent directory to path to import from main codebase
# Works in both notebooks and scripts
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

from derivatives_gpt_core.agents.educational.rag.hybrid_retriever import HybridRetriever
from derivatives_gpt_core.agents.educational.rag.llm_reformulation import LLMReformulation

# %% [markdown]
# ## Initialize the Hybrid Retriever

# %%
# The hybrid retriever combines BM25 (keyword search) with FAISS (semantic search)
retriever = HybridRetriever()

# Query reformulation for better retrieval
reformulator = LLMReformulation()

# %% [markdown]
# ## Test Query: Black-Scholes Model

# %%
query = "What are the assumptions of the Black-Scholes model?"

# %% [markdown]
# ## Compare Retrieval Methods

# %%
# Compare different retrieval strategies
test_queries = [
    "Explain delta hedging",
    "What is the volatility smile?",
    "How do barrier options work?",
    "What is put-call parity?"
]

# %% [markdown]
# ## Context Filtering with LLM

# %%
# The system uses LLM to filter relevant context
query = "How to price an Asian option?"

# %% [markdown]
# ## RAG vs Pure LLM Response

# %%
async def compare_responses(query: str):
    """Compare RAG-augmented vs pure LLM responses"""
    from derivatives_gpt_core.agents.educational.nodes.search_knowledge import search_knowledge
    from derivatives_gpt_core.agents.educational.state import EducationalAgentState
    from langchain_core.messages import HumanMessage

    # RAG-augmented response
    state = EducationalAgentState(messages=[HumanMessage(content=query)])
    rag_result = await search_knowledge(state)

    return rag_result