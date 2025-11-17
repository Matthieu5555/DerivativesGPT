"""
Backward Compatibility Shim for Agent Routing
==============================================
This module re-exports all routing functions from the new routing/ submodule
to maintain backward compatibility with existing code.

The routing logic has been reorganized from a single file into:
- routing/orchestrator.py
- routing/educational.py
- routing/pricing.py
- routing/helpers.py

All existing imports continue to work:
    from derivatives_gpt_core.core.graph.agent_routing import route_to_agent
"""

# Re-export everything from routing module
from derivatives_gpt_core.core.graph.routing import (
    # Orchestrator
    route_to_agent,

    # Educational
    route_educational_query,
    route_after_explanation_quality,

    # Pricing
    route_pricing_query,
    route_after_extraction,
    route_after_validation,
    route_after_decomposition,
    route_after_execution,

    # Helpers
    should_transfer_to_pricing,
    should_transfer_to_educational,
    get_agent_from_state,
    log_routing_decision,
)

__all__ = [
    # Orchestrator
    "route_to_agent",

    # Educational
    "route_educational_query",
    "route_after_explanation_quality",

    # Pricing
    "route_pricing_query",
    "route_after_extraction",
    "route_after_validation",
    "route_after_decomposition",
    "route_after_execution",

    # Helpers
    "should_transfer_to_pricing",
    "should_transfer_to_educational",
    "get_agent_from_state",
    "log_routing_decision",
]
