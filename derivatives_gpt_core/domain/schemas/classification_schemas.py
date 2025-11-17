"""
Classification result schemas.

This module defines Pydantic models for LLM classification outputs.
"""

from typing import Literal
from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    """
    Structured classification output from LLM.

    This model validates JSON output from the classification LLM,
    extracting product type, features, and pricing feasibility.
    """

    can_price: bool = Field(
        description="True if request is priceable with available methods"
    )
    product_type: str = Field(
        description="Specific product type detected (e.g., 'european_call', 'asian_option', 'unknown')"
    )
    features_detected: list[str] = Field(
        default_factory=list,
        description="List of detected features"
    )
    asset_class: str = Field(
        description="Asset class (equity, fx, commodity, interest_rate, credit, other)"
    )
    response_type: Literal["can_price", "recognize_but_refuse", "clarify", "off_topic", "explain_concept"] = Field(
        description="How to respond to this query"
    )
    reasoning: str = Field(
        description="Brief explanation of classification decision"
    )
    ticker: str | None = Field(
        default=None,
        description="Extracted ticker symbol (e.g., 'AAPL', 'TSLA')"
    )

    # Multi-ticker support (different underlyings)
    multi_ticker: bool = Field(
        default=False,
        description="True if user requests multiple options on different tickers"
    )
    tickers: list[str] | None = Field(
        default=None,
        description="List of ticker symbols for multi-ticker vanilla requests"
    )
    option_types: list[str] | None = Field(
        default=None,
        description="List of option types matching tickers: ['call', 'put', 'call']"
    )
    strikes: list[float] | None = Field(
        default=None,
        description="List of strike prices matching tickers: [150, 200, 500]"
    )

    # Multi-leg strategy support (same underlying)
    strategy_type: str | None = Field(
        default=None,
        description="Strategy type: 'single', 'straddle', 'strangle', 'spread', 'butterfly'"
    )
    multi_leg: bool = Field(
        default=False,
        description="True if multi-leg strategy on same underlying (e.g., straddle, spread)"
    )
    legs: list[dict] | None = Field(
        default=None,
        description="Leg definitions for multi-leg strategies"
    )

    # Parameter extraction - single ticker fields
    time_to_expiry_days: float | None = Field(
        default=None,
        description="Time to expiration in days. Extract from phrases like '30 days', 'three months' (90)"
    )
    option_type: Literal["call", "put"] | None = Field(
        default=None,
        description="Option type: 'call' or 'put'"
    )
    strike_price: float | None = Field(
        default=None,
        description="Strike price ONLY if explicitly stated. Do NOT extract if relative."
    )
    volatility: float | None = Field(
        default=None,
        description="Volatility as decimal if user explicitly provides it"
    )
    risk_free_rate: float | None = Field(
        default=None,
        description="Interest rate as decimal if user explicitly provides it"
    )

    # Exotic derivative parameters
    barrier_level: float | None = Field(
        default=None,
        description="Barrier price level for barrier options"
    )
    barrier_type: Literal["knock_in", "knock_out", "up", "down"] | None = Field(
        default=None,
        description="Type of barrier activation"
    )
    averaging_type: Literal["arithmetic", "geometric"] | None = Field(
        default=None,
        description="Averaging method for Asian options"
    )
    averaging_period_days: float | None = Field(
        default=None,
        description="Days over which to average for Asian options"
    )
    lookback_type: Literal["fixed_strike", "floating_strike"] | None = Field(
        default=None,
        description="Strike type for lookback options"
    )
    exotic_tickers: list[str] | None = Field(
        default=None,
        description="List of tickers for multi-asset exotic options (rainbow, basket)"
    )
    asset_weights: list[float] | None = Field(
        default=None,
        description="Weights for basket options"
    )
    basket_type: Literal["best_of", "worst_of", "average"] | None = Field(
        default=None,
        description="Type of multi-asset payoff"
    )
    compound_type: Literal["call_on_call", "call_on_put", "put_on_call", "put_on_put"] | None = Field(
        default=None,
        description="Type of compound option"
    )
    underlying_strike: float | None = Field(
        default=None,
        description="Strike of the underlying option in compound"
    )
    compound_strike: float | None = Field(
        default=None,
        description="Strike to acquire the underlying option"
    )
    variance_strike: float | None = Field(
        default=None,
        description="Strike variance for variance swaps"
    )
    volatility_strike: float | None = Field(
        default=None,
        description="Strike volatility for volatility swaps"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "can_price": True,
                "product_type": "european_call",
                "features_detected": ["vanilla"],
                "asset_class": "equity",
                "response_type": "can_price",
                "reasoning": "Standard European call option on equity, can price with Black-Scholes"
            }
        }
    }
