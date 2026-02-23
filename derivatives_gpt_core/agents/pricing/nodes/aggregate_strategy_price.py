"""Aggregate leg prices for multi-leg strategies."""

from derivatives_gpt_core.agents.pricing.state import PricingState
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def aggregate_strategy_price(state: PricingState) -> Dict[str, Any]:
    """
    Aggregate individual leg prices into total strategy price.

    Aggregation rules by strategy:
    - Straddle: call_price + put_price (both long positions)
    - Strangle: call_price + put_price (both long positions)
    - Spread: long_price - short_price (net debit/credit)
    - Butterfly: wing_prices - 2 * body_price
    - Single: pass through price

    Args:
        state: State with execution_results containing leg prices

    Returns:
        dict: Total strategy price and updated legs with individual prices

    Examples:
        Straddle: call=$10.50, put=$8.20 -> total=$18.70
        Bull call spread: buy_150=$10, sell_160=$5 -> total=$5 (net debit)
        Single call: $10.50 -> total=$10.50
    """
    if not state.execution_results:
        logger.warning("No execution results to aggregate")
        return {
            "option_price": None,
            "legs": None,
            "price_breakdown": "No execution results available"
        }

    results = state.execution_results
    strategy = state.strategy_type or "single"

    # Extract leg prices from execution results
    leg_prices = []
    for task_id, result in results.items():
        if "price" in result:
            leg_prices.append({
                "type": result.get("option_type", "unknown"),
                "price": result["price"],
                "strike": result.get("strike")
            })

    if not leg_prices:
        logger.error("No leg prices found in results")
        return {"option_price": None}

    # Aggregate based on strategy type
    if strategy in ["straddle", "strangle"]:
        # Sum of all legs (both long positions)
        total = sum(leg["price"] for leg in leg_prices)
        logger.info(f"{strategy.capitalize()} total price: ${total:.2f}")

        # Build detailed breakdown
        breakdown_parts = []
        for leg in leg_prices:
            breakdown_parts.append(f"{leg['type']}=${leg['price']:.2f}")
        breakdown = " + ".join(breakdown_parts) + f" = ${total:.2f}"

    elif strategy == "spread":
        # Net debit/credit (typically buy - sell)
        if len(leg_prices) == 2:
            # Assume first leg is long, second is short (planner should ensure this)
            total = leg_prices[0]["price"] - leg_prices[1]["price"]
            logger.info(f"Spread net price: ${total:.2f}")

            breakdown = f"Buy {leg_prices[0]['type']}=${leg_prices[0]['price']:.2f} - Sell {leg_prices[1]['type']}=${leg_prices[1]['price']:.2f} = ${total:.2f}"
        else:
            logger.error(f"Spread requires 2 legs, got {len(leg_prices)}")
            total = None
            breakdown = "Error: Invalid spread structure"

    elif strategy == "butterfly":
        # Wings - 2*body
        if len(leg_prices) == 3:
            # Sort by strike to identify wings and body
            sorted_legs = sorted(leg_prices, key=lambda x: x.get("strike", 0))
            total = (sorted_legs[0]["price"] + sorted_legs[2]["price"]) - 2 * sorted_legs[1]["price"]
            logger.info(f"Butterfly net price: ${total:.2f}")

            breakdown = f"(Wing1=${sorted_legs[0]['price']:.2f} + Wing2=${sorted_legs[2]['price']:.2f}) - 2*Body=${sorted_legs[1]['price']:.2f} = ${total:.2f}"
        else:
            logger.error(f"Butterfly requires 3 legs, got {len(leg_prices)}")
            total = None
            breakdown = "Error: Invalid butterfly structure"

    else:
        # Single option or unknown strategy
        if len(leg_prices) == 1:
            total = leg_prices[0]["price"]
            breakdown = f"${total:.2f}"
            logger.info(f"Single option price: ${total:.2f}")
        else:
            # Fallback: sum all legs
            total = sum(leg["price"] for leg in leg_prices)
            breakdown = " + ".join([f"${leg['price']:.2f}" for leg in leg_prices]) + f" = ${total:.2f}"
            logger.warning(f"Unknown strategy '{strategy}', summing all legs: ${total:.2f}")

    # Update legs with individual prices
    updated_legs = state.legs or []
    for i, leg in enumerate(updated_legs):
        if i < len(leg_prices):
            leg["price"] = leg_prices[i]["price"]

    return {
        "option_price": total,
        "legs": updated_legs,
        "price_breakdown": breakdown
    }
