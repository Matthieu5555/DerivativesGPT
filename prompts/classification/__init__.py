"""
Classification prompts module.

Re-exports all classification prompts for backward compatibility.
Code that imports from prompts.classification_prompts will continue to work.
"""

from prompts.classification.intent import INITIAL_CLASSIFICATION_PROMPT
from prompts.classification.contextual import CLASSIFICATION_SYSTEM_PROMPT
from prompts.classification.asset_type import ASSET_CLASSIFICATION_PROMPT
from prompts.classification.option_type import OPTION_CLASSIFICATION_PROMPT

__all__ = [
    "INITIAL_CLASSIFICATION_PROMPT",
    "CLASSIFICATION_SYSTEM_PROMPT",
    "ASSET_CLASSIFICATION_PROMPT",
    "OPTION_CLASSIFICATION_PROMPT",
]
