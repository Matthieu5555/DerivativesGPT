"""
Educational Agent State
========================
State for educational agent with explanation generation and conversation tracking.

Inherits from BaseAgentState and adds educational-specific fields:
- Explanation generation and quality
- User comprehension assessment
- Conversation tracking (topic continuity, follow-ups)
"""

from typing import Literal
from pydantic import Field

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.core.state.educational_state import EducationalConversationState


class EducationalState(BaseAgentState):
    """
    State for educational agent.

    Extends BaseAgentState with:
    - Explanation generation and quality assessment
    - User comprehension tracking
    - Conversation state (topic continuity, follow-ups)
    """

    # === EXPLANATION GENERATION ===
    explanation_text: str | None = Field(
        default=None,
        description="Generated educational explanation"
    )
    explanation_quality_score: float | None = Field(
        default=None,
        description="Critic's evaluation of explanation quality (1-5)"
    )
    explanation_attempt_count: int = Field(
        default=0,
        description="Number of explanation generation attempts"
    )
    explanation_critique: dict | None = Field(
        default=None,
        description="Full critique feedback (scores, strengths, weaknesses)"
    )

    # === USER COMPREHENSION ===
    verification_questions: list[str] = Field(
        default_factory=list,
        description="Questions to verify user understanding"
    )
    user_understanding_score: float | None = Field(
        default=None,
        description="Assessment of user's comprehension (1-5)"
    )
    user_comprehension_assessment: dict | None = Field(
        default=None,
        description="Full comprehension assessment (score, gaps, misconceptions)"
    )
    user_confusion_signals: list[str] = Field(
        default_factory=list,
        description="Identified gaps or misconceptions from user's responses"
    )
    adaptive_difficulty_level: Literal["beginner", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="User's knowledge level for adaptive explanations"
    )

    # === LEARNING REFLECTION ===
    learning_reflection: str | None = Field(
        default=None,
        description="Learning summary with key takeaways, pitfalls, and next steps"
    )

    # === CONVERSATION TRACKING (ORTHOGONAL MODULE) ===
    educational_context: EducationalConversationState = Field(
        default_factory=EducationalConversationState,
        description="Educational conversation tracking: topic continuity, mode, follow-ups"
    )
