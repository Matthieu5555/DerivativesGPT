#!/usr/bin/env python
"""
Test that Iron Condor format displays properly in Chainlit.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage

# Minimal logging
logging.basicConfig(level=logging.WARNING)


async def main():
    """Test Iron Condor format display."""
    print("\n" + "=" * 60)
    print("TESTING IRON CONDOR FORMAT DISPLAY")
    print("=" * 60)

    # Build the orchestrator graph
    graph = build_orchestrator_graph()

    print("\n1. Testing Initial Explanation (should show Iron Condor format)...")
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="What is delta and how does it affect option pricing?")]}
    )

    if result and result.get("messages"):
        # Find all AI messages
        ai_messages = [msg for msg in result["messages"]
                      if hasattr(msg, 'content') and not isinstance(msg, HumanMessage)]

        print(f"\nFound {len(ai_messages)} AI messages")

        # Check each message
        for i, msg in enumerate(ai_messages, 1):
            content = msg.content
            print(f"\n--- Message {i} Preview (first 200 chars) ---")
            print(content[:200] + "...")

            # Check what this message contains
            if "**TL;DR**" in content or "TL;DR" in content:
                print("  ✅ This is the Iron Condor formatted explanation")
            if "Learning Reflection" in content:
                print("  ⚠️ This is a Learning Reflection (should be skipped)")
            if "verify" in content.lower() or "understanding" in content.lower():
                print("  📝 This appears to be verification questions")

        # The LAST message is what Chainlit shows
        last_msg = ai_messages[-1].content if ai_messages else ""

        print("\n" + "=" * 60)
        print("WHAT CHAINLIT DISPLAYS (Last Message):")
        print("=" * 60)

        if "**TL;DR**" in last_msg or "## TL;DR" in last_msg:
            print("✅ SUCCESS: Iron Condor format is displayed!")
            print("\nPreview of displayed content:")
            print(last_msg[:500] + "...")
        elif "Learning Reflection" in last_msg:
            print("❌ FAIL: Learning Reflection is displayed instead of Iron Condor format")
        else:
            print("⚠️ UNKNOWN: Last message doesn't match expected format")
            print("\nActual content preview:")
            print(last_msg[:500] + "...")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())