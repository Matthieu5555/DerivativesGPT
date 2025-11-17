#!/usr/bin/env python
"""
Final test of all fixes.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def main():
    """Test all fixes."""
    print("\n" + "=" * 60)
    print("FINAL TEST OF ALL FIXES")
    print("=" * 60)

    # Build the orchestrator graph
    graph = build_orchestrator_graph()

    print("\n1. Testing Delta Question...")
    result1 = await graph.ainvoke(
        {"messages": [HumanMessage(content="What is delta and how does it affect option pricing?")]}
    )

    if result1 and result1.get("messages"):
        # Find all AI messages
        ai_messages = [msg for msg in result1["messages"]
                      if hasattr(msg, 'content') and not isinstance(msg, HumanMessage)]

        print(f"\nFound {len(ai_messages)} AI messages")

        # Check if structured explanation exists (should have TL;DR)
        full_response = "\n".join([msg.content for msg in ai_messages])

        if "TL;DR" in full_response or "**TL;DR**" in full_response:
            print("✅ Iron Condor format found (has TL;DR section)")
        else:
            print("❌ No TL;DR section found - not using Iron Condor format")

        if "Learning Reflection" in full_response:
            print("✅ Learning Reflection added")

        # Show last message (what Chainlit shows)
        last_msg = ai_messages[-1].content if ai_messages else ""
        print(f"\nLAST MESSAGE (shown in Chainlit):\n{last_msg[:500]}...")

    print("\n2. Testing Follow-up...")
    messages = result1.get("messages", [])
    messages.append(HumanMessage(content="yes what is gamma?"))

    result2 = await graph.ainvoke({
        "messages": messages,
        "last_agent": result1.get("last_agent"),
        "last_topic": result1.get("last_topic"),
        "conversation_depth": result1.get("conversation_depth", 0)
    })

    if result2 and result2.get("messages"):
        response2 = result2["messages"][-1].content
        if "gamma" in response2.lower():
            print("✅ Follow-up working - mentions gamma")
        else:
            print("❌ Follow-up not working - no gamma mention")

    print("\n3. Testing Pricing (should not crash)...")
    try:
        result3 = await graph.ainvoke(
            {"messages": [HumanMessage(content="Price a 1-year European call on AAPL, strike 5% above current")]}
        )
        if result3:
            print("✅ Pricing works without crashing")
    except Exception as e:
        print(f"❌ Pricing crashed: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())