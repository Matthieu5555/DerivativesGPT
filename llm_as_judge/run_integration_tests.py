"""
Integration Test Runner for DerivativesGPT-v4

Executes test queries against the full graph and validates results.

Usage:
    # Run all tests
    uv run python tests/evaluation/run_integration_tests.py

    # Run specific suite
    uv run python tests/evaluation/run_integration_tests.py --suite vanilla_european

    # Run with detailed output
    uv run python tests/evaluation/run_integration_tests.py --verbose

    # Save results to file
    uv run python tests/evaluation/run_integration_tests.py --output results.json
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.evaluation.integration_test_suite import (
    ALL_TEST_QUERIES,
    TestQuery,
    get_all_test_queries,
    get_test_suite
)
from derivatives_gpt_core.agent_graph_definition import create_option_pricing_graph
from derivatives_gpt_core.conversation_memory.checkpoint_manager import get_checkpointer
from langchain_core.messages import HumanMessage


class TestResult:
    """Result of a single test execution"""
    def __init__(
        self,
        query: TestQuery,
        success: bool,
        actual_option_type: str = None,
        actual_strategy: str = None,
        option_price: float = None,
        error: str = None,
        execution_time_ms: float = None
    ):
        self.query = query
        self.success = success
        self.actual_option_type = actual_option_type
        self.actual_strategy = actual_strategy
        self.option_price = option_price
        self.error = error
        self.execution_time_ms = execution_time_ms

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "query": self.query.query,
            "description": self.query.description,
            "expected_option_type": self.query.expected_option_type,
            "expected_strategy": self.query.expected_strategy,
            "should_price": self.query.should_price,
            "success": self.success,
            "actual_option_type": self.actual_option_type,
            "actual_strategy": self.actual_strategy,
            "option_price": self.option_price,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms
        }


async def run_single_test(
    query: TestQuery,
    graph: Any,
    thread_id: str,
    verbose: bool = False
) -> TestResult:
    """Execute a single test query against the graph"""
    import time

    if verbose:
        print(f"\n{'='*80}")
        print(f"Testing: {query.description}")
        print(f"Query: {query.query}")
        print(f"Expected: {query.expected_option_type} ({query.expected_strategy})")

    start_time = time.time()

    try:
        # Execute graph
        config = {"configurable": {"thread_id": thread_id}}
        final_state = await graph.ainvoke(
            {"messages": [HumanMessage(content=query.query)]},
            config=config
        )

        execution_time = (time.time() - start_time) * 1000  # Convert to ms

        # Extract results from final state
        actual_option_type = getattr(final_state, "option_type_classified", None)
        actual_strategy = getattr(final_state, "strategy_type", "single")
        option_price = getattr(final_state, "option_price", None)

        # Determine success
        success = True
        error = None

        # Check option type match
        if actual_option_type != query.expected_option_type:
            success = False
            error = f"Option type mismatch: expected {query.expected_option_type}, got {actual_option_type}"

        # Check strategy match (if multi-leg)
        if query.expected_strategy != "single":
            if actual_strategy != query.expected_strategy:
                success = False
                error = f"Strategy mismatch: expected {query.expected_strategy}, got {actual_strategy}"

        # Check pricing expectation
        if query.should_price:
            if option_price is None:
                success = False
                error = "Expected pricing but no price calculated"
        else:
            if option_price is not None and query.expected_option_type not in ["educational", "refusal"]:
                # Informational: priced when shouldn't have
                pass

        if verbose:
            print(f"Actual: {actual_option_type} ({actual_strategy})")
            print(f"Price: ${option_price:.2f}" if option_price else "Price: None")
            print(f"Time: {execution_time:.0f}ms")
            print(f"Status: {'✓ PASS' if success else '✗ FAIL'}")
            if error:
                print(f"Error: {error}")

        return TestResult(
            query=query,
            success=success,
            actual_option_type=actual_option_type,
            actual_strategy=actual_strategy,
            option_price=option_price,
            error=error,
            execution_time_ms=execution_time
        )

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000

        if verbose:
            print(f"Exception: {str(e)}")
            print(f"Status: ✗ FAIL")

        return TestResult(
            query=query,
            success=False,
            error=f"Exception: {str(e)}",
            execution_time_ms=execution_time
        )


async def run_test_suite(
    suite_name: str = None,
    verbose: bool = False,
    output_file: str = None
) -> Dict[str, Any]:
    """Run test suite and return results"""

    # Get test queries
    if suite_name:
        queries = get_test_suite(suite_name)
        if not queries:
            print(f"Error: Unknown suite '{suite_name}'")
            print(f"Available suites: {list(ALL_TEST_QUERIES.keys())}")
            return {}
    else:
        queries = get_all_test_queries()

    print(f"\n{'='*80}")
    print(f"RUNNING INTEGRATION TEST SUITE")
    print(f"{'='*80}")
    print(f"Suite: {suite_name or 'all'}")
    print(f"Queries: {len(queries)}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")

    # Initialize graph
    print("Initializing graph...")
    checkpointer = await get_checkpointer()
    graph = create_option_pricing_graph(checkpointer)
    print("Graph initialized.\n")

    # Run tests
    results = []
    passed = 0
    failed = 0

    for i, query in enumerate(queries, 1):
        thread_id = f"test-{suite_name or 'all'}-{i}"

        result = await run_single_test(
            query=query,
            graph=graph,
            thread_id=thread_id,
            verbose=verbose
        )

        results.append(result)

        if result.success:
            passed += 1
        else:
            failed += 1

        # Progress indicator (non-verbose)
        if not verbose:
            status = "✓" if result.success else "✗"
            print(f"  [{i}/{len(queries)}] {status} {query.description[:60]}")

    # Summary
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total:  {len(queries)}")
    print(f"Passed: {passed} ({passed/len(queries)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(queries)*100:.1f}%)")
    print(f"{'='*80}\n")

    # Failed tests detail
    if failed > 0:
        print("FAILED TESTS:")
        for result in results:
            if not result.success:
                print(f"  ✗ {result.query.description}")
                print(f"    Query: {result.query.query}")
                print(f"    Error: {result.error}")
        print()

    # Prepare results dict
    results_dict = {
        "timestamp": datetime.now().isoformat(),
        "suite": suite_name or "all",
        "total": len(queries),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / len(queries) * 100,
        "results": [r.to_dict() for r in results]
    }

    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results_dict, f, indent=2)
        print(f"Results saved to: {output_file}\n")

    return results_dict


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Run DerivativesGPT integration tests")
    parser.add_argument(
        "--suite",
        type=str,
        help=f"Test suite to run. Options: {list(ALL_TEST_QUERIES.keys())} or 'all'",
        default=None
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output (show each test execution)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Save results to JSON file",
        default=None
    )

    args = parser.parse_args()

    # Run tests
    asyncio.run(run_test_suite(
        suite_name=args.suite,
        verbose=args.verbose,
        output_file=args.output
    ))


if __name__ == "__main__":
    main()
