#!/usr/bin/env python
"""Test that RAG citations appear in pricing responses."""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage

# Minimal logging
logging.basicConfig(level=logging.WARNING)

async def main():
    """Test RAG citations in pricing response."""
    print("\n" + "=" * 60)
    print("TESTING PRICING RAG CITATIONS")
    print("=" * 60)

    graph = build_orchestrator_graph()

    print("\nAsking: Price a 1-year European call on AAPL, strike 5% above current")
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="Price a 1-year European call on AAPL, strike 5% above current")]}
    )

    if result and result.get("messages"):
        response = result["messages"][-1].content

        print("\n" + "=" * 60)
        print("RESPONSE:")
        print("=" * 60)
        print(response)

        print("\n" + "=" * 60)
        print("CHECKING FOR CITATIONS:")
        print("=" * 60)

        # Check for citations
        if "Sources" in response or "sources" in response:
            print("✅ Sources section found")
        else:
            print("❌ No sources section")

        if '\"' in response and "(" in response and ")" in response:
            print("✅ Citation format found with quotes")
        else:
            print("⚠️ No quoted citations found")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
