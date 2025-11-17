"""Handler for unknown option types - asks for clarification."""

from derivatives_gpt_core.agents.pricing.state import PricingState
from langchain_core.messages import AIMessage
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def handle_clarify_option(state: PricingState) -> Dict[str, Any]:
    """
    Handle unknown option type by asking user for clarification.

    Concise message under 200 words.

    Loop protection:
    - Tracks clarification_attempts
    - Fails gracefully after max attempts

    Args:
        state: Current state with asset_type_classified

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
                f"but couldn't determine the option type.\n\n"
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
    
    asset_type = state.asset_type_classified or "this asset"

    # Check if this is specifically about missing direction
    if state.clarification_context == "missing_direction":
        response = f"""I detected you want to price an option on {asset_type}, but I need to know:

**Do you want a CALL or PUT option?**

- **Call**: Right to buy at the strike price (profits when price goes up)
- **Put**: Right to sell at the strike price (profits when price goes down)

For example: "American call on AAPL" or "American put on AAPL"

Please clarify which direction you want."""
    else:
        response = f"""I understand this is about {asset_type} derivatives, but couldn't determine the specific option type.

**What I understood:**
- Asset: {asset_type}
- Query: "{user_query[:100]}..."

**What I need:**
What type of option are you interested in?
- **Call/Put**: Standard European options
- **American**: Early exercise allowed
- **Strategy**: Straddle, strangle, spread, butterfly
- **Exotic**: Asian, barrier, digital, lookback

Please specify or describe the payoff structure."""

    return {
        "messages": [AIMessage(content=response)],
        "clarification_attempts": clarification_attempts
    }
