#!/usr/bin/env python
"""
Test parameter inheritance fix for contextual references.

Tests the scenario:
1. "Price AAPL call, strike 5% above, 3 months"
2. "same option but now american"

Expected: Second request inherits ticker, strike, and expiry from first.
"""

import asyncio
import sys
from derivatives_gpt_core.graph_nodes.extract_parameters import extract_parameters
from derivatives_gpt_core.graph_state_schema import OptionPricingState
from langchain_core.messages import HumanMessage, AIMessage


async def test_parameter_inheritance():
    """Test that 'same option but american' inherits parameters."""

    print("=" * 70)
    print("TESTING PARAMETER INHERITANCE FIX")
    print("=" * 70)

    # Scenario 1: First request - establish baseline
    print("\n[TEST 1] First Request: Price AAPL call, strike 5% above, 3 months")
    print("-" * 70)

    state1 = OptionPricingState(
        messages=[
            HumanMessage(content="Price AAPL call, strike 5% above, 3 months")
        ],
        option_type_classified="call",
        asset_type_classified="equity"
    )

    result1 = await extract_parameters(state1)

    print(f"✓ Extracted ticker: {result1.get('ticker')}")
    print(f"✓ Extracted strike: {result1.get('strike_price')}")
    print(f"✓ Extracted expiry: {result1.get('time_to_expiry_days')} days")
    print(f"✓ Extraction successful: {result1.get('extraction_successful')}")

    # Simulate state after first extraction
    state2 = OptionPricingState(
        messages=[
            HumanMessage(content="Price AAPL call, strike 5% above, 3 months"),
            AIMessage(content="I can price that AAPL call option. Let me get the data..."),
            HumanMessage(content="same option but now american")
        ],
        # State carries forward from first request
        ticker=result1.get('ticker', 'AAPL'),
        strike_price=result1.get('strike_price', '5% above'),
        time_to_expiry_days=result1.get('time_to_expiry_days', 90.0),
        option_type="call",
        spot_price=268.0,  # Simulated fetched spot price
        option_type_classified="american_call",
        asset_type_classified="equity"
    )

    # Scenario 2: Second request - test inheritance
    print("\n[TEST 2] Second Request: same option but now american")
    print("-" * 70)

    result2 = await extract_parameters(state2)

    print(f"✓ Extracted ticker: {result2.get('ticker')}")
    print(f"✓ Extracted strike: {result2.get('strike_price')}")
    print(f"✓ Extracted expiry: {result2.get('time_to_expiry_days')} days")
    print(f"✓ Extraction successful: {result2.get('extraction_successful')}")

    # Verify inheritance worked
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    success = True

    if result2.get('ticker') == 'AAPL':
        print("[PASS] Ticker inherited correctly: AAPL")
    else:
        print(f"[FAIL] Ticker inheritance FAILED: got {result2.get('ticker')}, expected AAPL")
        success = False

    if result2.get('strike_price') == '5% above':
        print("[PASS] Strike inherited correctly: 5% above")
    else:
        print(f"[FAIL] Strike inheritance FAILED: got {result2.get('strike_price')}, expected '5% above'")
        success = False

    if result2.get('time_to_expiry_days') == 90.0:
        print("[PASS] Expiry inherited correctly: 90.0 days")
    else:
        print(f"[FAIL] Expiry inheritance FAILED: got {result2.get('time_to_expiry_days')}, expected 90.0")
        success = False

    if result2.get('extraction_successful'):
        print("[PASS] Extraction marked as successful")
    else:
        print("[FAIL] Extraction marked as FAILED (should be successful with inheritance)")
        success = False

    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] ALL TESTS PASSED - Parameter inheritance working!")
        print("=" * 70)
        return 0
    else:
        print("💥 TESTS FAILED - Parameter inheritance not working correctly")
        print("=" * 70)
        return 1


async def test_non_contextual_request():
    """Test that non-contextual requests still work normally."""

    print("\n\n" + "=" * 70)
    print("TESTING NON-CONTEXTUAL REQUEST (Baseline)")
    print("=" * 70)

    state = OptionPricingState(
        messages=[
            HumanMessage(content="Price TSLA put, strike 200, 6 months")
        ],
        option_type_classified="put",
        asset_type_classified="equity"
    )

    result = await extract_parameters(state)

    print(f"✓ Extracted ticker: {result.get('ticker')}")
    print(f"✓ Extracted strike: {result.get('strike_price')}")
    print(f"✓ Extracted expiry: {result.get('time_to_expiry_days')} days")
    print(f"✓ Extraction successful: {result.get('extraction_successful')}")

    if result.get('ticker') == 'TSLA' and result.get('strike_price') == 200.0:
        print("\n[PASS] Non-contextual extraction still works!")
        return 0
    else:
        print("\n[FAIL] Non-contextual extraction broken!")
        return 1


async def main():
    """Run all tests."""

    try:
        # Test inheritance
        result1 = await test_parameter_inheritance()

        # Test baseline (non-contextual)
        result2 = await test_non_contextual_request()

        if result1 == 0 and result2 == 0:
            print("\n" + "=" * 70)
            print("[PASS] ALL TESTS PASSED - FIX VERIFIED!")
            print("=" * 70)
            return 0
        else:
            print("\n" + "=" * 70)
            print("[FAIL] SOME TESTS FAILED - FIX NEEDS WORK")
            print("=" * 70)
            return 1

    except Exception as e:
        print(f"\n💥 TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
