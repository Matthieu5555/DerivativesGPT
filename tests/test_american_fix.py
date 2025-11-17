#!/usr/bin/env python3
"""
Test script to validate American option pricing fix.

This tests the race condition fix where pricing tasks were running
before market data fetches completed.
"""

import asyncio
import logging
from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph

# Configure logging to see diagnostic output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_american_option():
    """Test American option pricing without user-provided market data."""
    print("\n" + "="*60)
    print("AMERICAN OPTION RACE CONDITION TEST")
    print("="*60)

    graph = await build_orchestrator_graph()

    test_cases = [
        {
            "name": "American put on MSFT",
            "query": "Price an American put on MSFT with strike $510, expiring in 30 days"
        },
        {
            "name": "American call on AAPL",
            "query": "What's the value of an American call on AAPL, strike 150, 30 days to expiry?"
        },
        {
            "name": "American put on TSLA",
            "query": "Calculate American put price: ticker TSLA, strike 200, expires in 45 days"
        }
    ]

    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_cases)}: {test_case['name']}")
        print(f"Query: {test_case['query']}")
        print('='*60)

        try:
            # Invoke the graph with the test query
            result = await graph.ainvoke({
                "messages": [{"role": "user", "content": test_case['query']}]
            })

            # Check if pricing succeeded
            if result.get("option_price"):
                print(f"SUCCESS: Price = ${result['option_price']:.2f}")
                success_count += 1

                # Show what market data was fetched
                if result.get("execution_results"):
                    print("\nMarket data fetched:")
                    for task_id, output in result["execution_results"].items():
                        if "spot_price" in output:
                            print(f"  - Spot price: ${output['spot_price']:.2f}")
                        if "volatility" in output:
                            print(f"  - Volatility: {output['volatility']:.2%}")
                        if "risk_free_rate" in output:
                            print(f"  - Risk-free rate: {output['risk_free_rate']:.2%}")
            else:
                print(f"FAILED: No price returned")
                print(f"Execution results: {result.get('execution_results', {})}")

                # Check for errors
                if result.get("execution_error"):
                    print(f"Error: {result['execution_error']}")

        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

        # Small delay between tests
        await asyncio.sleep(1)

    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {success_count}/{len(test_cases)}")

    if success_count == len(test_cases):
        print("SUCCESS ALL TESTS PASSED - Race condition appears to be fixed!")
    else:
        print("WARNING Some tests failed - check logs for race condition indicators")
        print("Look for 'LIKELY RACE CONDITION' in error messages")

    return success_count == len(test_cases)


async def test_multi_leg_strategy():
    """Test that multi-leg strategies still work after the fix."""
    print("\n" + "="*60)
    print("MULTI-LEG STRATEGY TEST (Iron Condor)")
    print("="*60)

    graph = await build_orchestrator_graph()

    query = "Price an iron condor on SPY with strikes 420/425/430/435, expiring in 30 days"

    try:
        result = await graph.ainvoke({
            "messages": [{"role": "user", "content": query}]
        })

        if result.get("option_price"):
            print(f"SUCCESS Iron condor priced successfully: ${result['option_price']:.2f}")
            return True
        else:
            print(f"FAILED Iron condor pricing failed")
            return False

    except Exception as e:
        print(f"FAILED ERROR: {str(e)}")
        return False


async def main():
    """Run all tests."""
    # Test American options (the main fix)
    american_passed = await test_american_option()

    # Test multi-leg strategies still work
    multi_leg_passed = await test_multi_leg_strategy()

    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)

    if american_passed and multi_leg_passed:
        print("SUCCESS ALL TESTS PASSED")
        print("The race condition fix is working correctly!")
        print("American options price successfully without user-provided data.")
        print("Multi-leg strategies continue to work as expected.")
    else:
        print("WARNING SOME TESTS FAILED")
        if not american_passed:
            print("- American option pricing still has issues")
        if not multi_leg_passed:
            print("- Multi-leg strategy pricing was broken by the fix")


if __name__ == "__main__":
    asyncio.run(main())