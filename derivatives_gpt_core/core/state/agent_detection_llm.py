"""
LLM-based Agent Type Detection
================================
Detects which agent (educational, pricing) should handle a user query using LLM classification.
This replaces the hardcoded regex patterns with a proper AI-based approach.
"""

from typing import Literal, List
from dataclasses import dataclass
import logging
from derivatives_gpt_core.llm_provider import get_classification_llm
from langchain_core.messages import SystemMessage, HumanMessage
import json

logger = logging.getLogger(__name__)

# Define agent types
AgentType = Literal["educational", "pricing", "unified"]


@dataclass
class AgentDetectionResult:
    """Result of agent type detection"""
    agent_type: AgentType
    confidence: float  # 0.0 to 1.0
    reasoning: str


AGENT_DETECTION_PROMPT = """
You are a classifier that determines whether a user query should be handled by the EDUCATIONAL agent or PRICING agent.

EDUCATIONAL agent handles:
- Conceptual questions ("what is", "explain", "how does X work")
- Learning requests ("teach me", "help me understand")
- General knowledge queries about derivatives concepts
- Greeks explanations (delta, gamma, theta, vega, rho)

PRICING agent handles:
- Requests to calculate option prices
- Queries with specific parameters (strike, expiry, volatility)
- Multi-leg strategy pricing (straddles, strangles, spreads)
- Questions about specific option values

Examples:
- "What is delta?" → EDUCATIONAL (wants to learn concept)
- "Explain Black-Scholes model" → EDUCATIONAL (conceptual understanding)
- "Price a call on AAPL strike 150" → PRICING (needs calculation)
- "Calculate straddle on TSLA" → PRICING (needs calculation)
- "What is delta and calculate it for my option" → PRICING (primarily needs calculation)
- "How does volatility affect prices?" → EDUCATIONAL (conceptual question)
- "What's the price of a 1-month call?" → PRICING (asking for specific price)
- "Can you teach me about iron condors?" → EDUCATIONAL (learning request)
- "Price an iron condor on SPY" → PRICING (specific calculation)

Return a JSON response:
{
    "agent_type": "EDUCATIONAL" or "PRICING",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this agent was chosen"
}

User Query: """


async def detect_agent_type_llm(user_message: str) -> AgentDetectionResult:
    """
    Detect which agent should handle the user message using LLM classification.

    This replaces the regex-based detection with proper AI classification,
    using few-shot examples to guide the LLM.

    Args:
        user_message: The user's input text

    Returns:
        AgentDetectionResult with detected agent type and metadata
    """
    try:
        # Get classification LLM
        llm = get_classification_llm()

        # Build prompt with user message
        prompt = AGENT_DETECTION_PROMPT + user_message

        # Get LLM classification
        response = await llm.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_message)
        ])

        # Parse JSON response
        response_text = response.content.strip()

        # Extract JSON from response
        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text

            classification = json.loads(json_str)

            # Map to our agent types
            agent_type = classification["agent_type"].lower()
            if agent_type not in ["educational", "pricing"]:
                # Default to unified if unclear
                agent_type = "unified"

            result = AgentDetectionResult(
                agent_type=agent_type,
                confidence=float(classification.get("confidence", 0.5)),
                reasoning=classification.get("reasoning", "LLM classification")
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}. Response: {response_text}")
            # Fallback to unified agent
            result = AgentDetectionResult(
                agent_type="unified",
                confidence=0.3,
                reasoning="Failed to parse LLM response, defaulting to unified"
            )

    except Exception as e:
        logger.error(f"LLM agent detection failed: {e}")
        # Fallback to unified agent
        result = AgentDetectionResult(
            agent_type="unified",
            confidence=0.3,
            reasoning=f"LLM detection failed: {str(e)}"
        )

    # Log the detection
    logger.info(
        f"Agent Detection (LLM): {result.agent_type.upper()} "
        f"(confidence: {result.confidence:.2f}) - {result.reasoning}"
    )

    return result


def detect_agent_type(user_message: str) -> AgentDetectionResult:
    """
    Synchronous wrapper for backward compatibility.

    This maintains the same interface as the old regex-based function
    but uses LLM classification under the hood.

    Args:
        user_message: The user's input text

    Returns:
        AgentDetectionResult with detected agent type
    """
    import asyncio

    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, detect_agent_type_llm(user_message))
                return future.result()
        else:
            # Run normally
            return loop.run_until_complete(detect_agent_type_llm(user_message))
    except:
        # Fallback for edge cases
        return asyncio.run(detect_agent_type_llm(user_message))


def get_agent_emoji(agent_type: AgentType) -> str:
    """Get emoji representation for agent type"""
    return {
        "educational": "[EDU]",
        "pricing": "[PRICE]",
        "unified": "[UNI]"
    }.get(agent_type, "[?]")


def format_detection_summary(result: AgentDetectionResult) -> str:
    """Format detection result for display"""
    emoji = get_agent_emoji(result.agent_type)

    summary = f"{emoji} **Agent: {result.agent_type.upper()}** (confidence: {result.confidence:.0%})\n"
    summary += f"*Reasoning: {result.reasoning}*"

    return summary