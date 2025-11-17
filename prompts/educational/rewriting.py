"""Explanation rewriting prompts - pure functions."""


def build_rewriting_prompt(
    query: str,
    previous_explanation: str,
    critique_feedback: dict,
    user_gaps: str | None,
    difficulty: str,
) -> str:
    """
    Pure function: Build prompt for rewriting explanation.

    Args:
        query: Original user question
        previous_explanation: Previous explanation that needs improvement
        critique_feedback: Feedback from critic node
        user_gaps: Identified gaps from user's response (if verification failed)
        difficulty: Target difficulty level

    Returns:
        Formatted rewriting prompt
    """
    critique_section = f"""
CRITIQUE FEEDBACK:
- Average Quality Score: {critique_feedback.get('average_score', 'N/A')}/5
- Strengths: {critique_feedback.get('strengths', 'N/A')}
- Weaknesses: {critique_feedback.get('weaknesses', 'N/A')}
- Specific Improvements Needed: {critique_feedback.get('specific_improvements', 'N/A')}
"""

    user_gaps_section = ""
    if user_gaps:
        user_gaps_section = f"""
USER COMPREHENSION GAPS (from verification):
{user_gaps}

CRITICAL: Address these specific gaps in your rewrite!
"""

    prompt = f"""You are an expert financial educator improving an explanation.

USER QUESTION: {query}

DIFFICULTY LEVEL: {difficulty}

PREVIOUS EXPLANATION (NEEDS IMPROVEMENT):
{previous_explanation}
{critique_section}
{user_gaps_section}

TASK:
Rewrite the explanation to address the identified issues while maintaining accuracy.

REWRITING GUIDELINES:
1. Keep what worked well (from strengths)
2. Directly address the weaknesses and specific improvements mentioned
3. If user gaps identified, explicitly address those misunderstandings
4. Use different examples or analogies than before
5. Break down complex ideas into simpler steps
6. Ensure appropriate language for {difficulty} level
7. Maintain the same structure: definition → intuition → example → application

RESPOND WITH:
An improved explanation that directly addresses the feedback. Do NOT include meta-commentary about the rewrite process.

Begin your improved explanation:"""

    return prompt
