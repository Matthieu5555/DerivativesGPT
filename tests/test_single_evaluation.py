#!/usr/bin/env python3
"""
Run a single test case through the FULL graph to debug extraction.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.graph_builder import create_option_pricing_graph
from langchain_core.messages import HumanMessage

# Enable ALL logging to see diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_single_test():
    """Run single test case through full graph."""

    # Create graph
    graph = create_option_pricing_graph()

    # Test query that's failing in evaluation
    test_query = "Price a call option on AAPL with strike 150, expiring in 30 days"

    print(f"\n{'='*80}")
    print(f"RUNNING FULL GRAPH TEST")
    print(f"Query: {test_query}")
    print('='*80)

    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=test_query)],
    }

    # Run graph
    config = {"configurable": {"thread_id": "test_single"}}

    print("\n🚀 Starting graph execution...\n")

    result = await graph.ainvoke(initial_state, config)

    print(f"\n{'='*80}")
    print("FINAL STATE:")
    print('='*80)
    print(f"ticker: {result.get('ticker')}")
    print(f"strike_price: {result.get('strike_price')}")
    print(f"time_to_expiry_days: {result.get('time_to_expiry_days')}")
    print(f"option_type: {result.get('option_type')}")
    print(f"extraction_successful: {result.get('extraction_successful')}")
    print(f"extraction_attempts: {result.get('extraction_attempts')}")
    print(f"\nFinal reasoning: {result.get('reasoning')}")


if __name__ == "__main__":
    asyncio.run(run_single_test())
