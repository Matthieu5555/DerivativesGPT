"""
Handler for educational concept explanation queries.

Pure async function - deterministic output from state.
"""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from typing import Dict, Any

from .helpers import build_message_response, format_list_items


# ============================================================================
# EDUCATIONAL HANDLER
# ============================================================================

async def handle_explain_concept(state: BaseAgentState) -> Dict[str, Any]:
    """
    Handle educational concept explanation queries with stateful loop.

    Pure async function - takes state, returns dict.

    This is now an EDUCATIONAL LOOP:
    1. User asks "What is delta?"
    2. System retrieves RAG + web search and explains
    3. Graph PAUSES (returns to END)
    4. User follows up: "What about gamma?"
    5. Conversation history preserved, new graph execution starts
    6. RAG + web search re-run with CUMULATIVE history
    7. System explains gamma in context of delta
    8. Loop continues until user changes intent (asks for pricing)

    The loop is managed by the graph architecture:
    - explain_concept → END (graph pauses)
    - User sends follow-up → new graph starts from classify
    - classify detects educational intent → routes back to explain_concept
    - RAG sees full conversation history → smarter answers

    Called by: graph routing when response_type is "explain_concept"

    Examples:
    - "What is delta?" → Explain delta with book references
    - "Explain Black-Scholes" → Show formula derivation from sources
    - "How does volatility affect prices?" → Educational explanation

    Edge cases handled:
    - No RAG sources: Provide generic explanation
    - Empty query: Generic response

    Args:
        state: Current option pricing state

    Returns:
        dict: Updated messages with concept explanation
    """
    sources = state.rag_sources or []
    reformulated_rag = state.reformulated_rag
    web_results = state.web_search_results or []

    # Use reformulated RAG if available (LLM cleaned up the context)
    if reformulated_rag:
        # Build explanation using LLM-reformulated content
        response = (
            f"{reformulated_rag}\n\n"
            f"Would you like me to explain another concept, or price an option?"
        )
        return build_message_response(response)

    # Fallback: Use raw RAG sources
    if not sources:
        # No RAG sources - provide gentle redirect
        recommended_books = [
            "Hull's *Options, Futures, and Other Derivatives*",
            "Shreve's *Stochastic Calculus for Finance*"
        ]

        response = (
            f"I'd love to explain that concept, but I don't have access to relevant textbook sections right now.\n\n"
            f"I'm specialized in **pricing European call and put options** using Black-Scholes. "
            f"For detailed derivatives concepts, I recommend consulting:\n"
            f"{format_list_items(recommended_books)}\n\n"
            f"Would you like me to price an option instead?"
        )
        return build_message_response(response)

    # Build explanation from RAG sources
    response_parts = []

    for i, source in enumerate(sources[:3], 1):  # Show top 3
        text = source.get("text", "")
        book = source.get("book", "Unknown")
        page = source.get("page", 0)
        score = source.get("score", 0.0)

        # Only show high-relevance sources (score > 0.5)
        if score > 0.5:
            response_parts.append(
                f"\n**Source {i}: {book}, Page {page}**\n"
                f"{text[:500]}{'...' if len(text) > 500 else ''}\n"
            )

    # Add web results if available
    if web_results:
        response_parts.append("\n**Additional Resources:**\n")
        for i, result in enumerate(web_results[:2], 1):
            title = result.get("title", "Unknown")
            url = result.get("url", "")
            response_parts.append(f"{i}. [{title}]({url})\n")

    # Add friendly closing
    response_parts.append(
        "\n---\n\n"
        "*Would you like me to explain another concept, or price an option?*"
    )

    response = "".join(response_parts)

    return build_message_response(response)
