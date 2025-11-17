"""Pure helper functions for LangSmith trace enrichment - functional approach."""

from typing import Any, Dict, List, Literal
from datetime import datetime
import time

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.config import get_settings


# === ENVIRONMENT DETECTION (Pure) ===


def get_current_environment() -> Literal["dev", "staging", "prod"]:
    """
    Pure function: Determine current environment.

    Returns:
        Environment string for project selection
    """
    settings = get_settings()

    # Check if we're in production based on config
    if hasattr(settings, 'environment'):
        return settings.environment

    # Fallback: Check project name for environment hints
    project = settings.langsmith_project
    if 'prod' in project.lower():
        return "prod"
    elif 'staging' in project.lower():
        return "staging"
    else:
        return "dev"


def should_enable_ticker_tagging(environment: str) -> bool:
    """
    Pure predicate: Should ticker tagging be enabled?

    Privacy-first: Only enable in dev/staging, never in prod.

    Args:
        environment: Current environment

    Returns:
        bool: True if ticker tagging allowed
    """
    return environment in ["dev", "staging"]


# === TAG GENERATION (Pure) ===


def get_run_tags(
    state: BaseAgentState,
    environment: str | None = None
) -> List[str]:
    """
    Pure function: Generate LangSmith run tags from state.

    Tags follow format: "category:value"

    Args:
        state: Current graph state
        environment: Environment override (defaults to auto-detect)

    Returns:
        List of tag strings
    """
    settings = get_settings()
    env = environment or get_current_environment()

    tags = [env]  # Always include environment

    # Product type tag (e.g., european_call, american_put)
    # Safely check for pricing-specific attributes
    if settings.langsmith_tag_product_type and hasattr(state, 'product_type') and state.product_type:
        if hasattr(state, 'option_type') and state.option_type:
            product_tag = f"{state.product_type}_{state.option_type}"
        else:
            product_tag = state.product_type
        tags.append(f"product:{product_tag}")

    # Asset class tag (e.g., equity, fx, commodity)
    if settings.langsmith_tag_asset_class and hasattr(state, 'asset_class') and state.asset_class:
        tags.append(f"asset:{state.asset_class}")

    # Pricing method tag
    if settings.langsmith_tag_pricing_method and hasattr(state, 'product_type') and state.product_type:
        if "european" in state.product_type.lower():
            tags.append("method:black_scholes")
        elif "american" in state.product_type.lower():
            tags.append("method:binomial")
        elif state.product_type in ["barrier", "asian", "lookback"]:
            tags.append("method:monte_carlo")

    # Ticker tag (privacy-gated)
    if (settings.langsmith_tag_ticker
        and hasattr(state, 'ticker')
        and state.ticker
        and should_enable_ticker_tagging(env)):
        tags.append(f"ticker:{state.ticker}")

    return tags


# === METADATA EXTRACTION (Pure) ===


def extract_financial_metadata(state: BaseAgentState) -> Dict[str, Any]:
    """
    Pure function: Extract financial fields from state.

    Priority 1 metadata: Core pricing parameters

    Returns:
        Dict of financial metadata (empty if no data)
    """
    metadata = {}

    # Safely access pricing-specific attributes (only exist in PricingState)
    if hasattr(state, 'ticker') and state.ticker:
        metadata["ticker"] = state.ticker
    if hasattr(state, 'strike_price') and state.strike_price is not None:
        # Handle both numeric and string strikes ("ATM", "5% above", etc.)
        if isinstance(state.strike_price, (int, float)):
            metadata["strike"] = float(state.strike_price)
        else:
            metadata["strike"] = str(state.strike_price)
    if hasattr(state, 'spot_price') and state.spot_price is not None:
        metadata["spot_price"] = float(state.spot_price)
    if hasattr(state, 'volatility') and state.volatility is not None:
        metadata["implied_volatility"] = float(state.volatility)
    if hasattr(state, 'option_price') and state.option_price is not None:
        metadata["option_price"] = float(state.option_price)

    return metadata


def extract_operational_metadata(
    node_name: str,
    start_time: float,
    success: bool,
    error_type: str | None = None
) -> Dict[str, Any]:
    """
    Pure function: Extract operational metrics.

    Priority 2 metadata: Node execution stats

    Args:
        node_name: Name of current node
        start_time: time.time() at node start
        success: Whether node succeeded
        error_type: Error type if failed

    Returns:
        Dict of operational metadata
    """
    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "node": node_name,
        "latency_ms": elapsed_ms,
        "success": success,
        "error_type": error_type,
        "timestamp": datetime.utcnow().isoformat()
    }


def extract_quality_metadata(state: BaseAgentState) -> Dict[str, Any]:
    """
    Pure function: Extract quality/confidence fields.

    Priority 3 metadata: Debugging signals

    Returns:
        Dict of quality metadata
    """
    metadata = {}

    if hasattr(state, 'extraction_attempts') and state.extraction_attempts:
        metadata["extraction_attempts"] = state.extraction_attempts
    if hasattr(state, 'validation_warnings') and state.validation_warnings:
        metadata["validation_warning_count"] = len(state.validation_warnings)
    if hasattr(state, 'validation_errors') and state.validation_errors:
        metadata["validation_error_count"] = len(state.validation_errors)

    return metadata


def combine_metadata(
    state: BaseAgentState,
    node_name: str,
    start_time: float,
    success: bool,
    error_type: str | None = None,
    extra: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Pure function: Combine all metadata sources.

    Merges: financial + operational + quality + extra

    Args:
        state: Current graph state
        node_name: Node name
        start_time: Start timestamp
        success: Success flag
        error_type: Error type if failed
        extra: Additional metadata

    Returns:
        Combined metadata dict
    """
    metadata = {}

    # Merge in priority order
    metadata.update(extract_financial_metadata(state))
    metadata.update(extract_operational_metadata(node_name, start_time, success, error_type))
    metadata.update(extract_quality_metadata(state))

    if extra:
        metadata.update(extra)

    return metadata


# === TRACE ATTACHMENT (Side Effect - Isolated) ===


def attach_to_current_trace(
    tags: List[str],
    metadata: Dict[str, Any]
) -> None:
    """
    Side effect: Attach tags and metadata to current LangSmith trace.

    This is the ONLY function with side effects - all others are pure.

    Args:
        tags: Tags to attach
        metadata: Metadata to attach
    """
    try:
        from langsmith import get_current_run_tree

        run = get_current_run_tree()
        if not run:
            return

        # Attach tags
        for tag in tags:
            if tag not in run.tags:
                run.tags.append(tag)

        # Attach metadata
        run.metadata.update(metadata)

    except Exception:
        # Silently fail - observability shouldn't break app
        pass


# === HIGH-LEVEL INSTRUMENTATION (Composing Pure Functions) ===


def instrument_node(
    state: BaseAgentState,
    node_name: str,
    start_time: float,
    success: bool,
    error_type: str | None = None,
    extra_metadata: Dict[str, Any] | None = None,
    environment: str | None = None
) -> None:
    """
    Convenience function: Full node instrumentation.

    Composes pure functions and isolates side effect to one place.

    Usage in nodes:
        start = time.time()
        try:
            # ... node logic ...
            instrument_node(state, "my_node", start, success=True)
        except Exception as e:
            instrument_node(state, "my_node", start, success=False, error_type=type(e).__name__)

    Args:
        state: Current state
        node_name: Node name
        start_time: Start time
        success: Success flag
        error_type: Error type
        extra_metadata: Additional metadata
        environment: Environment override
    """
    # Pure functions - compose without side effects
    tags = get_run_tags(state, environment)
    metadata = combine_metadata(state, node_name, start_time, success, error_type, extra_metadata)

    # Single side effect - isolated
    attach_to_current_trace(tags, metadata)
