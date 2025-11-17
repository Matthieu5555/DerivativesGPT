#!/usr/bin/env python
"""
Simple evaluation runner script.

Usage:
    python tests/evaluation/run_evaluation.py --suite all
    python tests/evaluation/run_evaluation.py --category educational
    python tests/evaluation/run_evaluation.py --category pricing_vanilla
"""

import asyncio
import argparse
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from derivatives_gpt_core.core.graph.graph_builder import create_option_pricing_graph
from derivatives_gpt_core.conversation_memory.checkpoint_manager import get_checkpointer
from derivatives_gpt_core.llm_provider import get_judge_llm
from tests.evaluation.evaluation.batch_runner import run_evaluation_suite


async def main():
    """Main evaluation runner."""
    parser = argparse.ArgumentParser(description="Run DerivativesGPT evaluation suite")
    parser.add_argument(
        "--suite",
        default="all",
        help="Test suite to run (all, pricing_vanilla, educational, clarification, edge_case)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Number of questions to run in parallel (default: 3)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("DerivativesGPT Evaluation Runner")
    print("=" * 60)
    print(f"Suite: {args.suite}")
    print(f"Batch size: {args.batch_size}")
    print("=" * 60)

    # Build graph
    print("\n[1/3] Building graph...")
    checkpointer = await get_checkpointer()
    graph = create_option_pricing_graph(checkpointer)
    print("✓ Graph compiled")

    # Get judge LLM
    print("\n[2/3] Initializing judge LLM...")
    judge_llm = get_judge_llm()
    print("✓ Judge LLM ready")

    # Run evaluation
    print("\n[3/3] Running evaluation suite...")
    print("-" * 60)

    summary = await run_evaluation_suite(
        graph=graph,
        judge_llm=judge_llm,
        suite_name=args.suite,
        batch_size=args.batch_size
    )

    print("-" * 60)
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Total tests: {summary['summary']['total_tests']}")
    print(f"Passed: {summary['summary']['passed']} ({summary['summary']['pass_rate']*100:.1f}%)")
    print(f"Failed: {summary['summary']['failed']}")
    print(f"Average score: {summary['summary']['avg_score']:.3f}")
    print("=" * 60)

    if summary['summary']['failed'] > 0:
        print("\nFailed tests:")
        for test in summary['failed_tests'][:5]:  # Show first 5
            print(f"  - {test['id']}: {test['score']:.2f}")

    print("\n✓ Full report saved to tests/evaluation/reports/")


if __name__ == "__main__":
    asyncio.run(main())
