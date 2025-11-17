"""Build on user understanding node - pure function."""

from langchain_core.messages import AIMessage

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_narrator_llm
from prompts.educational.build_on_understanding import build_targeted_response_prompt


async def build_on_understanding(state: EducationalState) -> dict:
    """
    Pure async function: Generate targeted response based on user's understanding.

    This is the human-in-the-loop core - after user explains their understanding,
    we assess it and build a conversational response that:
    - Acknowledges what they understood correctly
    - Addresses gaps or misconceptions
    - Builds on their understanding with next concepts
    - Asks probing questions

    Reads:
        - messages: User's explanation of understanding
        - explanation_text: Original explanation we provided
        - user_comprehension_assessment: Assessment of their understanding
        - user_confusion_signals: Identified gaps/misconceptions
        - user_understanding_score: Score 1-5
        - educational_context: Topic and conversation state

    Writes:
        - messages: Appends AI response building on understanding
        - educational_context: Updates understanding check state

    Args:
        state: Current graph state

    Returns:
        State updates dict (for immutable update)
    """
    # Extract data from state
    user_explanation = state.messages[-1].content if state.messages else ""
    original_explanation = state.explanation_text or ""
    assessment = state.user_comprehension_assessment or {}
    gaps = state.user_confusion_signals or []
    score = state.user_understanding_score or 3.0
    topic = state.educational_context.current_topic or "this concept"

    # Build prompt for targeted response
    prompt = build_targeted_response_prompt(
        topic=topic,
        original_explanation=original_explanation,
        user_explanation=user_explanation,
        understanding_score=score,
        identified_gaps=gaps,
        assessment=assessment,
    )

    # Get LLM response (use narrator for conversational quality)
    llm = get_narrator_llm()
    response = await llm.ainvoke(prompt)

    targeted_response = response.content if hasattr(response, "content") else str(response)

    # Update educational context
    edu_context = state.educational_context
    updated_context = edu_context.model_dump()
    updated_context["awaiting_user_understanding"] = False  # User responded
    updated_context["user_explained_understanding"] = True
    updated_context["understanding_check_count"] = edu_context.understanding_check_count + 1

    # Return immutable state updates
    return {
        "messages": [AIMessage(content=targeted_response)],
        "educational_context": updated_context,
    }
