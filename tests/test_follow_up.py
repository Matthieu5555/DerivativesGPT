#!/usr/bin/env python
"""
Test follow-up question handling.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage, AIMessage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_follow_up():
    """Test follow-up question handling."""
    print("\n=== Testing Follow-up Question Handling ===")
    graph = build_orchestrator_graph()

    # First question about delta
    query1 = "What is delta and how does it affect option pricing?"
    print(f"\nUser: {query1}")

    result1 = await graph.ainvoke({
        "messages": [HumanMessage(content=query1)]
    })

    if result1 and result1.get("messages"):
        response1 = result1["messages"][-1].content
        print(f"\nAssistant: {response1[:300]}...")

    # Follow-up about second-order derivative
    query2 = "ah I see so in some sense its the first order derivative wrt the underlying's price, is there a second order derivative used in the industry, what would be its purpose?"
    print(f"\nUser: {query2}")

    # Build conversation with FULL STATE including conversation context
    messages = result1.get("messages", [])
    messages.append(HumanMessage(content=query2))

    # Pass the full state including last_agent
    state_for_follow_up = {
        "messages": messages,
        "last_agent": result1.get("last_agent", None),
        "last_topic": result1.get("last_topic", None),
        "conversation_depth": result1.get("conversation_depth", 0)
    }

    print(f"\nDEBUG: Passing state with last_agent={state_for_follow_up.get('last_agent')}")

    result2 = await graph.ainvoke(state_for_follow_up)

    if result2 and result2.get("messages"):
        response2 = result2["messages"][-1].content
        print(f"\nAssistant: {response2[:500]}...")

        # Check if responses are different
        if response1 == response2:
            print("\n❌ FAILED: Responses are identical - follow-up not handled properly")
            return False
        elif "gamma" in response2.lower() or "second" in response2.lower():
            print("\n✅ SUCCESS: Follow-up handled correctly - mentions gamma/second derivative")
            return True
        else:
            print("\n⚠️  PARTIAL: Response is different but doesn't address gamma")
            return False

    return False


if __name__ == "__main__":
    success = asyncio.run(test_follow_up())
    exit(0 if success else 1)