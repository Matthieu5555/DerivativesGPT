"""Pydantic schemas for LLM outputs.

This module defines schemas for validating JSON responses from LLMs.
Using these schemas with extract_and_validate() prevents silent failures from LLM drift.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal


class ExecutionTask(BaseModel):
    """Single task in execution plan."""
    id: str = Field(..., description="Unique task identifier")
    type: Literal["market_data", "volatility", "risk_free_rate", "pricing", "sum"] = Field(
        ..., description="Task type"
    )
    params: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    depends_on: List[str] = Field(default_factory=list, description="Task dependencies")


class ExecutionPlan(BaseModel):
    """Complete execution plan from planner LLM."""
    tasks: List[ExecutionTask] = Field(..., description="All tasks to execute")
    parallel_groups: List[List[str]] = Field(..., description="Groups of tasks that can run in parallel")
    can_execute: bool = Field(..., description="Whether system can execute this plan")
    complexity: Literal["simple", "medium", "complex"] = Field(
        default="simple", description="Plan complexity level"
    )


class ParameterExtraction(BaseModel):
    """Extracted parameters from user query (single asset)."""
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    strike_price: Optional[float | str] = Field(None, description="Strike price (numeric or relative like 'ATM')")
    time_to_expiry_days: Optional[float] = Field(None, description="Time to expiry in days")
    spot_price: Optional[float] = Field(None, description="Current spot price")
    volatility: Optional[float] = Field(None, description="Annualized volatility (decimal)")
    risk_free_rate: Optional[float] = Field(None, description="Risk-free rate (decimal)")
    option_type: Optional[str] = Field(
        None,
        description=(
            "Option direction: MUST be 'call' or 'put'. "
            "NOT 'digital_call', NOT 'american_put', NOT 'straddle'. "
            "Extract the direction only. Auto-fix layer will validate."
        )
    )
    option_style: Optional[str] = Field(
        None,
        description=(
            "Option style if explicitly mentioned: 'american', 'european', 'digital', 'asian', 'barrier'. "
            "Only extract if user explicitly says 'American option', 'European option', 'Barrier option', etc. "
            "Leave as None if not specified (will default to European)."
        )
    )
    # Barrier option specific parameters
    barrier_level: Optional[float] = Field(None, description="Barrier price level for barrier options")
    barrier_type: Optional[str] = Field(
        None,
        description="Barrier type: 'down-out', 'down-in', 'up-out', 'up-in'. Extract from phrases like 'down-and-out', 'knock-in', etc."
    )
    rebate: Optional[float] = Field(None, description="Rebate amount paid if barrier is hit (for knock-out options)")

    extraction_successful: bool = Field(..., description="Whether extraction found all required fields")
    missing_info: List[str] = Field(default_factory=list, description="List of missing required fields")
    is_multi_asset: bool = Field(default=False, description="Whether this is a multi-asset request")


class MultiAssetExtraction(BaseModel):
    """Extracted parameters for multi-asset options."""
    is_multi_asset: bool = Field(True, description="Must be True for multi-asset")
    num_assets: int = Field(..., description="Number of underlying assets")
    assets: List[Dict[str, Any]] = Field(..., description="List of asset specifications")
    extraction_successful: bool = Field(..., description="Whether extraction found all required fields")
    missing_info: List[str] = Field(default_factory=list, description="List of missing information")


class StrategyLeg(BaseModel):
    """Single leg in multi-leg strategy."""
    type: Literal["call", "put"] = Field(..., description="Option type")
    strike: Optional[float | str] = Field(None, description="Strike price (numeric or relative)")
    position: Literal["long", "short"] = Field("long", description="Long or short position")
    quantity: int = Field(1, description="Number of contracts")


class StrategyDecomposition(BaseModel):
    """Decomposition of multi-leg strategy."""
    strategy_type: str = Field(..., description="Strategy name (straddle, strangle, spread, etc.)")
    legs: Optional[List[StrategyLeg]] = Field(None, description="Individual option legs")
    can_decompose: bool = Field(..., description="Whether decomposition succeeded")
    complexity: Optional[Literal["simple", "medium", "complex"]] = Field(None, description="Strategy complexity")
    reason: Optional[str] = Field(None, description="Reason if cannot decompose")


class InitialClassification(BaseModel):
    """Initial binary classification: option-related or not."""
    is_option_related: bool = Field(..., description="Whether query is option/derivatives related")
    reasoning: str = Field(..., description="Reasoning for classification")
    ticker: Optional[str] = Field(None, description="Extracted ticker symbol if present")


class IntentClassification(BaseModel):
    """User intent classification result."""
    intent: Literal[
        "price_option",
        "explain_strategy",
        "compare_strategies",
        "market_data",
        "general_question",
        "greeting",
        "unclear"
    ] = Field(..., description="Classified user intent")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Classification confidence")
    reasoning: str = Field(default="", description="Why this intent was chosen")


class AssetTypeClassification(BaseModel):
    """Asset type classification result."""
    asset_type: Literal[
        "equity",
        "fx",
        "commodity",
        "interest_rate",
        "credit",
        "fixed_income",
        "inflation",
        "volatility",
        "correlation",
        "real_estate",
        "unknown"
    ] = Field(..., description="Type of underlying asset")
    reasoning: str = Field(..., description="Why this asset type was chosen")
    extracted_ticker: Optional[str] = Field(None, description="Extracted ticker symbol if present")


class OptionTypeClassification(BaseModel):
    """Option type classification result."""
    option_type: str = Field(..., description="Option type (vanilla_call, vanilla_put, asian, barrier, etc.)")
    reasoning: str = Field(..., description="Why this option type was chosen")
    features_detected: List[str] = Field(default_factory=list, description="Detected option features")
    can_price: bool = Field(..., description="Whether this option type can be priced")
    requires_method: Optional[str] = Field(None, description="Method required for pricing if can_price=False")
    missing_direction: bool = Field(default=False, description="True if user did not specify call vs put direction")
    response_type: Optional[str] = Field(None, description="Response type: 'explain_concept' for educational queries, None otherwise")


class TickerSearchResult(BaseModel):
    """Result from ticker search."""
    ticker: str = Field(..., description="Found ticker symbol")
    company_name: Optional[str] = Field(None, description="Company name")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Search confidence")
    alternatives: List[str] = Field(default_factory=list, description="Alternative ticker symbols")
