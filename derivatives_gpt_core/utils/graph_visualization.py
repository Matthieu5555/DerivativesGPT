"""
Graph Visualization Utilities
==============================
Provides proper graph visualization using LangGraph's built-in capabilities.

Policy:
- No ASCII art in production code
- Use LangGraph's get_graph() for Mermaid diagrams
- Use draw_mermaid_png() for visual output
- Keep visualization separate from business logic
"""

from typing import Optional
from langgraph.graph import StateGraph
import logging

logger = logging.getLogger(__name__)


def get_graph_mermaid(graph: StateGraph) -> str:
    """
    # Called by: any module needing graph visualization as Mermaid markdown
    # Returns Mermaid diagram string that can be rendered in documentation or notebooks

    Args:
        graph: Compiled LangGraph StateGraph

    Returns:
        Mermaid diagram string
    """
    try:
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        logger.error(f"Failed to generate Mermaid diagram: {e}")
        return ""


def save_graph_visualization(graph: StateGraph, output_path: str, format: str = "png") -> bool:
    """
    # Called by: development tools, documentation generators
    # Saves graph visualization to file for documentation purposes

    Args:
        graph: Compiled LangGraph StateGraph
        output_path: Path where to save the visualization
        format: Output format (png, mermaid)

    Returns:
        True if successful, False otherwise
    """
    try:
        if format == "png":
            png_data = graph.get_graph().draw_mermaid_png()
            with open(output_path, "wb") as f:
                f.write(png_data)
        elif format == "mermaid":
            mermaid_str = graph.get_graph().draw_mermaid()
            with open(output_path, "w") as f:
                f.write(mermaid_str)
        else:
            logger.error(f"Unsupported format: {format}")
            return False

        logger.info(f"Graph visualization saved to {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save graph visualization: {e}")
        return False


def display_graph_in_notebook(graph: StateGraph):
    """
    # Called by: Jupyter notebooks for interactive development
    # Displays graph visualization inline in Jupyter notebooks

    Args:
        graph: Compiled LangGraph StateGraph
    """
    try:
        from IPython.display import Image, display
        display(Image(graph.get_graph().draw_mermaid_png()))
    except ImportError:
        logger.warning("IPython not available - cannot display graph")
    except Exception as e:
        logger.error(f"Failed to display graph: {e}")