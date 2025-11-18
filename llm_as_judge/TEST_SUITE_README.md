# Integration Test Suite for DerivativesGPT-v4

## 📊 Test Coverage

### 10 Test Categories | 40+ Test Cases

| Category | Tests | What It Tests |
|----------|-------|---------------|
| **Vanilla European** | 4 | Black-Scholes pricing, ATM/relative strikes |
| **American Options** | 2 | Binomial tree, early exercise premium |
| **Digital Options** | 2 | Binary payouts, cash-or-nothing |
| **Exotic Options** | 3 | Asian (geometric), barrier (not impl) |
| **Multi-Leg Strategies** | 4 | Straddles, strangles, spreads, condors |
| **Parameter Extraction** | 4 | Edge cases, missing params, clarification |
| **Validation Logic** | 3 | Negative values, unrealistic inputs |
| **Multi-Asset** | 2 | Basket options, best-of (not impl) |
| **Educational** | 3 | Pure explanation queries |
| **Error Handling** | 3 | Invalid tickers, gibberish, unsupported |

---

## 🚀 Quick Start

### Run All Tests
```bash
uv run python tests/evaluation/run_integration_tests.py
```

### Run Specific Suite
```bash
# Vanilla European options only
uv run python tests/evaluation/run_integration_tests.py --suite vanilla_european

# American options
uv run python tests/evaluation/run_integration_tests.py --suite american_options

# Multi-leg strategies
uv run python tests/evaluation/run_integration_tests.py --suite multi_leg_strategies
```

### Verbose Output
```bash
uv run python tests/evaluation/run_integration_tests.py --verbose
```

### Save Results to File
```bash
uv run python tests/evaluation/run_integration_tests.py --output results.json
```

---

## 📋 Sample Test Queries

### ✅ Implemented & Should Pass

```python
# Vanilla European
"Price a 3-month ATM call on AAPL"
"What's the value of a MSFT put with strike $400 expiring in 30 days?"

# American Options
"Price an American call on NVDA with strike 500, expiring in 60 days"
"What's the value of an American put on AMZN at strike 150, 3 months to expiry?"

# Digital Options
"Price a digital call on GOOGL with strike 140, pays $100 if above strike at expiry in 45 days"

# Exotic Options
"Price a geometric Asian call on AAPL, strike 200, 90-day averaging period"

# Multi-Leg Strategies
"Price an AMZN straddle at 150 strike, 60 days to expiry"
"Value a TSLA strangle with call strike 260, put strike 240, 90-day expiry"
"Price a SPY bull call spread: long 450 call, short 460 call, 30 days"
"Calculate an AAPL iron condor: 200/210/230/240, 45-day expiry"
```

### ⚠️ Expected to Fail (Not Implemented Yet)

```python
# Arithmetic Asian (only geometric implemented)
"Calculate the value of an arithmetic Asian put on SPY with 180-day averaging"

# Barrier Options
"Price a barrier option on TSLA with knock-out at 300"

# Basket/Multi-Asset
"Price a basket call on AAPL, MSFT, GOOGL with equal weights, ATM, 60 days"
```

---

## 📊 Test Output Format

### Console Output (Non-Verbose)
```
================================================================================
RUNNING INTEGRATION TEST SUITE
================================================================================
Suite: all
Queries: 43
Timestamp: 2025-11-10T18:00:00
================================================================================

Initializing graph...
Graph initialized.

  [1/43] ✓ Basic vanilla call with ATM strike
  [2/43] ✓ Vanilla put with absolute strike
  [3/43] ✗ Missing parameters (clarification needed)
  ...

================================================================================
TEST SUMMARY
================================================================================
Total:  43
Passed: 38 (88.4%)
Failed: 5 (11.6%)
================================================================================
```

### Verbose Output
```
================================================================================
Testing: Basic vanilla call with ATM strike
Query: Price a 3-month ATM call on AAPL
Expected: vanilla_call (single)
Actual: vanilla_call (single)
Price: $9.77
Time: 2341ms
Status: ✓ PASS
```

### JSON Output (--output results.json)
```json
{
  "timestamp": "2025-11-10T18:00:00",
  "suite": "vanilla_european",
  "total": 4,
  "passed": 4,
  "failed": 0,
  "pass_rate": 100.0,
  "results": [
    {
      "query": "Price a 3-month ATM call on AAPL",
      "description": "Basic vanilla call with ATM strike",
      "expected_option_type": "vanilla_call",
      "expected_strategy": "single",
      "should_price": true,
      "success": true,
      "actual_option_type": "vanilla_call",
      "actual_strategy": "single",
      "option_price": 9.77,
      "error": null,
      "execution_time_ms": 2341
    }
  ]
}
```

---

## 🧪 Using with Pytest

Run as pytest tests:
```bash
# All tests
pytest tests/evaluation/integration_test_suite.py -v

# Specific suite
pytest tests/evaluation/integration_test_suite.py::test_vanilla_options -v

# With markers
pytest tests/evaluation/integration_test_suite.py -m "not slow" -v
```

---

## 📈 Integration with LangSmith

Test results automatically appear in LangSmith:
1. Each test creates a unique thread_id: `test-{suite}-{number}`
2. All traces logged to your LangSmith project
3. View at: https://smith.langchain.com/

Filter traces by thread_id pattern:
```
thread_id:test-vanilla_european-*
```

---

## 🔧 Customizing Tests

### Add New Test Query

Edit `tests/evaluation/integration_test_suite.py`:

```python
NEW_CATEGORY_TESTS = [
    TestQuery(
        query="Your test query here",
        expected_option_type="vanilla_call",
        expected_asset_class="equity",
        should_price=True,
        expected_strategy="single",
        expected_num_legs=0,
        description="What this tests"
    ),
]

# Add to ALL_TEST_QUERIES
ALL_TEST_QUERIES["new_category"] = NEW_CATEGORY_TESTS
```

### Modify Validation Logic

Edit `tests/evaluation/run_integration_tests.py`:

```python
# Check option type match
if actual_option_type != query.expected_option_type:
    success = False
    error = f"Option type mismatch: expected {query.expected_option_type}, got {actual_option_type}"
```

---

## 📊 Expected Pass Rates by Category

| Category | Expected Pass Rate | Notes |
|----------|-------------------|-------|
| Vanilla European | 100% | Fully implemented |
| American Options | 100% | Binomial tree working |
| Digital Options | 100% | Closed-form formulas |
| Exotic Options | 33% | Only geometric Asian works |
| Multi-Leg | 100% | Decomposition working |
| Parameter Extraction | 50% | Clarification flow partial |
| Validation | 100% | All validations working |
| Multi-Asset | 0% | Not implemented |
| Educational | 100% | RAG retrieval working |
| Error Handling | 67% | Most edge cases handled |

**Overall Expected**: ~75-80% pass rate

---

## 🐛 Debugging Failed Tests

### Check State Attributes
```python
print(f"Final state keys: {list(final_state.__dict__.keys())}")
print(f"Option type: {final_state.option_type_classified}")
print(f"Strategy: {final_state.strategy_type}")
print(f"Price: {final_state.option_price}")
```

### View Full Trace in LangSmith
1. Copy the thread_id from test output
2. Search in LangSmith: `thread_id:test-suite-N`
3. View full execution trace with all node outputs

### Run Single Test in Isolation
```python
# In Python REPL
from tests.evaluation.run_integration_tests import run_single_test
from tests.evaluation.integration_test_suite import VANILLA_EUROPEAN_TESTS

query = VANILLA_EUROPEAN_TESTS[0]
result = await run_single_test(query, graph, "test-debug", verbose=True)
```

---

## 📝 Test Suite Maintenance

### When Adding New Features
1. Add test queries to `integration_test_suite.py`
2. Run full suite: `uv run python tests/evaluation/run_integration_tests.py`
3. Update expected pass rates in this README
4. Commit results to git

### Before Releases
```bash
# Run all tests with output
uv run python tests/evaluation/run_integration_tests.py --output release_v1.0.json

# Check pass rate >= 80%
grep "pass_rate" release_v1.0.json
```

---

## 🔗 Related Files

- `integration_test_suite.py` - Test query definitions
- `run_integration_tests.py` - Test runner
- `results.json` - Test results (generated)
- `../../LANGSMITH_IMPLEMENTATION_STATUS.md` - Instrumentation guide
