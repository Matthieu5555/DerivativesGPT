#!/usr/bin/env python3
"""
Test parameter extraction WITH classification context.
This simulates the actual evaluation scenario where option_type_classified is present.
"""

import logging
from derivatives_gpt_core.llm_provider import get_classification_llm
from derivatives_gpt_core.utils.llm_parsing import extract_and_validate_with_retry
from derivatives_gpt_core.schemas.llm_schemas import ParameterExtraction
from prompts.graph_nodes.parameter_extraction_prompts import PARAMETER_EXTRACTION_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_extraction_with_classification():
    """Test parameter extraction WITH classification context (like in real evaluation)."""

    test_cases = [
        {
            "query": "Price a call option on AAPL with strike 150, expiring in 30 days",
            "asset_type": "equity",
            "option_class": "vanilla_call"
        },
        {
            "query": "What's the value of a TSLA put at strike 200, 60 days to expiration?",
            "asset_type": "equity",
            "option_class": "american_put"
        },
        {
            "query": "Price SPY 450 call expiring next month",
            "asset_type": "equity",
            "option_class": "vanilla_call"
        },
    ]

    llm = get_classification_llm()

    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        asset_type = test_case["asset_type"]
        option_class = test_case["option_class"]

        print(f"\n{'='*80}")
        print(f"TEST {i}: {query}")
        print(f"Asset Type: {asset_type}")
        print(f"Option Class: {option_class}")
        print('='*80)

        # Build context EXACTLY like the real extract_parameters node does
        context_parts = [
            "=== CONVERSATION HISTORY ===",
            f"User: {query}",
            "",
            "=== CURRENT REQUEST ===",
            f"User Query: {query}",
            "",
            "=== EXISTING PARAMETERS FROM PREVIOUS DISCUSSION ===",
            "(No previous parameters in state)",
            "",
            "=== CLASSIFICATION INFO ===",
            f"Asset Type: {asset_type}",
            f"Option Class: {option_class}",  # THIS IS THE SUSPECT!
            "",
            "=== EXTRACTION INSTRUCTIONS ===",
            "1. If user says 'same option', 'same parameters', 'but now', inherit ALL previous parameters",
            "2. Only override what the user explicitly changes in current query",
            "3. For 'same option but american', keep strike and expiry from previous, just change type"
        ]

        context = "\n".join(context_parts)

        print(f"\n📥 CONTEXT SENT TO LLM:")
        print("-" * 80)
        print(context)
        print("-" * 80)

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

            if not validated_params.extraction_successful:
                print(f"\n⚠️  EXTRACTION MARKED AS UNSUCCESSFUL!")
                print(f"  Missing: {validated_params.missing_info}")
        else:
            print(f"\n❌ PARSING FAILED!")
            print(f"Could not validate response against ParameterExtraction schema")


if __name__ == "__main__":
    test_extraction_with_classification()
