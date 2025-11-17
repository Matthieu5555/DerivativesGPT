"""Handler for unknown asset types - asks for clarification."""

from derivatives_gpt_core.agents.shared.base_state import BaseAgentState
from langchain_core.messages import AIMessage
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def handle_clarify_asset(state: BaseAgentState) -> Dict[str, Any]:
    """
    Handle unknown asset type by asking user for clarification.

    Concise message under 200 words explaining what we understood
    and what we need clarified.

    Loop protection:
    - Tracks clarification_attempts
    - Fails gracefully after max attempts

    Args:
        state: Current state

    Returns:
        dict: {"messages": [AIMessage], "clarification_attempts": int}
    """
    # Check loop protection
    clarification_attempts = state.clarification_attempts + 1

    if clarification_attempts > state.max_clarification_attempts:
        logger.warning(f"Max clarification attempts ({state.max_clarification_attempts}) reached")
        return {
            "messages": [AIMessage(content=(
                f"I've asked for clarification {state.max_clarification_attempts} times "
                f"but couldn't determine the asset type.\n\n"
                f"Please provide a complete pricing request like:\n"
                f'"Price a call on AAPL strike $150, expiring in 30 days"'
            ))],
            "clarification_attempts": clarification_attempts
        }

    # Get user query
    user_query = ""
    if state.messages:
        from langchain_core.messages import HumanMessage
        for msg in reversed(state.messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break
    
    response = f"""I understand you're asking about derivatives, but I couldn't determine the asset type.

**What I understood:**
- Your query: "{user_query[:100]}..."

**What I need:**
Which asset class are you interested in?
- **Equity**: Stock options (e.g., AAPL call)
- **FX**: Currency options (e.g., EUR/USD)
- **Commodity**: Oil, gold, agricultural
- **Interest Rate**: Caps, floors, swaptions
- **Credit**: CDS, credit derivatives

Please specify the asset type or provide more context."""

    return {
        "messages": [AIMessage(content=response)],
        "clarification_attempts": clarification_attempts
    }
