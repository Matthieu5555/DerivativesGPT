"""
Individual task executor.

Executes individual pricing tasks including market data fetching,
parameter estimation, and option pricing calculations.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.langchain_tools.volatility_tool import estimate_annualized_volatility
from derivatives_gpt_core.langchain_tools.risk_free_rate_tool import estimate_risk_free_rate
from derivatives_gpt_core.features.vanilla.pricing import calculate_black_scholes_price
from derivatives_gpt_core.features.digital.pricing import calculate_digital_option_price
from derivatives_gpt_core.features.american.pricing import calculate_american_option_price
from derivatives_gpt_core.features.asian.pricing import calculate_geometric_asian_option_price
from derivatives_gpt_core.utils.llm_parsing import parse_percentage_from_text
from derivatives_gpt_core.utils.strike_resolution import resolve_strike
from derivatives_gpt_core.workflow.execution.market_data_providers import (
    MarketDataProvider,
    YFinanceProvider
)
from derivatives_gpt_core.constants import (
    DEFAULT_VOLATILITY_FALLBACK,
    DEFAULT_RISK_FREE_RATE_FALLBACK
)
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


# Task handler registry - self-registering task types
# Each handler receives (task, task_id, state, provider)
_TASK_HANDLERS = {}


def register_task_handler(task_type: str):
    """Decorator to register task handlers."""
    def decorator(func):
        _TASK_HANDLERS[task_type] = func
        return func
    return decorator


async def execute_task(
    task: Dict[str, Any],
    state: BaseAgentState,
    market_data_provider: MarketDataProvider | None = None
) -> Dict[str, Any]:
    """
    Execute single task from execution plan using registry pattern.

    Supported task types (via handler registry):
    - market_data: Fetch spot price from market data provider
    - volatility: Estimate historical volatility
    - risk_free_rate: Fetch treasury rate
    - pricing: Price single option leg using appropriate formula
    - sum: Aggregation task (skipped, handled in aggregator node)

    Args:
        task: Task dict with id, type, params
        state: Current state with pricing parameters
        market_data_provider: Optional injected provider (defaults to YFinance)

    Returns:
        dict: Task result with id and output or error

    Example task:
    ```python
    {
        "id": "fetch_spot_AAPL",
        "type": "market_data",
        "params": {"ticker": "AAPL"}
    }
    ```
    """
    task_id = task["id"]
    task_type = task["type"]

    logger.info(f"Executing task: {task_id} ({task_type})")

    # Use injected provider or default to YFinance
    if market_data_provider is None:
        market_data_provider = YFinanceProvider()

    try:
        # Look up handler in registry
        handler = _TASK_HANDLERS.get(task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {task_type}")

        # Execute handler
        return await handler(task, task_id, state, market_data_provider)

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        return {"id": task_id, "error": str(e)}


@register_task_handler("market_data")
async def _execute_market_data_task(
    task: Dict[str, Any],
    task_id: str,
    state: BaseAgentState,
    market_data_provider: MarketDataProvider
) -> Dict[str, Any]:
    """Execute market data fetching task."""
    ticker = task["params"]["ticker"]
    spot = market_data_provider.get_spot_price(ticker)
    logger.info(f"Fetched spot price for {ticker}: ${spot:.2f}")
    return {"id": task_id, "output": {"spot_price": spot}}


@register_task_handler("volatility")
async def _execute_volatility_task(
    task: Dict[str, Any],
    task_id: str,
    state: BaseAgentState,
    market_data_provider: MarketDataProvider
) -> Dict[str, Any]:
    """Execute volatility estimation task."""
    ticker = task["params"]["ticker"]
    volatility_result_text = estimate_annualized_volatility.invoke({
        "ticker": ticker,
        "lookback_days": 30
    })

    # Parse volatility from string result
    calculated_volatility = parse_percentage_from_text(volatility_result_text)
    if calculated_volatility is None:
        logger.warning(
            f"Failed to parse volatility for {ticker}, "
            f"using fallback: {DEFAULT_VOLATILITY_FALLBACK:.1%}"
        )
        calculated_volatility = DEFAULT_VOLATILITY_FALLBACK

    logger.info(f"Fetched volatility for {ticker}: {calculated_volatility:.1%}")
    return {
        "id": task_id,
        "output": {
            "volatility": calculated_volatility,
            "method": volatility_result_text
        }
    }


@register_task_handler("risk_free_rate")
async def _execute_rate_task(
    task: Dict[str, Any],
    task_id: str,
    state: BaseAgentState,
    market_data_provider: MarketDataProvider
) -> Dict[str, Any]:
    """Execute treasury rate fetching task."""
    time_horizon_days = state.time_to_expiry_days or 365
    rate_result_text = estimate_risk_free_rate.invoke({
        "time_horizon_days": time_horizon_days
    })

    # Parse rate from string result
    calculated_risk_free_rate = parse_percentage_from_text(rate_result_text)
    if calculated_risk_free_rate is None:
        logger.warning(
            f"Failed to parse risk-free rate, "
            f"using fallback: {DEFAULT_RISK_FREE_RATE_FALLBACK:.2%}"
        )
        calculated_risk_free_rate = DEFAULT_RISK_FREE_RATE_FALLBACK

    logger.info(f"Fetched risk-free rate: {calculated_risk_free_rate:.2%}")
    return {
        "id": task_id,
        "output": {
            "risk_free_rate": calculated_risk_free_rate,
            "method": rate_result_text
        }
    }


@register_task_handler("pricing")
async def _execute_pricing_task(
    task: Dict[str, Any],
    task_id: str,
    state: BaseAgentState,
    market_data_provider: MarketDataProvider
) -> Dict[str, Any]:
    """Execute option pricing task."""
    option_type = task["params"]["option_type"]

    # Comprehensive diagnostic logging for pricing tasks
    logger.info(f"PRICING TASK {task_id} STARTING")
    logger.info(f"  Option type: {option_type}")
    logger.info(f"  State values:")
    logger.info(f"    spot_price: {state.spot_price}")
    logger.info(f"    volatility: {state.volatility}")
    logger.info(f"    risk_free_rate: {state.risk_free_rate}")
    logger.info(f"    strike_price (from state): {state.strike_price}")
    logger.info(f"    time_to_expiry_days: {state.time_to_expiry_days}")

    # Extract and normalize strike parameter
    strike_param = task["params"].get("strike")
    if strike_param in ("null", "None"):
        strike_param = None  # Normalize string literals to Python None

    strike = strike_param or state.strike_price

    # Resolve relative strikes to absolute values
    if strike is None and state.spot_price is not None:
        strike = state.spot_price
        logger.info(f"No strike specified, defaulting to ATM: ${strike:.2f}")
    elif isinstance(strike, str) and state.spot_price is not None:
        strike = resolve_strike(strike, state.spot_price, option_type)
        logger.info(
            f"Resolved relative strike '{strike_param or state.strike_price}' "
            f"to ${strike:.2f} for {option_type}"
        )

    # Validate required parameters
    _validate_pricing_parameters(state, strike)

    # Calculate option price using appropriate formula
    time_years = state.time_to_expiry_days / 365
    price = _calculate_option_price(option_type, state, strike, time_years)

    return {
        "id": task_id,
        "output": {
            "price": price,
            "option_type": option_type,
            "strike": strike
        }
    }


@register_task_handler("sum")
async def _execute_sum_task(
    task: Dict[str, Any],
    task_id: str,
    state: BaseAgentState,
    market_data_provider: MarketDataProvider
) -> Dict[str, Any]:
    """Aggregation task - skipped here, handled in aggregator node."""
    logger.info("Aggregation task skipped in executor (handled in aggregator)")
    return {"id": task_id, "output": {}}


def _validate_pricing_parameters(state: BaseAgentState, strike: float) -> None:
    """Validate with detailed error reporting for debugging."""
    validations = {
        "spot_price": (state.spot_price, state.spot_price is not None and state.spot_price > 0),
        "strike": (strike, strike is not None and strike > 0),
        "time_to_expiry_days": (state.time_to_expiry_days,
                                state.time_to_expiry_days is not None and state.time_to_expiry_days > 0),
        "volatility": (state.volatility, state.volatility is not None and 0 < state.volatility < 10),
        "risk_free_rate": (state.risk_free_rate,
                          state.risk_free_rate is not None and -0.1 < state.risk_free_rate < 1)
    }

    failures = []
    for param, (value, is_valid) in validations.items():
        if not is_valid:
            failures.append(f"{param}={value}")

    if failures:
        error_msg = f"Pricing validation failed: {', '.join(failures)}"
        logger.error(error_msg)
        logger.error(f"Full state dump: {state.model_dump()}")

        # Check if this is likely a race condition
        if state.spot_price and not state.volatility:
            logger.error("LIKELY RACE CONDITION: Spot fetched but volatility missing")
            logger.error("This suggests pricing ran before all fetches completed")
        elif state.volatility and not state.spot_price:
            logger.error("LIKELY RACE CONDITION: Volatility fetched but spot missing")
            logger.error("This suggests pricing ran before all fetches completed")

        raise ValueError(error_msg)


def _calculate_barrier_option_price(
    option_type: str,
    state: BaseAgentState,
    strike: float,
    time_years: float
) -> float:
    """
    Calculate barrier option price using Merton-Reiner formulas.

    Extracts barrier parameters from state and dispatches to appropriate formula.
    """
    from derivatives_gpt_core.features.barrier.pricing import price_barrier_option

    # Extract barrier level from state (should be set during parameter extraction)
    barrier_level = getattr(state, 'barrier_level', None)
    if not barrier_level:
        # Try to infer from state or use a default
        logger.warning("No barrier level found in state, using 80% of spot for down barrier")
        barrier_level = state.spot_price * 0.8 if "down" in option_type else state.spot_price * 1.2

    # Map option_type to barrier_type and option direction
    barrier_type_map = {
        "down_out_call": ("down-out", "call"),
        "down_out_put": ("down-out", "put"),
        "down_in_call": ("down-in", "call"),
        "down_in_put": ("down-in", "put"),
        "up_out_call": ("up-out", "call"),
        "up_out_put": ("up-out", "put"),
        "up_in_call": ("up-in", "call"),
        "up_in_put": ("up-in", "put"),
    }

    barrier_type, option_dir = barrier_type_map.get(option_type, ("down-out", "call"))

    return price_barrier_option(
        barrier_type=barrier_type,
        option_type=option_dir,
        S=state.spot_price,
        K=strike,
        H=barrier_level,
        T=time_years,
        r=state.risk_free_rate,
        sigma=state.volatility,
        rebate=getattr(state, 'rebate', 0.0)
    )


def _calculate_option_price(
    option_type: str,
    state: BaseAgentState,
    strike: float,
    time_years: float
) -> float:
    """
    Calculate option price using appropriate formula.

    Dispatches to:
    - Bjerksund-Stensland for American options
    - Analytical formula for digital options
    - Analytical formula for geometric Asian options
    - Black-Scholes for vanilla European options
    """
    if option_type in ("american_call", "american_put"):
        price = calculate_american_option_price(
            spot_price=state.spot_price,
            strike_price=strike,
            time_to_expiry_years=time_years,
            volatility=state.volatility,
            risk_free_rate=state.risk_free_rate,
            option_type="call" if "call" in option_type else "put"
        )
        logger.info(f"Priced {option_type} option (Bjerksund-Stensland): ${price:.2f}")

    elif option_type in ("digital_call", "digital_put"):
        price = calculate_digital_option_price(
            spot_price=state.spot_price,
            strike_price=strike,
            time_to_expiry_years=time_years,
            volatility=state.volatility,
            risk_free_rate=state.risk_free_rate,
            option_type="call" if "call" in option_type else "put"
        )
        logger.info(f"Priced {option_type} option (analytical): ${price:.2f}")

    elif option_type in ("geometric_asian_call", "geometric_asian_put"):
        price = calculate_geometric_asian_option_price(
            spot_price=state.spot_price,
            strike_price=strike,
            time_to_expiry_years=time_years,
            volatility=state.volatility,
            risk_free_rate=state.risk_free_rate,
            option_type="call" if "call" in option_type else "put"
        )
        logger.info(f"Priced {option_type} option (geometric Asian): ${price:.2f}")

    elif any(barrier_type in option_type for barrier_type in
             ["down_out", "down_in", "up_out", "up_in"]):
        # Handle barrier options
        price = _calculate_barrier_option_price(
            option_type=option_type,
            state=state,
            strike=strike,
            time_years=time_years
        )
        logger.info(f"Priced {option_type} option (Merton-Reiner): ${price:.2f}")

    else:
        # Default to Black-Scholes for vanilla options
        price = calculate_black_scholes_price(
            spot_price=state.spot_price,
            strike_price=strike,
            time_to_expiry_years=time_years,
            volatility=state.volatility,
            risk_free_rate=state.risk_free_rate,
            option_type="call" if "call" in option_type else "put"
        )
        logger.info(f"Priced {option_type} option (Black-Scholes): ${price:.2f}")

    return price
