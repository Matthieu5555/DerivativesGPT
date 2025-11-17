"""
Pricing Agent State
===================
State for pricing agent with option parameter extraction, validation, and pricing.

Inherits from BaseAgentState and adds pricing-specific fields:
- Single/multi-asset option parameters
- Multi-leg strategies
- Exotic derivatives parameters
- Execution planning
- Validation and loop protection
- Pricing results
"""

from typing import Literal
from pydantic import Field

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState


class PricingState(BaseAgentState):
    """
    State for pricing agent.

    Extends BaseAgentState with:
    - Option parameters (vanilla, exotic, multi-leg)
    - Execution planning
    - Validation and error handling
    - Pricing results
    """

    # === SINGLE ASSET PARAMETERS ===
    # Note: spot_price inherited from BaseAgentState
    strike_price: float | str | None = None  # Numeric (150.0) or relative ("ATM", "5% above")
    time_to_expiry_days: float | None = None
    volatility: float | None = None
    risk_free_rate: float | None = None
    option_type: str | None = None  # "call", "put", "american_call", etc.

    # === MULTI-ASSET PARAMETERS ===
    is_multi_asset: bool | None = Field(
        default=None,
        description="Flag indicating multi-asset query"
    )
    num_assets: int | None = Field(
        default=None,
        description="Number of underlying assets"
    )
    assets: list[dict] | None = Field(
        default=None,
        description="Asset specifications: [{'ticker': 'AAPL', 'strike': 150, 'option_type': 'call', ...}]"
    )

    # === MULTI-LEG STRATEGY SUPPORT ===
    strategy_type: Literal["single", "straddle", "strangle", "spread", "butterfly"] | None = Field(
        default=None,
        description="Strategy type: single vanilla or multi-leg"
    )
    multi_leg: bool | None = Field(
        default=None,
        description="Flag indicating multi-leg strategy (same underlying)"
    )
    legs: list[dict] | None = Field(
        default=None,
        description="Leg definitions: [{'type': 'call', 'strike': 150, 'position': 'long', 'quantity': 1}, ...]"
    )

    # === EXOTIC DERIVATIVE PARAMETERS ===
    barrier_level: float | None = Field(
        default=None,
        description="Barrier price level for barrier options"
    )
    barrier_type: str | None = Field(
        default=None,
        description="Type of barrier activation"
    )
    averaging_type: str | None = Field(
        default=None,
        description="Averaging method for Asian options"
    )
    averaging_period_days: float | None = Field(
        default=None,
        description="Days over which to average for Asian options"
    )
    lookback_type: str | None = Field(
        default=None,
        description="Strike type for lookback options"
    )
    exotic_tickers: list[str] | None = Field(
        default=None,
        description="List of tickers for multi-asset exotic options (basket, rainbow)"
    )
    asset_weights: list[float] | None = Field(
        default=None,
        description="Weights for basket options"
    )
    basket_type: str | None = Field(
        default=None,
        description="Type of multi-asset payoff"
    )
    compound_type: str | None = Field(
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

    # === EXECUTION PLANNING ===
    execution_plan: dict | None = Field(
        default=None,
        description="DAG execution plan with tasks and parallel groups"
    )
    plan_generated: bool = Field(
        default=False,
        description="Whether execution plan has been generated"
    )
    can_execute: bool | None = Field(
        default=None,
        description="Planner/decomposer assessment of executability"
    )
    execution_results: dict | None = Field(
        default=None,
        description="Results from parallel task execution"
    )

    # === PARAMETER EXTRACTION ===
    ticker_extraction_successful: bool | None = Field(
        default=None,
        description="Whether ticker extraction was successful"
    )
    extraction_successful: bool | None = Field(
        default=None,
        description="Whether parameter extraction was successful"
    )
    # Note: extraction_attempts and max_extraction_attempts inherited from BaseAgentState

    # === CLARIFICATION LOOP PROTECTION ===
    # Note: clarification_attempts and max_clarification_attempts inherited from BaseAgentState

    # === VALIDATION ===
    validation_errors: list[str] | None = None
    validation_warnings: list[str] | None = None
    validation_attempt: int = Field(
        default=0,
        description="Current validation attempt count (for loop-back)"
    )
    max_validation_retries: int = Field(
        default=2,
        description="Maximum validation retry attempts"
    )

    # === HUMAN APPROVAL (legacy, may be removed) ===
    human_approved: bool | None = Field(
        default=None,
        description="Whether human approved pricing with proposed parameters"
    )
    human_feedback: str | None = Field(
        default=None,
        description="Free-text feedback from human during approval"
    )

    # === PRICING RESULTS ===
    option_price: float | None = None
    price_breakdown: str | None = Field(
        default=None,
        description="Human-readable price breakdown for multi-leg strategies"
    )
