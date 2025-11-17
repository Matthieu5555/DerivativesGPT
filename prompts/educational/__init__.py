"""Educational prompt builders - pure functions."""

from .generation import build_explanation_prompt, format_rag_content, format_web_content
from .critique import build_critique_prompt
from .verification import build_verification_prompt
from .rewriting import build_rewriting_prompt
from .topic_continuity import build_topic_continuity_prompt

__all__ = [
    "build_explanation_prompt",
    "format_rag_content",
    "build_critique_prompt",
    "build_verification_prompt",
    "build_rewriting_prompt",
    "build_topic_continuity_prompt",
]
