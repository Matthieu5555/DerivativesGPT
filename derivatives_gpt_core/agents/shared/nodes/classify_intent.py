"""Initial intent classification node - Binary decision: option-related or not."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.config import get_settings
from derivatives_gpt_core.observability.metrics import metrics_tracker
from derivatives_gpt_core.observability.trace_helpers import instrument_node
from prompts.classification import INITIAL_CLASSIFICATION_PROMPT
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import InitialClassification
from derivatives_gpt_core.utils.chart_manager import chart_manager
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
from typing import Dict, Any
import json
import logging
import time

logger = logging.getLogger(__name__)


async def _display_chart_if_ticker(ticker: str | None) -> float | None:
    """
    Display price chart immediately after ticker extraction using error-resilient chart manager.

    Returns:
        Current spot price (float) if successful, None otherwise

    Note: This function NEVER raises exceptions - chart failures are logged but don't break flow.
    """
    if not ticker:
        return None

    logger.info(f"Displaying chart for {ticker} using error-resilient chart manager")

    # Use error-resilient chart manager (handles all errors gracefully)
    result = await chart_manager.display_chart_async(
        ticker=ticker,
        lookback_days=252,
        include_volume=True,
        include_sma=True
    )

    if result.success:
        logger.info(f"Chart displayed for {ticker}, spot price: ${result.spot_price:.2f}")
        return result.spot_price
    else:
        # Chart failed, but that's OK - user can still get pricing
        logger.warning(f"Chart display failed for {ticker}: {result.error_message}")
        logger.warning("Continuing with pricing workflow (chart not required for pricing)")
        return None


@traceable(name="classify_intent", metadata={"node_type": "classification", "version": "2.0"})
async def classify_user_intent(state: BaseAgentState) -> Dict[str, Any]:
    """
    Initial binary classification: is the query option-related or off-topic?

    This is a lightweight first pass that routes:
    - Option-related queries → augmentation (RAG + web search)
    - Off-topic queries → off_topic handler (skip augmentation)

    Detailed classification (pricing vs concept, parameter extraction, clarification)
    happens AFTER augmentation in the classify_with_context node.

    Tracks metrics:
    - classification_latency: Time to classify query
    - classification_success: Whether classification succeeded

    Returns:
        dict: Classification fields to merge into state
            - is_option_related: bool
            - initial_reasoning: str
    """
    start_time = time.time()
    settings = get_settings()

    # Start metrics tracking
    if settings.langsmith_track_metrics:
        metrics_tracker.start_timer("classification")

    # Get last user message
    user_message = state.messages[-1].content

    # Get cost-effective classification LLM
    classification_model = get_classification_llm()

    # Classify with JSON output
    response = classification_model.invoke([
        SystemMessage(content=INITIAL_CLASSIFICATION_PROMPT),
        HumanMessage(content=user_message)
    ])

    response_text = response.content.strip()

    # Parse and validate JSON using Pydantic schema
    try:
        validated_classification = extract_and_validate_with_retry(response_text, InitialClassification, max_attempts=3, strict=False)

        if validated_classification is None:
            raise ValueError("Failed to extract or validate classification JSON from response")

        # End metrics tracking - SUCCESS
        if settings.langsmith_track_metrics:
            metrics_tracker.end_timer("classification")
            metrics_tracker.record_success("classification", True)

        logger.info(
            f"Initial classification: is_option_related={validated_classification.is_option_related}, "
            f"reasoning={validated_classification.reasoning}, ticker={validated_classification.ticker}"
        )

        # Display chart immediately if ticker extracted AND extract spot price
        spot_price = None
        if validated_classification.ticker:
            spot_price = await _display_chart_if_ticker(validated_classification.ticker)

        # Return binary classification result with ticker
        result = {
            "is_option_related": validated_classification.is_option_related,
            "initial_reasoning": validated_classification.reasoning
        }

        # Add ticker if extracted
        if validated_classification.ticker:
            result["extracted_ticker"] = validated_classification.ticker

        # Add spot_price if successfully extracted from chart data
        if spot_price is not None:
            result["spot_price"] = spot_price
            logger.info(f"Stored spot price ${spot_price:.2f} in state from chart data")

        # Instrument node with LangSmith - SUCCESS
        instrument_node(state, "classify_intent", start_time, success=True)

        return result

    except (json.JSONDecodeError, Exception) as e:
        # Classification failed - default to off_topic
        logger.error(f"Initial classification error: {e}")
        logger.error(f"Response text: {response_text}")

        # End metrics tracking - FAILURE
        if settings.langsmith_track_metrics:
            metrics_tracker.end_timer("classification")
            metrics_tracker.record_success("classification", False)

        # Instrument node with LangSmith - FAILURE
        instrument_node(state, "classify_intent", start_time, success=False, error_type=type(e).__name__)

        return {
            "is_option_related": False,
            "initial_reasoning": "Classification error - defaulting to off-topic"
        }
