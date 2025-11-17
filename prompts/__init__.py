"""
Centralized prompt templates for DerivativesGPT agent nodes.

This module provides separation of concerns between prompt configuration
and agent logic. All system prompts are defined here and imported by
their respective graph nodes.

Module Structure:
- classification_prompts.py: Prompts for classify_intent node
- pricing_prompts.py: Prompts for calculate_option_price node
- narration_prompts.py: Prompts for narrate_execution node

Usage:
    from prompts.pricing_prompts import PRICING_SYSTEM_PROMPT
"""

from prompts.pricing_prompts import PRICING_SYSTEM_PROMPT
from prompts.classification import CLASSIFICATION_SYSTEM_PROMPT  # Reorganized into classification/
from prompts.narration_prompts import NARRATION_SYSTEM_PROMPT

__all__ = [
    "PRICING_SYSTEM_PROMPT",
    "CLASSIFICATION_SYSTEM_PROMPT",
    "NARRATION_SYSTEM_PROMPT",
]
