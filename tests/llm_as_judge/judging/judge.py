"""LLM-as-a-judge implementation - pure async functions."""

import json
from typing import Any

from tests.llm_as_judge.datasets.test_questions import TestQuestion
from prompts.evaluation.llm_judge_prompts import STATE_ALIGNMENT_PROMPT


async def evaluate_response(
    question: TestQuestion,
    agent_response: dict[str, Any],
    judge_llm: Any,
) -> dict[str, Any]:
    """
    Pure async function: Evaluate agent response against rubric and state alignment.

    NEW APPROACH: Primary evaluation is state-response alignment
    - Does the response match the expected graph state?
    - Educational query → Educational response
    - Pricing query → Pricing response
    - Off-topic → Polite refusal
    - Exotic → Recognize but refuse

    Args:
        question: Test question with rubric and expected_graph_state
        agent_response: Agent's output state
        judge_llm: LLM instance for judging

    Returns:
        Evaluation result dict with scores and rationale
    """
    # Extract response text
    messages = agent_response.get("messages", [])
    last_message = messages[-1].content if messages else "No response"

    # STEP 1: Evaluate state alignment (most critical)
    state_alignment_prompt = STATE_ALIGNMENT_PROMPT.format(
        query=question["question"],
        response=last_message,
        expected_state=question.get("expected_graph_state", "unknown")
    )

    state_judge_output = await judge_llm.ainvoke(state_alignment_prompt)
    state_judge_text = state_judge_output.content if hasattr(state_judge_output, "content") else str(state_judge_output)

    # Parse state alignment score
    try:
        state_result = parse_simple_judge_response(state_judge_text)
        state_score = state_result["score"] / 5.0  # Normalize to 0-1
        state_reasoning = state_result["reasoning"]
    except (json.JSONDecodeError, ValueError, KeyError):
        state_score = 0.5
        state_reasoning = "Failed to parse state alignment evaluation"

    # STEP 2: Evaluate against rubric (for detailed criteria)
    prompt = build_judge_prompt(
        question=question["question"],
        expected_behavior=question["expected_behavior"],
        response=agent_response,
        rubric=question["rubric"],
    )

    judge_output = await judge_llm.ainvoke(prompt)
    judge_text = judge_output.content if hasattr(judge_output, "content") else str(judge_output)

    # Parse rubric scores
    try:
        rubric_scores = parse_judge_response(judge_text, question["rubric"])
    except (json.JSONDecodeError, ValueError):
        rubric_scores = {
            key: {"score": 0.5, "rationale": "Parse error"}
            for key in question["rubric"].keys()
        }

    # Calculate rubric score
    rubric_score = calculate_weighted_score(rubric_scores, question["rubric"])

    # STEP 3: Combined overall score (state alignment is 50%, rubric is 50%)
    overall_score = (state_score * 0.5) + (rubric_score * 0.5)

    return {
        "question_id": question["id"],
        "category": question["category"],
        "overall_score": overall_score,
        "state_alignment_score": state_score,
        "state_alignment_reasoning": state_reasoning,
        "rubric_score": rubric_score,
        "category_scores": rubric_scores,
        "passed": overall_score >= question["min_passing_score"],
        "judge_feedback": extract_feedback(judge_text),
    }


def build_judge_prompt(
    question: str,
    expected_behavior: str,
    response: dict[str, Any],
    rubric: dict[str, dict],
) -> str:
    """
    Pure function: Build judge evaluation prompt.

    Args:
        question: User's question
        response: Agent's response state
        rubric: Evaluation rubric

    Returns:
        Formatted prompt string
    """
    # Extract relevant fields from response
    messages = response.get("messages", [])
    last_message = messages[-1].content if messages else "No response"

    # Format rubric for prompt
    rubric_text = ""
    for i, (key, criteria) in enumerate(rubric.items(), 1):
        rubric_text += f"""
{i}. **{key}** (weight: {criteria['weight']})
   - Expected: {criteria.get('expected', 'N/A')}
   - Score 1.0 if criterion met, 0.0-0.5 for partial, 0.0 if not met
"""

    prompt = f"""You are evaluating an AI agent's response to a financial derivatives question.

USER QUESTION: {question}

EXPECTED BEHAVIOR: {expected_behavior}

AGENT'S RESPONSE:
{last_message}

AGENT STATE (for verification):
- Ticker: {response.get('ticker', 'None')} (extracted: {response.get('extracted_ticker', 'None')})
- Option type: {response.get('option_type', 'None')} (classified: {response.get('option_type_classified', 'None')})
- Strike price: {response.get('strike_price', 'None')}
- Time to expiry: {response.get('time_to_expiry_days', 'None')} days
- Option price: {response.get('option_price', 'None')}
- Extraction successful: {response.get('extraction_successful', 'None')}
- Can execute: {response.get('can_execute', 'None')}
- Used RAG: {bool(response.get('rag_sources'))}

EVALUATION RUBRIC:
{rubric_text}

INSTRUCTIONS - SCORING RULES (BE DIRECT):
- Each criterion is a YES/NO check based on agent state
- If the expected value is present in agent state = score 1.0
- If the expected value is NOT present in agent state = score 0.0
- NO PARTIAL SCORES unless criterion explicitly requires quality judgment
- Example: "extracted_ticker: AAPL" in state = 1.0, period. Not 0.8, not 0.6, but 1.0
- Example: "pricing_completed: True" in state = 1.0, period
- If you say "successfully extracted" or "performed excellently", the score MUST be 1.0
- Be objective and consistent: either criterion met (1.0) or not met (0.0)

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "scores": {{
    "{list(rubric.keys())[0]}": {{"score": <0.0-1.0>, "rationale": "<brief reason>"}},
    ...
  }},
  "overall_feedback": "<summary of agent performance>"
}}

Provide your evaluation:"""

    return prompt


def parse_judge_response(judge_text: str, rubric: dict) -> dict[str, dict]:
    """
    Pure function: Parse judge's JSON response.

    Args:
        judge_text: Raw LLM response
        rubric: Original rubric for validation

    Returns:
        Parsed scores dict

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    # Extract JSON from markdown code blocks if present
    if "```json" in judge_text:
        start = judge_text.find("```json") + 7
        end = judge_text.find("```", start)
        judge_text = judge_text[start:end].strip()
    elif "```" in judge_text:
        start = judge_text.find("```") + 3
        end = judge_text.find("```", start)
        judge_text = judge_text[start:end].strip()

    parsed = json.loads(judge_text)
    return parsed.get("scores", {})


def calculate_weighted_score(
    scores: dict[str, dict],
    rubric: dict[str, dict]
) -> float:
    """
    Pure function: Calculate weighted average score.

    Args:
        scores: Score dict from judge
        rubric: Original rubric with weights

    Returns:
        Weighted average score (0.0-1.0)
    """
    total_weight = sum(item["weight"] for item in rubric.values())
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(
        scores.get(key, {}).get("score", 0.0) * rubric[key]["weight"]
        for key in rubric.keys()
    )

    return weighted_sum / total_weight


def parse_simple_judge_response(judge_text: str) -> dict[str, Any]:
    """
    Pure function: Parse simple judge response with score and reasoning.

    Args:
        judge_text: Raw LLM response

    Returns:
        Dict with score and reasoning

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    # Extract JSON from markdown code blocks if present
    if "```json" in judge_text:
        start = judge_text.find("```json") + 7
        end = judge_text.find("```", start)
        judge_text = judge_text[start:end].strip()
    elif "```" in judge_text:
        start = judge_text.find("```") + 3
        end = judge_text.find("```", start)
        judge_text = judge_text[start:end].strip()

    parsed = json.loads(judge_text)
    return {
        "score": parsed.get("score", 3),
        "reasoning": parsed.get("reasoning", "No reasoning provided")
    }


def extract_feedback(judge_text: str) -> str:
    """
    Pure function: Extract overall feedback from judge response.

    Args:
        judge_text: Raw LLM response

    Returns:
        Feedback string
    """
    try:
        # Try to parse JSON
        if "```json" in judge_text:
            start = judge_text.find("```json") + 7
            end = judge_text.find("```", start)
            judge_text = judge_text[start:end].strip()

        parsed = json.loads(judge_text)
        return parsed.get("overall_feedback", "No feedback provided")
    except (json.JSONDecodeError, ValueError):
        # Fallback: return first 200 chars
        return judge_text[:200] + "..." if len(judge_text) > 200 else judge_text
