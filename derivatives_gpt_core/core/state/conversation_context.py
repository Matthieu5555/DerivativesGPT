"""
Conversation Context Management
================================
Maintains conversation continuity across agent transitions.
"""

from typing import Optional, Tuple
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Tracks conversation flow and agent assignments"""
    last_agent: Optional[str] = None
    last_topic: Optional[str] = None
    last_was_educational: bool = False
    last_was_pricing: bool = False
    conversation_depth: int = 0  # How many exchanges in current topic


def detect_follow_up(current_message: str, previous_message: Optional[str] = None) -> Tuple[bool, float]:
    """
    Detect if current message is a follow-up to previous conversation.

    Returns:
        Tuple of (is_follow_up, confidence)
    """
    if not previous_message:
        return False, 0.0

    current_lower = current_message.lower()

    # Strong follow-up indicators
    FOLLOW_UP_PATTERNS = [
        r"^(yes|yeah|yep|sure|ok|okay|alright|got it|i see|ah|oh)",
        r"^(and|but|so|also|furthermore|moreover)",
        r"^(what about|how about|what if)",
        r"^(can you|could you|would you).*(more|explain|elaborate|clarify)",
        r"^(that|this|it)\s+(is|was|seems|sounds)",
        r"^in (that|this) case",
        r"^(thanks|thank you).*(but|and|what)",
        r"more (specifically|precisely|exactly)",
        r"(tell|explain|show) me more",
        r"what (else|more)",
        r"anything else",
        r"another (question|thing)",
        r"one more",
    ]

    # Check for follow-up patterns
    for pattern in FOLLOW_UP_PATTERNS:
        if re.search(pattern, current_lower):
            return True, 0.8

    # Check for pronouns referring to previous context
    CONTEXT_PRONOUNS = [
        r"\b(that|this|it|its|these|those|such)\b",
        r"\b(the same|similar|like that)\b",
        r"\b(above|previous|mentioned|discussed)\b",
    ]

    pronoun_count = sum(1 for p in CONTEXT_PRONOUNS if re.search(p, current_lower))
    if pronoun_count >= 2:
        return True, 0.7
    elif pronoun_count == 1:
        return True, 0.6

    # Check for topic continuity (shared key terms)
    # Extract key terms (nouns, verbs) from both messages
    KEY_TERM_PATTERNS = [
        r"\b(delta|gamma|theta|vega|rho)\b",  # Greeks
        r"\b(option|call|put|strike|expiry|volatility)\b",  # Options terms
        r"\b(derivative|underlying|hedge|risk)\b",  # General derivatives
        r"\b(black[\s-]scholes|binomial|monte[\s-]carlo)\b",  # Models
    ]

    prev_terms = set()
    curr_terms = set()

    for pattern in KEY_TERM_PATTERNS:
        if re.search(pattern, previous_message.lower()):
            prev_terms.add(pattern)
        if re.search(pattern, current_lower):
            curr_terms.add(pattern)

    # If significant overlap in key terms, likely a follow-up
    if prev_terms and curr_terms:
        overlap = len(prev_terms & curr_terms) / len(prev_terms | curr_terms)
        if overlap > 0.3:
            return True, 0.5 + overlap * 0.5

    return False, 0.0


def should_maintain_agent(
    current_message: str,
    last_agent: Optional[str],
    last_message: Optional[str] = None,
    confidence_threshold: float = 0.6
) -> Tuple[bool, Optional[str], str]:
    """
    Determine if we should maintain the same agent for continuity.

    Returns:
        Tuple of (should_maintain, agent_to_use, reasoning)
    """
    if not last_agent:
        return False, None, "No previous agent context"

    is_follow_up, confidence = detect_follow_up(current_message, last_message)

    if is_follow_up and confidence >= confidence_threshold:
        reasoning = f"Follow-up detected (confidence: {confidence:.0%}) - maintaining {last_agent} agent"
        logger.info(reasoning)
        return True, last_agent, reasoning

    # Check for explicit agent switch requests
    SWITCH_PATTERNS = {
        "pricing": [
            r"\b(now|let's|can you|please)\s+(price|calculate|value)",
            r"how much (would|does|is)",
            r"what's the (price|premium|cost)",
        ],
        "educational": [
            r"\b(now|let's|can you)\s+(explain|teach|help me understand)",
            r"(switch|change) to (explaining|teaching)",
            r"forget (pricing|calculating)",
        ]
    }

    current_lower = current_message.lower()

    for agent_type, patterns in SWITCH_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, current_lower):
                if agent_type != last_agent:
                    reasoning = f"Explicit switch to {agent_type} agent requested"
                    logger.info(reasoning)
                    return False, None, reasoning

    # Default: re-detect if not a clear follow-up
    return False, None, "No clear follow-up pattern - re-detecting agent"


def enhance_agent_detection_with_context(
    detection_result,
    conversation_context: ConversationContext,
    current_message: str,
    last_message: Optional[str] = None
) -> tuple:
    """
    Enhance agent detection with conversation context.

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