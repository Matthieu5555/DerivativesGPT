#!/usr/bin/env python3
"""
Test that the pricing capabilities module correctly identifies what we can price.
"""

from derivatives_gpt_core.pricing_capabilities import (
    can_price_option_type,
    get_pricing_method,
    get_capabilities_summary,
    get_tool_list_for_llm
)


def test_supported_options():
    """Test that supported options are correctly identified."""
    print("\n" + "="*60)
    print("TESTING SUPPORTED OPTIONS")
    print("="*60)

    supported = [
        # Vanilla
        ("vanilla_call", True, "Black-Scholes"),
        ("european_put", True, "Black-Scholes"),
        ("american_call", True, "Bjerksund-Stensland"),
        ("american_put", True, "Bjerksund-Stensland"),

        # Digital
        ("digital_call", True, "Analytical formula"),
        ("binary_put", True, "Analytical formula"),

        # Geometric Asian
        ("geometric_asian_call", True, "Analytical formula"),
        ("geometric_asian_put", True, "Analytical formula"),

        # Barrier options (NEW)
        ("down_out_call", True, "Merton-Reiner"),
        ("up_in_put", True, "Merton-Reiner"),
        ("barrier_call", True, "Merton-Reiner"),
        ("knock_out", True, "Merton-Reiner"),

        # Multi-leg
        ("straddle", True, "aggregation"),
        ("iron_condor", True, "aggregation"),
    ]

    passed = 0
    for option_type, expected_can_price, method_hint in supported:
        can_price = can_price_option_type(option_type)
        method = get_pricing_method(option_type)

        if can_price == expected_can_price:
            print(f"OK   {option_type:20} can_price={can_price} ({method})")
            passed += 1
        else:
            print(f"FAIL {option_type:20} expected={expected_can_price}, got={can_price}")

    print(f"\nSupported options: {passed}/{len(supported)} tests passed")
    return passed == len(supported)


def test_unsupported_options():
    """Test that unsupported options are correctly identified."""
    print("\n" + "="*60)
    print("TESTING UNSUPPORTED OPTIONS")
    print("="*60)

    unsupported = [
        # Arithmetic Asian
        ("arithmetic_asian_call", False, "Monte Carlo"),
        ("asian_put", False, "ambiguous"),  # Could be arithmetic or geometric

        # Lookback
        ("lookback_call", False, "path tracking"),
        ("floating_strike", False, "path tracking"),

        # Basket
        ("basket_call", False, "correlation"),
        ("rainbow_option", False, "correlation"),

        # Variance
        ("variance_swap", False, "replication"),
        ("volatility_swap", False, "volatility model"),

        # Complex
        ("compound_call", False, "nested"),
        ("chooser", False, "numerical"),
    ]

    passed = 0
    for option_type, expected_can_price, reason_hint in unsupported:
        can_price = can_price_option_type(option_type)
        method = get_pricing_method(option_type)

        if can_price == expected_can_price:
            print(f"OK   {option_type:20} can_price={can_price} (reason: {method})")
            passed += 1
        else:
            print(f"FAIL {option_type:20} expected={expected_can_price}, got={can_price}")

    print(f"\nUnsupported options: {passed}/{len(unsupported)} tests passed")
    return passed == len(unsupported)


def test_llm_prompt_generation():
    """Test that LLM prompt includes correct capabilities."""
    print("\n" + "="*60)
    print("TESTING LLM PROMPT GENERATION")
    print("="*60)

    prompt = get_tool_list_for_llm()
    print("\nGenerated prompt for LLM:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)

    # Check that key elements are present
    checks = [
        ("Barrier options mentioned", "barrier" in prompt.lower()),
        ("Merton-Reiner mentioned", "merton" in prompt.lower()),
        ("Monte Carlo mentioned as limitation", "monte carlo" in prompt.lower()),
        ("Multi-leg strategies mentioned", "straddle" in prompt.lower()),
    ]

    passed = 0
    for check_name, check_result in checks:
        if check_result:
            print(f"OK   {check_name}")
            passed += 1
        else:
            print(f"FAIL {check_name}")

    print(f"\nPrompt checks: {passed}/{len(checks)} passed")
    return passed == len(checks)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PRICING CAPABILITIES TEST SUITE")
    print("="*60)

    # Show summary first
    print("\nCAPABILITIES SUMMARY:")
    print(get_capabilities_summary())

    tests = [
        ("Supported Options", test_supported_options),
        ("Unsupported Options", test_unsupported_options),
        ("LLM Prompt Generation", test_llm_prompt_generation),
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
        status = "PASSED" if results[i] else "FAILED"
        print(f"{test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\nSUCCESS! The pricing capabilities module is working correctly.")
        print("The classifier will now:")
        print("1. Correctly identify barrier options as PRICEABLE")
        print("2. Correctly identify arithmetic Asian as NOT PRICEABLE")
        print("3. Provide accurate reasoning for why something can't be priced")
    else:
        print("\nSome tests failed. Check the implementation.")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)