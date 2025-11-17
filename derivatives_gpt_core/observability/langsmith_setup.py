"""LangSmith tracing configuration."""

import os
from derivatives_gpt_core.config import get_settings
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState


def configure_langsmith() -> None:
    """Configure LangSmith tracing."""
    settings = get_settings()

    if settings.enable_langsmith and settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


def get_run_tags(state: BaseAgentState) -> list[str]:
    """
    Generate LangSmith run tags based on state and configuration.

    Tags help organize and filter traces in LangSmith:
    - product_type: "european_call", "american_put", etc.
    - asset_class: "equity", "fx", "commodity", etc.
    - pricing_method: "black_scholes", "binomial", etc.
    - ticker: "AAPL", "TSLA", etc. (optional, disabled by default)

    Args:
        state: Current graph state with pricing information

    Returns:
        list[str]: Tags to apply to the LangSmith run

    Example:
        state = BaseAgentState(...)
        tags = get_run_tags(state)
        # tags = ["product:european_call", "asset:equity", "method:black_scholes"]
    """
    settings = get_settings()
    tags = []

    # Product type tag (e.g., european_call, american_put)
    if settings.langsmith_tag_product_type and state.product_type:
        # Combine product_type and option_type if available
        if state.option_type:
            product_tag = f"{state.product_type}_{state.option_type}"
        else:
            product_tag = state.product_type
        tags.append(f"product:{product_tag}")

    # Asset class tag (e.g., equity, fx, commodity)
    if settings.langsmith_tag_asset_class and state.asset_class:
        tags.append(f"asset:{state.asset_class}")

    # Pricing method tag (currently just black_scholes for European options)
    if settings.langsmith_tag_pricing_method:
        # Infer pricing method from product type
        if state.product_type and "european" in state.product_type.lower():
            tags.append("method:black_scholes")
        elif state.product_type:
            tags.append(f"method:{state.product_type}")

    # Ticker tag (optional, disabled by default for privacy)
    if settings.langsmith_tag_ticker and state.ticker:
        tags.append(f"ticker:{state.ticker}")

    return tags
