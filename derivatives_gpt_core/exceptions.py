"""
Custom exception hierarchy for DerivativesGPT.

This module defines all domain-specific exceptions used throughout the application.
Using custom exceptions improves error handling, debugging, and API error responses.
"""

from typing import Any


# =============================================================================
# BASE EXCEPTION
# =============================================================================

class DerivativesGPTError(Exception):
    """
    Base exception for all DerivativesGPT errors.

    All custom exceptions inherit from this base class, allowing callers
    to catch all application-specific errors with a single except clause.

    Attributes:
        message: Human-readable error message
        details: Optional dict with additional error context
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


# =============================================================================
# PRICING ERRORS
# =============================================================================

class PricingError(DerivativesGPTError):
    """
    Base class for all pricing-related errors.

    Raised when option pricing calculations fail due to invalid inputs,
    numerical issues, or model limitations.

    When to use: Price calculation failures in any pricing model
    Where used: pricing_math/, langchain_tools/black_scholes_tool.py
    """
    pass


class BlackScholesError(PricingError):
    """
    Errors specific to Black-Scholes pricing model.

    Examples:
        - Negative time to expiry
        - Negative volatility or risk-free rate
        - Invalid option type

    Where used: pricing_math/black_scholes_formula.py (via InvalidParameterError alias)
    """
    pass


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(DerivativesGPTError):
    """
    Base class for input validation errors.

    Raised when user inputs or extracted parameters fail validation checks.

    When to use: Parameter validation failures
    Where used: graph_nodes/validate_inputs.py, utils/validation.py
    """
    pass


class ParameterValidationError(ValidationError):
    """
    Errors in pricing parameter validation.

    Examples:
        - Spot price <= 0
        - Strike price <= 0
        - Volatility < 0 or > 5
        - Risk-free rate outside reasonable bounds

    Where used: utils/moneyness.py
    """
    pass


# =============================================================================
# MARKET DATA ERRORS
# =============================================================================

class MarketDataError(DerivativesGPTError):
    """
    Base class for market data retrieval errors.

    Raised when fetching or processing market data fails.

    When to use: Any market data operation failure
    Where used: market_data/, langchain_tools/*_tool.py
    """
    pass


class DataFetchError(MarketDataError):
    """
    Errors when fetching data from external sources.

    Examples:
        - Yahoo Finance API timeout
        - Network connectivity issues
        - Rate limiting

    Where used: market_data/sql_data_provider.py, langchain_tools/
    """
    pass


class DataNotFoundError(MarketDataError):
    """
    Requested data does not exist.

    Examples:
        - Ticker not in database and fetch failed
        - No historical data available for date range
        - Empty dataset

    Where used: langchain_tools/volatility_tool.py
    """
    pass


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================

class ConfigurationError(DerivativesGPTError):
    """
    Base class for configuration errors.

    Raised when application configuration is invalid or incomplete.

    When to use: Configuration validation failures
    Where used: config.py, llm_provider.py
    """
    pass


class MissingAPIKeyError(ConfigurationError):
    """
    Required API key is missing or invalid.

    Examples:
        - OPENAI_API_KEY not set
        - GEMINI_API_KEY empty
        - Invalid API key format

    Where used: llm_provider.py, rag/hybrid_retriever.py
    """
    pass


class InvalidConfigError(ConfigurationError):
    """
    Configuration values are invalid.

    Examples:
        - Negative max_agent_iterations
        - Invalid LLM provider name
        - File paths don't exist

    Where used: config.py validation
    """
    pass


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

# Alias for backward compatibility with existing code
# TODO: Remove after migration to new exception hierarchy
InvalidParameterError = BlackScholesError
