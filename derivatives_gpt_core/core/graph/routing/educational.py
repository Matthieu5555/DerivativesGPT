"""
Educational Agent Routing Logic
================================
Routing functions for educational agent flow.
"""

import logging
from derivatives_gpt_core.agents.shared.base_state import BaseAgentState

logger = logging.getLogger(__name__)

# Type for node names
NodeName = str


def route_educational_query(state: BaseAgentState) -> NodeName:
    """
    Routing within educational agent flow.

    Educational flow:
    1. Check if RAG needed
    2. Generate explanation
    3. Assess quality
    4. Verify understanding
    5. Rewrite if needed

    Args:
        state: Current state (should have educational fields accessible)

    Returns:
        Next node name in educational flow
    """
    # Create educational wrapper for safe field access
    from derivatives_gpt_core.core.state.state_factory import create_educational_state
    wrapped = create_educational_state(state)

    # Check if we have an explanation already
    explanation = wrapped.get_field("explanation_text")

    if not explanation:
        # Need to generate explanation
        # First check if we need RAG
        rag_sources = wrapped.get_field("rag_sources")

        if not rag_sources:
            logger.info("Educational agent: Need RAG retrieval")
            return "educational_rag_retrieval"
        else:
            logger.info("Educational agent: Generate explanation")
            return "generate_explanation"

    # We have an explanation - check quality
    quality_score = wrapped.get_field("explanation_quality_score", 0)

    if quality_score == 0:
        # Need to assess quality
        logger.info("Educational agent: Assess explanation quality")
        return "assess_explanation_quality"

    elif quality_score < 0.7:
        # Quality too low - check attempts
        attempts = wrapped.get_field("explanation_attempt_count", 0)

        if attempts >= 3:
            logger.warning("Educational agent: Max attempts reached, returning current explanation")
            return "finalize_explanation"
        else:
            logger.info("Educational agent: Rewrite explanation (quality too low)")
            return "rewrite_explanation"

    # Quality is good - check if user understanding verified
    understanding_score = wrapped.get_field("user_understanding_score")

    if understanding_score is None:
        # Need to verify understanding
        verification_questions = wrapped.get_field("verification_questions", [])

        if not verification_questions:
            logger.info("Educational agent: Generate verification questions")
            return "generate_verification_questions"
        else:
            logger.info("Educational agent: Explanation complete, awaiting user response")
            return "finalize_explanation"

    # Understanding verified
    logger.info("Educational agent: Complete")
    return "finalize_explanation"


def route_after_explanation_quality(state: BaseAgentState) -> NodeName:
    """
    Route after explanation quality assessment.

    Routes:
    - High quality (≥0.7) → verify_understanding
    - Low quality (<0.7) → rewrite_explanation (if attempts < max)
    - Max attempts → finalize (accept current)

    Args:
        state: State with explanation_quality_score

    Returns:
        Next node name
    """
    from derivatives_gpt_core.core.state.state_factory import create_educational_state
    wrapped = create_educational_state(state)

    quality_score = wrapped.get_field("explanation_quality_score", 0)
    attempts = wrapped.get_field("explanation_attempt_count", 0)

    if quality_score >= 0.7:
        logger.info(f"Explanation quality good ({quality_score:.2f}), proceeding to verification")
        return "generate_verification_questions"
    elif attempts >= 3:
        logger.warning(f"Max attempts reached, accepting current explanation (quality: {quality_score:.2f})")
        return "finalize_explanation"
    else:
        logger.info(f"Explanation quality low ({quality_score:.2f}), rewriting (attempt {attempts + 1}/3)")
        return "rewrite_explanation"
