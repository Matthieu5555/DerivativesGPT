"""Input validation for option pricing parameters."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.utils.strike_resolution import resolve_strike
from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


def validate_mathematical_consistency(state: BaseAgentState) -> List[str]:
    """
    Validate mathematical consistency for multi-leg strategies.

    Checks:
    - Straddle: Same strike for call and put
    - Strangle: Call strike > put strike
    - Spread: Different strikes required
    - Put-call parity bounds (if prices exist)

    Args:
        state: Current state with strategy and legs

    Returns:
        list[str]: Mathematical validation errors (empty if valid)

    Examples:
        Straddle with same strikes -> []
        Straddle with different strikes -> ["Straddle requires same strike for call and put"]
        Strangle with call_strike <= put_strike -> ["Strangle call strike must be > put strike"]
    """
    errors = []

    if not state.strategy_type or state.strategy_type == "single":
        return errors

    # NEW: Check legs exist for multi-leg strategies
    if state.strategy_type in ("straddle", "strangle", "spread", "butterfly"):
        if not state.legs or len(state.legs) < 2:
            errors.append(
                f"Multi-leg strategy '{state.strategy_type}' requires at least 2 legs, "
                f"but only {len(state.legs) if state.legs else 0} provided"
            )
            return errors  # Can't validate further without legs

    # Straddle validation
    if state.strategy_type == "straddle":
        if state.legs and len(state.legs) >= 2:
            call_leg = next((leg for leg in state.legs if leg.get("type") == "call"), None)
            put_leg = next((leg for leg in state.legs if leg.get("type") == "put"), None)

            if call_leg and put_leg:
                call_strike = call_leg.get("strike")
                put_strike = put_leg.get("strike")

                # Only validate if both strikes are specified (not ATM)
                if call_strike is not None and put_strike is not None:
                    if call_strike != put_strike:
                        errors.append(f"Straddle requires same strike for call and put (got call={call_strike}, put={put_strike})")

    # Strangle validation
    if state.strategy_type == "strangle":
        if state.legs and len(state.legs) >= 2:
            call_leg = next((leg for leg in state.legs if leg.get("type") == "call"), None)
            put_leg = next((leg for leg in state.legs if leg.get("type") == "put"), None)

            if call_leg and put_leg:
                call_strike = call_leg.get("strike")
                put_strike = put_leg.get("strike")

                # Only validate if both strikes are specified
                if call_strike is not None and put_strike is not None:
                    # Resolve relative strikes if spot_price is available
                    if state.spot_price is not None:
                        try:
                            resolved_call = resolve_strike(
                                call_strike, state.spot_price, "call"
                            )
                            resolved_put = resolve_strike(
                                put_strike, state.spot_price, "put"
                            )

                            if resolved_call <= resolved_put:
                                errors.append(
                                    f"Strangle call strike must be > put strike "
                                    f"(got call={call_strike} [${resolved_call:.2f}], "
                                    f"put={put_strike} [${resolved_put:.2f}])"
                                )
                        except Exception as e:
                            logger.warning(f"Could not resolve relative strikes for validation: {e}")
                            # Fall back to warning - will validate during execution
                    else:
                        # Can't validate without spot_price if strikes are relative
                        if isinstance(call_strike, str) or isinstance(put_strike, str):
                            logger.warning(
                                f"Strangle has relative strikes but no spot_price available yet, "
                                "skipping validation"
                            )
                        else:
                            # Both absolute - can validate
                            if call_strike <= put_strike:
                                errors.append(
                                    f"Strangle call strike must be > put strike "
                                    f"(got call=${call_strike:.2f}, put=${put_strike:.2f})"
                                )

    # Spread validation
    if state.strategy_type == "spread":
        if state.legs and len(state.legs) == 2:
            strikes = [leg.get("strike") for leg in state.legs if leg.get("strike") is not None]

            if len(strikes) == 2 and strikes[0] == strikes[1]:
                errors.append("Spread requires different strikes")

    if errors:
        logger.info(f"Mathematical consistency errors: {errors}")

    return errors


def validate_pricing_parameters(state: BaseAgentState) -> dict:
    """
    Validate all pricing parameters before calculation.

    Checks:
    - All required parameters are present
    - Parameters are within reasonable ranges
    - Types are correct

    Args:
        state: Current graph state with pricing parameters

    Returns:
        dict: validation_errors (blocking) and validation_warnings (non-blocking)
    """
    # LangSmith Tracing: START
    try:
        # Log received parameters for debugging state transfer
        logger.info(
            f"Validation received: "
            f"option_type={state.option_type}, "
            f"ticker={state.ticker}, "
            f"time_to_expiry_days={state.time_to_expiry_days}, "
            f"strike_price={state.strike_price}"
        )

        errors = []
        warnings = []

        # Check required parameters exist
        # Note: spot_price, volatility, risk_free_rate can be None - they'll be fetched during execution
        # Strike price can be relative (string) - it will be resolved during execution
        if state.strike_price is None:
            errors.append("Strike price is missing")
        if state.time_to_expiry_days is None:
            errors.append("Time to expiry is missing")
        if state.option_type is None:
            errors.append("Option type (call/put) is missing")
        if not (state.ticker or state.extracted_ticker):
            errors.append("Ticker symbol is missing")

        # If any required parameter is missing, return early
        if errors:
            return {"validation_errors": errors}

        # Validate spot price (only if provided - it may be fetched during execution)
        if state.spot_price is not None:
            if state.spot_price <= 0:
                errors.append(f"Spot price must be positive, got ${state.spot_price:.2f}")
            elif state.spot_price > 100000:
                errors.append(
                    f"Spot price ${state.spot_price:.2f} seems unrealistic (>$100,000). "
                    "Please verify the value."
                )

        # Validate strike price (only if it's numeric - relative strikes will be resolved during execution)
        if isinstance(state.strike_price, (int, float)):
            if state.strike_price <= 0:
                errors.append(f"Strike price must be positive, got ${state.strike_price:.2f}")
            elif state.strike_price > 100000:
                errors.append(
                    f"Strike price ${state.strike_price:.2f} seems unrealistic (>$100,000). "
                    "Please verify the value."
                )
        elif isinstance(state.strike_price, str):
            # Relative strike (e.g., "ATM", "5% above") - validate format before execution
            strike_lower = state.strike_price.lower().strip()
            valid_patterns = ["atm", "at the money", "% above", "%above", "% below", "%below", "otm", "out of the money", "itm", "in the money"]

            if not any(pattern in strike_lower for pattern in valid_patterns):
                errors.append(
                    f"Unrecognized relative strike format: '{state.strike_price}'. "
                    f"Supported formats: 'ATM', '5% above', '10% below', 'OTM', 'ITM'"
                )
            else:
                logger.info(f"Relative strike detected: {state.strike_price} - will be resolved during execution")
                warnings.append(f"Using relative strike: {state.strike_price}")

                # NEW: Warn if spot price not yet available (will be fetched during execution)
                if state.spot_price is None:
                    warnings.append(
                        f"Relative strike '{state.strike_price}' requires spot price, "
                        "which will be fetched automatically"
                    )

        # Validate time to expiry
        if state.time_to_expiry_days <= 0:
            errors.append(
                f"Time to expiry must be positive, got {state.time_to_expiry_days} days"
            )
        elif state.time_to_expiry_days > 3650:  # 10 years
            errors.append(
                f"Time to expiry {state.time_to_expiry_days} days (>{state.time_to_expiry_days/365:.1f} years) "
                "seems too long. Black-Scholes is less accurate for very long-dated options."
            )

        # Validate volatility (only if provided)
        if state.volatility is not None:
            if not (0.01 <= state.volatility <= 2.0):
                errors.append(
                    f"Volatility {state.volatility:.1%} seems unrealistic. "
                    "Expected range: 1% to 200%. Please verify."
                )

        # Validate risk-free rate (warning only, non-blocking, only if provided)
        if state.risk_free_rate is not None:
            if state.risk_free_rate < -0.05 or state.risk_free_rate > 0.20:
                warnings.append(
                f"Risk-free rate {state.risk_free_rate:.2%} is outside typical range (-5% to 20%). "
                "This may indicate an error."
            )

        # Validate option type (accept both simple types and classified types)
        # Simple types: "call", "put"
        # Classified types: "american_call", "digital_put", "geometric_asian_call", etc.
        valid_simple_types = ("call", "put")
        valid_classified_types = (
            "vanilla_call", "vanilla_put",
            "american_call", "american_put",
            "digital_call", "digital_put",
            "geometric_asian_call", "geometric_asian_put"
        )

        if state.option_type not in valid_simple_types and state.option_type not in valid_classified_types:
            # Check if it at least contains call/put
            if "call" not in state.option_type.lower() and "put" not in state.option_type.lower():
                errors.append(
                    f"Option type must contain 'call' or 'put', got '{state.option_type}'"
                )

        # Moneyness check (informational only, non-blocking)
        if state.spot_price and state.strike_price:
            # Resolve relative strike if needed
            try:
                # Extract base option type (call/put) from classified type
                base_option_type = "call" if "call" in state.option_type.lower() else "put"

                resolved_strike = resolve_strike(
                    state.strike_price,
                    state.spot_price,
                    base_option_type
                )
                moneyness = state.spot_price / resolved_strike
                if moneyness < 0.5 or moneyness > 2.0:
                    itm_otm = "in" if (moneyness > 1 and "call" in state.option_type.lower()) or \
                                       (moneyness < 1 and "put" in state.option_type.lower()) else "out of"
                    warnings.append(
                        f"This option is deeply {itm_otm}-the-money "
                        f"(spot=${state.spot_price:.2f} / strike=${resolved_strike:.2f} = {moneyness:.2f})."
                    )
                    logger.info(f"Moneyness check executed successfully with spot_price from chart data")
            except Exception as e:
                logger.warning(f"Could not compute moneyness: {e}")

        # NEW: Add mathematical consistency validation
        math_errors = validate_mathematical_consistency(state)
        errors.extend(math_errors)

        # Check validation attempt count (prevent infinite loops)
        # NOTE: Don't convert errors to warnings! Let routing handle max attempts.
        # Converting errors to warnings allows invalid inputs through to pricing.

        result = {
            "validation_errors": errors,
            "validation_warnings": warnings,
            "validation_attempt": state.validation_attempt + 1
        }

        # LangSmith Tracing: Structured logging for observability
        logger.info(
            f"[validate_inputs] Validation complete | "
            f"errors={len(errors)} | warnings={len(warnings)} | "
            f"ticker={state.ticker} | strike={state.strike_price} | "
            f"status={'FAILURE' if errors else 'SUCCESS'}"
        )

        return result

    except Exception as e:
        # LangSmith Tracing: Log errors for observability
        logger.error(
            f"[validate_inputs] EXCEPTION | ticker={state.ticker} | error={str(e)}",
            exc_info=True
        )
        # Re-raise to allow error handling upstream
        raise
