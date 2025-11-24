"""Understanding verification prompts - pure functions."""


def build_verification_prompt(
    query: str,
    explanation: str,
    difficulty: str,
) -> str:
    """
    Pure function: Build prompt for generating verification questions.

    Args:
        query: Original user question
        explanation: Explanation provided to user
        difficulty: User's knowledge level

    Returns:
        Formatted verification prompt
    """
    prompt = f"""You are an expert educator assessing student understanding.

USER'S ORIGINAL QUESTION: {query}

EXPLANATION PROVIDED:
{explanation}

DIFFICULTY LEVEL: {difficulty}

TASK:
Generate 1-2 follow-up questions to verify the user understands the explanation.

QUESTION TYPES:
1. **Comprehension Check**: Ask user to explain the concept in their own words
   - "Can you explain what [concept] means in your own words?"
   - "How would you describe [concept] to a friend?"

2. **Application Question**: Ask user to apply the concept
   - "If [scenario], what would happen to [concept]?"
   - "How would you use this concept in [practical situation]?"

GUIDELINES:
- For "beginner": Ask simple comprehension questions with clear scenarios
- For "intermediate": Ask application questions with realistic examples
- For "advanced": Ask analytical questions requiring deeper reasoning
- Keep questions concise and focused
- Questions should help identify if user truly understood

RESPOND IN THIS EXACT FORMAT:
{
  "verification_questions": [
    "Your first question here?",
    "Your second question here?"
  ],
  "rationale": "Brief explanation of what these questions will verify"
}

Generate verification questions:"""

    return prompt


def build_assessment_prompt(
    verification_question: str,
    user_answer: str,
    original_explanation: str,
) -> str:
    """
    Pure function: Build prompt for assessing user's answer.

    Args:
        verification_question: Question asked to user
        user_answer: User's response
        original_explanation: Original explanation provided

    Returns:
        Formatted assessment prompt
    """
    prompt = f"""You are an expert educator assessing student comprehension.

VERIFICATION QUESTION ASKED: {verification_question}

USER'S ANSWER:
{user_answer}

ORIGINAL EXPLANATION (FOR REFERENCE):
{original_explanation}

TASK:
Assess whether the user's answer demonstrates understanding of the concept.

SCORING RUBRIC:
- **5**: Excellent understanding - answer is accurate, complete, shows deep comprehension
- **4**: Good understanding - answer is mostly accurate with minor gaps
- **3**: Partial understanding - answer shows some comprehension but has significant gaps or misconceptions
- **2**: Limited understanding - answer shows confusion or misunderstanding of key concepts
- **1**: No understanding - answer is completely off-track or nonsensical

RESPOND IN THIS EXACT JSON FORMAT:
{
  "understanding_score": <1-5>,
  "demonstrates_understanding": <true/false>,
  "assessment_rationale": "<brief explanation of the score>",
  "identified_gaps": "<what the user still doesn't understand, if any>",
  "identified_misconceptions": "<any incorrect beliefs the user has, if any>"
}

Provide your assessment:"""

    return prompt
