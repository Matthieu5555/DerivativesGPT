"""Topic continuity classification prompts - pure functions."""


def build_topic_continuity_prompt(
    current_question: str,
    previous_topic: str | None,
    previous_question: str | None,
    previous_explanation: str | None = None,
) -> str:
    """
    Pure function: Build prompt for classifying topic continuity.

    Determines:
    1. Is the new question about the same topic as before?
    2. Is it still financial/options-related?

    Args:
        current_question: User's current question
        previous_topic: Previously discussed topic (e.g., "iron condor")
        previous_question: User's previous question (for context)
        previous_explanation: Preview of previous explanation (for reference detection)

    Returns:
        Formatted classification prompt
    """
    context_section = ""
    if previous_topic and previous_question:
        context_section = f"""
PREVIOUS CONTEXT:
- Previous topic: {previous_topic}
- Previous question: {previous_question}
"""
        if previous_explanation:
            # Include first 300 chars of explanation for reference detection
            preview = previous_explanation[:300] + "..." if len(previous_explanation) > 300 else previous_explanation
            context_section += f"""- Previous explanation preview: {preview}
"""
    elif previous_topic:
        context_section = f"""
PREVIOUS CONTEXT:
- Previous topic: {previous_topic}
"""
    else:
        context_section = """
PREVIOUS CONTEXT:
- This is the first question in the conversation
"""

    prompt = f"""You are an expert conversation analyst specializing in financial education dialogues.

Your task is to determine whether the current question continues the previous topic or starts a new topic.

You MUST classify the question along two dimensions:
1. Topic continuity (same vs different topic)
2. Domain relevance (financial vs off-topic)

{context_section}

CURRENT QUESTION:
{current_question}

###CLASSIFICATION RULES###

**SAME TOPIC (is_same_topic: true)** if:
- Asking for clarification on the previous topic
- Diving deeper into a specific aspect mentioned before
- Asking "why", "how", "can you explain more about X" where X was discussed
- Requesting examples or applications of the previous concept
- Comparing previous topic with related concepts
- Using pronouns like "it", "this", "that" referring to previous explanation
- Saying "explain that differently", "can you give an example", "what did you mean by..."

Examples:
- Previous: "iron condor", Current: "What's the max loss on an iron condor?" → SAME
- Previous: "Black-Scholes", Current: "How do you calculate d1 and d2?" → SAME
- Previous: "straddle", Current: "When should I use a straddle vs strangle?" → SAME (comparing related concepts)
- Previous: "delta", Current: "Can you explain that differently?" → SAME (pronoun reference)
- Previous: "implied volatility", Current: "Give me an example" → SAME (requesting example of previous topic)

**DIFFERENT TOPIC (is_same_topic: false)** if:
- Asking about a completely different strategy/concept
- Switching from one derivatives type to another unrelated one
- Moving to a different area of finance

Examples:
- Previous: "iron condor", Current: "Explain variance swaps" → DIFFERENT
- Previous: "call options", Current: "What is the VIX?" → DIFFERENT (related but different topic)

**FINANCIAL-RELATED (is_financial_related: true)** if:
- About options, derivatives, pricing models, strategies, risk management
- About financial markets, volatility, Greeks, trading
- About quantitative finance, stochastic calculus applied to finance

**OFF-TOPIC (is_financial_related: false)** if:
- About weather, sports, general knowledge unrelated to finance
- Personal advice not about financial concepts
- General chitchat

RESPOND IN THIS EXACT JSON FORMAT:
{
  "is_same_topic": <true or false>,
  "is_financial_related": <true or false>,
  "extracted_topic": "<concise topic name from current question>",
  "reasoning": "<brief explanation of your classification>"
}

IMPORTANT:
- If this is the FIRST question (no previous context), always return is_same_topic: false
- Be strict: only mark is_same_topic: true if genuinely a follow-up
- Extract a concise topic name (e.g., "iron condor", "Black-Scholes model", "delta hedging")

Provide your classification:"""

    return prompt
