"""
Central configuration (backward compatibility wrapper).

This module re-exports components for backward compatibility.
The actual implementation has been refactored into:
- core/config/settings_schema.py: Pydantic Settings model
- core/config/settings_singleton.py: Thread-safe singleton accessor
"""

from derivatives_gpt_core.core.config.settings_schema import Settings
from derivatives_gpt_core.core.config.settings_singleton import get_settings, reset_settings

# ============================================================================
# PARAMETER EXTRACTION VALID VALUES
# ============================================================================
# These define the ONLY valid values for parameter extraction fields.
# Used to constrain LLM output and prevent hallucinated values.

# Option type: ONLY the direction (call or put)
# NOT the full classification like "digital_call" or "american_put"
VALID_OPTION_TYPES = ["call", "put"]

# Asset classes for classification
VALID_ASSET_CLASSES = [
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
]

# Strategy types for multi-leg decomposition
VALID_STRATEGY_TYPES = [
    "single",      # Single option
    "straddle",    # Long call + long put, same strike
    "strangle",    # Long call + long put, different strikes
    "spread",      # Vertical spread (call spread, put spread)
    "butterfly"    # Butterfly spread
]

# For reference: What the option classifier might detect
# These are NOT extracted in parameters - only used for routing
DETECTED_OPTION_CLASSIFICATIONS = [
    "vanilla_call",
    "vanilla_put",
    "american_call",
    "american_put",
    "digital_call",
    "digital_put",
    "geometric_asian_call",
    "geometric_asian_put",
    "educational",
    "unknown"
]

# Re-export for backward compatibility
__all__ = [
    'Settings',
    'get_settings',
    'reset_settings',
    'VALID_OPTION_TYPES',
    'VALID_ASSET_CLASSES',
    'VALID_STRATEGY_TYPES',
    'DETECTED_OPTION_CLASSIFICATIONS'
]
