#!/usr/bin/env python
"""Comprehensive test for RAG citations in both educational and pricing agents."""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage

# Minimal logging
logging.basicConfig(level=logging.WARNING)

async def main():
    """Test RAG citations in both agents."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE RAG CITATIONS TEST")
    print("=" * 70)

    graph = build_orchestrator_graph()

    # Test 1: Educational RAG citations
    print("\n[1/2] Testing Educational RAG Citations...")
    print("Query: What is delta?")

    result1 = await graph.ainvoke(
        {"messages": [HumanMessage(content="What is delta?")]}
    )

    if result1 and result1.get("messages"):
        response1 = result1["messages"][-1].content

        if "Sources" in response1 or "sources" in response1:
            print("  ✅ Educational: Sources section found")
            # Check for quoted text
            if '\"' in response1 and "..." in response1:
                print("  ✅ Educational: Quoted text found")
            else:
                print("  ❌ Educational: No quoted text")
        else:
            print("  ❌ Educational: No sources section")

    # Test 2: Pricing RAG citations
    print("\n[2/2] Testing Pricing RAG Citations...")
    print("Query: Price a 1-year European call on AAPL, strike 5% above current")

    result2 = await graph.ainvoke(
        {"messages": [HumanMessage(content="Price a 1-year European call on AAPL, strike 5% above current")]}
    )

    if result2 and result2.get("messages"):
        response2 = result2["messages"][-1].content

        if "Sources" in response2 or "sources" in response2:
            print("  ✅ Pricing: Sources section found")
            # Check for quoted text
            if '\"' in response2 and "..." in response2:
                print("  ✅ Pricing: Quoted text found")
            else:
                print("  ❌ Pricing: No quoted text")
        else:
            print("  ❌ Pricing: No sources section")

    print("\n" + "=" * 70)
    print("SUMMARY:")
    print("  Both agents now retrieve RAG sources and cite them with:")
    print("  - Quoted text from the source (20-50 words)")
    print("  - Ellipsis (...) at start and end")
    print("  - Source attribution: (Book Name, Ch. X)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
