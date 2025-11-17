"""
Proof-of-Concept: Agent Type Detection
=======================================
Detects which agent (educational, pricing, or unified) should handle a user query.
This is a lightweight POC to validate the agent separation approach.
"""

from typing import Literal, Dict, Any, List
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)

# Define agent types
AgentType = Literal["educational", "pricing", "unified"]


@dataclass
class AgentDetectionResult:
    """Result of agent type detection"""
    agent_type: AgentType
    confidence: float  # 0.0 to 1.0
    matched_keywords: List[str]
    reasoning: str


# Keyword patterns for each agent type
EDUCATIONAL_KEYWORDS = [
    # Question words
    r"\bwhat is\b",
    r"\bwhat are\b",
    r"\bexplain\b",
    r"\bexplaining\b",
    r"\bhow does\b",
    r"\bhow do\b",
    r"\btell me about\b",
    r"\bhelp me understand\b",
    r"\bwhy does\b",
    r"\bwhy do\b",

    # Conceptual terms
    r"\bconcept\b",
    r"\bdefinition\b",
    r"\bdefine\b",
    r"\bmeaning\b",
    r"\bmean\b",
    r"\bdifference between\b",
    r"\bexample of\b",
    r"\bexamples of\b",
    r"\bunderstand\b",
    r"\bunderstanding\b",

    # Educational intent
    r"\blearn\b",
    r"\blearning\b",
    r"\bteach\b",
    r"\bteaching\b",
    r"\bclarify\b",
    r"\bclarification\b",

    # Greeks - educational concepts
    r"\bdelta\b",
    r"\bgamma\b",
    r"\btheta\b",
    r"\bvega\b",
    r"\brho\b",
    r"\bgreeks?\b",
]

PRICING_KEYWORDS = [
    # Pricing actions
    r"\bprice\b",
    r"\bpricing\b",
    r"\bcalculate\b",
    r"\bcompute\b",
    r"\bvalue\b",
    r"\bvaluation\b",
    r"\bcost\b",
    r"\bpremium\b",

    # Option parameters (strong signals)
    r"\bstrike\b",
    r"\bexpir(y|ation|es|ing)\b",
    r"\bvolatility\b",
    r"\brisk.free\b",
    r"\bspot price\b",
    r"\bdays to expiry\b",
    r"\btime to maturity\b",

    # Option types
    r"\bcall option\b",
    r"\bput option\b",
    r"\bamerican option\b",
    r"\beuropean option\b",
    r"\bdigital option\b",
    r"\basian option\b",
    r"\bbarrier option\b",

    # Strategy names
    r"\bstraddle\b",
    r"\bstrangle\b",
    r"\bspread\b",
    r"\bbutterfly\b",
    r"\biron condor\b",

    # Specific pricing requests
    r"\bhow much\b.*\boption\b",
    r"\bworth\b",
    r"\bfair value\b",
]


def detect_agent_type(user_message: str) -> AgentDetectionResult:
    """
    Detect which agent should handle the user message.

    Args:
        user_message: The user's input text

    Returns:
        AgentDetectionResult with detected agent type and metadata
    """
    message_lower = user_message.lower()

    # Count matches for each agent type
    educational_matches = []
    pricing_matches = []

    for pattern in EDUCATIONAL_KEYWORDS:
        if re.search(pattern, message_lower):
            educational_matches.append(pattern)

    for pattern in PRICING_KEYWORDS:
        if re.search(pattern, message_lower):
            pricing_matches.append(pattern)

    # Calculate scores
    educational_score = len(educational_matches)
    pricing_score = len(pricing_matches)

    # BUG FIX: Boost educational score if query starts with strong educational patterns
    # Queries like "What is X and how do you calculate Y?" should be educational despite "calculate"
    EDUCATIONAL_PRIORITY_PATTERNS = [
        r"^what is\b",
        r"^what are\b",
        r"^explain\b",
        r"^how does\b",
        r"^how do\b",
        r"^tell me about\b",
        r"^help me understand\b",
        r"^define\b",
    ]

    # Check if query starts with educational pattern (first 30 chars)
    query_start = message_lower[:30]
    for pattern in EDUCATIONAL_PRIORITY_PATTERNS:
        if re.search(pattern, query_start):
            educational_score *= 2.0  # Double educational score
            logger.info(f"Educational priority pattern detected at start of query, boosting score")
            break

    total_score = educational_score + pricing_score

    # Determine agent type
    if total_score == 0:
        # No clear signal - use unified agent
        result = AgentDetectionResult(
            agent_type="unified",
            confidence=0.3,
            matched_keywords=[],
            reasoning="No clear educational or pricing keywords detected"
        )
    elif educational_score > pricing_score * 1.5:
        # Strong educational signal
        confidence = min(0.9, 0.5 + (educational_score / 10))
        result = AgentDetectionResult(
            agent_type="educational",
            confidence=confidence,
            matched_keywords=educational_matches,
            reasoning=f"Educational keywords ({educational_score}) significantly outweigh pricing ({pricing_score})"
        )
    elif pricing_score > educational_score * 1.5:
        # Strong pricing signal
        confidence = min(0.9, 0.5 + (pricing_score / 10))
        result = AgentDetectionResult(
            agent_type="pricing",
            confidence=confidence,
            matched_keywords=pricing_matches,
            reasoning=f"Pricing keywords ({pricing_score}) significantly outweigh educational ({educational_score})"
        )
    elif educational_score > pricing_score:
        # Slight educational preference
        confidence = 0.6
        result = AgentDetectionResult(
            agent_type="educational",
            confidence=confidence,
            matched_keywords=educational_matches,
            reasoning=f"Educational keywords ({educational_score}) slightly more than pricing ({pricing_score})"
        )
    elif pricing_score > educational_score:
        # Slight pricing preference
        confidence = 0.6
        result = AgentDetectionResult(
            agent_type="pricing",
            confidence=confidence,
            matched_keywords=pricing_matches,
            reasoning=f"Pricing keywords ({pricing_score}) slightly more than educational ({educational_score})"
        )
    else:
        # Equal scores - use unified
        result = AgentDetectionResult(
            agent_type="unified",
            confidence=0.5,
            matched_keywords=educational_matches + pricing_matches,
            reasoning=f"Equal educational and pricing signals ({educational_score} each)"
        )

    # Log the detection
    logger.info(
        f"Agent Detection: {result.agent_type.upper()} "
        f"(confidence: {result.confidence:.2f}) - {result.reasoning}"
    )

    return result


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

    if result.matched_keywords:
        keywords_str = ", ".join(result.matched_keywords[:5])  # Show first 5
        if len(result.matched_keywords) > 5:
            keywords_str += f" (+{len(result.matched_keywords) - 5} more)"
        summary += f"\n*Matched: {keywords_str}*"

    return summary
