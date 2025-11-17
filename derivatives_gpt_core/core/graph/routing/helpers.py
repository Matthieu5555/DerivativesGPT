"""
Routing Helper Functions
=========================
Shared utilities for agent routing decisions.
"""

from typing import Literal
import logging

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.core.state.state_factory import detect_agent_from_message

logger = logging.getLogger(__name__)


def should_transfer_to_pricing(state: BaseAgentState) -> bool:
    """
    Check if educational agent should transfer to pricing agent.

    This happens when user asks a pricing question while in educational flow.

    Args:
        state: Current state

    Returns:
        True if should transfer to pricing
    """
    # Check if latest message indicates pricing intent
    messages = state.messages
    if not messages:
        return False

    latest_message = messages[-1]
    detection = detect_agent_from_message(latest_message)

    return detection.agent_type == "pricing" and detection.confidence > 0.6


def should_transfer_to_educational(state: BaseAgentState) -> bool:
    """
    Check if pricing agent should transfer to educational agent.

    This happens when user asks for explanation during pricing flow.

    Args:
        state: Current state

    Returns:
        True if should transfer to educational
    """
    # Check if latest message indicates educational intent
    messages = state.messages
    if not messages:
        return False

    latest_message = messages[-1]
    detection = detect_agent_from_message(latest_message)

    return detection.agent_type == "educational" and detection.confidence > 0.6


def get_agent_from_state(state: BaseAgentState) -> Literal["educational", "pricing", "unified"]:
    """
    Get the current agent type from state.

    Args:
        state: Current state

    Returns:
        Agent type: "educational", "pricing", or "unified"
    """
    if state.current_agent:
        return state.current_agent

    if state.detected_agent_type:
        return state.detected_agent_type

    # Detect from response_type
    if state.response_type == "explain_concept":
        return "educational"
    elif state.response_type == "can_price":
        return "pricing"

    return "unified"


def log_routing_decision(
    state: BaseAgentState,
    source_node: str,
    target_node: str,
    reason: str
):
    """
    Log a routing decision for debugging.

    Args:
        state: Current state
        source_node: Source node name
        target_node: Target node name
        reason: Reason for routing decision
    """
    agent = get_agent_from_state(state)
    logger.info(
        f"[{agent.upper()}] Routing: {source_node} → {target_node} ({reason})"
    )
