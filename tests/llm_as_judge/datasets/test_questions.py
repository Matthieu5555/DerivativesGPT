"""Test questions dataset - pure data (TypedDict)."""

from typing import TypedDict, Any


class TestQuestion(TypedDict):
    """Test question structure."""
    id: str
    category: str
    question: str
    expected_behavior: str
    expected_graph_state: str  # Expected terminal graph node (e.g., "pricing_complete", "off_topic", "generate_explanation")
    rubric: dict[str, Any]
    min_passing_score: float


# === PRICING - VANILLA OPTIONS (European) ===

PRICING_VANILLA: list[TestQuestion] = [
    {
        "id": "vanilla_001",
        "category": "pricing_vanilla",
        "question": "Price a call option on AAPL with strike 150, expiring in 30 days",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "AAPL", "weight": 0.25},
            "extracted_option_type": {"expected": "call", "weight": 0.25},
            "extracted_strike": {"expected": 150.0, "weight": 0.25},
            "pricing_completed": {"expected": True, "weight": 0.25}
        },
        "min_passing_score": 0.8
    },
    {
        "id": "vanilla_002",
        "category": "pricing_vanilla",
        "question": "What's the value of a TSLA put at strike 200, 60 days to expiration?",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "TSLA", "weight": 0.3},
            "extracted_option_type": {"expected": "put", "weight": 0.3},
            "extracted_strike": {"expected": 200.0, "weight": 0.2},
            "pricing_completed": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.75
    },
    {
        "id": "vanilla_003",
        "category": "pricing_vanilla",
        "question": "Price SPY 450 call expiring next month",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "SPY", "weight": 0.3},
            "extracted_option_type": {"expected": "call", "weight": 0.3},
            "extracted_strike": {"expected": 450.0, "weight": 0.2},
            "pricing_completed": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.75
    },
    {
        "id": "vanilla_004",
        "category": "pricing_vanilla",
        "question": "MSFT put option, strike 350, 45 days out",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "MSFT", "weight": 0.3},
            "extracted_option_type": {"expected": "put", "weight": 0.3},
            "extracted_strike": {"expected": 350.0, "weight": 0.2},
            "pricing_completed": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.75
    },
    {
        "id": "vanilla_005",
        "category": "pricing_vanilla",
        "question": "Price a call on NVDA at the money, 3 months to expiry",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "NVDA", "weight": 0.3},
            "extracted_option_type": {"expected": "call", "weight": 0.3},
            "recognized_atm": {"expected": True, "weight": 0.2},
            "pricing_completed": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.75
    },
]

# === PRICING - AMERICAN OPTIONS ===

PRICING_AMERICAN: list[TestQuestion] = [
    {
        "id": "american_001",
        "category": "pricing_american",
        "question": "Price an American put on AAPL, strike 175, 90 days to expiry",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "AAPL", "weight": 0.25},
            "extracted_option_type": {"expected": "american_put", "weight": 0.25},
            "extracted_strike": {"expected": 175.0, "weight": 0.25},
            "pricing_completed": {"expected": True, "weight": 0.25}
        },
        "min_passing_score": 0.8
    },
    {
        "id": "american_002",
        "category": "pricing_american",
        "question": "What's the price of an American call on MSFT strike 400, 60 days?",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "MSFT", "weight": 0.3},
            "extracted_option_type": {"expected": "american_call", "weight": 0.3},
            "extracted_strike": {"expected": 400.0, "weight": 0.2},
            "pricing_completed": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.75
    },
]

# === PRICING - DIGITAL/BINARY OPTIONS ===

PRICING_DIGITAL: list[TestQuestion] = [
    {
        "id": "digital_001",
        "category": "pricing_digital",
        "question": "Price a digital call on SPY with strike 500, expiring in 45 days",
        "expected_behavior": "extract_parameters_and_price",
        "expected_graph_state": "pricing_complete",
        "rubric": {
            "extracted_ticker": {"expected": "SPY", "weight": 0.3},
            "extracted_option_type": {"expected": "digital_call", "weight": 0.3},
            "extracted_strike": {"expected": 500.0, "weight": 0.2},
            "pricing_completed": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.75
    },
]

# === EDUCATIONAL QUESTIONS ===

EDUCATIONAL: list[TestQuestion] = [
    {
        "id": "educational_001",
        "category": "educational",
        "question": "What is delta?",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "uses_rag": {"expected": True, "weight": 0.3},
            "clear_definition": {"expected": True, "weight": 0.3},
            "provides_example": {"expected": True, "weight": 0.2},
            "cites_sources": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.7
    },
    {
        "id": "educational_002",
        "category": "educational",
        "question": "Explain the Black-Scholes formula assumptions",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "mentions_constant_volatility": {"expected": True, "weight": 0.2},
            "mentions_no_dividends": {"expected": True, "weight": 0.2},
            "mentions_european_style": {"expected": True, "weight": 0.2},
            "uses_rag_sources": {"expected": True, "weight": 0.4}
        },
        "min_passing_score": 0.7
    },
    {
        "id": "educational_003",
        "category": "educational",
        "question": "What is implied volatility?",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "clear_definition": {"expected": True, "weight": 0.4},
            "explains_relationship_to_price": {"expected": True, "weight": 0.3},
            "uses_rag": {"expected": True, "weight": 0.3}
        },
        "min_passing_score": 0.7
    },
    {
        "id": "educational_004",
        "category": "educational",
        "question": "How does theta affect option prices?",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "explains_time_decay": {"expected": True, "weight": 0.4},
            "mentions_theta_negative": {"expected": True, "weight": 0.3},
            "uses_rag": {"expected": True, "weight": 0.3}
        },
        "min_passing_score": 0.7
    },
    {
        "id": "educational_005",
        "category": "educational",
        "question": "What's the difference between American and European options?",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "explains_early_exercise": {"expected": True, "weight": 0.4},
            "contrasts_both_types": {"expected": True, "weight": 0.3},
            "uses_rag": {"expected": True, "weight": 0.3}
        },
        "min_passing_score": 0.7
    },
    {
        "id": "educational_006",
        "category": "educational",
        "question": "What is vega and why does it matter?",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "explains_vega": {"expected": True, "weight": 0.4},
            "relates_to_volatility": {"expected": True, "weight": 0.3},
            "uses_rag": {"expected": True, "weight": 0.3}
        },
        "min_passing_score": 0.7
    },
    {
        "id": "educational_007",
        "category": "educational",
        "question": "Explain what a straddle strategy is",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "explains_straddle_structure": {"expected": True, "weight": 0.4},
            "mentions_volatility_play": {"expected": True, "weight": 0.3},
            "uses_rag": {"expected": True, "weight": 0.3}
        },
        "min_passing_score": 0.7
    },
    {
        "id": "educational_008",
        "category": "educational",
        "question": "What are barrier options?",
        "expected_behavior": "explain_with_rag",
        "expected_graph_state": "generate_explanation",
        "rubric": {
            "explains_barrier_concept": {"expected": True, "weight": 0.4},
            "mentions_path_dependency": {"expected": True, "weight": 0.3},
            "uses_rag": {"expected": True, "weight": 0.3}
        },
        "min_passing_score": 0.7
    },
]

# === EXOTIC OPTIONS (Cannot Price) ===

EXOTIC_OPTIONS: list[TestQuestion] = [
    {
        "id": "exotic_001",
        "category": "exotic_options",
        "question": "Price a barrier option on AAPL with knock-out at 200",
        "expected_behavior": "recognize_but_refuse",
        "expected_graph_state": "recognize_but_refuse",
        "rubric": {
            "recognizes_exotic": {"expected": True, "weight": 0.3},
            "explains_why_cannot_price": {"expected": True, "weight": 0.3},
            "lists_what_can_price": {"expected": True, "weight": 0.4}
        },
        "min_passing_score": 0.75
    },
    {
        "id": "exotic_002",
        "category": "exotic_options",
        "question": "What's the price of an arithmetic Asian call on MSFT?",
        "expected_behavior": "recognize_but_refuse",
        "expected_graph_state": "recognize_but_refuse",
        "rubric": {
            "recognizes_exotic": {"expected": True, "weight": 0.3},
            "explains_why_cannot_price": {"expected": True, "weight": 0.3},
            "lists_what_can_price": {"expected": True, "weight": 0.4}
        },
        "min_passing_score": 0.75
    },
]

# === CLARIFICATION QUESTIONS ===

CLARIFICATION: list[TestQuestion] = [
    {
        "id": "clarification_001",
        "category": "clarification",
        "question": "Price a call on a tech stock",
        "expected_behavior": "clarify_ticker",
        "expected_graph_state": "clarify_asset",
        "rubric": {
            "recognizes_ambiguity": {"expected": True, "weight": 0.4},
            "asks_clarifying_question": {"expected": True, "weight": 0.4},
            "suggests_options": {"expected": True, "weight": 0.2}
        },
        "min_passing_score": 0.75
    },
    {
        "id": "clarification_002",
        "category": "clarification",
        "question": "What's the price of an option on AAPL?",
        "expected_behavior": "clarify_parameters",
        "expected_graph_state": "clarify_parameters",
        "rubric": {
            "recognizes_missing_params": {"expected": True, "weight": 0.5},
            "asks_for_strike": {"expected": True, "weight": 0.25},
            "asks_for_expiry": {"expected": True, "weight": 0.25}
        },
        "min_passing_score": 0.7
    },
]

# === OFF-TOPIC QUERIES ===

OFF_TOPIC: list[TestQuestion] = [
    {
        "id": "offtopic_001",
        "category": "off_topic",
        "question": "What's the weather in New York?",
        "expected_behavior": "recognize_off_topic",
        "expected_graph_state": "off_topic",
        "rubric": {
            "detects_off_topic": {"expected": True, "weight": 0.6},
            "polite_refusal": {"expected": True, "weight": 0.4}
        },
        "min_passing_score": 0.8
    },
    {
        "id": "offtopic_002",
        "category": "off_topic",
        "question": "Write me a poem about trading",
        "expected_behavior": "recognize_off_topic",
        "expected_graph_state": "off_topic",
        "rubric": {
            "detects_off_topic": {"expected": True, "weight": 0.6},
            "polite_refusal": {"expected": True, "weight": 0.4}
        },
        "min_passing_score": 0.8
    },
    {
        "id": "offtopic_003",
        "category": "off_topic",
        "question": "How do I make a sandwich?",
        "expected_behavior": "recognize_off_topic",
        "expected_graph_state": "off_topic",
        "rubric": {
            "detects_off_topic": {"expected": True, "weight": 0.6},
            "polite_refusal": {"expected": True, "weight": 0.4}
        },
        "min_passing_score": 0.8
    },
    {
        "id": "offtopic_004",
        "category": "off_topic",
        "question": "What's the capital of France?",
        "expected_behavior": "recognize_off_topic",
        "expected_graph_state": "off_topic",
        "rubric": {
            "detects_off_topic": {"expected": True, "weight": 0.6},
            "polite_refusal": {"expected": True, "weight": 0.4}
        },
        "min_passing_score": 0.8
    },
]

# === EDGE CASES ===

EDGE_CASES: list[TestQuestion] = [
    {
        "id": "edge_001",
        "category": "edge_case",
        "question": "Price a call on ZZZINVALID",
        "expected_behavior": "recognize_invalid_ticker",
        "expected_graph_state": "clarify_asset",
        "rubric": {
            "detects_invalid_ticker": {"expected": True, "weight": 0.5},
            "provides_helpful_error": {"expected": True, "weight": 0.5}
        },
        "min_passing_score": 0.8
    },
]


# === AGGREGATOR FUNCTIONS (Pure) ===

def get_all_test_questions() -> list[TestQuestion]:
    """Pure function: Return all test questions."""
    return (
        PRICING_VANILLA +
        PRICING_AMERICAN +
        PRICING_DIGITAL +
        EDUCATIONAL +
        EXOTIC_OPTIONS +
        CLARIFICATION +
        OFF_TOPIC +
        EDGE_CASES
    )


def filter_by_category(
    questions: list[TestQuestion],
    category: str
) -> list[TestQuestion]:
    """Pure function: Filter questions by category."""
    return [q for q in questions if q["category"] == category]


def get_categories() -> list[str]:
    """Pure function: Get list of all categories."""
    return [
        "pricing_vanilla",
        "pricing_american",
        "pricing_digital",
        "educational",
        "exotic_options",
        "clarification",
        "off_topic",
        "edge_case"
    ]


# Total: 27 focused, high-quality test questions across all graph states
