"""Narrate execution results to create progressive user-facing story."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.llm_provider import get_narrator_llm
from prompts.narration_prompts import NARRATION_SYSTEM_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def narrate_execution(state: BaseAgentState) -> Dict[str, Any]:
    """
    Create progressive narrative from execution results.

    Purpose: Transform raw execution_results into user-friendly streaming narrative.
    This is a VIEW layer - it READS state but doesn't modify pricing data.

    Timing: Called AFTER execute, BEFORE final validation

    Safe to read:
    - execution_results (all calculated data)
    - option_price (final price)
    - extracted_ticker, strike_price, option_type, time_to_expiry_days
    - strategy_type, legs

    Safe to write:
    - messages (append narrative)

    NEVER modify: option_price, execution_results, validation_errors

    Args:
        state: State after parallel execution with results

    Returns:
        dict: {"messages": [AIMessage with narrative]}
    """
    logger.info(f"[narrate_execution] Starting with state keys: {list(state.__dict__.keys())}")

    # LangSmith Tracing: START
    try:
        # Build context from execution results
        # NOTE: Validation should have already caught missing parameters,
        # so we don't duplicate those checks here
        if not state.execution_results:
            logger.warning("No execution_results available for narration")
            fallback_msg = (
                f"Calculated price: ${state.option_price:.2f}"
                if state.option_price
                else "Calculation completed."
            )
            logger.warning("[narrate_execution] FALLBACK | scenario=no_execution_results")
            return {"messages": [AIMessage(content=fallback_msg)]}

        narrator_model = get_narrator_llm()

        # Build prompt with execution results data
        methods_used = {
            "volatility": state.execution_results.get("fetch_vol", {}).get("method", "not specified"),
            "risk_free": state.execution_results.get("fetch_rate", {}).get("method", "not specified"),
            "pricing_model": "Black-Scholes European option model",
        }
        
        execution_context = {
            "results": state.execution_results,
            "methods_used": methods_used
        }

        # Add RAG sources if available (include text snippets for LLM to cite)
        rag_section = ""
        if state.rag_sources and len(state.rag_sources) > 0:
            rag_lines = ["RAG Sources Retrieved (cite these at the end):"]
            for i, source in enumerate(state.rag_sources[:3], 1):  # Top 3
                book = source.get("book", "Unknown")
                page = source.get("page", 0)
                text = source.get("text", "")[:300]  # First 300 chars
                score = source.get("score", 0.0)
                rag_lines.append(f"\nSource {i}:")
                rag_lines.append(f"  Book: {book}")
                rag_lines.append(f"  Page: {page}")
                rag_lines.append(f"  Relevance: {score:.2f}")
                rag_lines.append(f"  Content: {text}...")
            rag_section = "\n".join(rag_lines)

        context_parts = [
            f"Strategy: {state.strategy_type or 'single'}",
            f"Ticker: {state.extracted_ticker or state.ticker or 'unknown'}",
            f"Final Price: ${state.option_price:.2f}" if state.option_price else "Price: not calculated",
            "",
            "Execution Context:",
            str(execution_context),
        ]

        if rag_section:
            context_parts.append("")
            context_parts.append(rag_section)

        context = "\n".join(context_parts)

        logger.debug(f"[narrate_execution] Context:\n{context}")

        # Generate narrative (NO tool calls - chart already displayed in classify node)
        response = await narrator_model.ainvoke([
            SystemMessage(content=NARRATION_SYSTEM_PROMPT),
            HumanMessage(content=f"Create narrative from:\n{context}"),
        ])

        narrative = response.content

        # LangSmith Tracing: Structured logging for observability
        logger.info(
            f"[narrate_execution] SUCCESS | "
            f"length={len(narrative)} | has_rag={bool(state.rag_sources)} | "
            f"rag_count={len(state.rag_sources) if state.rag_sources else 0} | "
            f"price={state.option_price}"
        )

        return {"messages": [AIMessage(content=narrative)]}

    except (ConnectionError, TimeoutError) as e:
        # Network errors with LLM - graceful fallback
        fallback_msg = (
            f"Calculated price: ${state.option_price:.2f}"
            if state.option_price
            else "Calculation completed."
        )
        logger.warning(f"[narrate_execution] NETWORK_ERROR | error={str(e)}")
        return {"messages": [AIMessage(content=fallback_msg)]}
    except Exception as e:
        # Unexpected errors (bugs) - log and re-raise
        logger.error(f"[narrate_execution] EXCEPTION | ticker={state.ticker} | error={str(e)}", exc_info=True)
        raise