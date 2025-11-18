"""Utilities for parameter extraction notebook."""

import asyncio
from typing import Dict
from derivatives_gpt_core.agents.pricing.state import PricingState
from derivatives_gpt_core.agents.pricing.nodes.extract_parameters import extract_parameters
from langchain_core.messages import HumanMessage

async def extract_from_query(query: str) -> Dict:
    """Extract option parameters from natural language query."""

    state = PricingState(messages=[HumanMessage(content=query)])
    result = await extract_parameters(state)

    return {
        'ticker': result.get('ticker'),
        'option_type': result.get('option_type'),
        'strike': result.get('strike_price'),
        'expiry': result.get('time_to_expiry_days'),
        'spot': result.get('spot_price'),
        'volatility': result.get('volatility'),
        'product_type': result.get('product_type'),
        'extraction_success': result.get('extraction_successful', False)
    }