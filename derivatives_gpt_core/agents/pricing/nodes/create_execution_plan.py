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
    product_type = state.product_type or state.option_type or 'call'
    context_parts.append(f"Product type: {product_type}")
    context_parts.append(f"Asset class: {state.asset_class or 'equity'}")
    context_parts.append(f"Position: {state.position or 'long'}")

    # Add leg information
    if state.legs and len(state.legs) > 0:
        context_parts.append(f"Legs: {len(state.legs)} legs")
        for i, leg in enumerate(state.legs):
            context_parts.append(f"  Leg {i+1}: {leg.get('type')} strike={leg.get('strike', 'ATM')} position={leg.get('position', 'long')}")

    # Include what we already have
    if state.spot_price:
        context_parts.append(f"Has spot: ${state.spot_price:.2f}")
    if state.volatility:
        context_parts.append(f"Has vol: {state.volatility:.1%}")
    if state.strike_price:
        # Handle both numeric and string strikes
        if isinstance(state.strike_price, (int, float)):
            context_parts.append(f"Has strike: ${state.strike_price:.2f}")
        else:
            context_parts.append(f"Has strike: {state.strike_price}")
    if state.risk_free_rate:
        context_parts.append(f"Has rate: {state.risk_free_rate:.2%}")
    if state.time_to_expiry_days:
        context_parts.append(f"Expiry: {state.time_to_expiry_days} days")

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

        num_tasks = len(validated_plan.tasks)
        num_groups = len(validated_plan.parallel_groups)
        logger.info(f"Generated plan with {num_tasks} tasks, {num_groups} parallel groups")

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
