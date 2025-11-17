"""
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
Graph routing logic.
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
This module contains all conditional routing functions that determine
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
the flow between nodes in the LangGraph state machine.
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
"""
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
import logging
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
logger = logging.getLogger(__name__)


def route_after_initial_classification(state: BaseAgentState) -> str:
    """
    Route after initial intent classification.

    The chart has already been displayed during classification.

    Flow:
    - Educational queries → explain_concept (direct)
    - Option-related queries → augment_with_context (RAG + web search)
    - Off-topic queries → off_topic handler

    Args:
        state: Current graph state with is_option_related field

    Returns:
        str: Next node name
    """
    # Check if this is a purely educational query
    if state.response_type == "explain_concept":
        logger.info("Purely educational query detected, routing directly to explain_concept")
        return "explain_concept"

    if state.is_option_related:
        logger.info("Query is option-related, routing to augmentation (chart already shown)")
        return "augment_with_context"
    else:
        logger.info("Query is off-topic, routing to off_topic handler")
        return "off_topic"


def route_after_asset_classification(state: BaseAgentState) -> str:
    """
    Route after asset type classification.

    Routes:
    - Known asset type → classify_option_type
    - Unknown asset type → clarify_asset

    Args:
        state: State with asset_type_classified

    Returns:
        str: Next node name
    """
    asset_type = state.asset_type_classified

    if asset_type == "unknown":
        logger.info("Asset type unknown, requesting clarification")
        return "clarify_asset"
    else:
        logger.info(f"Asset type: {asset_type}, proceeding to option classification")
        return "classify_option_type"


def route_after_option_classification(state: BaseAgentState) -> str:
    """
    Route after option type classification.

    Routes:
    - Known option type → determine_action
    - Unknown option type → clarify_option

    Args:
        state: State with option_type_classified

    Returns:
        str: Next node name
    """
    option_type = state.option_type_classified

    if option_type == "unknown":
        logger.info("Option type unknown, requesting clarification")
        return "clarify_option"
    else:
        logger.info(f"Option type: {option_type}, determining action")
        return "determine_action"


def route_after_action_determination(state: BaseAgentState) -> str:
    """
    Route after action determination.

    Routes based on response_type:
    - can_price → extract_parameters
    - explain_concept → explain_concept handler
    - recognize_but_refuse → recognize_but_refuse handler
    - clarify → clarify_parameters handler
    - clarify_option → clarify_option (backward compatibility)

    Args:
        state: State with response_type

    Returns:
        str: Next node name
    """
    response_type = state.response_type

    if response_type == "can_price":
        return "extract_parameters"
    elif response_type == "explain_concept":
        return "explain_concept"
    elif response_type == "recognize_but_refuse":
        return "recognize_but_refuse"
    elif response_type == "clarify":
        return "clarify_parameters"
    elif response_type == "clarify_option":
        return "clarify_option"
    else:
        logger.warning(f"Unknown response_type: {response_type}, falling back to clarify_parameters")
        return "clarify_parameters"


def route_after_extraction(state: BaseAgentState) -> str:
    """
    Route after parameter extraction.

    Dual-mode routing:
    - Evaluation mode: Fail fast if extraction fails (no user to clarify)
    - Production mode: Ask user for clarification if extraction fails

    Routes:
    - extraction_successful → validate
    - extraction_unsuccessful + evaluation_mode → recognize_but_refuse (fail fast)
    - extraction_unsuccessful + production_mode → clarify_parameters (wait for user)
    - max_attempts exceeded → recognize_but_refuse (prevent infinite loop)

    Args:
        state: State with extraction_successful and is_evaluation_mode

    Returns:
        str: Next node name
    """
    # Enforce max extraction attempts to prevent infinite loop
    if state.extraction_attempts >= state.max_extraction_attempts:
        logger.error(f"Max extraction attempts ({state.max_extraction_attempts}) exceeded, failing gracefully")
        return "recognize_but_refuse"

    if state.extraction_successful:
        logger.info("Parameter extraction successful, routing to validation")
        return "validate"
    else:
        # Dual-mode routing: evaluation vs production
        if state.is_evaluation_mode:
            logger.info("Evaluation mode: extraction failed, failing fast (no user to clarify)")
            return "recognize_but_refuse"
        else:
            logger.info("Production mode: extraction incomplete, requesting user clarification")
            return "clarify_parameters"


def route_after_validation(state: BaseAgentState) -> str:
    """
    Route after parameter validation.

    Logic:
    - Max validation attempts exceeded → validation_failed
    - Critical errors → validation_failed
    - All required params present and valid → decompose

    Warnings and relative strikes are acceptable and don't block pricing.

    Args:
        state: State after validation

    Returns:
        str: "decompose" or "validation_failed"
    """
    # Enforce max validation attempts to prevent infinite loop
    # Use > not >= because validation_attempt is incremented BEFORE this check
    if state.validation_attempt > state.max_validation_retries:
        logger.error(f"Max validation attempts ({state.max_validation_retries}) exceeded, failing")
        return "validation_failed"

    errors = state.validation_errors or []
    critical_errors = [e for e in errors if not e.startswith(('WARNING:', 'INFO:', '[WARNING]', '[INFO]'))]

    if critical_errors:
        logger.warning(f"Validation failed: {critical_errors}")
        return "validation_failed"

    # Validation passed - proceed to pricing
    logger.info("Validation passed, proceeding directly to pricing")
    return "decompose"


def route_after_decomposition(state: BaseAgentState) -> str:
    """
    Route after strategy decomposition.

    Checks if strategy can be executed with current capabilities.

    Args:
        state: State after decomposition

    Returns:
        str: "create_plan" if executable, "recognize_but_refuse" otherwise
    """
    if not state.can_execute:
        logger.warning("Strategy cannot be executed (decomposer determined)")
        return "recognize_but_refuse"
    else:
        return "create_plan"


def requires_human_approval(state: BaseAgentState) -> bool:
    """
    Pure predicate: Should execution require human approval?

    Approval needed when:
    - Monte Carlo or Binomial methods (complex numerical methods)
    - User explicitly requested review

    Args:
        state: Current state

    Returns:
        bool: True if approval required
    """
    # Only require approval for complex numerical methods
    requires_monte_carlo = state.product_type in ["asian", "barrier", "lookback", "cliquet"]
    requires_binomial = state.option_type in ["american_call", "american_put"]
    user_requested = state.human_approved is False  # Explicitly set to False means "needs approval"

    return (requires_monte_carlo or requires_binomial) and user_requested


def route_after_planning(state: BaseAgentState) -> str:
    """
    Route after execution plan creation.

    Checks if planner determined strategy is executable.
    For exotic derivatives or cases with warnings, route through human approval.

    Args:
        state: State after planning

    Returns:
        str: Next node name
    """
    if not state.can_execute:
        logger.warning("Strategy cannot be executed (planner determined)")
        return "recognize_but_refuse"
    elif requires_human_approval(state):
        logger.info(f"Routing to human approval (exotic={state.product_type}, warnings={bool(state.validation_warnings)})")
        return "human_approval"
    else:
        return "execute"


def route_after_execution(state: BaseAgentState) -> str:
    """
    Route after parallel execution and narration.

    Multi-leg strategies need aggregation, single options go to pricing_complete.

    Args:
        state: State after execution and narration

    Returns:
        str: "aggregate" for multi-leg, "pricing_complete" for single
    """
    if state.strategy_type in ["straddle", "strangle", "spread", "butterfly"]:
        logger.info(f"{state.strategy_type} requires aggregation")
        return "aggregate"
    else:
        logger.info("Single option, going to pricing_complete")
        return "pricing_complete"


# Educational routing removed - now using simple direct explanation handler
