"""Extract pricing parameters from user query."""

from derivatives_gpt_core.agents.pricing.state import PricingState
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.observability.trace_helpers import instrument_node
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import ParameterExtraction, MultiAssetExtraction
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
from typing import Dict, Any
import logging
import time

# Import prompts from centralized location
from prompts.graph_nodes.parameter_extraction_prompts import PARAMETER_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


@traceable(name="extract_parameters", metadata={"node_type": "parameter_extraction", "version": "2.0"})
async def extract_parameters(state: PricingState) -> Dict[str, Any]:
    """
    Extract pricing parameters from user query.

    Uses LLM to parse user message and extract:
    - ticker
    - strike_price
    - time_to_expiry_days
    - spot_price (if user provides)
    - volatility (if user provides)
    - risk_free_rate (if user provides)
    - option_type (call/put)

    Loop protection:
    - Tracks extraction_attempts
    - Fails gracefully after max_extraction_attempts

    Args:
        state: State with user message

    Returns:
        dict: Extracted parameters + extraction_successful flag
    """
    start_time = time.time()

    # Check loop protection - increment counter
    extraction_attempts = state.extraction_attempts + 1

    # Note: We allow the attempts to reach max, then route_after_extraction will catch it
    # This node just marks the attempt count
    if extraction_attempts > state.max_extraction_attempts:
        logger.error(f"Max extraction attempts ({state.max_extraction_attempts}) exceeded")

        # Instrument node - FAILURE (max attempts exceeded)
        instrument_node(state, "extract_parameters", start_time, success=False, error_type="MaxAttemptsExceeded")

        return {
            "extraction_successful": False,
            "extraction_attempts": extraction_attempts,
            "reasoning": "Unable to extract required parameters after multiple attempts."
        }

    logger.info(f"Parameter extraction attempt {extraction_attempts}/{state.max_extraction_attempts}")

    logger.info(f"DIAGNOSTIC: extract_parameters called, attempt {extraction_attempts}/{state.max_extraction_attempts}")

    try:
        # Get conversation context (last 3 exchanges for context)
        from langchain_core.messages import HumanMessage as HM, AIMessage as AIM

        conversation_context = []
        if state.messages:
            # Get last 6 messages (3 human-AI exchanges)
            recent_messages = state.messages[-6:] if len(state.messages) > 6 else state.messages
            for msg in recent_messages:
                if isinstance(msg, HM):
                    conversation_context.append(f"User: {msg.content}")
                elif isinstance(msg, AIM):
                    # Truncate long AI responses
                    content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    conversation_context.append(f"Assistant: {content}")

        # Get current user query (last human message)
        user_query = ""
        if state.messages:
            for msg in reversed(state.messages):
                if isinstance(msg, HM):
                    user_query = msg.content
                    break

        if not user_query:
            logger.warning("No user query found for parameter extraction")
            return {"extraction_successful": False}

        # Use classification LLM (fast and cheap)
        llm = get_classification_llm()

        # Build comprehensive context with conversation history
        context_parts = [
            "=== CONVERSATION HISTORY ===",
            *conversation_context,
            "",
            "=== CURRENT REQUEST ===",
            f"User Query: {user_query}",
            "",
            "=== EXISTING PARAMETERS FROM PREVIOUS DISCUSSION ==="
        ]

        # Add existing state parameters (critical for "same option but X" patterns)
        has_previous_params = False
        if state.ticker:
            context_parts.append(f"Previous Ticker: {state.ticker}")
            has_previous_params = True
        if state.strike_price:
            context_parts.append(f"Previous Strike: {state.strike_price}")
            has_previous_params = True
        if state.time_to_expiry_days:
            context_parts.append(f"Previous Expiry: {state.time_to_expiry_days} days")
            has_previous_params = True
        if state.option_type:
            context_parts.append(f"Previous Option Type: {state.option_type}")
            has_previous_params = True
        if state.spot_price:
            context_parts.append(f"Current Spot Price: ${state.spot_price:.2f}")
            has_previous_params = True

        if not has_previous_params:
            context_parts.append("(No previous parameters in state)")

        context_parts.append("")
        context_parts.append("=== CLASSIFICATION INFO ===")

        if state.asset_type_classified:
            context_parts.append(f"Asset Type: {state.asset_type_classified}")

        if state.option_type_classified:
            context_parts.append(f"Option Class: {state.option_type_classified}")

        context_parts.extend([
            "",
            "=== EXTRACTION INSTRUCTIONS ===",
            "1. If user says 'same option', 'same parameters', 'but now', inherit ALL previous parameters",
            "2. Only override what the user explicitly changes in current query",
            "3. For 'same option but american', keep strike and expiry from previous, just change type"
        ])

        context = "\n".join(context_parts)

        # DIAGNOSTIC: Log user query and context
        logger.info(
            f"EXTRACTION INPUT:\n"
            f"  User Query: {user_query}\n"
            f"  Context (first 400 chars): {context[:400]}..."
        )

        response = llm.invoke([
            SystemMessage(content=PARAMETER_EXTRACTION_PROMPT),
            HumanMessage(content=context)
        ])

        # Parse and validate JSON response using Pydantic schema
        response_text = response.content.strip()

        # DIAGNOSTIC: Log what LLM actually returned
        logger.info(f"RAW LLM RESPONSE (first 600 chars):\n{response_text[:600]}")

        validated_params = extract_and_validate_with_retry(response_text, ParameterExtraction, max_attempts=3, strict=False)

        if validated_params is None:
            logger.error(f"EXTRACTION RETURNED NONE. Full raw response:\n{response_text}")
            logger.error("Failed to parse or validate parameter extraction JSON")
            return {
                "extraction_successful": False,
                "extraction_attempts": extraction_attempts
            }

        # ============================================================================
        # AUTO-FIX LAYER: Clean up common LLM mistakes
        # ============================================================================
        from derivatives_gpt_core.config import VALID_OPTION_TYPES

        if validated_params.option_type is not None:
            original_type = validated_params.option_type

            # Check if LLM extracted an invalid value
            if validated_params.option_type not in VALID_OPTION_TYPES:
                logger.warning(
                    f"LLM extracted invalid option_type: '{validated_params.option_type}'. "
                    f"Valid values are {VALID_OPTION_TYPES}. Attempting auto-fix..."
                )

                # Auto-fix common mistakes by extracting the direction
                option_type_lower = validated_params.option_type.lower()

                if "call" in option_type_lower:
                    validated_params.option_type = "call"
                    logger.info(f"  Auto-fixed: '{original_type}' → 'call'")
                elif "put" in option_type_lower:
                    validated_params.option_type = "put"
                    logger.info(f"  Auto-fixed: '{original_type}' → 'put'")
                elif "straddle" in option_type_lower or "strangle" in option_type_lower:
                    # For strategies, mark as extraction failure - these need multi-asset handling
                    logger.warning(
                        f"  '{original_type}' is a strategy, not a single option type. "
                        f"Marking extraction as incomplete."
                    )
                    validated_params.extraction_successful = False
                    if "option_type" not in validated_params.missing_info:
                        validated_params.missing_info.append("option_type (strategy detected)")
                    validated_params.option_type = None  # Clear invalid value
                else:
                    # Cannot auto-fix - mark as extraction failure
                    logger.error(
                        f"  Cannot auto-fix option_type: '{original_type}'. "
                        f"Does not contain 'call' or 'put'. Marking extraction as incomplete."
                    )
                    validated_params.extraction_successful = False
                    if "option_type" not in validated_params.missing_info:
                        validated_params.missing_info.append("option_type (invalid value)")
                    validated_params.option_type = None  # Clear invalid value

        # Log extracted parameters BEFORE inheritance
        logger.info(
            f"EXTRACTION RESULT (after auto-fix, before inheritance):\n"
            f"  ticker: {validated_params.ticker}\n"
            f"  strike_price: {validated_params.strike_price}\n"
            f"  time_to_expiry_days: {validated_params.time_to_expiry_days}\n"
            f"  option_type: {validated_params.option_type}\n"
            f"  extraction_successful: {validated_params.extraction_successful}\n"
            f"  missing_info: {validated_params.missing_info}"
        )

        # Apply inheritance for "same option" patterns
        inherit_patterns = ['same option', 'same but', 'but now', 'make it', 'change to', 'same parameters']
        should_inherit = any(pattern in user_query.lower() for pattern in inherit_patterns)

        if should_inherit and has_previous_params:
            logger.info(f"Detected contextual reference in query: '{user_query}'")
            logger.info("Applying parameter inheritance from previous state...")

            # Inherit parameters that were not extracted (None values)
            if validated_params.ticker is None and state.ticker:
                validated_params.ticker = state.ticker
                logger.info(f"  Inherited ticker: {state.ticker}")

            if validated_params.strike_price is None and state.strike_price:
                validated_params.strike_price = state.strike_price
                logger.info(f"  Inherited strike: {state.strike_price}")

            if validated_params.time_to_expiry_days is None and state.time_to_expiry_days:
                validated_params.time_to_expiry_days = state.time_to_expiry_days
                logger.info(f"  Inherited expiry: {state.time_to_expiry_days} days")

            # Handle option type changes (e.g., "same but american")
            if 'american' in user_query.lower():
                # User wants to change to American option
                if validated_params.option_type is None:
                    validated_params.option_type = 'call'  # Default assumption
                logger.info(f"  Detected American option request, type: {validated_params.option_type}")

            # Re-evaluate extraction_successful after inheritance
            required_params = [
                validated_params.ticker,
                validated_params.strike_price,
                validated_params.time_to_expiry_days,
                validated_params.option_type
            ]
            if all(p is not None for p in required_params):
                validated_params.extraction_successful = True
                validated_params.missing_info = []
                logger.info("  All parameters now available after inheritance!")

        # Log final parameters AFTER inheritance
        logger.info(
            f"Parameter extraction (final): ticker={validated_params.ticker}, strike={validated_params.strike_price}, "
            f"expiry={validated_params.time_to_expiry_days}, option_type={validated_params.option_type}, "
            f"successful={validated_params.extraction_successful}"
        )

        # Build response (only include non-None values to avoid overwriting state)
        response_dict = {
            "extraction_successful": validated_params.extraction_successful,
            "extraction_attempts": extraction_attempts,
            "reasoning": f"Missing: {', '.join(validated_params.missing_info)}" if validated_params.missing_info else "All required parameters extracted"
        }

        if validated_params.ticker is not None:
            response_dict["ticker"] = validated_params.ticker
            response_dict["extracted_ticker"] = validated_params.ticker

        if validated_params.strike_price is not None:
            # Handle both absolute (numeric) and relative (string) strikes
            if isinstance(validated_params.strike_price, (int, float)):
                response_dict["strike_price"] = float(validated_params.strike_price)
            elif isinstance(validated_params.strike_price, str):
                # Relative strike (e.g., "ATM", "5% above") - store as string
                # It will be resolved to a number during validation/execution
                response_dict["strike_price"] = validated_params.strike_price.strip()

        if validated_params.time_to_expiry_days is not None:
            response_dict["time_to_expiry_days"] = float(validated_params.time_to_expiry_days)

        if validated_params.spot_price is not None:
            response_dict["spot_price"] = float(validated_params.spot_price)

        if validated_params.volatility is not None:
            response_dict["volatility"] = float(validated_params.volatility)

        if validated_params.risk_free_rate is not None:
            response_dict["risk_free_rate"] = float(validated_params.risk_free_rate)

        # IMPORTANT: Construct product_type from style + direction
        # Priority: 1) Extracted option_style, 2) option_type_classified, 3) Default to European
        if validated_params.option_type is not None:
            direction = validated_params.option_type  # "call" or "put"

            # Check if option_style was explicitly extracted (NEW!)
            if hasattr(validated_params, 'option_style') and validated_params.option_style:
                style = validated_params.option_style.lower()
                if style == "american":
                    product_type = f"american_{direction}"
                elif style == "digital":
                    product_type = f"digital_{direction}"
                elif style in ("asian", "geometric_asian"):
                    product_type = f"geometric_asian_{direction}"
                elif style == "european":
                    product_type = f"vanilla_european_{direction}"
                else:
                    product_type = f"vanilla_european_{direction}"
                    logger.warning(f"Unknown style '{style}', defaulting to vanilla European")
                logger.info(f"Using explicitly extracted option_style: {style}")

            # Fall back to classification if no explicit style
            elif state.option_type_classified:
                classified = state.option_type_classified.lower()

                # Handle different classification formats
                if classified in ("american", "american_call", "american_put"):
                    product_type = f"american_{direction}"
                elif classified in ("digital", "digital_call", "digital_put"):
                    product_type = f"digital_{direction}"
                elif classified in ("asian", "geometric_asian", "geometric_asian_call", "geometric_asian_put"):
                    product_type = f"geometric_asian_{direction}"
                elif "vanilla" in classified or classified in ("call", "put", "european"):
                    product_type = f"vanilla_european_{direction}"
                else:
                    # Unknown classification - default to vanilla
                    product_type = f"vanilla_european_{direction}"
                    logger.warning(f"Unknown classification '{classified}', defaulting to vanilla")
            else:
                # No style or classification - default to vanilla European
                product_type = f"vanilla_european_{direction}"
                logger.info("No option style specified, defaulting to European")

            response_dict["option_type"] = direction  # Keep direction for backward compat
            response_dict["product_type"] = product_type  # Full product type for pricing
            logger.info(f"Constructed product_type: {product_type} from style='{getattr(validated_params, 'option_style', None)}' classification='{state.option_type_classified}' and direction='{direction}'")
        elif state.option_type_classified:
            # Have classification but no direction extracted - use classification as-is
            response_dict["option_type"] = state.option_type_classified

        # Instrument node - SUCCESS
        instrument_node(
            state,
            "extract_parameters",
            start_time,
            success=validated_params.extraction_successful,
            extra_metadata={"extraction_attempts": extraction_attempts}
        )

        return response_dict

    except Exception as e:
        logger.error(f"Parameter extraction failed: {e}", exc_info=True)

        # Instrument node - FAILURE
        instrument_node(state, "extract_parameters", start_time, success=False, error_type=type(e).__name__)

        return {"extraction_successful": False}
