"""
POC: Monitored Intent Classification
======================================
Enhanced version of classify_intent that includes agent detection and monitoring.
This is a proof-of-concept wrapper that adds agent awareness without modifying the original.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.core.state.agent_monitor import AgentMonitor
from derivatives_gpt_core.core.state.agent_detection import detect_agent_type, format_detection_summary
from derivatives_gpt_core.graph_nodes.classify_intent import classify_user_intent
from langsmith import traceable
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


@traceable(name="classify_intent_monitored", metadata={"node_type": "classification_poc", "version": "1.0"})
async def classify_user_intent_monitored(state: BaseAgentState) -> Dict[str, Any]:
    """
    Enhanced classification with agent detection POC.

    This wrapper:
    1. Detects which agent should handle the query
    2. Tracks field access patterns
    3. Logs agent routing decisions
    4. Calls the original classify_user_intent
    5. Monitors the results

    Returns:
        Same as classify_user_intent, plus:
            - detected_agent_type: str
            - agent_confidence: float
            - agent_reasoning: str
    """
    # Extract session ID from thread context if available
    session_id = getattr(state, "thread_id", "default")

    # Initialize monitoring
    monitor = AgentMonitor(state, node_name="classify_intent_monitored", session_id=session_id)
    monitor.log_node_entry()

    # Get the user's message
    user_message = monitor.read_field("messages", state.messages)[-1].content

    # Detect agent type
    detection_result = detect_agent_type(user_message)

    logger.info("=" * 60)
    logger.info("AGENT DETECTION POC")
    logger.info("=" * 60)
    logger.info(f"User Query: {user_message[:100]}...")
    logger.info(f"Detected Agent: {detection_result.agent_type.upper()}")
    logger.info(f"Confidence: {detection_result.confidence:.0%}")
    logger.info(f"Reasoning: {detection_result.reasoning}")
    if detection_result.matched_keywords:
        logger.info(f"Matched Keywords: {', '.join(detection_result.matched_keywords[:5])}")
    logger.info("=" * 60)

    # Call original classification
    result = await classify_user_intent(state)

    # Track which fields were written
    for key in result.keys():
        monitor.write_field(key, result[key])

    # Add agent detection results to state
    result["detected_agent_type"] = detection_result.agent_type
    result["agent_confidence"] = detection_result.confidence
    result["agent_reasoning"] = detection_result.reasoning

    # Log what the original classification determined
    is_option_related = result.get("is_option_related", False)
    monitor.log_routing_decision(
        next_node="augment_with_context" if is_option_related else "off_topic",
        reason=f"is_option_related={is_option_related}"
    )

    # Check for agent mismatch
    if is_option_related and detection_result.agent_type == "educational":
        logger.info(
            "Educational query detected, but classified as option-related. "
            "This might be an educational question about options."
        )
    elif not is_option_related and detection_result.agent_type == "pricing":
        logger.warning(
            "Pricing query detected, but classified as NOT option-related. "
            "Possible classification mismatch!"
        )

    monitor.log_node_exit()

    return result


def should_use_monitored_version() -> bool:
    """
    Check if POC monitoring should be enabled.

    Returns:
        True if monitoring is enabled (via env var or settings)
    """
    import os
    return os.getenv("ENABLE_AGENT_MONITORING_POC", "false").lower() in ("true", "1", "yes")
