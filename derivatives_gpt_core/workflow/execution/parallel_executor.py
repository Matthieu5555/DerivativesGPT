"""
Parallel task execution orchestrator.

Executes DAG execution plans with parallel task groups using asyncio.
Provides 2-3x speedup for multi-leg strategies through concurrent I/O.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.workflow.execution.market_data_providers import MarketDataProvider
from derivatives_gpt_core.workflow.execution.task_executor import execute_task
from typing import Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


async def execute_parallel_group(
    tasks: list[Dict],
    state: BaseAgentState,
    market_data_provider: MarketDataProvider | None = None
) -> list[Dict]:
    """
    Execute group of tasks in parallel using asyncio.gather.

    Args:
        tasks: List of task dicts
        state: Current pricing state (with updated values from previous groups)
        market_data_provider: Optional injected provider

    Returns:
        List of task results
    """
    # Log current state for debugging
    logger.debug(f"Executing group with state snapshot: "
                f"spot={state.spot_price}, vol={state.volatility}, "
                f"rate={state.risk_free_rate}")

    return await asyncio.gather(*[
        execute_task(task, state, market_data_provider) for task in tasks
    ])


def extract_updated_values(results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract state updates from execution results.

    Collects spot price, volatility, interest rate, and strike from task outputs
    to merge back into state.

    Args:
        results: Task results dict {task_id: output}

    Returns:
        dict: Updated values to merge into state
    """
    updated_values = {}

    for task_id, output in results.items():
        if "spot_price" in output:
            updated_values["spot_price"] = output["spot_price"]
        if "volatility" in output:
            updated_values["volatility"] = output["volatility"]
        if "risk_free_rate" in output:
            updated_values["risk_free_rate"] = output["risk_free_rate"]
        if "strike" in output:
            updated_values["strike_price"] = output["strike"]

    return updated_values


def extract_single_option_price(
    state: BaseAgentState,
    results: Dict[str, Dict[str, Any]]
) -> float | None:
    """
    Extract option price from results for single options.

    For single options (not multi-leg strategies), finds and returns the pricing
    task result. Multi-leg strategies are aggregated separately.

    Args:
        state: Current state
        results: Task results dict {task_id: output}

    Returns:
        float | None: Option price if found, None for multi-leg strategies
    """
    if state.strategy_type == "single" or not state.multi_leg:
        # Find the pricing task result
        for task_id, output in results.items():
            if "price" in output:
                logger.info(f"Extracted single option price: ${output['price']:.2f}")
                return output["price"]
    return None


def build_execution_response(
    updated_values: Dict[str, Any],
    results: Dict[str, Dict[str, Any]],
    option_price: float | None
) -> Dict[str, Any]:
    """
    Build response dict for execute_plan node.

    Args:
        updated_values: Updated state parameters (spot, vol, rate)
        results: Task execution results
        option_price: Single option price (if applicable)

    Returns:
        dict: Response to merge into state
    """
    return_dict = {
        "execution_results": results,
        **updated_values  # Merge updated params into state
    }

    # Add option_price for single options
    if option_price is not None:
        return_dict["option_price"] = option_price

    return return_dict


async def execute_plan(
    state: BaseAgentState,
    market_data_provider: MarketDataProvider | None = None
) -> Dict[str, Any]:
    """
    Execute DAG execution plan with parallel task groups.

    Performance Tradeoffs:
    - Sacrifice: Deterministic execution order, slightly harder debugging
    - Benefit: 2-3x speedup for multi-leg strategies (concurrent I/O)
    - Result: Faster pricing without blocking on network requests

    Execution Flow:
    1. Extract tasks from execution plan
    2. For each parallel group (sequential):
        a. Execute tasks within group in parallel (asyncio.gather)
        b. Update state with fetched values (spot, vol, rate)
        c. Check for critical task failures (fast-fail)
    3. Return all results for aggregator node

    Args:
        state: State with execution_plan field
        market_data_provider: Optional injected provider (defaults to YFinance)

    Returns:
        dict: Results from all tasks, updated parameters, or execution_error

    Example plan:
    ```python
    {
        "tasks": [
            {"id": "fetch_spot", "type": "market_data", "params": {"ticker": "AAPL"}},
            {"id": "price_call", "type": "pricing", "params": {"option_type": "call"}}
        ],
        "parallel_groups": [
            ["fetch_spot"],  # Group 1: Fetch data
            ["price_call"]   # Group 2: Price option (depends on Group 1)
        ]
    }
    ```
    """
    # LangSmith Tracing: START
    logger.info("=" * 50)
    logger.info("STARTING EXECUTION PLAN")
    logger.info(f"Initial state: spot={state.spot_price}, "
               f"vol={state.volatility}, rate={state.risk_free_rate}")
    logger.info("=" * 50)

    try:
        if not state.execution_plan:
            logger.warning("[execute_parallel_tasks] No execution plan | scenario=EMPTY_PLAN")
            return {"execution_results": {}}

        plan = state.execution_plan
        tasks_by_id = {task["id"]: task for task in plan["tasks"]}
        results = {}

        # Execute each parallel group sequentially, tasks within group in parallel
        for group in plan["parallel_groups"]:
            group_tasks = [
                tasks_by_id[task_id]
                for task_id in group
                if task_id in tasks_by_id
            ]

            if not group_tasks:
                continue

            logger.info(
                f"Executing parallel group: {group} ({len(group_tasks)} tasks)"
            )

            # Run group in parallel using asyncio
            group_results = await execute_parallel_group(
                group_tasks,
                state,
                market_data_provider
            )

            # Store results and check for critical task failures
            critical_tasks = ["fetch_spot", "market_data"]
            for result in group_results:
                if "error" in result:
                    logger.error(f"Task {result['id']} failed: {result['error']}")

                    # Fast-fail for critical tasks
                    if result["id"] in critical_tasks:
                        logger.error(
                            f"Critical task {result['id']} failed, aborting execution"
                        )
                        return {
                            "execution_results": {},
                            "execution_error": (
                                f"Critical task '{result['id']}' failed: {result['error']}"
                            )
                        }

                    continue
                results[result["id"]] = result["output"]

            # Update state for the NEXT group without mutating the original
            # This is the key fix: we create a new state copy for the next group
            group_updates = extract_updated_values(results)

            if group_updates:
                # Create an updated state for the next group
                # This ensures next group has the fetched values
                state = state.model_copy(update=group_updates)

                for key, value in group_updates.items():
                    logger.info(f"State updated for next group: {key} = {value}")

                logger.info(
                    f"State snapshot for next group: "
                    f"spot={state.spot_price}, vol={state.volatility}, rate={state.risk_free_rate}"
                )

        # Collect all updated values for return
        updated_values = extract_updated_values(results)
        logger.info(f"Parallel execution complete. Fetched: {list(updated_values.keys())}")

        # Extract option price for single options
        option_price = extract_single_option_price(state, results)

        # Build and return response
        response = build_execution_response(updated_values, results, option_price)

        # LangSmith Tracing: Structured logging for observability
        logger.info(
            f"[execute_parallel_tasks] SUCCESS | "
            f"total_tasks={len(plan['tasks'])} | groups={len(plan['parallel_groups'])} | "
            f"succeeded={len(results)} | has_price={option_price is not None} | "
            f"params={list(updated_values.keys())}"
        )

        return response

    except Exception as e:
        # LangSmith Tracing: Log errors for observability
        logger.error(
            f"[execute_parallel_tasks] EXCEPTION | ticker={state.ticker} | error={str(e)}",
            exc_info=True
        )
        # Re-raise to allow error handling upstream
        raise
