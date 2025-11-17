"""
Orchestrator Routing Logic
===========================
Main entry point for routing queries to appropriate agents.
"""

from typing import Literal
import logging

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.core.state.state_factory import detect_agent_from_message

logger = logging.getLogger(__name__)


def route_to_agent(state: BaseAgentState) -> Literal["educational_agent", "pricing_agent", "off_topic"]:
    """
    Main orchestrator routing: Determine which agent should handle the query.

    This is the entry point that decides whether to route to:
    - Educational agent (conceptual questions)
    - Pricing agent (pricing requests)
    - Off-topic handler (non-option queries)

    Args:
        state: Current graph state

    Returns:
        "educational_agent", "pricing_agent", or "off_topic"
    """
    # Check if response_type is already set (from classification)
    response_type = state.response_type

    if response_type == "explain_concept":
        logger.info("Routing to EDUCATIONAL agent (explain_concept)")
        return "educational_agent"

    elif response_type == "can_price":
        logger.info("Routing to PRICING agent (can_price)")
        return "pricing_agent"

    elif response_type == "off_topic":
        logger.info("Routing to OFF_TOPIC handler")
        return "off_topic"

    # Check for follow-up conversation context FIRST
    if getattr(state, 'is_follow_up', False) and getattr(state, 'last_agent', None):
        # This is a follow-up - maintain the same agent
        agent_type = state.last_agent
        logger.info(f"FOLLOW-UP detected: maintaining {agent_type} agent for conversation continuity")
    elif state.detected_agent_type:
        # Use the detected agent type (which may already consider context)
        agent_type = state.detected_agent_type
        logger.info(f"Using detected agent type: {agent_type}")
    else:
        # Detect from latest message
        messages = state.messages
        if messages:
            detection = detect_agent_from_message(messages[-1])
            agent_type = detection.agent_type
            # Store detection result
            state.detected_agent_type = agent_type
            state.agent_confidence = detection.confidence
            state.agent_reasoning = detection.reasoning
            logger.info(f"Fresh detection: {agent_type} (confidence: {detection.confidence:.0%})")
        else:
            agent_type = "unified"
            logger.warning("No messages to detect from, defaulting to unified")

    # Route based on detected agent
    if agent_type == "educational":
        return "educational_agent"
    elif agent_type == "pricing":
        return "pricing_agent"
    else:
        # Unified or unclear - check if option-related
        if state.is_option_related:
            return "pricing_agent"  # Default to pricing for option-related
        else:
            return "off_topic"
