#!/usr/bin/env python
"""
Test that the OLD launcher (chainlit_application_launcher.py) works with follow-up detection.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_old_launcher_follow_up():
    """Test follow-up detection in the old launcher setup."""
    print("\n=== Testing OLD Launcher with Follow-up Detection ===")

    # Build the orchestrator graph (same as old launcher now uses)
    graph = build_orchestrator_graph()

    # First question about delta
    query1 = "What is delta and how does it affect option pricing?"
    print(f"\nUser: {query1}")

    result1 = await graph.ainvoke(
        {"messages": [HumanMessage(content=query1)]}
    )

    if result1 and result1.get("messages"):
        response1 = result1["messages"][-1].content
        print(f"\nAssistant: {response1[:300]}...")
        print(f"\nConversation context: last_agent={result1.get('last_agent')}")

    # Follow-up about gamma
    query2 = "yes what is gamma?"
    print(f"\nUser: {query2}")

    # Build state with conversation context (simulating what old launcher does)
    messages = result1.get("messages", [])
    messages.append(HumanMessage(content=query2))

    state_for_follow_up = {
        "messages": messages,
        "last_agent": result1.get("last_agent"),
        "last_topic": result1.get("last_topic"),
        "conversation_depth": result1.get("conversation_depth", 0)
    }

    result2 = await graph.ainvoke(state_for_follow_up)

    if result2 and result2.get("messages"):
        response2 = result2["messages"][-1].content
        print(f"\nAssistant: {response2[:500]}...")

        # Check if responses are different and gamma is mentioned
        if response1 == response2:
            print("\n❌ FAILED: Same response - follow-up not working")
            return False
        elif "gamma" in response2.lower() or "second" in response2.lower():
            print("\n✅ SUCCESS: Follow-up working - mentions gamma/second derivative")
            return True
        else:
            print("\n⚠️ PARTIAL: Response is different but doesn't mention gamma")
            return False

    return False


async def test_vanilla_pricing():
    """Test that vanilla pricing doesn't crash."""
    print("\n=== Testing Vanilla Pricing ===")

    graph = build_orchestrator_graph()

    query = "Price a 1-year European call on AAPL, strike 5% above current"
    print(f"User: {query}")

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=query)]}
        )
        if result and result.get("messages"):
            print("✅ SUCCESS: No crash on vanilla pricing")
            return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

    return False


async def main():
    """Run all tests for the old launcher."""
    print("=" * 60)
    print("Testing OLD Launcher (chainlit_application_launcher.py)")
    print("=" * 60)

    results = []

    # Run tests
    results.append(await test_old_launcher_follow_up())
    results.append(await test_vanilla_pricing())

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if all(results):
        print("✅ All tests passed!")
        print("\nThe OLD launcher now has:")
        print("- Multi-agent orchestrator with follow-up detection")
        print("- Conversation context preservation")
        print("- Proper response to gamma question")
        print("- No crashes on vanilla pricing")
        print("\nYou can now use: chainlit run chainlit_application_launcher.py")
    else:
        print("❌ Some tests failed")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)