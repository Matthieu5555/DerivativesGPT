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
# ## Multi-Agent Orchestration
#
# The orchestrator graph coordinates the pricing and educational agents:
# - Classifies user intent (pricing vs educational vs off-topic)
# - Routes to the appropriate specialized agent
# - Handles agent transfers for complex queries
# - Manages conversation context and memory
#
# **Note**: The orchestrator graph visualization is skipped in this notebook
# to avoid async complexity. See the pricing and educational graphs above
# for the core agent architectures.

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

# Save as Mermaid format for GitHub/Markdown docs
save_graph_visualization(pricing_graph, "pricing_agent_graph.mmd", format="mermaid")
save_graph_visualization(educational_graph, "educational_agent_graph.mmd", format="mermaid")

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
# ## Key Architectural Patterns Demonstrated
#
# ### 1. Conditional Routing
# The pricing agent uses conditional edges to route based on:
# - Parameter extraction success/failure
# - Missing vs complete information
# - Product type classification
#
# ### 2. State Management
# - State flows through all nodes as TypedDict
# - Reducers manage state updates (e.g., `add_messages`)
# - Checkpointers enable conversation memory
#
# ### 3. Multi-Agent Orchestration
# The system includes:
# - **Pricing Agent**: Handles option calculations and market data
# - **Educational Agent**: Explains concepts with pedagogical patterns
# - **Orchestrator**: Routes queries to appropriate agent based on intent
