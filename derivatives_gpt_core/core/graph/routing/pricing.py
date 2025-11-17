"""
Pricing Agent Routing Logic
============================
Routing functions for pricing agent flow.
"""

import logging
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

logger = logging.getLogger(__name__)

# Type for node names
NodeName = str


def route_pricing_query(state: BaseAgentState) -> NodeName:
    """
    Routing within pricing agent flow.

    Pricing flow:
    1. Extract parameters
    2. Validate inputs
    3. Decompose strategy
    4. Create execution plan
    5. Execute tasks
    6. Narrate results

    Args:
        state: Current state (should have pricing fields accessible)

    Returns:
        Next node name in pricing flow
    """
    # Create pricing wrapper for safe field access
    from derivatives_gpt_core.core.state.state_factory import create_pricing_state
    wrapped = create_pricing_state(state)

    # Check if parameters extracted
    spot_price = wrapped.get_field("spot_price")
    strike_price = wrapped.get_field("strike_price")

    if not spot_price or not strike_price:
        # Need to extract parameters
        attempts = wrapped.get_field("extraction_attempts", 0)

        if attempts >= 3:
            logger.warning("Pricing agent: Max extraction attempts, cannot price")
            return "recognize_but_refuse"

        logger.info("Pricing agent: Extract parameters")
        return "extract_parameters"

    # Parameters extracted - check validation
    validation_errors = wrapped.get_field("validation_errors", [])

    if validation_errors:
        # Validation failed
        clarification_attempts = wrapped.get_field("clarification_attempts", 0)

        if clarification_attempts >= 3:
            logger.warning("Pricing agent: Max clarification attempts, cannot price")
            return "recognize_but_refuse"

        logger.info("Pricing agent: Need clarification")
        return "clarify_parameters"

    # Check if validated (not just no errors, but actually validated)
    if wrapped.get_field("validation_attempt", 0) == 0:
        logger.info("Pricing agent: Validate inputs")
        return "validate_inputs"

    # Validated - check execution plan
    execution_plan = wrapped.get_field("execution_plan")

    if not execution_plan:
        # Need to decompose and plan
        logger.info("Pricing agent: Decompose and plan")
        return "decompose_strategy"

    # Check if can execute
    can_execute = wrapped.get_field("can_execute")

    if can_execute is False:
        logger.warning("Pricing agent: Cannot execute this option type")
        return "recognize_but_refuse"

    # Check execution results
    execution_results = wrapped.get_field("execution_results")

    if not execution_results:
        logger.info("Pricing agent: Execute tasks")
        return "execute_tasks"

    # Check if we need to aggregate (multi-leg)
    strategy_type = wrapped.get_field("strategy_type", "single")

    if strategy_type != "single":
        option_price = wrapped.get_field("option_price")
        if option_price is None:
            logger.info("Pricing agent: Aggregate multi-leg results")
            return "aggregate_results"

    # Everything done - narrate
    logger.info("Pricing agent: Narrate results")
    return "narrate_results"


def route_after_extraction(state: BaseAgentState) -> NodeName:
    """
    Route after parameter extraction.

    Dual-mode routing:
    - Extraction successful → validate
    - Extraction failed + evaluation mode → fail fast
    - Extraction failed + production mode → clarify with user
    - Max attempts exceeded → fail

    Args:
        state: State with extraction_successful

    Returns:
        Next node name
    """
    from derivatives_gpt_core.core.state.state_factory import create_pricing_state
    wrapped = create_pricing_state(state)

    extraction_successful = wrapped.get_field("extraction_successful", False)
    attempts = wrapped.get_field("extraction_attempts", 0)
    is_eval_mode = wrapped.get_field("is_evaluation_mode", False)

    # Check max attempts
    if attempts >= 3:
        logger.error(f"Max extraction attempts (3) exceeded")
        return "recognize_but_refuse"

    if extraction_successful:
        logger.info("Extraction successful, proceeding to validation")
        return "validate_inputs"

    # Extraction failed
    if is_eval_mode:
        logger.info("Extraction failed in evaluation mode, failing fast")
        return "recognize_but_refuse"
    else:
        logger.info("Extraction failed, asking user for clarification")
        return "clarify_parameters"


def route_after_validation(state: BaseAgentState) -> NodeName:
    """
    Route after parameter validation.

    Routes:
    - Validation passed → decompose_strategy
    - Validation failed + attempts < max → clarify_parameters
    - Validation failed + attempts >= max → recognize_but_refuse
    - Critical errors → recognize_but_refuse

    Args:
        state: State with validation_errors

    Returns:
        Next node name
    """
    from derivatives_gpt_core.core.state.state_factory import create_pricing_state
    wrapped = create_pricing_state(state)

    validation_errors = wrapped.get_field("validation_errors", [])
    clarification_attempts = wrapped.get_field("clarification_attempts", 0)

    if not validation_errors:
        logger.info("Validation passed, decomposing strategy")
        return "decompose_strategy"

    # Check if errors are critical (not just warnings)
    has_critical_errors = any("critical" in err.lower() for err in validation_errors)

    if has_critical_errors:
        logger.error("Critical validation errors, cannot proceed")
        return "recognize_but_refuse"

    # Check attempts
    if clarification_attempts >= 3:
        logger.warning("Max clarification attempts exceeded")
        return "recognize_but_refuse"

    logger.info("Validation failed, requesting clarification")
    return "clarify_parameters"


def route_after_decomposition(state: BaseAgentState) -> NodeName:
    """
    Route after strategy decomposition.

    Routes:
    - Can execute → create_execution_plan
    - Cannot execute → recognize_but_refuse

    Args:
        state: State with can_execute

    Returns:
        Next node name
    """
    from derivatives_gpt_core.core.state.state_factory import create_pricing_state
    wrapped = create_pricing_state(state)

    can_execute = wrapped.get_field("can_execute")

    # BUG FIX: Check for explicit False, not just falsy (None should be treated as True)
    # If can_execute is explicitly False, refuse. Otherwise (True or None), proceed.
    if can_execute is False:
        logger.warning("Cannot execute this option type")
        return "recognize_but_refuse"
    else:
        logger.info("Strategy decomposed, creating execution plan")
        return "create_execution_plan"


def route_after_execution(state: BaseAgentState) -> NodeName:
    """
    Route after task execution.

    Routes:
    - Single option → narrate_results
    - Multi-leg strategy → aggregate_results

    Args:
        state: State with strategy_type and execution_results

    Returns:
        Next node name
    """
    from derivatives_gpt_core.core.state.state_factory import create_pricing_state
    wrapped = create_pricing_state(state)

    strategy_type = wrapped.get_field("strategy_type", "single")

    if strategy_type == "single":
        logger.info("Single option, proceeding to narration")
        return "narrate_results"
    else:
        logger.info("Multi-leg strategy, aggregating results")
        return "aggregate_results"
