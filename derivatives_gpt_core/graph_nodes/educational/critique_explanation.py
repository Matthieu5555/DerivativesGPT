"""Critique explanation node - pure function."""

import json

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_classification_llm
from prompts.educational.critique import build_critique_prompt


async def critique_explanation(state: EducationalState) -> dict:
    """
    Pure async function: Critique explanation quality.

    Reads:
        - messages: User's original question
        - explanation_text: Explanation to critique
        - adaptive_difficulty_level: Target difficulty level

    Writes:
        - explanation_quality_score: Average score (1-5)
        - explanation_critique: Full critique feedback dict

    Args:
        state: Current graph state

    Returns:
        State updates dict (for immutable update)
    """
    # Extract data from state
    user_query = state.messages[-1].content if state.messages else "Unknown question"
    explanation = state.explanation_text or ""
    difficulty = state.adaptive_difficulty_level or "intermediate"

    # Build prompt (pure function)
    prompt = build_critique_prompt(
        query=user_query,
        explanation=explanation,
        difficulty=difficulty,
    )

    # Get LLM critique
    llm = get_classification_llm()  # Use cost-effective model for critique
    response = await llm.ainvoke(prompt)

    critique_text = response.content if hasattr(response, "content") else str(response)

    # Parse JSON response
    try:
        critique_data = _parse_critique_json(critique_text)
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback if parsing fails
        critique_data = {
            "average_score": 3.0,
            "strengths": "Unable to parse critique",
            "weaknesses": f"Parse error: {str(e)}",
            "specific_improvements": "Reformat critique as valid JSON",
        }

    # Return immutable state updates
    return {
        "explanation_quality_score": critique_data.get("average_score", 3.0),
        "explanation_critique": critique_data,
    }


def _parse_critique_json(critique_text: str) -> dict:
    """
    Pure function: Parse critique JSON from LLM response.

    Args:
        critique_text: Raw LLM response

    Returns:
        Parsed critique dict

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    # Extract JSON from markdown code blocks if present
    if "```json" in critique_text:
        start = critique_text.find("```json") + 7
        end = critique_text.find("```", start)
        critique_text = critique_text[start:end].strip()
    elif "```" in critique_text:
        start = critique_text.find("```") + 3
        end = critique_text.find("```", start)
        critique_text = critique_text[start:end].strip()

    return json.loads(critique_text)
