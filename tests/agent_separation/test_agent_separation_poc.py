#!/usr/bin/env python3
"""
POC Test Script: Agent Separation Validation
=============================================
Tests agent detection and field tracking to validate the separation approach.

Usage:
    python test_agent_separation_poc.py
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from derivatives_gpt_core.core.state.agent_detection import (
    detect_agent_type,
    format_detection_summary,
    get_agent_emoji
)
from derivatives_gpt_core.core.state.field_tracker import (
    get_field_tracker,
    reset_field_tracker,
    SHARED_FIELDS,
    EDUCATIONAL_FIELDS,
    PRICING_FIELDS
)
from derivatives_gpt_core.core.state.agent_monitor import (
    AgentMonitor,
    get_session_report,
    reset_monitoring
)
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Test queries for each agent type
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


class MockState:
    """Mock state object for testing"""
    def __init__(self, message: str):
        self.messages = [MockMessage(message)]
        self.thread_id = "test_session"
        # Pricing fields
        self.spot_price = None
        self.strike_price = None
        self.option_type = None
        # Educational fields
        self.explanation_text = None
        self.user_understanding_score = None


class MockMessage:
    """Mock message object"""
    def __init__(self, content: str):
        self.content = content


def test_agent_detection():
    """Test 1: Agent type detection"""
    print("\n" + "=" * 80)
    print("TEST 1: AGENT TYPE DETECTION")
    print("=" * 80)

    for category, queries in TEST_QUERIES.items():
        print(f"\n{category.upper()} Queries:")
        print("-" * 80)

        for query in queries:
            result = detect_agent_type(query)
            emoji = get_agent_emoji(result.agent_type)

            print(f"\n  Query: {query}")
            print(f"  → {emoji} {result.agent_type.upper()} (confidence: {result.confidence:.0%})")
            print(f"  → {result.reasoning}")

            # Highlight mismatches
            if category == "educational" and result.agent_type != "educational":
                print(f"  ⚠️  MISMATCH: Expected educational, got {result.agent_type}")
            elif category == "pricing" and result.agent_type != "pricing":
                print(f"  ⚠️  MISMATCH: Expected pricing, got {result.agent_type}")

    print("\n" + "=" * 80)


def test_field_access_tracking():
    """Test 2: Field access tracking"""
    print("\n" + "=" * 80)
    print("TEST 2: FIELD ACCESS TRACKING")
    print("=" * 80)

    reset_field_tracker()
    tracker = get_field_tracker()

    # Simulate educational agent accessing fields
    print("\n📚 EDUCATIONAL AGENT:")
    print("-" * 80)

    edu_fields_to_test = [
        ("messages", True),  # Shared - should be allowed
        ("explanation_text", True),  # Educational - should be allowed
        ("user_understanding_score", True),  # Educational - should be allowed
        ("spot_price", False),  # Pricing - should be DENIED
        ("execution_plan", False),  # Pricing - should be DENIED
    ]

    for field, expected_allowed in edu_fields_to_test:
        allowed = tracker.track_access(field, "educational", "read")
        status = "✅ ALLOWED" if allowed else "❌ DENIED"
        match = "✓" if allowed == expected_allowed else "✗ UNEXPECTED"
        print(f"  {match} {status}: {field}")

    # Simulate pricing agent accessing fields
    print("\n💰 PRICING AGENT:")
    print("-" * 80)

    pricing_fields_to_test = [
        ("messages", True),  # Shared - should be allowed
        ("spot_price", True),  # Pricing - should be allowed
        ("execution_plan", True),  # Pricing - should be allowed
        ("explanation_text", False),  # Educational - should be DENIED
        ("user_understanding_score", False),  # Educational - should be DENIED
    ]

    for field, expected_allowed in pricing_fields_to_test:
        allowed = tracker.track_access(field, "pricing", "write")
        status = "✅ ALLOWED" if allowed else "❌ DENIED"
        match = "✓" if allowed == expected_allowed else "✗ UNEXPECTED"
        print(f"  {match} {status}: {field}")

    # Show tracker report
    print("\n" + tracker.generate_report())


def test_agent_monitor():
    """Test 3: Agent monitoring in simulated node execution"""
    print("\n" + "=" * 80)
    print("TEST 3: AGENT MONITORING SIMULATION")
    print("=" * 80)

    reset_monitoring()

    # Simulate educational query
    edu_query = "What is delta hedging?"
    edu_state = MockState(edu_query)

    print(f"\n📚 Educational Query: '{edu_query}'")
    print("-" * 80)

    monitor = AgentMonitor(edu_state, "test_node", "session_1")
    monitor.log_node_entry()

    # Simulate field accesses
    monitor.read_field("messages", edu_state.messages)
    monitor.write_field("explanation_text", "Delta hedging is...")
    monitor.write_field("user_understanding_score", 0.8)

    # Try to access pricing field (should log warning)
    monitor.write_field("spot_price", 150.0)

    monitor.log_node_exit()

    # Simulate pricing query
    pricing_query = "Price a call option on AAPL"
    pricing_state = MockState(pricing_query)

    print(f"\n💰 Pricing Query: '{pricing_query}'")
    print("-" * 80)

    monitor = AgentMonitor(pricing_state, "test_node", "session_2")
    monitor.log_node_entry()

    # Simulate field accesses
    monitor.read_field("messages", pricing_state.messages)
    monitor.write_field("spot_price", 150.0)
    monitor.write_field("strike_price", 155.0)

    # Try to access educational field (should log warning)
    monitor.write_field("explanation_text", "This is a call option...")

    monitor.log_node_exit()

    # Print session reports
    print("\n" + "=" * 80)
    print("SESSION REPORTS:")
    print("=" * 80)

    for session_id in ["session_1", "session_2"]:
        report = get_session_report(session_id)
        if report:
            print(report)


def test_field_categorization():
    """Test 4: Verify field categorization"""
    print("\n" + "=" * 80)
    print("TEST 4: FIELD CATEGORIZATION")
    print("=" * 80)

    print(f"\n📁 SHARED FIELDS ({len(SHARED_FIELDS)}):")
    print("  " + ", ".join(sorted(SHARED_FIELDS)))

    print(f"\n📚 EDUCATIONAL FIELDS ({len(EDUCATIONAL_FIELDS)}):")
    print("  " + ", ".join(sorted(EDUCATIONAL_FIELDS)))

    print(f"\n💰 PRICING FIELDS ({len(PRICING_FIELDS)}):")
    print("  " + ", ".join(sorted(PRICING_FIELDS)))

    # Check for overlaps (should be none)
    edu_pricing_overlap = EDUCATIONAL_FIELDS & PRICING_FIELDS
    edu_shared_overlap = EDUCATIONAL_FIELDS & SHARED_FIELDS
    pricing_shared_overlap = PRICING_FIELDS & SHARED_FIELDS

    print(f"\n🔍 OVERLAP ANALYSIS:")
    if edu_pricing_overlap:
        print(f"  ⚠️  Educational-Pricing overlap: {edu_pricing_overlap}")
    else:
        print(f"  ✅ No Educational-Pricing overlap")

    if edu_shared_overlap:
        print(f"  ⚠️  Educational-Shared overlap: {edu_shared_overlap}")
    else:
        print(f"  ✅ No Educational-Shared overlap")

    if pricing_shared_overlap:
        print(f"  ⚠️  Pricing-Shared overlap: {pricing_shared_overlap}")
    else:
        print(f"  ✅ No Pricing-Shared overlap")


def test_detection_accuracy():
    """Test 5: Calculate detection accuracy metrics"""
    print("\n" + "=" * 80)
    print("TEST 5: DETECTION ACCURACY METRICS")
    print("=" * 80)

    results = {
        "educational": {"correct": 0, "total": 0},
        "pricing": {"correct": 0, "total": 0},
        "mixed": {"correct": 0, "total": 0},
        "off_topic": {"correct": 0, "total": 0}
    }

    for category, queries in TEST_QUERIES.items():
        for query in queries:
            detection = detect_agent_type(query)
            results[category]["total"] += 1

            # Check if detection matches expectation
            if category == "educational" and detection.agent_type == "educational":
                results[category]["correct"] += 1
            elif category == "pricing" and detection.agent_type == "pricing":
                results[category]["correct"] += 1
            elif category == "mixed" and detection.agent_type == "unified":
                results[category]["correct"] += 1
            elif category == "off_topic" and detection.agent_type == "unified":
                results[category]["correct"] += 1

    print("\n📊 Accuracy by Category:")
    print("-" * 80)

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


def main():
    """Run all POC tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  AGENT SEPARATION POC - VALIDATION TEST SUITE".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        test_agent_detection()
        test_field_access_tracking()
        test_agent_monitor()
        test_field_categorization()
        test_detection_accuracy()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nNext Steps:")
        print("  1. Review detection accuracy and adjust keywords if needed")
        print("  2. Validate field categorization matches your architecture")
        print("  3. Enable POC in graph: export ENABLE_AGENT_MONITORING_POC=true")
        print("  4. Test with real queries in Chainlit")
        print("  5. Proceed with full agent separation implementation")
        print()

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
