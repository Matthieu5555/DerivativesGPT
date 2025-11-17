"""Assess user comprehension node - pure function."""

import json

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_classification_llm
from prompts.educational.verification import build_assessment_prompt


async def assess_comprehension(state: EducationalState) -> dict:
    """
    Pure async function: Assess user's answer to verification questions.

    Reads:
        - messages: User's answer (last message)
        - verification_questions: Questions that were asked
        - explanation_text: Original explanation

    Writes:
        - user_understanding_score: Score 1-5
        - user_comprehension_assessment: Full assessment dict
        - user_confusion_signals: Identified gaps/misconceptions

    Args:
        state: Current graph state

    Returns:
        State updates dict (for immutable update)
    """
    # Extract data from state
    user_answer = state.messages[-1].content if state.messages else ""
    verification_questions = state.verification_questions or []
    explanation = state.explanation_text or ""

    # Use first verification question for assessment prompt
    verification_question = verification_questions[0] if verification_questions else "Unknown question"

    # Build prompt (pure function)
    prompt = build_assessment_prompt(
        verification_question=verification_question,
        user_answer=user_answer,
        original_explanation=explanation,
    )

    # Get LLM assessment
    llm = get_classification_llm()
    response = await llm.ainvoke(prompt)

    assessment_text = response.content if hasattr(response, "content") else str(response)

    # Parse JSON response
    try:
        assessment_data = _parse_assessment_json(assessment_text)
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback if parsing fails
        assessment_data = {
            "understanding_score": 3,
            "demonstrates_understanding": True,
            "assessment_rationale": f"Parse error: {str(e)}",
            "identified_gaps": "Unable to assess",
            "identified_misconceptions": "",
        }

    # Extract confusion signals
    confusion_signals = []
    if assessment_data.get("identified_gaps"):
        confusion_signals.append(assessment_data["identified_gaps"])
    if assessment_data.get("identified_misconceptions"):
        confusion_signals.append(assessment_data["identified_misconceptions"])

    # Return immutable state updates
    return {
        "user_understanding_score": float(assessment_data.get("understanding_score", 3)),
        "user_comprehension_assessment": assessment_data,
        "user_confusion_signals": confusion_signals,
    }


def _parse_assessment_json(assessment_text: str) -> dict:
    """
    Pure function: Parse assessment JSON from LLM response.

    Args:
        assessment_text: Raw LLM response

    Returns:
        Parsed assessment dict

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    # Extract JSON from markdown code blocks if present
    if "```json" in assessment_text:
        start = assessment_text.find("```json") + 7
        end = assessment_text.find("```", start)
        assessment_text = assessment_text[start:end].strip()
    elif "```" in assessment_text:
        start = assessment_text.find("```") + 3
        end = assessment_text.find("```", start)
        assessment_text = assessment_text[start:end].strip()

    return json.loads(assessment_text)
