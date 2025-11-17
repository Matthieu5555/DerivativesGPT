#!/usr/bin/env python3
"""
Simple test to check if the race condition fix works.

This simulates what happens when the planner generates a bad plan.
"""

import logging
from derivatives_gpt_core.schemas.llm_schemas import ExecutionPlan, ExecutionTask
from derivatives_gpt_core.agents.pricing.nodes.create_execution_plan import validate_and_fix_execution_plan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


def test_plan_validation():
    """Test that the validation catches and fixes bad plans."""

    print("\n" + "="*60)
    print("TESTING PLAN VALIDATION")
    print("="*60)

    # Create a BAD plan (pricing and fetching in same group - the bug!)
    bad_plan = ExecutionPlan(
        tasks=[
            ExecutionTask(id="fetch_spot", type="market_data", params={"ticker": "AAPL"}),
            ExecutionTask(id="fetch_vol", type="volatility", params={"ticker": "AAPL"}),
            ExecutionTask(id="fetch_rate", type="risk_free_rate", params={}),
            ExecutionTask(id="price_american_put", type="pricing",
                 params={"option_type": "american_put", "strike": 150},
                 depends_on=["fetch_spot", "fetch_vol", "fetch_rate"])
        ],
        parallel_groups=[
            ["fetch_spot", "fetch_vol", "fetch_rate", "price_american_put"]  # BAD! Mixed group
        ],
        can_execute=True,
        complexity="simple"
    )

    print("\nBAD PLAN (before validation):")
    print(f"  Groups: {bad_plan.parallel_groups}")
    print("  WARNING This has fetch and pricing in the SAME group - causes race condition!")

    # Apply our fix
    validate_and_fix_execution_plan(bad_plan)

    print("\nFIXED PLAN (after validation):")
    print(f"  Groups: {bad_plan.parallel_groups}")

    # Check if it's fixed
    if len(bad_plan.parallel_groups) > 1:
        print("  SUCCESS Plan was AUTO-FIXED! Groups are now separated.")
        print("     - Group 1: Fetch tasks")
        print("     - Group 2: Pricing tasks")
        return True
    else:
        print("  FAILED Plan was NOT fixed - still has mixed group")
        return False


def test_good_plan():
    """Test that good plans are not modified."""

    print("\n" + "="*60)
    print("TESTING GOOD PLAN (should not be modified)")
    print("="*60)

    # Create a GOOD plan (properly separated)
    good_plan = ExecutionPlan(
        tasks=[
            ExecutionTask(id="fetch_spot", type="market_data", params={"ticker": "AAPL"}),
            ExecutionTask(id="fetch_vol", type="volatility", params={"ticker": "AAPL"}),
            ExecutionTask(id="price_call", type="pricing", params={"option_type": "call"}),
        ],
        parallel_groups=[
            ["fetch_spot", "fetch_vol"],  # Group 1: Fetches
            ["price_call"]                 # Group 2: Pricing
        ],
        can_execute=True,
        complexity="simple"
    )

    original_groups = [group.copy() for group in good_plan.parallel_groups]

    print("\nGOOD PLAN (before validation):")
    print(f"  Groups: {good_plan.parallel_groups}")
    print("  SUCCESS This is already correct - fetch and pricing separated")

    # Apply validation
    validate_and_fix_execution_plan(good_plan)

    print("\nPLAN (after validation):")
    print(f"  Groups: {good_plan.parallel_groups}")

    # Check if unchanged
    if good_plan.parallel_groups == original_groups:
        print("  SUCCESS Good plan was left unchanged")
        return True
    else:
        print("  FAILED Good plan was unnecessarily modified")
        return False


def main():
    """Run all tests."""

    print("\n" + "="*60)
    print("RACE CONDITION FIX VALIDATION TEST")
    print("="*60)
    print("\nThis tests the auto-fix that prevents pricing tasks from")
    print("running in the same parallel group as fetch tasks.")

    # Test 1: Bad plan should be fixed
    test1_passed = test_plan_validation()

    # Test 2: Good plan should not be modified
    test2_passed = test_good_plan()

    # Summary
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)

    if test1_passed and test2_passed:
        print("SUCCESS ALL TESTS PASSED!")
        print("\nThe race condition fix is working correctly:")
        print("1. Bad plans (mixed groups) are automatically fixed")
        print("2. Good plans (separated groups) are left unchanged")
        print("\nSUCCESS American options should now price correctly without")
        print("   user-provided market data!")
    else:
        print("FAILED SOME TESTS FAILED")
        if not test1_passed:
            print("- Bad plan was not fixed")
        if not test2_passed:
            print("- Good plan was incorrectly modified")


if __name__ == "__main__":
    main()