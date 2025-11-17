"""Generate educational explanation node - pure function."""

from langchain_core.messages import AIMessage

from derivatives_gpt_core.agents.educational.state import EducationalState
from derivatives_gpt_core.llm_provider import get_narrator_llm
from prompts.educational.generation import (
    build_explanation_prompt,
    format_rag_content,
)


async def generate_explanation(state: EducationalState) -> dict:
    """
    Pure async function: Generate educational explanation.

    Reads:
        - messages: User's question
        - rag_sources: Retrieved educational content
        - web_search_results: Web search results (Tavily)
        - adaptive_difficulty_level: User's knowledge level
        - explanation_attempt_count: Number of previous attempts
        - educational_context: Conversation mode and topic tracking

    Writes:
        - explanation_text: Generated explanation
        - explanation_attempt_count: Incremented counter
        - messages: Appends AI explanation

    Args:
        state: Current graph state

    Returns:
        State updates dict (for immutable update)
    """
    # Extract data from state
    user_query = state.messages[-1].content if state.messages else "Unknown question"
    rag_content = _format_rag_sources(state.rag_sources or [])
    web_content = _format_web_sources(state.web_search_results or [])
    difficulty = state.adaptive_difficulty_level or "intermediate"
    previous_attempts = state.explanation_attempt_count or 0
    conversation_mode = state.educational_context.conversation_mode or "initial_explanation"

    # Log mode for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Generating explanation in {conversation_mode} mode")

    # Build prompt (pure function)
    prompt = build_explanation_prompt(
        query=user_query,
        rag_content=rag_content,
        web_content=web_content,
        difficulty=difficulty,
        conversation_mode=conversation_mode,
        previous_attempts=previous_attempts,
    )

    # Get LLM response
    llm = get_narrator_llm()  # Use narrator LLM for quality explanations
    response = await llm.ainvoke(prompt)

    explanation = response.content if hasattr(response, "content") else str(response)

    # Return immutable state updates
    return {
        "explanation_text": explanation,
        "explanation_attempt_count": previous_attempts + 1,
        "messages": [AIMessage(content=explanation)],
    }


def _format_rag_sources(rag_sources: list[dict]) -> list[dict]:
    """
    Pure function: Transform rag_sources into format expected by prompt builder.

    Args:
        rag_sources: Raw RAG sources from state (has keys: text, book, page, score, chunk_id)

    Returns:
        Formatted list with 'source' and 'content' keys
    """
    formatted = []
    for source in rag_sources:
        # Build source attribution like "Exotic Options & Hybrids, Ch. 3"
        book = source.get("book", "Unknown")
        page = source.get("page", "")
        source_attr = f"{book}, {page}" if page else book

        formatted.append({
            "source": source_attr,
            "content": source.get("text", ""),
        })
    return formatted


def _format_web_sources(web_results: list[dict]) -> list[dict]:
    """
    Pure function: Transform web_search_results into format expected by prompt builder.

    Args:
        web_results: Raw web search results from Tavily

    Returns:
        Formatted list with 'title', 'url', 'content' keys
    """
    formatted = []
    for result in web_results:
        formatted.append({
            "title": result.get("title", "Unknown"),
            "url": result.get("url", ""),
            "content": result.get("content", ""),
        })
    return formatted
