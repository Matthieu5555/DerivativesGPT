"""Verify understanding node - pure function."""

import json

from langchain_core.messages import AIMessage

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_classification_llm
from prompts.educational.verification import build_verification_prompt


async def verify_understanding(state: EducationalState) -> dict:
    """
    Pure async function: Generate verification questions to check understanding.

    Reads:
        - messages: User's original question
        - explanation_text: Explanation provided to user
        - adaptive_difficulty_level: User's knowledge level

    Writes:
        - verification_questions: List of questions to ask user
        - messages: Appends AI message with verification questions

    Args:
        state: Current graph state

    Returns:
        State updates dict (for immutable update)
    """
    # Extract data from state
    user_query = state.messages[0].content if state.messages else "Unknown question"
    explanation = state.explanation_text or ""
    difficulty = state.adaptive_difficulty_level or "intermediate"

    # Build prompt (pure function)
    prompt = build_verification_prompt(
        query=user_query,
        explanation=explanation,
        difficulty=difficulty,
    )

    # Get LLM response
    llm = get_classification_llm()
    response = await llm.ainvoke(prompt)

    verification_text = response.content if hasattr(response, "content") else str(response)

    # Parse JSON response
    try:
        verification_data = _parse_verification_json(verification_text)
        questions = verification_data.get("verification_questions", [])
    except (json.JSONDecodeError, ValueError):
        # Fallback questions if parsing fails
        questions = ["Can you explain this concept in your own words?"]

    # DON'T show verification questions to user (per user feedback)
    # Just return the explanation without appending questions
    # Store questions in state for potential future use, but don't display them

    # Return immutable state updates
    return {
        "verification_questions": questions,
        "messages": [AIMessage(content=explanation)],
    }


def _parse_verification_json(verification_text: str) -> dict:
    """
    Pure function: Parse verification JSON from LLM response.

    Args:
        verification_text: Raw LLM response

    Returns:
        Parsed verification dict

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    # Extract JSON from markdown code blocks if present
    if "```json" in verification_text:
        start = verification_text.find("```json") + 7
        end = verification_text.find("```", start)
        verification_text = verification_text[start:end].strip()
    elif "```" in verification_text:
        start = verification_text.find("```") + 3
        end = verification_text.find("```", start)
        verification_text = verification_text[start:end].strip()

    return json.loads(verification_text)


def _format_verification_message(questions: list[str]) -> str:
    """
    Pure function: Format verification questions as user-friendly message.

    Args:
        questions: List of verification questions

    Returns:
        Formatted message string
    """
    if not questions:
        return "Does this explanation make sense to you?"

    if len(questions) == 1:
        return f"To check your understanding: {questions[0]}"

    formatted = "To check your understanding, please answer these questions:\n\n"
    for i, question in enumerate(questions, 1):
        formatted += f"{i}. {question}\n"

    return formatted.strip()
