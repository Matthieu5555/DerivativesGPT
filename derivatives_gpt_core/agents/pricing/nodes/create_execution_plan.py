"""Create execution plan with DAG structure."""

from derivatives_gpt_core.agents.pricing.state import PricingState
from derivatives_gpt_core.llm_provider import get_planner_llm
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import ExecutionPlan
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any
import json
import logging

# Import prompts from centralized location
from prompts.graph_nodes.execution_planning_prompts import PLANNER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def validate_and_fix_execution_plan(plan: ExecutionPlan) -> None:
    """
    Validate that execution plan respects dependencies and fix if needed.

    Critical: Ensures pricing tasks never run in same group as fetch tasks.
    """
    # Build task type map
    task_types = {task.id: task.type for task in plan.tasks}

    fetch_tasks = {tid for tid, ttype in task_types.items()
                   if ttype in ["market_data", "volatility", "risk_free_rate"]}
    price_tasks = {tid for tid, ttype in task_types.items()
                   if ttype == "pricing"}

    # Check each parallel group
    for group_idx, group in enumerate(plan.parallel_groups):
        group_set = set(group)
        has_fetch = bool(group_set & fetch_tasks)
        has_price = bool(group_set & price_tasks)

        if has_fetch and has_price:
            # CRITICAL: Pricing and fetching in same group - this causes the race condition!
            logger.error(f"INVALID PLAN DETECTED: Group {group_idx} mixes fetch and price tasks")
            logger.error(f"Fetch tasks in group: {group_set & fetch_tasks}")
            logger.error(f"Price tasks in group: {group_set & price_tasks}")

            # Auto-fix by splitting into separate groups
            new_groups = []
            fetch_group = [t for t in group if t in fetch_tasks]
            price_group = [t for t in group if t in price_tasks]
            other_group = [t for t in group if t not in fetch_tasks and t not in price_tasks]

            # Order matters: fetches first, then pricing, then others
            if fetch_group:
                new_groups.append(fetch_group)
            if price_group:
                new_groups.append(price_group)
            if other_group:
                new_groups.append(other_group)

            # Replace the bad group with properly ordered groups
            plan.parallel_groups[group_idx:group_idx+1] = new_groups
            logger.warning(f"AUTO-FIXED PLAN: Split group {group_idx} into {len(new_groups)} groups")
            logger.info(f"New groups: {new_groups}")


async def create_execution_plan(state: PricingState) -> Dict[str, Any]:
    """
    Create execution plan with dependency DAG.

    Purpose:
    - Identify required tasks (market data, pricing, aggregation)
    - Determine parallel execution opportunities
    - Self-assess if system can execute plan

    Optimization: Skip planner for simple single vanilla with all params

    Args:
        state: Current state after classification and decomposition

    Returns:
        dict: Execution plan or error

    Examples:
        Simple vanilla with params -> Skip planner, direct execution
        Straddle -> Plan with parallel legs: [fetch_data] -> [price_call, price_put] -> [aggregate]
        Missing params -> Plan to fetch spot, vol, rate first
    """
    # Note: We don't skip planner even if params exist, because the planner
    # determines which tasks to run (fetch spot, vol, rate) vs which to skip.
    # The executor will handle fetching missing parameters.

    planner_model = get_planner_llm()

    # Build planning context
    context_parts = [
        f"Strategy: {state.strategy_type or 'single'}",
        f"Ticker: {state.ticker or state.extracted_ticker or 'unknown'}",
    ]

    # Add product type information
    # Prefer product_type (e.g., "american_put") over option_type (e.g., "put")
    product_type = state.product_type or state.option_type or 'vanilla_european_call'
    context_parts.append(f"Product type: {product_type}")
    context_parts.append(f"Asset class: {state.asset_class or 'equity'}")
    context_parts.append(f"Position: {state.position or 'long'}")

    # Add leg information
    if state.legs and len(state.legs) > 0:
        context_parts.append(f"Legs: {len(state.legs)} legs")
        for i, leg in enumerate(state.legs):
            context_parts.append(f"  Leg {i+1}: {leg.get('type')} strike={leg.get('strike', 'ATM')} position={leg.get('position', 'long')}")

    # Include what we already have AND what's missing (critical for planner)
    if state.spot_price:
        context_parts.append(f"Has spot: ${state.spot_price:.2f}")
    else:
        context_parts.append("MISSING: spot price (needs fetch_spot task)")

    if state.volatility:
        context_parts.append(f"Has vol: {state.volatility:.1%}")
    else:
        context_parts.append("MISSING: volatility (needs fetch_vol task)")

    if state.strike_price:
        # Handle both numeric and string strikes
        if isinstance(state.strike_price, (int, float)):
            context_parts.append(f"Has strike: ${state.strike_price:.2f}")
        else:
            context_parts.append(f"Has strike: {state.strike_price}")
    else:
        context_parts.append("MISSING: strike price (will default to ATM)")

    if state.risk_free_rate:
        context_parts.append(f"Has rate: {state.risk_free_rate:.2%}")
    else:
        context_parts.append("MISSING: risk-free rate (needs fetch_rate task)")

    if state.time_to_expiry_days:
        context_parts.append(f"Expiry: {state.time_to_expiry_days} days")
    else:
        context_parts.append("MISSING: time to expiry")

    # Add exotic option parameters if present (functional approach)
    if hasattr(state, 'barrier_type') and state.barrier_type:
        context_parts.append(f"Barrier type: {state.barrier_type}")
    if hasattr(state, 'barrier_level') and state.barrier_level:
        context_parts.append(f"Barrier level: ${state.barrier_level:.2f}")
    if hasattr(state, 'rebate') and state.rebate:
        context_parts.append(f"Rebate: ${state.rebate:.2f}")

    context = "\n".join(context_parts)

    # Build legs description for prompt
    legs_description = ""
    if state.legs:
        legs_description = f"\nLegs to price: {json.dumps(state.legs, indent=2)}"
    else:
        legs_description = f"\nSingle option to price: {product_type}"

    prompt = f"""{context}
{legs_description}

Create execution plan with parallel opportunities."""

    try:
        response = await planner_model.ainvoke([
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])

        # Parse and validate JSON response using Pydantic schema
        response_text = response.content.strip()
        validated_plan = extract_and_validate_with_retry(response_text, ExecutionPlan, max_attempts=3, strict=False)

        if validated_plan is None:
            logger.error("Failed to extract or validate execution plan from planner response")
            return {
                "can_execute": False,
                "response_type": "recognize_but_refuse",
                "reasoning": "Planning failed - could not parse or validate execution plan",
                "execution_plan": None,
                "plan_generated": False
            }

        if not validated_plan.can_execute:
            logger.warning("Planner determined cannot execute")
            return {
                "can_execute": False,
                "response_type": "recognize_but_refuse",
                "reasoning": "Strategy requires capabilities not yet implemented",
                "execution_plan": None,
                "plan_generated": False
            }

        # Validate and fix execution plan before using it
        validate_and_fix_execution_plan(validated_plan)

        num_tasks = len(validated_plan.tasks)
        num_groups = len(validated_plan.parallel_groups)

        # Comprehensive diagnostic logging
        logger.info("=" * 50)
        logger.info("EXECUTION PLAN GENERATED")
        logger.info(f"Total tasks: {num_tasks}")
        logger.info(f"Parallel groups: {num_groups}")
        for i, group in enumerate(validated_plan.parallel_groups):
            logger.info(f"  Group {i+1}: {group}")
            for task_id in group:
                task = next((t for t in validated_plan.tasks if t.id == task_id), None)
                if task:
                    logger.info(f"    - {task_id}: type={task.type}, params={task.params}")
        logger.info("=" * 50)

        # Convert Pydantic model to dict for state storage
        plan_dict = validated_plan.model_dump()

        return {
            "execution_plan": plan_dict,
            "plan_generated": True,
            "can_execute": True
        }

    except json.JSONDecodeError as e:
        logger.error(f"Planning JSON parsing failed: {e}")
        return {
            "can_execute": False,
            "reasoning": f"Planning parsing error: {str(e)}",
            "execution_plan": None,
            "plan_generated": False
        }

    except Exception as e:
        logger.error(f"Planning failed: {e}")
        return {
            "can_execute": False,
            "reasoning": f"Planning error: {str(e)}",
            "execution_plan": None,
            "plan_generated": False
        }
