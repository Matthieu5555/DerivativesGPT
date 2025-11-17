"""
Orchestrator Graph
==================
Main orchestrator that routes queries to appropriate agent (educational or pricing).

This is the top-level graph that serves as the entry point for all user queries.
It performs intent classification and routes to the specialized agent graphs.

Flow:
  START → Classify Intent → Route to Agent → Execute Agent Graph → END

Features:
- Agent detection from user query
- Intent classification (option-related, educational, off-topic)
- Dynamic routing to educational or pricing agent
- Agent transfer detection
- Result aggregation
"""

from langgraph.graph import StateGraph, END
from typing import Literal
import logging
import asyncio

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.core.graph.agent_routing import route_to_agent
from derivatives_gpt_core.core.state.state_factory import detect_agent_from_message
from derivatives_gpt_core.core.state.conversation_context import (
    ConversationContext,
    detect_follow_up,
    should_maintain_agent,
    enhance_agent_detection_with_context
)
from derivatives_gpt_core.conversation_memory.checkpoint_manager import get_checkpointer

# Import classification nodes
from derivatives_gpt_core.graph_nodes.classify_intent import classify_user_intent

# Import agent graphs
from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph
from derivatives_gpt_core.agents.pricing.graph import build_pricing_agent_graph

# Import off-topic handler
from derivatives_gpt_core.graph_nodes.response_handlers.offtopic_handler import handle_off_topic

logger = logging.getLogger(__name__)


async def build_orchestrator_graph() -> StateGraph:
    """
    Build the main orchestrator graph.

    This graph coordinates between educational and pricing agents,
    performing initial classification and routing.

    Graph structure:
    ```
    START
      ↓
    classify_intent
      ↓
    detect_agent_type
      ↓
    ┌─────────┼─────────┐
    │         │         │
    │         │         │
    ▼         ▼         ▼
Educational Pricing  Off-Topic
   Agent     Agent    Handler
    │         │         │
    └────┬────┴─────────┘
         │
         ▼
       END
    ```

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Building orchestrator graph")

    # Create main graph (uses BaseAgentState - compatible with both agents)
    graph = StateGraph(BaseAgentState)

    # Build agent sub-graphs
    educational_graph = build_educational_agent_graph()
    pricing_graph = build_pricing_agent_graph()

    # ========================================================================
    # NODES
    # ========================================================================

    async def detect_and_route_agent(state: BaseAgentState) -> dict:
        """
        Detect agent type from user message and store in state.

        This node runs after classification to determine which agent
        should handle the query based on both classification result
        and keyword-based detection, WITH conversation context.
        """
        messages = state.messages
        if not messages:
            logger.warning("No messages to detect agent from")
            return {"detected_agent_type": "unified"}

        # Get current and previous messages
        current_message = messages[-1]
        previous_message = messages[-2] if len(messages) > 1 else None

        # Initial detection
        detection = detect_agent_from_message(current_message)

        # Create conversation context
        conversation_context = ConversationContext(
            last_agent=state.last_agent,
            last_topic=state.last_topic,
            conversation_depth=state.conversation_depth
        )

        # Check for follow-up patterns
        is_follow_up = False
        if previous_message and state.last_agent:
            is_follow_up, follow_up_confidence = detect_follow_up(
                current_message.content,
                previous_message.content if hasattr(previous_message, 'content') else str(previous_message)
            )

            if is_follow_up:
                logger.info(
                    f"Follow-up detected (confidence: {follow_up_confidence:.0%}) "
                    f"- maintaining {state.last_agent} agent"
                )

        # Enhance detection with context
        # CRITICAL: Only maintain agent for follow-ups if new detection is ambiguous
        # If user explicitly requests different task (high confidence), switch agents
        if is_follow_up and state.last_agent and detection.confidence < 0.75:
            # Follow-up with ambiguous intent - maintain previous agent for continuity
            logger.info(f"Ambiguous follow-up (new confidence {detection.confidence:.0%}) - maintaining {state.last_agent}")
            detection.agent_type = state.last_agent
            detection.confidence = 0.9
            detection.reasoning = f"Follow-up to previous {state.last_agent} conversation"
            depth = state.conversation_depth + 1
        else:
            # New topic or explicit switch (high confidence different agent)
            if is_follow_up and detection.confidence >= 0.75:
                logger.info(f"High-confidence switch (confidence {detection.confidence:.0%}) - changing to {detection.agent_type}")
            depth = 1 if detection.agent_type == state.last_agent else 0

        logger.info(
            f"Agent Detection: {detection.agent_type.upper()} "
            f"(confidence: {detection.confidence:.0%})"
        )
        logger.info(f"   Reasoning: {detection.reasoning}")

        return {
            "detected_agent_type": detection.agent_type,
            "agent_confidence": detection.confidence,
            "agent_reasoning": detection.reasoning,
            "is_follow_up": is_follow_up,
            "conversation_depth": depth,
            "current_agent": detection.agent_type  # Track the current agent
        }

    # Wrapper for educational agent (invokes sub-graph)
    async def run_educational_agent(state: BaseAgentState) -> dict:
        """Execute educational agent sub-graph."""
        logger.info("Invoking EDUCATIONAL agent")

        # Log incoming state for debugging
        logger.debug(f"Educational agent state: educational_context={state.educational_context if hasattr(state, 'educational_context') else None}")

        # Execute educational graph
        result = await educational_graph.ainvoke(state)

        # Track which agent handled this request
        result["last_agent"] = "educational"

        # Extract topic if available
        if hasattr(state, 'last_topic'):
            result["last_topic"] = state.last_topic

        logger.info("Educational agent completed")
        return result

    # Wrapper for pricing agent (invokes sub-graph)
    async def run_pricing_agent(state: BaseAgentState) -> dict:
        """Execute pricing agent sub-graph."""
        logger.info("Invoking PRICING agent")

        # Execute pricing graph
        result = await pricing_graph.ainvoke(state)

        # Track which agent handled this request
        result["last_agent"] = "pricing"

        # Extract topic if available
        if hasattr(state, 'last_topic'):
            result["last_topic"] = state.last_topic

        logger.info("Pricing agent completed")
        return result

    # Add nodes
    graph.add_node("classify_intent", classify_user_intent)
    graph.add_node("detect_agent", detect_and_route_agent)
    graph.add_node("educational_agent", run_educational_agent)
    graph.add_node("pricing_agent", run_pricing_agent)
    graph.add_node("off_topic", handle_off_topic)

    # ========================================================================
    # EDGES
    # ========================================================================

    # Entry point
    graph.set_entry_point("classify_intent")

    # From classify → detect agent
    graph.add_edge("classify_intent", "detect_agent")

    # From detect_agent → route to appropriate agent
    graph.add_conditional_edges(
        "detect_agent",
        route_to_agent,
        {
            "educational_agent": "educational_agent",
            "pricing_agent": "pricing_agent",
            "off_topic": "off_topic"
        }
    )

    # All agents → END
    graph.add_edge("educational_agent", END)
    graph.add_edge("pricing_agent", END)
    graph.add_edge("off_topic", END)

    # Compile with AsyncSqliteSaver for state persistence
    checkpointer = await get_checkpointer()
    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Orchestrator graph compiled successfully with async checkpointer")

    return compiled


def create_orchestrator() -> StateGraph:
    """
    Factory function to create orchestrator graph.

    This is the main entry point for the multi-agent system.

    Returns:
        Compiled orchestrator graph
    """
    return build_orchestrator_graph()


# ============================================================================
# AGENT TRANSFER SUPPORT
# ============================================================================

def build_orchestrator_with_transfers() -> StateGraph:
    """
    Build orchestrator with support for mid-conversation agent transfers.

    This enhanced version allows agents to transfer control to each other
    during a conversation (e.g., educational → pricing when user asks
    for a price calculation).

    NOT YET IMPLEMENTED - Future enhancement.

    Returns:
        StateGraph with transfer support
    """
    # TODO: Implement transfer detection and routing
    # For now, return standard orchestrator
    return build_orchestrator_graph()


# ============================================================================
# VISUALIZATION
# ============================================================================

def visualize_orchestrator_graph():
    """
    Generate a visual representation of the orchestrator graph.

    Returns ASCII art diagram of the graph flow.
    """
    diagram = """
Orchestrator Graph (Multi-Agent System)
========================================

                        ┌─────────────┐
                        │   START     │
                        │ (User Query)│
                        └──────┬──────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │ classify_intent  │
                    │ • Binary check   │
                    │ • Ticker extract │
                    │ • Chart display  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ detect_agent     │
                    │ • Keyword detect │
                    │ • Confidence calc│
                    │ • Agent select   │
                    └────────┬─────────┘
                             │
               ┌─────────────┼─────────────┐
               │             │             │
       [Educational]    [Pricing]    [Off-Topic]
               │             │             │
               ▼             ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────┐
    │ EDUCATIONAL  │ │   PRICING    │ │OFF-TOPIC │
    │    AGENT     │ │    AGENT     │ │ HANDLER  │
    ├──────────────┤ ├──────────────┤ ├──────────┤
    │• RAG Query   │ │• Extract     │ │• Polite  │
    │• Generate    │ │• Validate    │ │  redirect│
    │• Assess      │ │• Decompose   │ └────┬─────┘
    │• Rewrite     │ │• Plan        │      │
    │• Verify      │ │• Execute     │      │
    │              │ │• Narrate     │      │
    └──────┬───────┘ └──────┬───────┘      │
           │                │              │
           └────────┬───────┴──────────────┘
                    │
                    ▼
              ┌───────────┐
              │    END    │
              │  (Result) │
              └───────────┘

Agent Selection Logic:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Educational keywords > Pricing keywords → Educational
Pricing keywords > Educational keywords → Pricing
Equal or unclear                       → Use response_type
response_type="explain_concept"        → Educational
response_type="can_price"              → Pricing
response_type="off_topic"              → Off-Topic

State Management:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each agent has isolated field access:
• Educational: explanation_text, quality_score, etc.
• Pricing: spot_price, execution_plan, option_price, etc.
• Shared: messages, response_type, ticker, etc.

Checkpointing:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Thread IDs are hierarchical:
• session_123                → Orchestrator state
• session_123.educational    → Educational state
• session_123.pricing        → Pricing state
"""
    return diagram


def get_agent_statistics():
    """
    Get statistics about agent usage (for monitoring).

    Returns dict with agent execution stats.
    """
    # TODO: Implement proper statistics tracking
    return {
        "educational_invocations": 0,
        "pricing_invocations": 0,
        "off_topic_count": 0,
        "average_confidence": 0.0,
    }


if __name__ == "__main__":
    # Test graph compilation
    print("Testing orchestrator graph compilation...")
    graph = build_orchestrator_graph()
    print("Orchestrator graph compiled successfully!")
    print(visualize_orchestrator_graph())
