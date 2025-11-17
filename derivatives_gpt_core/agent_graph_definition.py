"""
Agent graph definition (backward compatibility wrapper).

This module re-exports the graph builder function for backward compatibility.
The actual implementation has been refactored into smaller modules:
- core/graph/graph_builder.py: Main graph construction
- core/graph/routing_logic.py: Routing functions
- workflow/response/completion_handlers.py: Response handlers
"""

from derivatives_gpt_core.core.graph.graph_builder import create_option_pricing_graph

# Re-export for backward compatibility
__all__ = ['create_option_pricing_graph']
