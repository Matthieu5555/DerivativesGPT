"""Explanation critique prompts - pure functions."""


def build_critique_prompt(
    query: str,
    explanation: str,
    difficulty: str,
) -> str:
    """
    Pure function: Build critique prompt for self-evaluation.

    Args:
        query: Original user question
        explanation: Generated explanation to critique
        difficulty: Target difficulty level

    Returns:
        Formatted critique prompt
    """
    prompt = f"""You are a critical reviewer of educational content about financial derivatives.

USER QUESTION: {query}

DIFFICULTY LEVEL: {difficulty}

EXPLANATION TO EVALUATE:
{explanation}

TASK:
Evaluate this explanation on the following criteria (score each 1-5):

1. **Clarity** (1-5): Is the explanation easy to understand?
   - 5: Crystal clear, perfectly understandable
   - 3: Somewhat clear but has confusing parts
   - 1: Very confusing or unclear

2. **Accuracy** (1-5): Is the information factually correct?
   - 5: Completely accurate, no errors
   - 3: Mostly accurate with minor issues
   - 1: Contains significant errors

3. **Completeness** (1-5): Does it fully answer the question?
   - 5: Comprehensive, addresses all aspects
   - 3: Addresses main points but misses some details
   - 1: Incomplete or misses key points

4. **Pedagogical Effectiveness** (1-5): Will this help the user learn?
   - 5: Excellent teaching approach with examples
   - 3: Decent but could use better examples
   - 1: Poor teaching, hard to learn from

5. **Appropriate for Level** (1-5): Matches the {difficulty} difficulty?
   - 5: Perfect match for {difficulty} level
   - 3: Somewhat appropriate but not ideal
   - 1: Too simple or too complex for this level

RESPOND IN THIS EXACT JSON FORMAT:
{
  "clarity": <score>,
  "accuracy": <score>,
  "completeness": <score>,
  "pedagogical_effectiveness": <score>,
  "appropriate_for_level": <score>,
  "average_score": <average of all scores>,
  "strengths": "<brief description of what works well>",
  "weaknesses": "<brief description of what needs improvement>",
  "specific_improvements": "<concrete suggestions for improvement>"
}

Provide your evaluation:"""

    return prompt
