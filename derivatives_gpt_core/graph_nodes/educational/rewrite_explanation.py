"""Rewrite explanation node - pure function."""

from langchain_core.messages import AIMessage

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_narrator_llm
from prompts.educational.rewriting import build_rewriting_prompt


async def rewrite_explanation(state: EducationalState) -> dict:
    """
    Pure async function: Rewrite explanation based on critique or user confusion.

    Reads:
        - messages: User's original question
        - explanation_text: Previous explanation
        - explanation_critique: Critique feedback
        - user_confusion_signals: Gaps identified from user's response
        - adaptive_difficulty_level: Target difficulty level

    Writes:
        - explanation_text: Improved explanation
        - messages: Appends AI message with improved explanation

    Args:
        state: Current graph state

    Returns:
        State updates dict (for immutable update)
    """
    # Extract data from state
    user_query = state.messages[0].content if state.messages else "Unknown question"
    previous_explanation = state.explanation_text or ""
    critique_feedback = state.explanation_critique or {}
    confusion_signals = state.user_confusion_signals or []
    difficulty = state.adaptive_difficulty_level or "intermediate"

    # Combine confusion signals into user gaps description
    user_gaps = "\n".join(confusion_signals) if confusion_signals else None

    # Build prompt (pure function)
    prompt = build_rewriting_prompt(
        query=user_query,
        previous_explanation=previous_explanation,
        critique_feedback=critique_feedback,
        user_gaps=user_gaps,
        difficulty=difficulty,
    )

    # Get LLM response
    llm = get_narrator_llm()  # Use narrator LLM for quality explanations
    response = await llm.ainvoke(prompt)

    improved_explanation = response.content if hasattr(response, "content") else str(response)

    # Return immutable state updates
    return {
        "explanation_text": improved_explanation,
        "messages": [AIMessage(content=improved_explanation)],
    }
