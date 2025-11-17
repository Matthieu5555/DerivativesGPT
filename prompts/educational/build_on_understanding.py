"""Prompts for building on user understanding (human-in-the-loop)."""


def build_targeted_response_prompt(
    topic: str,
    original_explanation: str,
    user_explanation: str,
    understanding_score: float,
    identified_gaps: list[str],
    assessment: dict,
) -> str:
    """
    Build prompt for generating targeted response based on user's understanding.

    This implements the human-in-the-loop Socratic method - building on what
    the user understood and addressing gaps conversationally.

    Args:
        topic: The topic being explained
        original_explanation: Our original explanation
        user_explanation: User's explanation of what they understood
        understanding_score: Score 1-5 from assessment
        identified_gaps: List of gaps or misconceptions
        assessment: Full assessment dict

    Returns:
        Formatted prompt string
    """
    gaps_section = ""
    if identified_gaps:
        gaps_list = "\n".join(f"  - {gap}" for gap in identified_gaps)
        gaps_section = f"""
**Identified Gaps/Misconceptions:**
{gaps_list}
"""

    prompt = f"""You are an expert derivatives educator using the Socratic method. A student just explained their understanding of {topic}, and you need to build on it conversationally.

**Your Original Explanation:**
{original_explanation[:1000]}...

**Student's Explanation:**
{user_explanation}

**Assessment:**
- Understanding Score: {understanding_score}/5.0
- Demonstrates Understanding: {assessment.get('demonstrates_understanding', True)}
- Rationale: {assessment.get('assessment_rationale', 'N/A')}

{gaps_section}

**Your Task:**
Generate a conversational, encouraging response that:

1. **Acknowledges** what they got right (be specific and genuine)
2. **Addresses gaps/misconceptions** if any exist (gently correct, don't criticize)
3. **Builds on their understanding** by adding the next layer of depth or connecting to practical examples
4. **Asks a probing question** or invites them to explore further (keep the dialogue going)

**Tone:**
- Conversational and encouraging
- Like explaining to a smart colleague over coffee
- Use "you" and "we"
- Relate to practical trading scenarios when relevant
- NO structured sections (no "TL;DR", no bullet points unless natural)
- NO emojis

**Format:**
- Natural flowing paragraphs
- 3-5 paragraphs maximum
- End with a question or invitation to continue

**Example Response Style:**
"Great! You've got the core idea - delta really is that sensitivity measure. I like how you connected it to the speed analogy.

One thing to refine though: when you said delta stays constant, that's where gamma comes in. Delta actually changes as the stock price moves. Think about that AAPL call at $200 strike - when AAPL is at $150, delta might be 0.20. But if AAPL rallies to $195, delta could jump to 0.70. It's not fixed.

This is crucial for hedging. If you sold that call and hedged with stock, your hedge breaks down as AAPL moves because delta keeps changing. That's why traders need to rebalance - they're constantly adjusting for that delta drift.

Want to explore how this affects your hedging strategy when you're managing a short call position?"

Generate your response now:"""

    return prompt
