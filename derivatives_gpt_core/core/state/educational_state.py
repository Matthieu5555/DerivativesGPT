"""
Educational Conversation State
================================
Orthogonal state management for educational agent conversation tracking.

This module contains state specific to educational conversations:
- Topic tracking and continuity
- Conversation mode (initial vs follow-up)
- User interaction state

Separated from pricing_state.py to maintain modularity and keep files under 300 lines.
"""

from typing import Literal
from pydantic import BaseModel, Field


class EducationalConversationState(BaseModel):
    """
    State tracking for educational conversation flow.

    This handles the conversational aspects of educational interactions:
    - Topic continuity detection (same topic vs topic change)
    - Conversation mode (initial structured explanation vs follow-up chat)
    - User interaction state (awaiting questions, etc.)

    Design principle: Orthogonal to pricing concerns.
    """

    # === TOPIC TRACKING ===
    current_topic: str | None = Field(
        default=None,
        description="Current topic being explained (e.g., 'iron condor', 'black-scholes model')"
    )

    initial_topic: str | None = Field(
        default=None,
        description="First topic asked in this educational session (for continuity tracking)"
    )

    topic_changed: bool = Field(
        default=False,
        description="Whether user changed topics (triggers new explanation vs follow-up)"
    )

    # === CONVERSATION MODE ===
    conversation_mode: Literal["initial_explanation", "followup_conversation"] = Field(
        default="initial_explanation",
        description=(
            "Conversation mode:\n"
            "- initial_explanation: First time explaining topic, use full structured template\n"
            "- followup_conversation: Answering follow-up questions, conversational style"
        )
    )

    awaiting_user_followup: bool = Field(
        default=False,
        description="Whether agent delivered explanation and is waiting for user follow-up questions"
    )

    # === FOLLOW-UP CONTEXT ===
    followup_count: int = Field(
        default=0,
        description="Number of follow-up questions asked on current topic"
    )

    last_user_question: str | None = Field(
        default=None,
        description="Last question asked by user (for topic continuity classification)"
    )

    # === TOPIC CONTINUITY CLASSIFICATION ===
    topic_continuity_checked: bool = Field(
        default=False,
        description="Whether topic continuity was checked for current message"
    )

    is_same_topic: bool | None = Field(
        default=None,
        description="LLM classification: Is new question about same topic? (None = not yet classified)"
    )

    is_financial_related: bool | None = Field(
        default=None,
        description="LLM classification: Is question financial/options-related? (for off-topic detection)"
    )

    topic_classification_reasoning: str | None = Field(
        default=None,
        description="LLM reasoning for topic continuity classification"
    )

    # === HUMAN-IN-THE-LOOP UNDERSTANDING CHECKS ===
    awaiting_user_understanding: bool = Field(
        default=False,
        description="Whether agent asked user to explain their understanding and is awaiting response"
    )

    user_explained_understanding: bool = Field(
        default=False,
        description="Whether user's last message was explaining their understanding (vs asking new question)"
    )

    understanding_check_count: int = Field(
        default=0,
        description="Number of understanding checks performed on current topic"
    )

    model_config = {"arbitrary_types_allowed": True}

    def reset_for_new_topic(self, new_topic: str) -> None:
        """
        Reset conversation state when user changes topics.

        Args:
            new_topic: The new topic being asked about
        """
        self.current_topic = new_topic
        if self.initial_topic is None:
            self.initial_topic = new_topic
        self.topic_changed = True
        self.conversation_mode = "initial_explanation"
        self.awaiting_user_followup = False
        self.followup_count = 0
        self.topic_continuity_checked = False
        # Reset understanding check fields
        self.awaiting_user_understanding = False
        self.user_explained_understanding = False
        self.understanding_check_count = 0
        # DON'T reset is_same_topic - it's already been set by classification

    def mark_followup(self) -> None:
        """
        Mark that we're in follow-up conversation mode.

        Called after initial explanation is delivered.
        """
        self.conversation_mode = "followup_conversation"
        self.awaiting_user_followup = True

    def record_followup_question(self, question: str) -> None:
        """
        Record a follow-up question on the current topic.

        Args:
            question: The user's follow-up question
        """
        self.followup_count += 1
        self.last_user_question = question
        self.conversation_mode = "followup_conversation"  # Switch to conversational mode for follow-ups
        self.topic_continuity_checked = False  # Need to check for next message
