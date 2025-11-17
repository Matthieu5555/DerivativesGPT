#!/usr/bin/env python
"""Test that RAG citations appear in educational responses."""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage

# Minimal logging
logging.basicConfig(level=logging.WARNING)

async def main():
    """Test RAG citations in educational response."""
    print("\n" + "=" * 60)
    print("TESTING RAG CITATIONS")
    print("=" * 60)

    graph = build_orchestrator_graph()

    print("\nAsking: What is delta?")
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="What is delta?")]}
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

        if "(" in response and ")" in response and "Ch." in response:
            print("✅ Citation format found (Book, Ch. X)")
        elif "[No knowledge base" in response:
            print("❌ Still showing '[No knowledge base content provided]'")
        else:
            print("⚠️ Unknown format")

        # Check for inline quotes
        if '\"' in response:
            print("✅ Quotes found in response")
        else:
            print("⚠️ No quotes found")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
