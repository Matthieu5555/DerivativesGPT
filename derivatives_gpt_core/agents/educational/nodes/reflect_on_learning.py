"""
Reflection node - summarize learning and suggest next steps.

Pure function node that generates a learning summary after explanation is complete.
Similar to an essay conclusion, but for educational content.
"""

import logging
from typing import Any

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_narrator_llm
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)


REFLECTION_PROMPT = """You are an educational AI helping a student reflect on what they've just learned.

TOPIC COVERED: {topic}

KEY CONCEPTS EXPLAINED:
{explanation_summary}

VERIFICATION QUESTIONS ASKED:
{verification_questions}

TASK:
Create a brief, encouraging learning summary that includes:

1. **Key Takeaways** (2-3 bullet points)
   - What are the most important points to remember?

2. **Common Pitfalls** (1-2 bullet points)
   - What mistakes do beginners often make with this concept?

3. **Next Steps** (2-3 suggestions)
   - What related topics should they explore next?
   - How can they apply this knowledge?

Keep the tone encouraging and constructive. Be concise (≤200 words total).

Generate the reflection:"""


async def reflect_on_learning(state: EducationalState) -> dict[str, Any]:
    """
    Generate a learning reflection summary.

    This node executes after the explanation is complete and creates:
    - Key takeaways from the explanation
    - Common pitfalls to avoid
    - Suggested next topics to explore

    Args:
        state: Current educational state with completed explanation

    Returns:
        Dict with reflection message added to conversation
    """
    logger.info("Generating learning reflection")

    # Extract topic and summary
    topic = state.educational_context.current_topic or "this concept"
    explanation_summary = _extract_key_points(state.explanation_text)

    # Format verification questions if they exist
    verification_qs = state.verification_questions or []
    questions_text = "\n".join(f"- {q}" for q in verification_qs) if verification_qs else "None generated"

    # Build prompt
    prompt = REFLECTION_PROMPT.format(
        topic=topic,
        explanation_summary=explanation_summary,
        verification_questions=questions_text
    )

    # Generate reflection
    llm = get_narrator_llm()
    try:
        reflection = await llm.ainvoke(prompt)
        reflection_text = reflection.content if hasattr(reflection, 'content') else str(reflection)

        logger.info(f"Learning reflection generated ({len(reflection_text)} chars)")

        # Create reflection message
        reflection_message = AIMessage(
            content=f"\n\n---\n\n## Learning Reflection\n\n{reflection_text}",
            name="reflection"
        )

        return {
            "messages": [reflection_message],
            "learning_reflection": reflection_text
        }

    except Exception as e:
        logger.error(f"Failed to generate reflection: {e}")
        # Return empty reflection on failure (non-critical)
        return {}


def _extract_key_points(explanation: str | None) -> str:
    """
    Extract first 500 characters of explanation as summary.

    Args:
        explanation: Full explanation text

    Returns:
        Truncated summary
    """
    if not explanation:
        return "No explanation provided"

    # Get first 500 chars (roughly TL;DR section)
    summary = explanation[:500]
    if len(explanation) > 500:
        summary += "..."

    return summary
