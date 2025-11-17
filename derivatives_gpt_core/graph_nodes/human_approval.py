"""Human-in-the-loop approval before pricing."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from derivatives_gpt_core.llm_provider import get_classification_llm
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from typing import Dict, Any
import chainlit as cl
import logging
import json

logger = logging.getLogger(__name__)


async def request_human_approval(state: BaseAgentState) -> Dict[str, Any]:
    """
    Request human approval before proceeding with pricing.

    Shows user the proposed pricing parameters and tools to be used.
    Displays any API errors or missing data warnings.
    Awaits free-text response.

    Args:
        state: State with extracted parameters

    Returns:
        dict: {"human_approved": bool, "human_feedback": str}
    """
    try:
        # Build pricing summary
        ticker = state.ticker or state.extracted_ticker or "unknown"
        option_type = state.option_type or "unknown"
        strike = state.strike_price
        expiry = state.time_to_expiry_days
        asset_type = state.asset_type_classified or "equity"
        option_class = state.option_type_classified or "vanilla"

        expiry_str = f"{expiry} days" if expiry else "TBD"
        strike_str = f"${strike}" if strike else "TBD"

        # Collect validation warnings (not errors - those block earlier)
        warnings = []
        if state.validation_warnings:
            warnings.extend(state.validation_warnings)

        # List parameters we'll need to fetch
        to_fetch = []
        if state.spot_price is None:
            to_fetch.append("spot price (from market data)")
        if state.volatility is None:
            to_fetch.append("volatility (historical estimate)")
        if state.risk_free_rate is None:
            to_fetch.append("risk-free rate (current estimate)")
        if strike is None:
            to_fetch.append("strike price (will default to ATM)")

        summary_parts = [
            "**Pricing Request Summary:**\n\n",
            f"- **Asset Type**: {asset_type}\n",
            f"- **Option Class**: {option_class}\n",
            f"- **Ticker**: {ticker}\n",
            f"- **Type**: {option_type}\n",
            f"- **Strike**: {strike_str}\n",
            f"- **Expiry**: {expiry_str}\n",
            f"- **Pricing Model**: Black-Scholes (European)\n"
        ]

        # Show what we'll fetch
        if to_fetch:
            summary_parts.append(f"\n**Will fetch automatically:**\n")
            for item in to_fetch:
                summary_parts.append(f"- {item}\n")

        # Show validation warnings if any
        if warnings:
            summary_parts.append("\n**Validation Warnings:**\n")
            for warning in warnings[:3]:  # Show max 3 warnings
                summary_parts.append(f"- {warning}\n")

        summary_parts.append("\nShould I proceed with pricing using these parameters?\n\n")
        summary_parts.append("Type your response (e.g., \"yes\", \"no\", \"use 4.5% risk-free rate\", etc.)")

        summary = "".join(summary_parts)
        
        # Send message and await response
        await cl.Message(content=summary).send()
        
        # Get user response (free text)
        response = await cl.AskUserMessage(
            content="",
            timeout=120  # 2 minutes
        ).send()
        
        if not response:
            logger.warning("No human response received, defaulting to not approved")
            return {
                "human_approved": False,
                "human_feedback": "No response"
            }
        
        user_text = response.get("output", "").strip()

        # Let LLM interpret the user's response (no hardcoded keywords!)
        llm = get_classification_llm()
        interpretation_prompt = """Interpret if the user is approving or rejecting the pricing request.

User's response: "{user_response}"

Return ONLY valid JSON:
{{
    "approved": true | false,
    "reasoning": "brief explanation"
}}

Examples:
- "yes" → {{"approved": true, "reasoning": "explicit approval"}}
- "no thanks" → {{"approved": false, "reasoning": "explicit rejection"}}
- "go ahead" → {{"approved": true, "reasoning": "approval to proceed"}}
- "wait, use 5% rate" → {{"approved": false, "reasoning": "user wants to modify parameters"}}
- "👍" → {{"approved": true, "reasoning": "emoji approval"}}
- "nope" → {{"approved": false, "reasoning": "rejection"}}
""".format(user_response=user_text)

        llm_response = llm.invoke([SystemMessage(content=interpretation_prompt)])

        try:
            # Parse LLM's interpretation
            result = json.loads(llm_response.content.strip())
            approved = result.get("approved", False)
            reasoning = result.get("reasoning", "")
            logger.info(f"Human approval: {approved}, reasoning: {reasoning}, feedback: {user_text}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM approval response, defaulting to False")
            approved = False

        return {
            "human_approved": approved,
            "human_feedback": user_text
        }
    
    except Exception as e:
        logger.error(f"Human approval failed: {e}")
        return {
            "human_approved": False,
            "human_feedback": f"Error: {e}"
        }
