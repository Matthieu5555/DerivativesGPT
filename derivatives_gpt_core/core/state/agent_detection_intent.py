"""
Intent-based agent detection using LLM.

Instead of hardcoded keywords, we detect the user's INTENT:
- Learning/Understanding → Educational Agent
- Executing/Calculating → Pricing Agent
"""

from typing import NamedTuple
from derivatives_gpt_core.llm_provider import get_classification_llm
import logging

logger = logging.getLogger(__name__)


class AgentDetectionResult(NamedTuple):
    """Result of agent detection."""
    agent_type: str  # "educational" or "pricing"
    confidence: float
    reasoning: str


INTENT_DETECTION_PROMPT = """Analyze the user's intent in this message and determine which agent should handle it.

User message: "{message}"

Determine the user's PRIMARY INTENT:

1. EDUCATIONAL INTENT (route to Educational Agent):
   - User wants to LEARN or UNDERSTAND a concept
   - Asking "what is", "how does it work", "explain", "why"
   - Seeking knowledge, theory, or conceptual understanding
   - Examples:
     * "What is delta?"
     * "How does gamma affect option pricing?"
     * "Explain the difference between European and American options"
     * "Why do options have time decay?"

2. PRICING/EXECUTION INTENT (route to Pricing Agent):
   - User wants to CALCULATE a specific price
   - User wants to EXECUTE a valuation
   - Providing specific parameters for computation
   - Examples:
     * "Price a call option on AAPL with strike $200"
     * "Calculate the value of this spread"
     * "What's the price of a 3-month put on TSLA?"
     * "Value this barrier option"

IMPORTANT: If the user mentions Greeks (delta, gamma, theta, vega, rho) WITHOUT specific pricing parameters,
they likely want to LEARN about the concept (Educational). Only route to Pricing if they want to calculate
specific Greek values for a specific option.

Respond with ONLY one of these two words: "educational" or "pricing"

Your answer:"""


async def detect_agent_intent(user_message: str) -> AgentDetectionResult:
    """
    Detect which agent should handle the message based on user intent.

    Uses LLM to understand whether user wants to:
    - Learn/understand something → Educational
    - Calculate/execute something → Pricing

    Args:
        user_message: The user's input

    Returns:
        AgentDetectionResult with detected agent and reasoning
    """
    try:
        llm = get_classification_llm()

        # Build the prompt
        prompt = INTENT_DETECTION_PROMPT.format(message=user_message)

        # Get LLM decision
        response = await llm.ainvoke(prompt)
        agent_type = response.content.strip().lower()

        # Validate response
        if agent_type not in ["educational", "pricing"]:
            logger.warning(f"Invalid LLM response for agent detection: {agent_type}")
            # Fallback to educational for questions
            if any(q in user_message.lower() for q in ["what", "how", "why", "explain"]):
                agent_type = "educational"
            else:
                agent_type = "pricing"

        # Generate reasoning
        reasoning = f"User intent detected as {agent_type} based on message analysis"

        return AgentDetectionResult(
            agent_type=agent_type,
            confidence=0.85,  # LLM-based detection has high confidence
            reasoning=reasoning
        )

    except Exception as e:
        logger.error(f"Error in intent-based agent detection: {e}")
        # Fallback to simple heuristic
        if "price" in user_message.lower() or "calculate" in user_message.lower():
            return AgentDetectionResult("pricing", 0.5, "Fallback: pricing keywords detected")
        else:
            return AgentDetectionResult("educational", 0.5, "Fallback: defaulting to educational")


def detect_agent_type_intent_based(user_message: str) -> AgentDetectionResult:
    """
    # Called by: Alternative agent routing implementation (experimental)
    # Uses intent analysis rather than keyword matching or structured classification
    # Synchronous wrapper around detect_agent_intent() async function

    Args:
        user_message: The user's input text

    Returns:
        AgentDetectionResult with detected agent type
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(detect_agent_intent(user_message))