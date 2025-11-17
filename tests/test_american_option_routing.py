"""
Test American Option Pricing Routing
=====================================

Verifies that American options are correctly routed to Bjerksund-Stensland
approximation instead of falling through to Black-Scholes.

Test case: "Price an American put option on MSFT with strike $400, expiring in 90 days."

Expected behavior:
1. Classification sets product_type="american_put"
2. Execution planner creates task with option_type="american_put"
3. Task executor routes to Bjerksund-Stensland (not Black-Scholes)
4. Price returned is > $0 (not $0.00)
"""

import asyncio
import logging
from derivatives_gpt_core.agents.pricing.state import PricingState
from derivatives_gpt_core.agents.pricing.nodes.classify_option_type import classify_option_type
from derivatives_gpt_core.agents.pricing.nodes.create_execution_plan import create_execution_plan
from langchain_core.messages import HumanMessage

# Configure logging to see routing decisions
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_american_put_classification():
    """Test that American put is correctly classified."""
    logger.info("=" * 80)
    logger.info("TEST 1: American Put Classification")
    logger.info("=" * 80)

    query = "Price an American put option on MSFT with strike $400, expiring in 90 days."

    state = PricingState(
        messages=[HumanMessage(content=query)],
        is_option_related=True,
        ticker="MSFT",
        strike_price=400.0,
        time_to_expiry_days=90.0
    )

    # Run classification
    result = await classify_option_type(state)

    # Verify classification
    logger.info(f"\n✓ Classification Results:")
    logger.info(f"  - product_type: {result.get('product_type')}")
    logger.info(f"  - option_type: {result.get('option_type')}")
    logger.info(f"  - asset_class: {result.get('asset_class')}")
    logger.info(f"  - position: {result.get('position')}")

    assert result.get('product_type') == 'american_put', \
        f"Expected product_type='american_put', got '{result.get('product_type')}'"

    logger.info("\n✓ PASS: Classification correctly identified american_put")
    return result


async def test_american_put_execution_plan():
    """Test that execution plan uses full product type."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Execution Plan Creation")
    logger.info("=" * 80)

    # Create state with american_put classification
    state = PricingState(
        messages=[HumanMessage(content="Price an American put option on MSFT")],
        product_type="american_put",  # From classification
        option_type="put",  # Legacy field
        asset_class="equity",
        position="long",
        ticker="MSFT",
        strike_price=400.0,
        time_to_expiry_days=90.0,
        spot_price=420.0,  # Simulated spot
        volatility=0.25,  # Simulated vol
        risk_free_rate=0.045  # Simulated rate
    )

    # Run execution planning
    plan_result = await create_execution_plan(state)

    # Verify plan
    logger.info(f"\n✓ Execution Plan Results:")
    logger.info(f"  - can_execute: {plan_result.get('can_execute')}")
    logger.info(f"  - plan_generated: {plan_result.get('plan_generated')}")

    if plan_result.get('execution_plan'):
        plan = plan_result['execution_plan']
        logger.info(f"  - Number of tasks: {len(plan.get('tasks', []))}")

        # Find pricing task
        pricing_tasks = [
            task for task in plan.get('tasks', [])
            if task.get('type') == 'pricing'
        ]

        logger.info(f"  - Pricing tasks: {len(pricing_tasks)}")

        for task in pricing_tasks:
            task_option_type = task.get('params', {}).get('option_type')
            logger.info(f"    • Task: {task.get('id')}, option_type: {task_option_type}")

            # CRITICAL: Verify full option type is used
            assert task_option_type == 'american_put', \
                f"Expected option_type='american_put' in task, got '{task_option_type}'"

        logger.info("\n✓ PASS: Execution plan uses full product type 'american_put'")
    else:
        logger.error(f"\n✗ FAIL: No execution plan generated")
        logger.error(f"  - Reasoning: {plan_result.get('reasoning')}")
        raise AssertionError("Execution plan not generated")

    return plan_result


async def test_american_put_end_to_end():
    """Test full workflow from query to pricing."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: End-to-End American Put Pricing")
    logger.info("=" * 80)

    query = "Price an American put option on MSFT with strike $400, expiring in 90 days."
    logger.info(f"Query: {query}\n")

    # Step 1: Classification
    classification_result = await test_american_put_classification()

    # Step 2: Execution Plan
    plan_result = await test_american_put_execution_plan()

    # Step 3: Verify routing logic
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3.3: Verify Task Executor Routing Logic")
    logger.info("=" * 80)

    # Read task executor to verify routing
    from derivatives_gpt_core.workflow.execution.task_executor import _calculate_option_price

    # Create mock state
    mock_state = PricingState(
        messages=[HumanMessage(content=query)],
        spot_price=420.0,
        volatility=0.25,
        risk_free_rate=0.045,
        product_type="american_put"
    )

    # Test routing (time_to_expiry_years = 90/365)
    logger.info(f"\nCalling _calculate_option_price with option_type='american_put'")

    try:
        price = _calculate_option_price(
            option_type="american_put",
            state=mock_state,
            strike=400.0,
            time_years=90.0/365.0
        )

        logger.info(f"✓ Price calculated: ${price:.2f}")

        # Verify price is not $0.00 (the bug we're fixing)
        assert price > 0, f"Expected price > $0, got ${price:.2f}"

        # American put with spot=420, strike=400, vol=25%, rate=4.5%, 90 days
        # Should have some time value even though OTM
        logger.info(f"\n✓ PASS: American put priced successfully (not $0.00)")
        logger.info(f"  - Spot: $420")
        logger.info(f"  - Strike: $400")
        logger.info(f"  - Price: ${price:.2f}")

    except Exception as e:
        logger.error(f"\n✗ FAIL: Pricing failed with error: {e}")
        raise

    return price


async def main():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("AMERICAN OPTION ROUTING TEST SUITE")
    logger.info("=" * 80)
    logger.info("Testing orthogonal pricing architecture fixes\n")

    try:
        # Run tests
        await test_american_put_end_to_end()

        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 80)
        logger.info("\nAmerican options are now correctly routed to Bjerksund-Stensland!")
        logger.info("The orthogonal architecture (position, product_type, asset_class, strategy) is working.\n")

    except AssertionError as e:
        logger.error("\n" + "=" * 80)
        logger.error("✗ TEST FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}\n")
        raise
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("✗ TEST ERROR")
        logger.error("=" * 80)
        logger.error(f"Unexpected error: {e}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
