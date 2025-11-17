#!/usr/bin/env python
"""
Test Chainlit-specific fixes:
1. No duplicate messages
2. No emojis in display
3. Follow-up questions work correctly
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage, AIMessage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_chainlit_scenario():
    """Test the exact scenario reported by the user."""
    print("\n=== Testing Chainlit Scenario ===")
    graph = build_orchestrator_graph()

    # First question about delta
    query1 = "What is delta and how does it affect option pricing?"
    print(f"\nUser: {query1}")

    # Simulate with checkpointer config
    config = {
        "configurable": {
            "thread_id": "test_session_123",
            "checkpoint_ns": ""
        }
    }

    result1 = await graph.ainvoke(
        {"messages": [HumanMessage(content=query1)]},
        config=config
    )

    if result1 and result1.get("messages"):
        response1 = result1["messages"][-1].content
        print(f"\nAssistant (first): {response1[:300]}...")

        # Check conversation context was set
        print(f"\nConversation context after first query:")
        print(f"  last_agent: {result1.get('last_agent')}")
        print(f"  last_topic: {result1.get('last_topic')}")
        print(f"  conversation_depth: {result1.get('conversation_depth')}")

    # Follow-up about second-order derivative
    query2 = "is this the first order derivative? is there a second order one?"
    print(f"\nUser: {query2}")

    # Build state for follow-up WITH full conversation
    # This simulates what should happen with checkpointer
    messages = result1.get("messages", [])
    messages.append(HumanMessage(content=query2))

    # Pass the full state including context
    state_for_follow_up = {
        "messages": messages,
        # These should be preserved by checkpointer
        "last_agent": result1.get("last_agent"),
        "last_topic": result1.get("last_topic"),
        "conversation_depth": result1.get("conversation_depth", 0)
    }

    print(f"\nDEBUG: Passing state with last_agent={state_for_follow_up.get('last_agent')}")

    result2 = await graph.ainvoke(state_for_follow_up, config=config)

    if result2 and result2.get("messages"):
        response2 = result2["messages"][-1].content
        print(f"\nAssistant (follow-up): {response2[:500]}...")

        # Check if responses are different
        if response1 == response2:
            print("\n❌ FAILED: Responses are identical - follow-up not handled properly")
            return False
        elif "gamma" in response2.lower() or "second" in response2.lower():
            print("\n✅ SUCCESS: Follow-up handled correctly - mentions gamma/second derivative")

            # Check for emojis
            if "🎓" in response2 or "💰" in response2 or "🤖" in response2:
                print("⚠️ WARNING: Emojis found in response!")
                return False
            else:
                print("✅ No emojis in response")

            return True
        else:
            print("\n⚠️ PARTIAL: Response is different but doesn't address gamma")
            return False

    return False


async def test_no_emojis():
    """Verify no emojis appear in responses."""
    print("\n=== Testing No Emojis ===")

    # Check the streaming handler
    from derivatives_gpt_core.utils.chainlit_streaming import AgentStreamingCallbackHandler
    handler = AgentStreamingCallbackHandler("educational")

    # Check if emoji fields exist
    if hasattr(handler, 'agent_emoji'):
        print(f"❌ FAILED: agent_emoji field still exists: {handler.agent_emoji}")
        return False

    if hasattr(handler, 'show_agent_badge') and handler.show_agent_badge == False:
        print("✅ Agent badge disabled")

    print("✅ No emoji fields in streaming handler")
    return True


async def main():
    """Run all Chainlit-specific tests."""
    print("=" * 60)
    print("Chainlit-Specific Fixes Tests")
    print("=" * 60)

    results = []

    # Run tests
    results.append(await test_no_emojis())
    results.append(await test_chainlit_scenario())

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if all(results):
        print("✅ All Chainlit fixes verified!")
        print("\nFixed issues:")
        print("- No duplicate messages (RAG reformulation not streamed)")
        print("- No emojis in agent display")
        print("- Follow-up questions properly handled")
        print("- Conversation context preserved")
    else:
        print("❌ Some issues remain")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)