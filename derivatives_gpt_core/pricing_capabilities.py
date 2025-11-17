"""
Pricing Capabilities Registry - Source of truth for what we can price.

This module provides a single source of truth for:
- What option types we can price
- What methods we use
- What tools are available

This registry is injected into LLM prompts to ground their decisions in reality.
"""

from typing import Dict, List


# ============================================================================
# PRICING TOOLS REGISTRY - Source of Truth
# ============================================================================

PRICING_TOOLS = {
    "price_european_option": {
        "description": "Price European call/put options using Black-Scholes",
        "method": "Black-Scholes analytical formula",
        "option_types": ["vanilla_call", "vanilla_put", "european_call", "european_put"],
        "can_price": True,
        "tool_file": "black_scholes_tool.py"
    },
    "price_american_option": {
        "description": "Price American call/put options using Bjerksund-Stensland approximation",
        "method": "Bjerksund-Stensland analytical approximation",
        "option_types": ["american_call", "american_put"],
        "can_price": True,
        "tool_file": "american_option_tool.py"
    },
    "price_digital_option": {
        "description": "Price digital/binary options (cash-or-nothing payoff)",
        "method": "Analytical formula for discontinuous payoff",
        "option_types": ["digital_call", "digital_put", "binary_call", "binary_put"],
        "can_price": True,
        "tool_file": "digital_option_tool.py"
    },
    "price_geometric_asian_option": {
        "description": "Price geometric Asian options (geometric average payoff)",
        "method": "Analytical formula for geometric averaging",
        "option_types": ["geometric_asian_call", "geometric_asian_put"],
        "can_price": True,
        "tool_file": "geometric_asian_tool.py"
    }
}


# ============================================================================
# CANNOT PRICE - Explicit list of what we recognize but can't handle
# ============================================================================

CANNOT_PRICE = {
    "arithmetic_asian": {
        "reason": "Requires Monte Carlo simulation (no closed-form solution)",
        "option_types": ["asian_call", "asian_put", "arithmetic_asian_call", "arithmetic_asian_put"]
    },
    "barrier": {
        "reason": "Requires path-dependent simulation with continuous barrier monitoring",
        "option_types": ["barrier_call", "barrier_put", "knock_in", "knock_out", "up_and_in", "down_and_out"]
    },
    "lookback": {
        "reason": "Requires path-dependent simulation tracking maximum/minimum prices",
        "option_types": ["lookback_call", "lookback_put", "floating_strike", "fixed_strike"]
    },
    "basket": {
        "reason": "Requires multi-dimensional Monte Carlo with correlation matrix",
        "option_types": ["basket_call", "basket_put", "rainbow_option", "multi_asset"]
    },
    "variance_swap": {
        "reason": "Requires variance replication using option strips and volatility modeling",
        "option_types": ["variance_swap", "volatility_swap"]
    },
    "compound": {
        "reason": "Requires nested Black-Scholes with recursive valuation",
        "option_types": ["compound_call", "compound_put", "option_on_option"]
    },
    "exotic_other": {
        "reason": "Advanced numerical methods not currently implemented",
        "option_types": ["chooser", "shout", "cliquet", "napoleon", "power", "quanto"]
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_capabilities_summary() -> str:
    """
    Generate human-readable summary of pricing capabilities.

    Returns:
        Formatted string listing what we can and cannot price
    """
    can_price_types = []
    for tool_name, tool_info in PRICING_TOOLS.items():
        can_price_types.extend(tool_info["option_types"])

    cannot_price_types = []
    for category, info in CANNOT_PRICE.items():
        cannot_price_types.extend(info["option_types"])

    summary = f"""
PRICING CAPABILITIES:

[CAN PRICE] ({len(can_price_types)} option types):
{', '.join(sorted(set(can_price_types)))}

[CANNOT PRICE] ({len(cannot_price_types)} option types):
{', '.join(sorted(set(cannot_price_types)))}

AVAILABLE TOOLS ({len(PRICING_TOOLS)} tools):
{chr(10).join(f"- {name}: {info['description']}" for name, info in PRICING_TOOLS.items())}
"""
    return summary.strip()


def get_tool_list_for_llm() -> str:
    """
    Generate concise tool list for LLM context injection.

    Returns:
        Formatted string for LLM prompts
    """
    tools_list = []
    for tool_name, tool_info in PRICING_TOOLS.items():
        tools_list.append(
            f"- {tool_name}(): {tool_info['description']} (supports: {', '.join(tool_info['option_types'])})"
        )

    cannot_list = []
    for category, info in CANNOT_PRICE.items():
        cannot_list.append(
            f"- {', '.join(info['option_types'])}: {info['reason']}"
        )

    return f"""
AVAILABLE PRICING TOOLS:
{chr(10).join(tools_list)}

CANNOT PRICE (require methods not implemented):
{chr(10).join(cannot_list)}
""".strip()


def can_price_option_type(option_type: str) -> bool:
    """
    Check if we can price a given option type.

    Args:
        option_type: Option type string (e.g., "vanilla_call", "barrier_put")

    Returns:
        True if we have a tool for this option type
    """
    option_type_lower = option_type.lower()

    # Check all pricing tools
    for tool_info in PRICING_TOOLS.values():
        if option_type_lower in [ot.lower() for ot in tool_info["option_types"]]:
            return True

    return False


def get_pricing_method(option_type: str) -> str | None:
    """
    Get the pricing method for a given option type.

    Args:
        option_type: Option type string

    Returns:
        Pricing method description or None if can't price
    """
    option_type_lower = option_type.lower()

    for tool_info in PRICING_TOOLS.values():
        if option_type_lower in [ot.lower() for ot in tool_info["option_types"]]:
            return tool_info["method"]

    # Check cannot price
    for info in CANNOT_PRICE.values():
        if option_type_lower in [ot.lower() for ot in info["option_types"]]:
            return info["reason"]

    return None
