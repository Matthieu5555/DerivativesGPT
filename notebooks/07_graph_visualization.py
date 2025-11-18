# %% [markdown]
# # LangGraph Visualization
# Showcase the graph visualization utilities and multi-agent architecture
#
# **Note:** This notebook only visualizes graph structures and doesn't require API keys
# unless you want to actually execute the graphs.

# %%
import sys
from pathlib import Path
import os

# Add parent directory to path to import from main codebase
# Works in both notebooks and scripts
notebook_dir = Path(os.getcwd()) if '__file__' not in globals() else Path(__file__).parent
project_root = notebook_dir.parent
sys.path.insert(0, str(project_root))

from derivatives_gpt_core.utils.graph_visualization import (
    get_graph_mermaid,
    save_graph_visualization,
    display_graph_in_notebook
)
from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent
from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph
from derivatives_gpt_core.core.graph.orchestrator_graph import create_orchestrator

# %% [markdown]
# ## Pricing Agent Graph

# %%
# Create the pricing agent graph
pricing_graph = create_pricing_agent()

# Display in notebook (requires Jupyter)
display_graph_in_notebook(pricing_graph)

# %% [markdown]
# ## Educational Agent Graph

# %%
# Create the educational agent graph
educational_graph = build_educational_agent_graph()

# Display in notebook
display_graph_in_notebook(educational_graph)

# %% [markdown]
# ## Orchestrator Graph (Multi-Agent System)

# %%
# Create the orchestrator graph
import asyncio
orchestrator_graph = create_orchestrator()

# Display in notebook
display_graph_in_notebook(orchestrator_graph)

# %% [markdown]
# ## Export as Mermaid Diagram

# %%
# Get Mermaid diagram as string (for documentation)
pricing_mermaid = get_graph_mermaid(pricing_graph)
print("Pricing Agent Mermaid diagram generated")
print(f"Length: {len(pricing_mermaid)} characters")

# %% [markdown]
# ## Save Visualizations to Files

# %%
# Save all graphs as PNG files for documentation
save_graph_visualization(pricing_graph, "pricing_agent_graph.png", format="png")
save_graph_visualization(educational_graph, "educational_agent_graph.png", format="png")
save_graph_visualization(orchestrator_graph, "orchestrator_graph.png", format="png")

# Save as Mermaid format for GitHub/Markdown docs
save_graph_visualization(pricing_graph, "pricing_agent_graph.mmd", format="mermaid")
save_graph_visualization(educational_graph, "educational_agent_graph.mmd", format="mermaid")
save_graph_visualization(orchestrator_graph, "orchestrator_graph.mmd", format="mermaid")

print("All graphs saved successfully!")

# %% [markdown]
# ## Graph Structure Analysis

# %%
# Examine the pricing agent graph structure
pricing_graph_obj = pricing_graph.get_graph()

print("Pricing Agent Graph Nodes:")
print(f"Total nodes: {len(pricing_graph_obj.nodes)}")
for node in pricing_graph_obj.nodes:
    print(f"  - {node}")

print("\nPricing Agent Graph Edges:")
print(f"Total edges: {len(pricing_graph_obj.edges)}")
for edge in pricing_graph_obj.edges:
    print(f"  {edge.source} → {edge.target}")

# %% [markdown]
# ## Key Architectural Patterns in the Graphs

# %%
print("=" * 60)
print("LangGraph Patterns Demonstrated in DerivativesGPT")
print("=" * 60)

# Pattern 1: Conditional Routing
print("\n1. CONDITIONAL ROUTING")
print("   Pricing Agent:")
for edge in pricing_graph_obj.edges:
    if "extract_parameters" in edge.source:
        print(f"     {edge.source} → {edge.target}")

print("\n   The agent routes based on:")
print("     - Parameter extraction success/failure")
print("     - Missing vs complete information")
print("     - Product type classification")

# Pattern 2: State Management
print("\n2. STATE MANAGEMENT")
print("   Total nodes in pricing agent:", len(pricing_graph_obj.nodes))
print("   Total edges:", len(pricing_graph_obj.edges))
print("   State flows through all nodes as TypedDict")

# Pattern 3: Multi-Agent System
print("\n3. MULTI-AGENT ORCHESTRATION")
print("   Agents in the system:")
print("     - Pricing Agent (handles option calculations)")
print("     - Educational Agent (explains concepts)")
print("     - Orchestrator (routes queries to appropriate agent)")

print("\n" + "=" * 60)
