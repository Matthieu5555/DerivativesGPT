"""
State Factory - Agent-Aware State Creation
===========================================
Factory functions for creating agent-aware state wrappers and detecting agent types.
"""

from typing import Optional, Dict, Any
import logging
from langchain_core.messages import BaseMessage

from .agent_state_wrapper import (
    AgentStateWrapper,
    AgentType,
    create_agent_wrapper
)
from .agent_detection import detect_agent_type, AgentDetectionResult

logger = logging.getLogger(__name__)


def create_state_for_agent(
    base_state: Any,  # BaseAgentState
    agent_type: Optional[AgentType] = None,
    enforce: bool = True
) -> AgentStateWrapper:
    """
    Create an agent-aware state wrapper.

    Args:
        base_state: The underlying BaseAgentState
        agent_type: Agent type, or None to detect from state
        enforce: Whether to enforce access control

    Returns:
        AgentStateWrapper configured for the specified agent
    """
    return create_agent_wrapper(base_state, agent_type, enforce)


def detect_agent_from_message(message: str | BaseMessage) -> AgentDetectionResult:
    """
    Detect which agent should handle a message.

    Args:
        message: User message (string or BaseMessage)

    Returns:
        AgentDetectionResult with detected agent type
    """
    # Extract content if BaseMessage
    if isinstance(message, BaseMessage):
        content = message.content
    else:
        content = message

    return detect_agent_type(content)


def create_state_from_message(
    base_state: Any,  # BaseAgentState
    message: Optional[str | BaseMessage] = None,
    enforce: bool = True
) -> tuple[AgentStateWrapper, AgentDetectionResult]:
    """
    Create state wrapper with agent detection from message.

    Args:
        base_state: The underlying BaseAgentState
        message: User message to detect agent from, or None to use state's last message
        enforce: Whether to enforce access control

    Returns:
        Tuple of (AgentStateWrapper, AgentDetectionResult)
    """
    # Get message to detect from
    if message is None:
        # Try to get last message from state
        messages = getattr(base_state, "messages", [])
        if messages:
            message = messages[-1]
        else:
            # No message available, default to unified
            detection = AgentDetectionResult(
                agent_type="unified",
                confidence=0.5,
                matched_keywords=[],
                reasoning="No message available for detection"
            )
            wrapper = create_agent_wrapper(base_state, "unified", enforce)
            return wrapper, detection

    # Detect agent type
    detection = detect_agent_from_message(message)

    # Store detection result in state
    base_state.detected_agent_type = detection.agent_type
    base_state.agent_confidence = detection.confidence
    base_state.agent_reasoning = detection.reasoning

    # Create wrapper
    wrapper = create_agent_wrapper(base_state, detection.agent_type, enforce)

    logger.info(
        f"Created state for {detection.agent_type} agent "
        f"(confidence: {detection.confidence:.0%})"
    )

    return wrapper, detection


def merge_agent_states(
    educational_state: AgentStateWrapper,
    pricing_state: AgentStateWrapper,
    target_state: Optional[Any] = None
) -> Any:
    """
    Merge educational and pricing agent states into a unified state.

    Useful for orchestrator that needs to combine results from both agents.

    Args:
        educational_state: State from educational agent
        pricing_state: State from pricing agent
        target_state: Optional target state to merge into, or create new

    Returns:
        Merged BaseAgentState
    """
    if target_state is None:
        # Create new state
        from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
        target_state = BaseAgentState()

    # Get underlying states
    edu_dict = educational_state.to_dict(include_all=False)
    pricing_dict = pricing_state.to_dict(include_all=False)

    # Merge (pricing takes precedence for shared fields)
    merged = {**edu_dict, **pricing_dict}

    # Special handling for messages (combine, not replace)
    edu_messages = educational_state.get_field("messages", [])
    pricing_messages = pricing_state.get_field("messages", [])

    # Combine messages, removing duplicates
    all_messages = []
    seen_contents = set()

    for msg in edu_messages + pricing_messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        if content not in seen_contents:
            all_messages.append(msg)
            seen_contents.add(content)

    merged["messages"] = all_messages

    # Update target state
    for key, value in merged.items():
        if hasattr(target_state, key):
            setattr(target_state, key, value)

    logger.info(
        f"Merged states: {len(edu_dict)} educational fields + "
        f"{len(pricing_dict)} pricing fields = {len(merged)} total"
    )

    return target_state


def split_state_for_agents(
    unified_state: Any  # BaseAgentState
) -> Dict[AgentType, AgentStateWrapper]:
    """
    Split a unified state into agent-specific wrappers.

    Useful for parallel agent execution.

    Args:
        unified_state: A unified BaseAgentState

    Returns:
        Dict mapping agent types to their wrapped states
    """
    return {
        "educational": create_agent_wrapper(unified_state, "educational", enforce=True),
        "pricing": create_agent_wrapper(unified_state, "pricing", enforce=True),
        "unified": create_agent_wrapper(unified_state, "unified", enforce=False),
    }


def clone_state_for_agent(
    source_state: Any,  # BaseAgentState
    agent_type: AgentType
) -> Any:
    """
    Clone state and prepare it for a specific agent.

    Creates a new state instance with only the fields relevant to the agent.

    Args:
        source_state: Source state to clone
        agent_type: Target agent type

    Returns:
        New BaseAgentState instance with agent-relevant fields
    """
    from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

    # Create wrapper to get allowed fields
    wrapper = create_agent_wrapper(source_state, agent_type, enforce=False)
    agent_dict = wrapper.to_dict(include_all=False)

    # Create new state with only allowed fields
    new_state = BaseAgentState()

    for key, value in agent_dict.items():
        if hasattr(new_state, key):
            setattr(new_state, key, value)

    logger.debug(
        f"Cloned state for {agent_type} agent: {len(agent_dict)} fields"
    )

    return new_state


def inherit_context_fields(
    target_state: Any,  # BaseAgentState
    source_state: Any,  # BaseAgentState
    fields: Optional[list[str]] = None
) -> Any:
    """
    Inherit specific context fields from source to target state.

    Useful for multi-turn conversations where context needs to be preserved.

    Args:
        target_state: State to update
        source_state: State to inherit from
        fields: Specific fields to inherit, or None for all shared fields

    Returns:
        Updated target state
    """
    if fields is None:
        # Default to shared fields
        from .agent_state_wrapper import get_shared_fields
        fields = list(get_shared_fields())

    inherited_count = 0

    for field in fields:
        source_value = getattr(source_state, field, None)
        target_value = getattr(target_state, field, None)

        # Only inherit if target doesn't have a value
        if source_value is not None and target_value is None:
            setattr(target_state, field, source_value)
            inherited_count += 1

    if inherited_count > 0:
        logger.debug(f"Inherited {inherited_count} context fields")

    return target_state


def create_fresh_state_with_messages(
    messages: list[BaseMessage],
    agent_type: Optional[AgentType] = None
) -> tuple[Any, AgentStateWrapper]:
    """
    Create a fresh state with only messages, suitable for new conversation.

    Args:
        messages: List of messages to initialize with
        agent_type: Optional agent type, or None to detect

    Returns:
        Tuple of (BaseAgentState, AgentStateWrapper)
    """
    from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

    state = BaseAgentState(messages=messages)

    # Detect agent if not specified
    if agent_type is None and messages:
        wrapper, _ = create_state_from_message(state, messages[-1])
    else:
        wrapper = create_agent_wrapper(state, agent_type or "unified")

    return state, wrapper


# Convenience aliases
create_educational_state = lambda state: create_agent_wrapper(state, "educational", enforce=True)
create_pricing_state = lambda state: create_agent_wrapper(state, "pricing", enforce=True)
create_unified_state = lambda state: create_agent_wrapper(state, "unified", enforce=False)
