#!/usr/bin/env python3
"""
Quick diagnostic script to test parameter extraction.
Tests a simple query to see what the LLM actually returns.
"""

import asyncio
import logging
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import ParameterExtraction
from prompts.graph_nodes.parameter_extraction_prompts import PARAMETER_EXTRACTION_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_extraction():
    """Test parameter extraction with a simple query."""

    # Test queries from the failing test suite
    test_queries = [
        "Price a call option on AAPL with strike 150, expiring in 30 days",
        "What's the value of a TSLA put at strike 200, 60 days to expiration?",
        "Price SPY 450 call expiring next month",
        "MSFT put option, strike 350, 45 days out",
    ]

    llm = get_classification_llm()

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {query}")
        print('='*80)

        # Simple context (minimal)
        context = f"""=== CURRENT REQUEST ===
User Query: {query}

=== EXISTING PARAMETERS FROM PREVIOUS DISCUSSION ===
(No previous parameters in state)

=== EXTRACTION INSTRUCTIONS ===
Extract all available parameters from the user query."""

        # Invoke LLM
        response = llm.invoke([
            SystemMessage(content=PARAMETER_EXTRACTION_PROMPT),
            HumanMessage(content=context)
        ])

        response_text = response.content.strip()

        print(f"\n📤 RAW LLM RESPONSE:")
        print("-" * 80)
        print(response_text)
        print("-" * 80)

        # Try to parse it
        validated_params = extract_and_validate_with_retry(
            response_text,
            ParameterExtraction,
            max_attempts=3,
            strict=False
        )

        if validated_params:
            print(f"\n✅ PARSED SUCCESSFULLY:")
            print(f"  ticker: {validated_params.ticker}")
            print(f"  strike_price: {validated_params.strike_price}")
            print(f"  time_to_expiry_days: {validated_params.time_to_expiry_days}")
            print(f"  option_type: {validated_params.option_type}")
            print(f"  extraction_successful: {validated_params.extraction_successful}")
            print(f"  missing_info: {validated_params.missing_info}")
        else:
            print(f"\n❌ PARSING FAILED!")
            print(f"Could not validate response against ParameterExtraction schema")


if __name__ == "__main__":
    test_extraction()
