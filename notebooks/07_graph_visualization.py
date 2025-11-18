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
# Works in both .py scripts and .ipynb Jupyter notebooks
if '__file__' in globals():
    notebook_dir = Path(__file__).parent
    project_root = notebook_dir.parent
else:
    # Running in Jupyter - find project root by marker file
    current = Path(os.getcwd())
    project_root = current if (current / 'pyproject.toml').exists() else current.parent

sys.path.insert(0, str(project_root))

from derivatives_gpt_core.utils.graph_visualization import display_graph_in_notebook
from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent
from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph

# %% [markdown]
# ## Pricing Agent Graph

# %%
# Create the pricing agent graph
pricing_graph = create_pricing_agent()

# Display in notebook
try:
    display_graph_in_notebook(pricing_graph)
    print("✓ Pricing agent graph displayed")
except Exception as e:
    print(f"Graph display: {pricing_graph.get_graph().nodes.keys()}")

# %% [markdown]
# ## Educational Agent Graph

# %%
# Create the educational agent graph
educational_graph = build_educational_agent_graph()

# Display in notebook
try:
    # Try local rendering to avoid mermaid.ink API issues
    from langgraph.graph.mermaid import MermaidDrawMethod
    from IPython.display import Image, display
    img = educational_graph.get_graph().draw_mermaid_png(
        draw_method=MermaidDrawMethod.API,
        background_color="white"
    )
    display(Image(img))
    print("✓ Educational agent graph displayed")
except Exception as e:
    print(f"Note: Graph visualization unavailable (API issue). Graph has {len(educational_graph.get_graph().nodes)} nodes.")

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
