#!/usr/bin/env python3
"""
POC Test Script: Simple Agent Detection Test
=============================================
Standalone test for agent detection that doesn't require full dependencies.

Usage:
    python test_agent_detection_simple.py
"""

import re
from typing import Literal, List
from dataclasses import dataclass

# Define agent types
AgentType = Literal["educational", "pricing", "unified"]


@dataclass
class AgentDetectionResult:
    """Result of agent type detection"""
    agent_type: AgentType
    confidence: float
    matched_keywords: List[str]
    reasoning: str


# Keyword patterns
EDUCATIONAL_KEYWORDS = [
    r"\bwhat is\b", r"\bwhat are\b", r"\bexplain\b", r"\bexplaining\b",
    r"\bhow does\b", r"\bhow do\b", r"\btell me about\b", r"\bhelp me understand\b",
    r"\bwhy does\b", r"\bwhy do\b", r"\bconcept\b", r"\bdefinition\b",
    r"\bdefine\b", r"\bmeaning\b", r"\bmean\b", r"\bdifference between\b",
    r"\bexample of\b", r"\bexamples of\b", r"\bunderstand\b", r"\bunderstanding\b",
    r"\blearn\b", r"\blearning\b", r"\bteach\b", r"\bteaching\b",
    r"\bclarify\b", r"\bclarification\b",
]

PRICING_KEYWORDS = [
    r"\bprice\b", r"\bpricing\b", r"\bcalculate\b", r"\bcompute\b",
    r"\bvalue\b", r"\bvaluation\b", r"\bcost\b", r"\bpremium\b",
    r"\bstrike\b", r"\bexpir(y|ation|es|ing)\b", r"\bvolatility\b",
    r"\brisk.free\b", r"\bspot price\b", r"\bdays to expiry\b",
    r"\btime to maturity\b", r"\bcall option\b", r"\bput option\b",
    r"\bamerican option\b", r"\beuropean option\b", r"\bdigital option\b",
    r"\basian option\b", r"\bbarrier option\b", r"\bstraddle\b",
    r"\bstrangle\b", r"\bspread\b", r"\bbutterfly\b", r"\biron condor\b",
    r"\bhow much\b.*\boption\b", r"\bworth\b", r"\bfair value\b",
]


def detect_agent_type(user_message: str) -> AgentDetectionResult:
    """Detect which agent should handle the user message."""
    message_lower = user_message.lower()

    educational_matches = [p for p in EDUCATIONAL_KEYWORDS if re.search(p, message_lower)]
    pricing_matches = [p for p in PRICING_KEYWORDS if re.search(p, message_lower)]

    educational_score = len(educational_matches)
    pricing_score = len(pricing_matches)
    total_score = educational_score + pricing_score

    if total_score == 0:
        return AgentDetectionResult(
            agent_type="unified",
            confidence=0.3,
            matched_keywords=[],
            reasoning="No clear educational or pricing keywords detected"
        )
    elif educational_score > pricing_score * 1.5:
        confidence = min(0.9, 0.5 + (educational_score / 10))
        return AgentDetectionResult(
            agent_type="educational",
            confidence=confidence,
            matched_keywords=educational_matches,
            reasoning=f"Educational keywords ({educational_score}) significantly outweigh pricing ({pricing_score})"
        )
    elif pricing_score > educational_score * 1.5:
        confidence = min(0.9, 0.5 + (pricing_score / 10))
        return AgentDetectionResult(
            agent_type="pricing",
            confidence=confidence,
            matched_keywords=pricing_matches,
            reasoning=f"Pricing keywords ({pricing_score}) significantly outweigh educational ({educational_score})"
        )
    elif educational_score > pricing_score:
        return AgentDetectionResult(
            agent_type="educational",
            confidence=0.6,
            matched_keywords=educational_matches,
            reasoning=f"Educational keywords ({educational_score}) slightly more than pricing ({pricing_score})"
        )
    elif pricing_score > educational_score:
        return AgentDetectionResult(
            agent_type="pricing",
            confidence=0.6,
            matched_keywords=pricing_matches,
            reasoning=f"Pricing keywords ({pricing_score}) slightly more than educational ({educational_score})"
        )
    else:
        return AgentDetectionResult(
            agent_type="unified",
            confidence=0.5,
            matched_keywords=educational_matches + pricing_matches,
            reasoning=f"Equal educational and pricing signals ({educational_score} each)"
        )


# Test queries
TEST_QUERIES = {
    "educational": [
        "What is a call option?",
        "Explain delta hedging to me",
        "How does the Black-Scholes model work?",
        "Tell me about implied volatility",
        "What's the difference between American and European options?",
        "Can you explain what theta decay means?",
        "Help me understand put-call parity",
    ],
    "pricing": [
        "Price a 30-day call option on AAPL with strike $150",
        "Calculate the value of a put with strike 100, expiry 60 days",
        "What's the premium for a straddle on TSLA?",
        "I need to price a digital call option",
        "How much is this barrier option worth?",
        "Calculate a bull call spread",
        "What's the fair value of this Asian option?",
    ],
    "mixed": [
        "What is a straddle and how much would one cost on AAPL?",
        "Explain gamma and calculate it for my option",
        "Price this call and explain why it has that value",
        "What's an iron condor and can you price one?",
    ],
    "off_topic": [
        "What's the weather like?",
        "Tell me a joke",
        "How do I cook pasta?",
        "What time is it?",
    ]
}


def get_agent_emoji(agent_type: AgentType) -> str:
    """Get emoji representation for agent type"""
    return {"educational": "🎓", "pricing": "💰", "unified": "🤖"}.get(agent_type, "❓")


def main():
    """Run detection tests"""
    print("\n" + "=" * 80)
    print("AGENT DETECTION POC - VALIDATION TEST")
    print("=" * 80)

    # Test detection on all queries
    results = {
        "educational": {"correct": 0, "total": 0},
        "pricing": {"correct": 0, "total": 0},
        "mixed": {"correct": 0, "total": 0},
        "off_topic": {"correct": 0, "total": 0}
    }

    for category, queries in TEST_QUERIES.items():
        print(f"\n{category.upper()} Queries:")
        print("-" * 80)

        for query in queries:
            result = detect_agent_type(query)
            emoji = get_agent_emoji(result.agent_type)

            print(f"\n  Query: {query}")
            print(f"  → {emoji} {result.agent_type.upper()} (confidence: {result.confidence:.0%})")
            print(f"  → {result.reasoning}")

            results[category]["total"] += 1

            # Check correctness
            is_correct = False
            if category == "educational" and result.agent_type == "educational":
                is_correct = True
            elif category == "pricing" and result.agent_type == "pricing":
                is_correct = True
            elif category in ["mixed", "off_topic"] and result.agent_type == "unified":
                is_correct = True

            if is_correct:
                results[category]["correct"] += 1
                print(f"  ✅ CORRECT")
            else:
                print(f"  ⚠️  MISMATCH: Expected {category}, got {result.agent_type}")

    # Summary
    print("\n" + "=" * 80)
    print("ACCURACY SUMMARY")
    print("=" * 80)

    total_correct = 0
    total_queries = 0

    for category, stats in results.items():
        if stats["total"] > 0:
            accuracy = (stats["correct"] / stats["total"]) * 100
            print(f"  {category:15} {stats['correct']:2}/{stats['total']:2} ({accuracy:5.1f}%)")
            total_correct += stats["correct"]
            total_queries += stats["total"]

    if total_queries > 0:
        overall_accuracy = (total_correct / total_queries) * 100
        print("-" * 80)
        print(f"  {'OVERALL':15} {total_correct:2}/{total_queries:2} ({overall_accuracy:5.1f}%)")

    print("\n" + "=" * 80)
    if overall_accuracy >= 80:
        print("✅ DETECTION WORKING WELL (>=80% accuracy)")
    elif overall_accuracy >= 60:
        print("⚠️  DETECTION NEEDS IMPROVEMENT (60-80% accuracy)")
    else:
        print("❌ DETECTION NEEDS SIGNIFICANT WORK (<60% accuracy)")
    print("=" * 80)

    print("\nNext Steps:")
    print("  1. Review any mismatches above")
    print("  2. Adjust keywords if needed")
    print("  3. Install full dependencies to run comprehensive tests")
    print("  4. Test with real queries in your application")
    print()


if __name__ == "__main__":
    main()
