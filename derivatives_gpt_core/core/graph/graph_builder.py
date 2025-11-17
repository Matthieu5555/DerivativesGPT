"""
Option pricing graph builder.

This module constructs the LangGraph state machine that orchestrates
the entire option pricing workflow, including:
- Intent classification
- RAG augmentation
- Parameter extraction and validation
- Pricing execution
- Multi-turn conversations
"""

from langgraph.graph import StateGraph, END
from langgraph.pregel import Pregel
from langgraph.checkpoint.base import BaseCheckpointSaver
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.graph_nodes.classify_intent import classify_user_intent
from derivatives_gpt_core.graph_nodes.validate_inputs import validate_pricing_parameters
from derivatives_gpt_core.graph_nodes.response_handlers import (
    handle_recognize_but_refuse,
    handle_clarify_parameters,
    handle_off_topic,
    handle_explain_concept
)
from derivatives_gpt_core.graph_nodes.human_approval import request_human_approval
from derivatives_gpt_core.graph_nodes.augment_with_context import augment_with_context
from derivatives_gpt_core.graph_nodes.web_search import web_search
from derivatives_gpt_core.graph_nodes.classify_asset_type import classify_asset_type
from derivatives_gpt_core.graph_nodes.classify_option_type import classify_option_type
from derivatives_gpt_core.graph_nodes.determine_action import determine_action
from derivatives_gpt_core.graph_nodes.extract_parameters import extract_parameters
from derivatives_gpt_core.graph_nodes.clarify_asset import handle_clarify_asset
from derivatives_gpt_core.graph_nodes.clarify_option import handle_clarify_option
from derivatives_gpt_core.graph_nodes.decompose_strategy import decompose_strategy
from derivatives_gpt_core.graph_nodes.create_execution_plan import create_execution_plan
from derivatives_gpt_core.graph_nodes.execute_parallel_tasks import execute_plan
from derivatives_gpt_core.graph_nodes.aggregate_strategy_price import aggregate_strategy_price
from derivatives_gpt_core.graph_nodes.narrate_execution import narrate_execution
from derivatives_gpt_core.core.graph.routing_logic import (
    route_after_initial_classification,
    route_after_asset_classification,
    route_after_option_classification,
    route_after_action_determination,
    route_after_extraction,
    route_after_validation,
    route_after_decomposition,
    route_after_planning,
    route_after_execution
)
from derivatives_gpt_core.workflow.response.completion_handlers import (
    handle_validation_failure,
    handle_pricing_complete
)
import logging

logger = logging.getLogger(__name__)


def create_option_pricing_graph(checkpointer: BaseCheckpointSaver | None) -> Pregel:
    """
    Create option pricing graph with educational loop and multi-turn conversations.

    WORKFLOW OVERVIEW:
        classify (chart displays here)
          ├─> augment_with_context → web_search → classify_asset_type → classify_option_type
          │    → determine_action
          │      ├─> explain_concept (educational loop) → END
          │      ├─> extract_parameters → validate → decompose → plan → execute → narrate → END
          │      ├─> clarify_parameters → END (wait for user)
          │      └─> recognize_but_refuse → END
          └─> off_topic → END

    KEY ARCHITECTURAL DETAILS:

    1. Chart Display (T=800ms):
       - Chart displays during classify_intent node via _display_chart_if_ticker()
       - User sees chart while system does RAG + classification + pricing
       - Non-blocking and error-resilient

    2. Educational Loop:
       - User: "What is delta?" → classify → augment → explain_concept → END
       - User: "What about gamma?" → NEW graph starts with full history
       - RAG retrieval uses conversation history for context-aware answers

    3. Pricing Flow:
       - classify → augment → web_search → classify_asset → classify_option
       - → determine_action → extract_parameters → validate → decompose
       - → plan → execute → narrate → END
       - Relative strikes ("ATM", "5% above") are valid specifications

    4. Multi-Turn Clarification:
       - Missing params → clarify_parameters → END → wait for user
       - Unknown asset → clarify_asset → END → wait for user
       - Validation fails → validation_failed → clarify_parameters → END

    5. Loop Protection:
       - extraction_attempts counter (max 3)
       - clarification_attempts counter (max 3)
       - validation_attempt counter (max 2)

    Args:
        checkpointer: Checkpoint saver for conversation memory (required for multi-turn)

    Returns:
        Compiled LangGraph Pregel instance
    """
    workflow = StateGraph(BaseAgentState)

    # Initial classification node
    workflow.add_node("classify", classify_user_intent)

    # Augmentation nodes
    workflow.add_node("augment_with_context", augment_with_context)
    workflow.add_node("web_search", web_search)

    # Classification nodes (post-augmentation)
    workflow.add_node("classify_asset_type", classify_asset_type)
    workflow.add_node("classify_option_type", classify_option_type)
    workflow.add_node("determine_action", determine_action)

    # Parameter extraction and validation
    workflow.add_node("extract_parameters", extract_parameters)
    workflow.add_node("validate", validate_pricing_parameters)

    # Response handlers
    workflow.add_node("recognize_but_refuse", handle_recognize_but_refuse)
    workflow.add_node("clarify_parameters", handle_clarify_parameters)
    workflow.add_node("clarify_asset", handle_clarify_asset)
    workflow.add_node("clarify_option", handle_clarify_option)
    workflow.add_node("off_topic", handle_off_topic)
    workflow.add_node("validation_failed", handle_validation_failure)
    workflow.add_node("human_approval", request_human_approval)

    # Educational explanation handler (simple direct response)
    workflow.add_node("explain_concept", handle_explain_concept)

    # Orchestrator nodes
    workflow.add_node("decompose", decompose_strategy)
    workflow.add_node("create_plan", create_execution_plan)
    workflow.add_node("execute", execute_plan)
    workflow.add_node("narrate", narrate_execution)
    workflow.add_node("aggregate", aggregate_strategy_price)
    workflow.add_node("pricing_complete", handle_pricing_complete)

    # Set entry point
    workflow.set_entry_point("classify")

    # Initial classification routing
    workflow.add_conditional_edges(
        "classify",
        route_after_initial_classification,
        {
            "augment_with_context": "augment_with_context",
            "off_topic": "off_topic",
            "explain_concept": "explain_concept"  # Direct to simple explanation handler
        }
    )

    # After RAG augmentation, do web search
    workflow.add_edge("augment_with_context", "web_search")

    # After web search, classify asset type
    workflow.add_edge("web_search", "classify_asset_type")

    # Asset classification routing
    workflow.add_conditional_edges(
        "classify_asset_type",
        route_after_asset_classification,
        {
            "classify_option_type": "classify_option_type",
            "clarify_asset": "clarify_asset"
        }
    )

    # Option classification routing
    workflow.add_conditional_edges(
        "classify_option_type",
        route_after_option_classification,
        {
            "determine_action": "determine_action",
            "clarify_option": "clarify_option"
        }
    )

    # Action determination routing
    workflow.add_conditional_edges(
        "determine_action",
        route_after_action_determination,
        {
            "extract_parameters": "extract_parameters",
            "explain_concept": "explain_concept",  # Direct to simple explanation handler
            "recognize_but_refuse": "recognize_but_refuse",
            "clarify_parameters": "clarify_parameters",
            "clarify_option": "clarify_option"
        }
    )

    # After parameter extraction, validate
    workflow.add_conditional_edges(
        "extract_parameters",
        route_after_extraction,
        {
            "validate": "validate",
            "clarify_parameters": "clarify_parameters",
            "recognize_but_refuse": "recognize_but_refuse"
        }
    )

    # Validation routing
    workflow.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "decompose": "decompose",
            "validation_failed": "validation_failed"
        }
    )

    # Decomposition routing
    workflow.add_conditional_edges(
        "decompose",
        route_after_decomposition,
        {
            "create_plan": "create_plan",
            "recognize_but_refuse": "recognize_but_refuse"
        }
    )

    # Planning routing (with optional human approval for exotic derivatives)
    workflow.add_conditional_edges(
        "create_plan",
        route_after_planning,
        {
            "execute": "execute",
            "human_approval": "human_approval",
            "recognize_but_refuse": "recognize_but_refuse"
        }
    )

    # After human approval, proceed to execution
    workflow.add_edge("human_approval", "execute")

    # Execute plan, then narrate results
    workflow.add_edge("execute", "narrate")

    # After narration, route based on strategy type
    workflow.add_conditional_edges(
        "narrate",
        route_after_execution,
        {
            "aggregate": "aggregate",
            "pricing_complete": "pricing_complete"
        }
    )

    # Multi-turn conversation: clarification nodes END to wait for user response
    workflow.add_edge("clarify_asset", END)
    workflow.add_edge("clarify_option", END)
    workflow.add_edge("clarify_parameters", END)

    # Validation failure asks user to fix errors
    workflow.add_edge("validation_failed", "clarify_parameters")

    # Terminal exits
    workflow.add_edge("explain_concept", END)
    workflow.add_edge("aggregate", END)
    workflow.add_edge("pricing_complete", END)
    workflow.add_edge("recognize_but_refuse", END)
    workflow.add_edge("off_topic", END)

    # Compile with checkpointing
    graph = workflow.compile(checkpointer=checkpointer)

    logger.info("Graph compiled with multi-stage classification workflow")

    return graph
