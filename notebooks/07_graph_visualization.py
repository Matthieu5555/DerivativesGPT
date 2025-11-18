# %% [markdown]
# # LangGraph Multi-Agent Architecture
# Visualize the three-tier agent system

# %%
import sys
from pathlib import Path
import os

# Works in both .py scripts and .ipynb Jupyter notebooks
if '__file__' in globals():
    notebook_dir = Path(__file__).parent
    project_root = notebook_dir.parent
else:
    current = Path(os.getcwd())
    project_root = current if (current / 'pyproject.toml').exists() else current.parent

sys.path.insert(0, str(project_root))

from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent
from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph

# %% [markdown]
# ## Pricing Agent Graph

# %%
pricing_graph = create_pricing_agent()
pricing_nodes = list(pricing_graph.get_graph().nodes.keys())
pricing_edges = list(pricing_graph.get_graph().edges)

print("PRICING AGENT")
print(f"Nodes ({len(pricing_nodes)}): {', '.join(pricing_nodes)}")
print(f"\nEdges ({len(pricing_edges)}):")
for edge in pricing_edges:
    print(f"  {edge.source} → {edge.target}")

# %% [markdown]
# ## Educational Agent Graph

# %%
educational_graph = build_educational_agent_graph()
edu_nodes = list(educational_graph.get_graph().nodes.keys())
edu_edges = list(educational_graph.get_graph().edges)

print("EDUCATIONAL AGENT")
print(f"Nodes ({len(edu_nodes)}): {', '.join(edu_nodes)}")
print(f"\nEdges ({len(edu_edges)}):")
for edge in edu_edges:
    print(f"  {edge.source} → {edge.target}")

# %% [markdown]
# ## Orchestrator Agent (Multi-Agent Router)

# %%
print("ORCHESTRATOR (Multi-Agent Router)")
print("\nRouting Logic:")
print("  1. classify_intent → Detect if query is pricing/educational/off-topic")
print("  2. route_to_agent → Send to pricing_agent or educational_agent")
print("  3. pricing_agent → Full pricing graph execution")
print("  4. educational_agent → Full educational graph execution")
print("  5. Returns aggregated results with conversation memory")

print("\nKey Features:")
print("  - Intent classification with LLM")
print("  - Agent detection from conversation context")
print("  - Follow-up detection (maintains same agent)")
print("  - Checkpoint-based conversation memory")
print("  - Off-topic query handling")

# %% [markdown]
# ## Architecture Summary
#
# **Three-Tier System:**
#
# 1. **Orchestrator** (Top Level)
#    - Classifies user intent (pricing/educational/off-topic)
#    - Routes to specialized agents
#    - Manages conversation context
#
# 2. **Pricing Agent** (Specialized)
#    - Parameter extraction → validation → decomposition
#    - Market data fetching (parallel execution)
#    - Option pricing (Black-Scholes, American, Exotic)
#    - Strategy aggregation and narration
#
# 3. **Educational Agent** (Specialized)
#    - RAG retrieval from textbooks
#    - Explanation generation with citations
#    - Comprehension assessment
#    - Adaptive teaching (rewrite if unclear)
