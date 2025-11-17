#!/usr/bin/env python
"""
Debug pricing flow to understand why it's failing.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from langchain_core.messages import HumanMessage
import json

# Setup verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def debug_pricing():
    """Debug vanilla option pricing."""
    print("\n=== Debugging Vanilla Option Pricing ===")
    graph = build_orchestrator_graph()

    # Test a vanilla call pricing request
    query = "Can you help me to price a 1-year european call on AAPL with a strike 5% above the current market price?"

    try:
        result = await graph.ainvoke({
            "messages": [HumanMessage(content=query)]
        })

        # Debug: Print the state
        print("\n=== RESULT KEYS ===")
        if result:
            print(f"Keys in result: {list(result.keys())}")

            # Check specific fields
            fields_to_check = [
                "extraction_successful",
                "extraction_attempts",
                "spot_price",
                "strike_price",
                "option_price",
                "validation_errors",
                "messages"
            ]

            print("\n=== STATE FIELDS ===")
            for field in fields_to_check:
                if field in result:
                    value = result[field]
                    if field == "messages" and value:
                        print(f"{field}: {len(value)} messages")
                        if len(value) > 0:
                            last_msg = value[-1]
                            print(f"  Last message type: {type(last_msg).__name__}")
                            print(f"  Last message preview: {str(last_msg.content)[:200]}...")
                    else:
                        print(f"{field}: {value}")
                else:
                    print(f"{field}: NOT IN RESULT")

        # Check if we got a response
        if result and result.get("messages"):
            last_message = result["messages"][-1]
            print(f"\n=== SUCCESS ===")
            print(f"Got response without crash")
            print(f"Full last message:\n{last_message.content}")
            return True
        else:
            print("\n=== FAILED ===")
            print("No response generated")
            return False

    except Exception as e:
        print(f"\n=== EXCEPTION ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(debug_pricing())
    print(f"\n=== FINAL RESULT: {'SUCCESS' if success else 'FAILED'} ===")
    exit(0 if success else 1)