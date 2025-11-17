"""
Agent Routing Module
====================
Re-exports all routing functions for backward compatibility.

This module was reorganized from a single file (agent_routing.py) into
separate modules by agent type:
- orchestrator.py: Main entry point routing
- educational.py: Educational agent routing
- pricing.py: Pricing agent routing
- helpers.py: Shared routing utilities

All imports continue to work:
    from derivatives_gpt_core.core.graph.agent_routing import route_to_agent
"""

# Orchestrator routing
from derivatives_gpt_core.core.graph.routing.orchestrator import (
    route_to_agent,
)

# Educational routing
from derivatives_gpt_core.core.graph.routing.educational import (
    route_educational_query,
    route_after_explanation_quality,
)

# Pricing routing
from derivatives_gpt_core.core.graph.routing.pricing import (
    route_pricing_query,
    route_after_extraction,
    route_after_validation,
    route_after_decomposition,
    route_after_execution,
)

# Helpers
from derivatives_gpt_core.core.graph.routing.helpers import (
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
