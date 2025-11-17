"""
Evaluation Prompts

Prompts used for LLM-as-a-judge evaluation.
"""

from prompts.evaluation.llm_judge_prompts import (
    CORRECTNESS_PROMPT,
    COMPLETENESS_PROMPT,
    CLARITY_PROMPT,
    RAG_QUALITY_PROMPT
)

__all__ = [
    "CORRECTNESS_PROMPT",
    "COMPLETENESS_PROMPT",
    "CLARITY_PROMPT",
    "RAG_QUALITY_PROMPT",
]
