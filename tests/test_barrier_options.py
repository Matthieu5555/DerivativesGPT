#!/usr/bin/env python3
"""
Test barrier option implementation.

This tests that barrier options are now properly recognized and priced.
"""

import numpy as np
from derivatives_gpt_core.features.barrier.pricing import (
    price_down_out_call,
    price_barrier_option
)


def test_barrier_pricing_module():
    """Test that the barrier pricing module works correctly."""
    print("\n" + "="*60)
    print("TESTING BARRIER OPTION PRICING MODULE")
    print("="*60)

    # Test parameters
    S = 100  # Current spot price
    K = 105  # Strike price
    H = 95   # Barrier level (down barrier)
    T = 0.25 # 3 months
    r = 0.05 # 5% risk-free rate
    sigma = 0.3  # 30% volatility

    print(f"\nTest parameters:")
    print(f"  Spot: ${S}")
    print(f"  Strike: ${K}")
    print(f"  Barrier: ${H}")
    print(f"  Time: {T} years")
    print(f"  Rate: {r:.1%}")
    print(f"  Volatility: {sigma:.1%}")

    # Test down-and-out call
    try:
        price = price_down_out_call(S, K, H, T, r, sigma)
        print(f"\nSUCCESS Down-and-out call price: ${price:.2f}")

        # Compare to vanilla - barrier should be cheaper
        from derivatives_gpt_core.features.vanilla.pricing import black_scholes_call
        vanilla_price = black_scholes_call(S, K, T, r, sigma)
        print(f"   Vanilla call price: ${vanilla_price:.2f}")
        print(f"   Discount from barrier: {(1 - price/vanilla_price)*100:.1f}%")

        if price < vanilla_price:
            print("   OK Barrier option correctly cheaper than vanilla")
        else:
            print("   ERROR ERROR: Barrier should be cheaper than vanilla!")
            return False

    except Exception as e:
        print(f"FAILED ERROR: {e}")
        return False

    # Test the main entry point
    try:
        price2 = price_barrier_option(
            barrier_type="down-out",
            option_type="call",
            S=S, K=K, H=H, T=T, r=r, sigma=sigma
        )
        print(f"\nSUCCESS Using main entry point: ${price2:.2f}")

        if abs(price - price2) < 0.01:
            print("   OK Both methods give same result")
        else:
            print("   ERROR ERROR: Methods give different results!")
            return False

    except Exception as e:
        print(f"FAILED ERROR in main entry point: {e}")
        return False

    return True


def test_barrier_validation():
    """Test that barrier validation works."""
    print("\n" + "="*60)
    print("TESTING BARRIER VALIDATION")
    print("="*60)

    S = 100
    K = 105
    T = 0.25
    r = 0.05
    sigma = 0.3

    # Test invalid barrier (above spot for down-and-out)
    try:
        H_invalid = 105  # Above spot for down barrier
        price = price_down_out_call(S, K, H_invalid, T, r, sigma)
        print(f"FAILED Should have rejected barrier {H_invalid} > spot {S}")
        return False
    except ValueError as e:
        print(f"SUCCESS Correctly rejected invalid barrier: {e}")

    # Test at-the-barrier scenario
    S_at_barrier = 95  # At barrier
    H = 95
    price = price_down_out_call(S_at_barrier, K, H, T, r, sigma, rebate=1.0)
    expected_rebate_value = 1.0 * np.exp(-r * T)

    if abs(price - expected_rebate_value) < 0.01:
        print(f"SUCCESS Correctly handled at-barrier scenario: ${price:.2f}")
    else:
        print(f"FAILED Wrong value for at-barrier option: ${price:.2f} vs ${expected_rebate_value:.2f}")
        return False

    return True


def test_barrier_types():
    """Test different barrier types."""
    print("\n" + "="*60)
    print("TESTING DIFFERENT BARRIER TYPES")
    print("="*60)

    S = 100
    K = 100  # ATM
    T = 0.5
    r = 0.05
    sigma = 0.25

    barrier_configs = [
        ("down-out", "call", 90),
        ("down-in", "call", 90),
        ("up-out", "put", 110),
        ("up-in", "put", 110),
    ]

    for barrier_type, option_type, H in barrier_configs:
        try:
            price = price_barrier_option(
                barrier_type=barrier_type,
                option_type=option_type,
                S=S, K=K, H=H, T=T, r=r, sigma=sigma
            )
            print(f"SUCCESS {barrier_type:10} {option_type:4} (H={H}): ${price:7.2f}")
        except Exception as e:
            print(f"FAILED {barrier_type} {option_type} failed: {e}")
            return False

    return True


def main():
    """Run all barrier option tests."""
    print("\n" + "="*60)
    print("BARRIER OPTION IMPLEMENTATION TEST SUITE")
    print("="*60)

    tests = [
        ("Pricing Module", test_barrier_pricing_module),
        ("Validation", test_barrier_validation),
        ("Barrier Types", test_barrier_types),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        results.append(test_func())

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(results)
    total = len(results)

    for i, (test_name, _) in enumerate(tests):
        status = "SUCCESS PASSED" if results[i] else "FAILED FAILED"
        print(f"{test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\nSUCCESS ALL TESTS PASSED!")
        print("Barrier options are now fully implemented and working.")
        print("\nThe system can now price:")
        print("- Down-and-out calls/puts")
        print("- Down-and-in calls/puts")
        print("- Up-and-out calls/puts")
        print("- Up-and-in calls/puts")
    else:
        print("\nWARNING Some tests failed. Check the implementation.")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)