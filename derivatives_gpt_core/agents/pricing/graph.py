"""
Pricing Agent Graph
===================
LangGraph implementation for the pricing agent with parameter extraction,
validation, execution, and narration.

Flow:
  Entry → Extract Parameters → Validate → Decompose → Plan → RAG Retrieval → Execute → Narrate → Exit

Features:
- Parameter extraction with retries (max 3 attempts)
- Comprehensive validation with clarification
- Strategy decomposition for multi-leg options
- RAG retrieval for educational context citations
- Parallel task execution
- Natural language narration of results with source citations
"""

from langgraph.graph import StateGraph, END
from typing import Literal
import logging

from derivatives_gpt_core.agents.pricing.state import PricingState
from derivatives_gpt_core.core.graph.agent_routing import (
    route_pricing_query,
    route_after_extraction,
    route_after_validation,
    route_after_decomposition,
    route_after_execution
)

# Import pricing nodes
from derivatives_gpt_core.agents.pricing.nodes.extract_parameters import extract_parameters
from derivatives_gpt_core.agents.pricing.nodes.validate_inputs import validate_pricing_parameters
from derivatives_gpt_core.agents.pricing.nodes.decompose_strategy import decompose_strategy
from derivatives_gpt_core.agents.pricing.nodes.create_execution_plan import create_execution_plan
# Import from workflow (not moved)
from derivatives_gpt_core.workflow.execution.parallel_executor import execute_plan
from derivatives_gpt_core.agents.pricing.nodes.aggregate_strategy_price import aggregate_strategy_price
from derivatives_gpt_core.agents.pricing.nodes.narrate_execution import narrate_execution

# Import shared nodes
from derivatives_gpt_core.agents.shared.nodes.augment_with_context import augment_with_context

# Import response handlers (still in original location)
from derivatives_gpt_core.graph_nodes.response_handlers.clarify_handler import handle_clarify_parameters
from derivatives_gpt_core.graph_nodes.response_handlers.exotic_handler import handle_recognize_but_refuse

logger = logging.getLogger(__name__)


def build_pricing_agent_graph() -> StateGraph:
    """
    Build the pricing agent graph with full pricing workflow.

    Graph structure:
    ```
    START
      ↓
    extract_parameters
      ↓
    [Success] → validate
    [Failed + eval_mode] → refuse
    [Failed + prod_mode] → clarify (wait for user) → END
    [Failed + max_attempts] → refuse
      ↓
    validate
      ↓
    [Valid] → decompose
    [Invalid + attempts<max] → clarify (wait for user) → END
    [Invalid + max_attempts] → refuse
      ↓
    decompose
      ↓
    [Can execute] → create_plan
    [Cannot execute] → refuse
      ↓
    create_plan
      ↓
    execute_tasks
      ↓
    [Multi-leg] → aggregate → narrate → END
    [Single] → narrate → END
      ↓
    narrate → END
    ```

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building pricing agent graph")

    # Create graph with BaseAgentState
    graph = StateGraph(PricingState)

    # ========================================================================
    # NODES
    # ========================================================================

    # Finalize pricing (terminal node before END)
    def finalize_pricing(state: PricingState) -> dict:
        """Mark pricing as complete."""
        logger.info("Pricing agent: Pricing finalized")
        return {
            "response_type": "can_price",
            "current_agent": "pricing"
        }

    # Add nodes
    graph.add_node("extract_parameters", extract_parameters)
    graph.add_node("validate_inputs", validate_pricing_parameters)
    graph.add_node("decompose_strategy", decompose_strategy)
    graph.add_node("create_plan", create_execution_plan)
    graph.add_node("rag_retrieval", augment_with_context)  # Retrieve RAG sources for narration citations
    graph.add_node("execute_tasks", execute_plan)
    graph.add_node("aggregate_results", aggregate_strategy_price)
    graph.add_node("narrate_results", narrate_execution)
    graph.add_node("clarify_parameters", handle_clarify_parameters)
    graph.add_node("recognize_but_refuse", handle_recognize_but_refuse)
    graph.add_node("finalize", finalize_pricing)

    # ========================================================================
    # EDGES
    # ========================================================================

    # Entry point
    graph.set_entry_point("extract_parameters")

    # From extract_parameters → conditional
    graph.add_conditional_edges(
        "extract_parameters",
        route_after_extraction,
        {
            "validate_inputs": "validate_inputs",
            "clarify_parameters": "clarify_parameters",
            "recognize_but_refuse": "recognize_but_refuse"
        }
    )

    # From validate → conditional
    graph.add_conditional_edges(
        "validate_inputs",
        route_after_validation,
        {
            "decompose_strategy": "decompose_strategy",
            "clarify_parameters": "clarify_parameters",
            "recognize_but_refuse": "recognize_but_refuse"
        }
    )

    # From decompose → conditional
    graph.add_conditional_edges(
        "decompose_strategy",
        route_after_decomposition,
        {
            "create_execution_plan": "create_plan",
            "recognize_but_refuse": "recognize_but_refuse"
        }
    )

    # From create_plan → rag_retrieval → execute
    graph.add_edge("create_plan", "rag_retrieval")
    graph.add_edge("rag_retrieval", "execute_tasks")

    # From execute → conditional (single vs multi-leg)
    graph.add_conditional_edges(
        "execute_tasks",
        route_after_execution,
        {
            "aggregate_results": "aggregate_results",
            "narrate_results": "narrate_results"
        }
    )

    # From aggregate → narrate
    graph.add_edge("aggregate_results", "narrate_results")

    # From narrate → finalize → END
    graph.add_edge("narrate_results", "finalize")
    graph.add_edge("finalize", END)

    # From clarify → END (wait for user)
    graph.add_edge("clarify_parameters", END)

    # From refuse → END
    graph.add_edge("recognize_but_refuse", END)

    # Compile
    compiled = graph.compile()
    logger.info("Pricing agent graph compiled successfully")

    return compiled


def create_pricing_agent() -> StateGraph:
    """
    Factory function to create pricing agent graph.

    Returns:
        Compiled pricing agent graph
    """
    return build_pricing_agent_graph()


# ============================================================================
# VISUALIZATION
# ============================================================================

if __name__ == "__main__":
    # Test graph compilation
    print("Testing pricing agent graph compilation...")
    graph = build_pricing_agent_graph()
    print("Graph compiled successfully!")

    # Use proper visualization for development
    from derivatives_gpt_core.utils.graph_visualization import save_graph_visualization
    save_graph_visualization(graph, "pricing_graph.png", format="png")
