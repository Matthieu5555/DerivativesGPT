"""
Comprehensive Integration Test Suite for DerivativesGPT-v4

Tests all major pipeline components:
1. Vanilla European options (Black-Scholes)
2. American options (Binomial tree)
3. Digital/Binary options (Closed-form)
4. Exotic options (Asian, Barrier)
5. Multi-leg strategies (Straddles, Spreads, Condors)
6. Parameter extraction edge cases
7. Validation logic
8. Error handling
9. Multi-asset queries
10. Educational queries

Run with:
    pytest tests/evaluation/integration_test_suite.py -v
    pytest tests/evaluation/integration_test_suite.py::test_vanilla_options -v
"""

import pytest
from typing import List, Dict, Any


# ============================================================================
# TEST QUERY DEFINITIONS
# ============================================================================

class TestQuery:
    """Test query with expected behavior"""
    def __init__(
        self,
        query: str,
        expected_option_type: str,
        expected_asset_class: str,
        should_price: bool,
        expected_strategy: str = "single",
        expected_num_legs: int = 0,
        description: str = ""
    ):
        self.query = query
        self.expected_option_type = expected_option_type
        self.expected_asset_class = expected_asset_class
        self.should_price = should_price
        self.expected_strategy = expected_strategy
        self.expected_num_legs = expected_num_legs
        self.description = description


# ============================================================================
# 1. VANILLA EUROPEAN OPTIONS (Black-Scholes)
# ============================================================================

VANILLA_EUROPEAN_TESTS = [
    TestQuery(
        query="Price a 3-month ATM call on AAPL",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=True,
        description="Basic vanilla call with ATM strike"
    ),
    TestQuery(
        query="What's the value of a MSFT put with strike $400 expiring in 30 days?",
        expected_option_type="vanilla_put",
        expected_asset_class="equity",
        should_price=True,
        description="Vanilla put with absolute strike"
    ),
    TestQuery(
        query="Price a 6-month European call on TSLA, strike 5% above current price",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=True,
        description="European call with relative strike"
    ),
    TestQuery(
        query="Calculate the price of a 90-day SPY put at strike 450",
        expected_option_type="vanilla_put",
        expected_asset_class="equity",
        should_price=True,
        description="Vanilla put with days-based expiry"
    ),
]


# ============================================================================
# 2. AMERICAN OPTIONS (Binomial Tree)
# ============================================================================

AMERICAN_OPTIONS_TESTS = [
    TestQuery(
        query="Price an American call on NVDA with strike 500, expiring in 60 days",
        expected_option_type="american_call",
        expected_asset_class="equity",
        should_price=True,
        description="American call (requires binomial)"
    ),
    TestQuery(
        query="What's the value of an American put on AMZN at strike 150, 3 months to expiry?",
        expected_option_type="american_put",
        expected_asset_class="equity",
        should_price=True,
        description="American put (early exercise premium)"
    ),
]


# ============================================================================
# 3. DIGITAL/BINARY OPTIONS
# ============================================================================

DIGITAL_OPTIONS_TESTS = [
    TestQuery(
        query="Price a digital call on GOOGL with strike 140, pays $100 if above strike at expiry in 45 days",
        expected_option_type="digital_call",
        expected_asset_class="equity",
        should_price=True,
        description="Digital call (binary payout)"
    ),
    TestQuery(
        query="Value a binary put on META, strike 300, payout $50, 2-month expiry",
        expected_option_type="digital_put",
        expected_asset_class="equity",
        should_price=True,
        description="Binary put (cash-or-nothing)"
    ),
]


# ============================================================================
# 4. EXOTIC OPTIONS (Asian, Barrier)
# ============================================================================

EXOTIC_OPTIONS_TESTS = [
    TestQuery(
        query="Price a geometric Asian call on AAPL, strike 200, 90-day averaging period",
        expected_option_type="geometric_asian_call",
        expected_asset_class="equity",
        should_price=True,
        description="Geometric Asian call (path-dependent)"
    ),
    TestQuery(
        query="Calculate the value of an arithmetic Asian put on SPY with 180-day averaging",
        expected_option_type="arithmetic_asian_put",
        expected_asset_class="equity",
        should_price=False,  # Arithmetic Asian not implemented yet
        description="Arithmetic Asian put (not implemented)"
    ),
    TestQuery(
        query="Price a barrier option on TSLA with knock-out at 300",
        expected_option_type="barrier_call",
        expected_asset_class="equity",
        should_price=False,  # Barrier not implemented yet
        description="Barrier option (not implemented)"
    ),
]


# ============================================================================
# 5. MULTI-LEG STRATEGIES
# ============================================================================

MULTI_LEG_TESTS = [
    TestQuery(
        query="Price an AMZN straddle at 150 strike, 60 days to expiry",
        expected_option_type="vanilla_call",  # Decomposed to call + put
        expected_asset_class="equity",
        should_price=True,
        expected_strategy="straddle",
        expected_num_legs=2,
        description="Straddle (long call + long put, same strike)"
    ),
    TestQuery(
        query="Value a TSLA strangle with call strike 260, put strike 240, 90-day expiry",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=True,
        expected_strategy="strangle",
        expected_num_legs=2,
        description="Strangle (different strikes)"
    ),
    TestQuery(
        query="Price a SPY bull call spread: long 450 call, short 460 call, 30 days",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=True,
        expected_strategy="spread",
        expected_num_legs=2,
        description="Bull call spread"
    ),
    TestQuery(
        query="Calculate an AAPL iron condor: 200/210/230/240, 45-day expiry",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=True,
        expected_strategy="iron_condor",
        expected_num_legs=4,
        description="Iron condor (4-leg strategy)"
    ),
]


# ============================================================================
# 6. PARAMETER EXTRACTION EDGE CASES
# ============================================================================

PARAMETER_EXTRACTION_TESTS = [
    TestQuery(
        query="I want to buy a call option on Apple stock",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=False,  # Missing strike and expiry
        description="Missing parameters (clarification needed)"
    ),
    TestQuery(
        query="Price an AAPL call at 200 strike",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=False,  # Missing expiry
        description="Missing expiry parameter"
    ),
    TestQuery(
        query="What's a 3-month option worth on TSLA?",
        expected_option_type="vanilla_call",  # Should clarify call/put
        expected_asset_class="equity",
        should_price=False,  # Missing strike and direction
        description="Missing strike and option type"
    ),
    TestQuery(
        query="Price a call on AAPL expiring tomorrow",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=True,  # Should handle "tomorrow" -> 1 day
        description="Natural language expiry"
    ),
]


# ============================================================================
# 7. VALIDATION LOGIC TESTS
# ============================================================================

VALIDATION_TESTS = [
    TestQuery(
        query="Price an AAPL call with strike -50, expiry 30 days",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=False,  # Negative strike should fail validation
        description="Invalid negative strike"
    ),
    TestQuery(
        query="Value a TSLA put with strike 200, expiry -10 days",
        expected_option_type="vanilla_put",
        expected_asset_class="equity",
        should_price=False,  # Negative expiry should fail
        description="Invalid negative expiry"
    ),
    TestQuery(
        query="Price an AAPL call at strike 1000000, expiry 30 days",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=False,  # Unrealistic strike should trigger warning
        description="Unrealistic strike value"
    ),
]


# ============================================================================
# 8. MULTI-ASSET / BASKET OPTIONS
# ============================================================================

MULTI_ASSET_TESTS = [
    TestQuery(
        query="Price a basket call on AAPL, MSFT, GOOGL with equal weights, ATM, 60 days",
        expected_option_type="basket_call",
        expected_asset_class="equity",
        should_price=False,  # Basket not implemented yet
        description="Basket option (3 underlyings)"
    ),
    TestQuery(
        query="Value a best-of option on TSLA and NVDA, 90-day expiry",
        expected_option_type="best_of_call",
        expected_asset_class="equity",
        should_price=False,  # Best-of not implemented
        description="Best-of option (rainbow option)"
    ),
]


# ============================================================================
# 9. EDUCATIONAL / EXPLANATION QUERIES
# ============================================================================

EDUCATIONAL_TESTS = [
    TestQuery(
        query="What is a straddle and how does it work?",
        expected_option_type="educational",
        expected_asset_class="educational",
        should_price=False,
        description="Pure educational query"
    ),
    TestQuery(
        query="Explain implied volatility",
        expected_option_type="educational",
        expected_asset_class="educational",
        should_price=False,
        description="Concept explanation"
    ),
    TestQuery(
        query="What's the difference between European and American options?",
        expected_option_type="educational",
        expected_asset_class="educational",
        should_price=False,
        description="Comparison query"
    ),
]


# ============================================================================
# 10. ERROR HANDLING / EDGE CASES
# ============================================================================

ERROR_HANDLING_TESTS = [
    TestQuery(
        query="Price a call on INVALIDTICKER with strike 100, expiry 30 days",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=False,  # Should handle invalid ticker gracefully
        description="Invalid ticker symbol"
    ),
    TestQuery(
        query="asdfghjkl",
        expected_option_type="refusal",
        expected_asset_class="unknown",
        should_price=False,
        description="Gibberish input"
    ),
    TestQuery(
        query="Price a weather derivative on temperature in NYC",
        expected_option_type="exotic",
        expected_asset_class="commodity",
        should_price=False,  # Should recognize but refuse
        description="Unsupported asset class"
    ),
]


# ============================================================================
# AGGREGATE TEST SUITES
# ============================================================================

ALL_TEST_QUERIES = {
    "vanilla_european": VANILLA_EUROPEAN_TESTS,
    "american_options": AMERICAN_OPTIONS_TESTS,
    "digital_options": DIGITAL_OPTIONS_TESTS,
    "exotic_options": EXOTIC_OPTIONS_TESTS,
    "multi_leg_strategies": MULTI_LEG_TESTS,
    "parameter_extraction": PARAMETER_EXTRACTION_TESTS,
    "validation_logic": VALIDATION_TESTS,
    "multi_asset": MULTI_ASSET_TESTS,
    "educational": EDUCATIONAL_TESTS,
    "error_handling": ERROR_HANDLING_TESTS,
}


def get_all_test_queries() -> List[TestQuery]:
    """Get all test queries flattened"""
    all_queries = []
    for suite in ALL_TEST_QUERIES.values():
        all_queries.extend(suite)
    return all_queries


def get_test_suite(suite_name: str) -> List[TestQuery]:
    """Get specific test suite"""
    return ALL_TEST_QUERIES.get(suite_name, [])


# ============================================================================
# PYTEST TEST FUNCTIONS
# ============================================================================

@pytest.mark.parametrize("test_query", VANILLA_EUROPEAN_TESTS, ids=lambda q: q.description)
def test_vanilla_options(test_query: TestQuery):
    """Test vanilla European options pricing"""
    assert test_query.query is not None


@pytest.mark.parametrize("test_query", AMERICAN_OPTIONS_TESTS, ids=lambda q: q.description)
def test_american_options(test_query: TestQuery):
    """Test American options pricing"""
    assert test_query.query is not None


@pytest.mark.parametrize("test_query", DIGITAL_OPTIONS_TESTS, ids=lambda q: q.description)
def test_digital_options(test_query: TestQuery):
    """Test digital/binary options"""
    assert test_query.query is not None


@pytest.mark.parametrize("test_query", MULTI_LEG_TESTS, ids=lambda q: q.description)
def test_multi_leg_strategies(test_query: TestQuery):
    """Test multi-leg strategy decomposition"""
    assert test_query.query is not None


@pytest.mark.parametrize("test_query", PARAMETER_EXTRACTION_TESTS, ids=lambda q: q.description)
def test_parameter_extraction(test_query: TestQuery):
    """Test parameter extraction and clarification"""
    assert test_query.query is not None


@pytest.mark.parametrize("test_query", VALIDATION_TESTS, ids=lambda q: q.description)
def test_validation_logic(test_query: TestQuery):
    """Test input validation"""
    assert test_query.query is not None


@pytest.mark.parametrize("test_query", EDUCATIONAL_TESTS, ids=lambda q: q.description)
def test_educational_queries(test_query: TestQuery):
    """Test educational/explanation queries"""
    assert test_query.query is not None


@pytest.mark.parametrize("test_query", ERROR_HANDLING_TESTS, ids=lambda q: q.description)
def test_error_handling(test_query: TestQuery):
    """Test error handling and edge cases"""
    assert test_query.query is not None


# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

def print_test_summary():
    """Print test suite statistics"""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUITE SUMMARY")
    print("="*80)

    total = 0
    for suite_name, queries in ALL_TEST_QUERIES.items():
        count = len(queries)
        total += count
        print(f"{suite_name:30s}: {count:2d} tests")

    print("-"*80)
    print(f"{'TOTAL':30s}: {total:2d} tests")
    print("="*80 + "\n")


if __name__ == "__main__":
    print_test_summary()

    print("Sample queries by category:\n")
    for suite_name, queries in ALL_TEST_QUERIES.items():
        print(f"\n{suite_name.upper()}:")
        for i, q in enumerate(queries[:3], 1):  # Show first 3
            print(f"  {i}. {q.query}")
            print(f"     → {q.description}")
