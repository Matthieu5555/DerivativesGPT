"""
LLM-based Conversation Context Management
==========================================
Maintains conversation continuity across agent transitions using LLM classification.
This replaces hardcoded regex patterns with AI-based understanding.
"""

from typing import Optional, Tuple
from dataclasses import dataclass
import logging
from derivatives_gpt_core.llm_provider import get_classification_llm
from langchain_core.messages import SystemMessage, HumanMessage
import json

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Tracks conversation flow and agent assignments"""
    last_agent: Optional[str] = None
    last_topic: Optional[str] = None
    last_was_educational: bool = False
    last_was_pricing: bool = False
    conversation_depth: int = 0  # How many exchanges in current topic


FOLLOW_UP_DETECTION_PROMPT = """
You are a conversation analyzer that determines if a message is a follow-up to the previous conversation or a new topic.

Analyze the conversation to determine:
1. Is this a FOLLOW_UP to the same topic?
2. Is this a NEW_TOPIC (different subject)?
3. Is this an AGENT_SWITCH (same topic but needs different handling)?

Examples:

Previous: "What is implied volatility?"
Current: "Can you give an example?" → FOLLOW_UP (asking for more on same topic)

Previous: "Explain delta hedging"
Current: "What about gamma?" → NEW_TOPIC (switching to different Greek)

Previous: "How does Black-Scholes work?"
Current: "I'm still confused about the d1 term" → FOLLOW_UP (diving deeper into same topic)

Previous: "Explain what a straddle is"
Current: "Now price a straddle on AAPL" → AGENT_SWITCH (educational to pricing on same strategy)

Previous: "Price a call option"
Current: "Actually, what is a call option?" → AGENT_SWITCH (pricing to educational)

Previous: "Calculate the price of TSLA calls"
Current: "Thanks! Now explain put-call parity" → NEW_TOPIC (finished pricing, new concept)

Return JSON:
{
    "is_follow_up": true/false,
    "confidence": 0.0-1.0,
    "detected_shift": "none" | "topic_change" | "agent_switch",
    "reasoning": "Brief explanation"
}

Previous Topic: {previous_topic}
Previous Message: {previous_message}
Current Message: {current_message}
"""


async def detect_follow_up_llm(
    current_message: str,
    previous_message: Optional[str] = None,
    previous_topic: Optional[str] = None
) -> Tuple[bool, float]:
    """
    Detect if current message is a follow-up using LLM classification.

    Args:
        current_message: Current user message
        previous_message: Previous message for context
        previous_topic: Previous conversation topic

    Returns:
        Tuple of (is_follow_up, confidence)
    """
    if not previous_message:
        return False, 0.0

    try:
        # Get classification LLM
        llm = get_classification_llm()

        # Build prompt with context
        prompt = FOLLOW_UP_DETECTION_PROMPT.format(
            previous_topic=previous_topic or "Unknown",
            previous_message=previous_message,
            current_message=current_message
        )

        # Get LLM classification
        response = await llm.ainvoke([
            SystemMessage(content=prompt)
        ])

        # Parse JSON response
        response_text = response.content.strip()

        try:
            # Handle potential markdown code blocks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text

            classification = json.loads(json_str)

            is_follow_up = classification.get("is_follow_up", False)
            confidence = float(classification.get("confidence", 0.5))
            detected_shift = classification.get("detected_shift", "none")

            logger.info(
                f"Follow-up Detection (LLM): is_follow_up={is_follow_up}, "
                f"confidence={confidence:.2f}, shift={detected_shift}, "
                f"reason={classification.get('reasoning', 'N/A')}"
            )

            return is_follow_up, confidence

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return False, 0.0

    except Exception as e:
        logger.error(f"LLM follow-up detection failed: {e}")
        return False, 0.0


def detect_follow_up(current_message: str, previous_message: Optional[str] = None) -> Tuple[bool, float]:
    """
    Synchronous wrapper for backward compatibility.

    Args:
        current_message: Current user message
        previous_message: Previous message for context

    Returns:
        Tuple of (is_follow_up, confidence)
    """
    import asyncio

    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    detect_follow_up_llm(current_message, previous_message, None)
                )
                return future.result()
        else:
            # Run normally
            return loop.run_until_complete(
                detect_follow_up_llm(current_message, previous_message, None)
            )
    except:
        # Fallback for edge cases
        return asyncio.run(detect_follow_up_llm(current_message, previous_message, None))


async def should_maintain_agent_llm(
    current_message: str,
    last_agent: Optional[str],
    last_message: Optional[str] = None,
    confidence_threshold: float = 0.6
) -> Tuple[bool, Optional[str], str]:
    """
    Determine if we should maintain the same agent using LLM understanding.

    Args:
        current_message: Current user message
        last_agent: Previous agent that handled the conversation
        last_message: Previous message for context
        confidence_threshold: Minimum confidence to maintain agent

    Returns:
        Tuple of (should_maintain, agent_to_use, reasoning)
    """
    if not last_agent:
        return False, None, "No previous agent context"

    is_follow_up, confidence = await detect_follow_up_llm(current_message, last_message, None)

    if is_follow_up and confidence >= confidence_threshold:
        reasoning = f"Follow-up detected (confidence: {confidence:.0%}) - maintaining {last_agent} agent"
        logger.info(reasoning)
        return True, last_agent, reasoning

    # Check for explicit agent switch using a simple LLM prompt
    try:
        llm = get_classification_llm()

        switch_prompt = f"""
        Does this message explicitly request a different type of help than before?

        Previous context: User was using {last_agent} agent
        Current message: {current_message}

        Return JSON:
        {{
            "explicit_switch": true/false,
            "target_agent": "pricing" | "educational" | null,
            "reasoning": "Brief explanation"
        }}
        """

        response = await llm.ainvoke([
            SystemMessage(content=switch_prompt)
        ])

        response_text = response.content.strip()
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text

        switch_detection = json.loads(json_str)

        if switch_detection.get("explicit_switch"):
            target = switch_detection.get("target_agent")
            if target and target != last_agent:
                reasoning = f"Explicit switch to {target} agent requested"
                logger.info(reasoning)
                return False, None, reasoning

    except Exception as e:
        logger.warning(f"Failed to detect explicit switch: {e}")

    # Default: re-detect if not a clear follow-up
    return False, None, "No clear follow-up pattern - re-detecting agent"


def should_maintain_agent(
    current_message: str,
    last_agent: Optional[str],
    last_message: Optional[str] = None,
    confidence_threshold: float = 0.6
) -> Tuple[bool, Optional[str], str]:
    """
    Synchronous wrapper for backward compatibility.

    Returns:
        Tuple of (should_maintain, agent_to_use, reasoning)
    """
    import asyncio

    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    should_maintain_agent_llm(current_message, last_agent, last_message, confidence_threshold)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                should_maintain_agent_llm(current_message, last_agent, last_message, confidence_threshold)
            )
    except:
        return asyncio.run(
            should_maintain_agent_llm(current_message, last_agent, last_message, confidence_threshold)
        )


def enhance_agent_detection_with_context(
    detection_result,
    conversation_context: ConversationContext,
    current_message: str,
    last_message: Optional[str] = None
) -> tuple:
    """
    Enhance agent detection with conversation context using LLM understanding.

    Args:
        detection_result: Original detection result
        conversation_context: Current conversation context
        current_message: Current user message
        last_message: Previous message for context

    Returns:
        Enhanced detection result
    """
    # Check if we should maintain the previous agent
    should_maintain, maintained_agent, reasoning = should_maintain_agent(
        current_message,
        conversation_context.last_agent,
        last_message
    )

    if should_maintain and maintained_agent:
        # Override detection with context-aware routing
        detection_result.agent_type = maintained_agent
        detection_result.confidence = 0.9  # High confidence for continuity
        detection_result.reasoning = f"Conversation continuity: {reasoning}"

        logger.info(
            f"Context-aware routing: Maintaining {maintained_agent} agent "
            f"(was going to route to {detection_result.agent_type})"
        )

    return detection_result