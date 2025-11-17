"""Classify topic continuity node - pure function."""

import json
import logging

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_classification_llm
from prompts.educational.topic_continuity import build_topic_continuity_prompt

logger = logging.getLogger(__name__)


async def classify_topic_continuity(state: EducationalState) -> dict:
    """
    Pure async function: Classify whether user question is follow-up or new topic.

    Determines:
    1. Is user still on the same topic? (follow-up vs new topic)
    2. Is it still financial/options-related? (for off-topic detection)

    Reads:
        - messages: Current and previous user questions
        - educational_context: Previous topic and conversation state

    Writes:
        - educational_context: Updated with topic continuity classification

    Args:
        state: Current graph state

    Returns:
        State updates dict with educational_context modifications
    """
    # Extract current question
    current_question = _get_latest_user_question(state.messages)

    if not current_question:
        logger.warning("No user question found for topic continuity classification")
        return {}

    # Get previous context
    edu_context = state.educational_context
    previous_topic = edu_context.current_topic
    previous_question = edu_context.last_user_question
    previous_explanation = state.explanation_text  # Include for reference detection

    # SHORT-CIRCUIT: If no previous context exists, this MUST be a new topic
    # Don't trust LLM to follow instructions - it hallucinates previous context
    if previous_topic is None and previous_question is None:
        logger.info("First question detected (no previous context) - classifying as new topic")
        classification = {
            "is_same_topic": False,
            "is_financial_related": True,  # Assume financial unless off-topic
            "extracted_topic": "initial question",
            "reasoning": "First question in conversation - no previous context to follow up on"
        }
    else:
        # Build prompt
        prompt = build_topic_continuity_prompt(
            current_question=current_question,
            previous_topic=previous_topic,
            previous_question=previous_question,
            previous_explanation=previous_explanation,
        )

        # Get LLM classification
        llm = get_classification_llm()
        response = await llm.ainvoke(prompt)
        classification_text = response.content if hasattr(response, "content") else str(response)

        # Parse JSON response
        try:
            classification = _parse_classification_json(classification_text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse topic continuity classification: {e}")
            # Fallback: treat as new topic, assume financial-related
            classification = {
                "is_same_topic": False,
                "is_financial_related": True,
                "extracted_topic": "unknown topic",
                "reasoning": f"Parse error: {str(e)}"
            }

    # Update educational context
    updated_context = _update_educational_context(
        edu_context=edu_context,
        classification=classification,
        current_question=current_question,
    )

    logger.info(
        f"Topic Continuity: is_same_topic={classification['is_same_topic']}, "
        f"topic='{classification['extracted_topic']}', "
        f"financial={classification['is_financial_related']}"
    )
    logger.info(f"   Reasoning: {classification['reasoning']}")

    return {
        "educational_context": updated_context
    }


def _get_latest_user_question(messages: list) -> str | None:
    """
    Extract the latest user question from messages.

    Args:
        messages: List of conversation messages

    Returns:
        Latest user question text, or None if no user message found
    """
    if not messages:
        return None

    from langchain_core.messages import HumanMessage

    # Get last user message
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content

    return None


def _parse_classification_json(classification_text: str) -> dict:
    """
    Parse topic continuity classification JSON from LLM response.

    Args:
        classification_text: Raw LLM response

    Returns:
        Parsed classification dict

    Raises:
        json.JSONDecodeError: If JSON is invalid
    """
    # Extract JSON from markdown code blocks if present
    if "```json" in classification_text:
        start = classification_text.find("```json") + 7
        end = classification_text.find("```", start)
        classification_text = classification_text[start:end].strip()
    elif "```" in classification_text:
        start = classification_text.find("```") + 3
        end = classification_text.find("```", start)
        classification_text = classification_text[start:end].strip()

    return json.loads(classification_text)


def _update_educational_context(
    edu_context,  # EducationalConversationState
    classification: dict,
    current_question: str,
) -> dict:
    """
    Update educational context based on classification result.

    Args:
        edu_context: Current educational conversation state
        classification: Topic continuity classification result
        current_question: User's current question

    Returns:
        Updated educational context as dict (for immutable state update)
    """
    # Create a copy of the context
    from derivatives_gpt_core.core.state.educational_state import EducationalConversationState
    updated = EducationalConversationState(**edu_context.dict())

    # Update classification results
    updated.is_same_topic = classification["is_same_topic"]
    updated.is_financial_related = classification["is_financial_related"]
    updated.topic_classification_reasoning = classification["reasoning"]
    updated.topic_continuity_checked = True

    extracted_topic = classification["extracted_topic"]

    if classification["is_same_topic"]:
        # Follow-up question on same topic
        updated.record_followup_question(current_question)
        updated.topic_changed = False
        # Keep current_topic as is
    else:
        # New topic
        updated.reset_for_new_topic(extracted_topic)

    return updated
