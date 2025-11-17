#!/usr/bin/env python
"""
Quick test of the fixes for pricing crash and educational response.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_vanilla_pricing():
    """Test that vanilla option pricing doesn't crash."""
    print("\n=== Testing Vanilla Option Pricing ===")
    graph = build_orchestrator_graph()

    # Test a vanilla call pricing request
    query = "Can you help me to price a 1-year european call on AAPL with a strike 5% above the current market price?"

    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=query)]
        })

        # Check if we got a response
        if result and result.get("messages"):
            last_message = result["messages"][-1]
            print(f"SUCCESS: Got response without crash")
            print(f"Response preview: {str(last_message.content)[:200]}...")
            return True
        else:
            print("FAILED: No response generated")
            return False

    except Exception as e:
        print(f"FAILED: {e}")
        return False


async def test_educational_response():
    """Test that educational responses don't show 'RAG chunks' text."""
    print("\n=== Testing Educational Response ===")
    graph = build_orchestrator_graph()

    # Test an educational query
    query = "What is delta and how does it affect option pricing?"

    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=query)]
        })

        if result and result.get("messages"):
            last_message = result["messages"][-1]
            content = str(last_message.content)

            # Check for bad phrases
            bad_phrases = [
                "Here is a concise summary",
                "RAG chunks",
                "provided RAG chunks",
                "Educational Explanation:"
            ]

            found_bad_phrases = []
            for phrase in bad_phrases:
                if phrase in content:
                    found_bad_phrases.append(phrase)

            if found_bad_phrases:
                print(f"FAILED: Found bad phrases: {found_bad_phrases}")
                print(f"Response preview: {content[:500]}...")
                return False
            else:
                print("SUCCESS: No bad phrases found")
                print(f"Response preview: {content[:200]}...")
                return True
        else:
            print("FAILED: No response generated")
            return False

    except Exception as e:
        print(f"FAILED: {e}")
        return False


async def test_topic_continuity():
    """Test that topic continuity detects follow-up questions."""
    print("\n=== Testing Topic Continuity ===")
    graph = build_orchestrator_graph()

    # First message about delta
    query1 = "What is delta?"
    result1 = await graph.ainvoke({
        "messages": [HumanMessage(content=query1)]
    })

    # Follow-up about the same topic
    query2 = "Can you explain that more simply?"

    # Get messages from result1 and add the follow-up
    messages = result1.get("messages", [])
    messages.append(HumanMessage(content=query2))

    try:
        result2 = await graph.ainvoke({
            "messages": messages
        })

        if result2 and result2.get("messages"):
            last_message = result2["messages"][-1]
            content = str(last_message.content)

            # Check if it's different from the first response
            first_response = str(result1["messages"][-1].content)

            if content != first_response:
                print("SUCCESS: Follow-up generated different response")
                return True
            else:
                print("FAILED: Follow-up repeated same response")
                print(f"First: {first_response[:100]}...")
                print(f"Second: {content[:100]}...")
                return False
        else:
            print("FAILED: No response generated")
            return False

    except Exception as e:
        print(f"FAILED: {e}")
        return False


async def main():
    """Run all tests."""
    print("Testing fixes...\n")

    results = []

    # Test vanilla pricing
    results.append(("Vanilla Pricing", await test_vanilla_pricing()))

    # Test educational response
    results.append(("Educational Response", await test_educational_response()))

    # Test topic continuity
    results.append(("Topic Continuity", await test_topic_continuity()))

    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\nALL TESTS PASSED!")
    else:
        print("\nSOME TESTS FAILED - Need more fixes")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)