#!/usr/bin/env python
"""
Evaluation runner for multi-agent architecture.

Usage:
    uv run python run_agent_evaluation.py
    uv run python run_agent_evaluation.py --suite educational
"""

import asyncio
import argparse
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from derivatives_gpt_core.conversation_memory.checkpoint_manager import get_checkpointer
from derivatives_gpt_core.llm_provider import get_judge_llm
from tests.llm_as_judge.evaluation.batch_runner import run_evaluation_suite


async def main():
    """Main evaluation runner for agent architecture."""
    parser = argparse.ArgumentParser(description="Run DerivativesGPT Agent Evaluation")
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

    print("=" * 80)
    print("DerivativesGPT AGENT SEPARATION Evaluation")
    print("=" * 80)
    print(f"Architecture: Multi-Agent (Educational + Pricing + Orchestrator)")
    print(f"Suite: {args.suite}")
    print(f"Batch size: {args.batch_size}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Build orchestrator graph
    print("\n[1/3] Building orchestrator graph with agent separation...")
    try:
        checkpointer = await get_checkpointer()
        graph = build_orchestrator_graph()  # New multi-agent orchestrator
        print("✓ Orchestrator graph compiled successfully")
        print("  - Educational agent graph: LOADED")
        print("  - Pricing agent graph: LOADED")
        print("  - Agent routing: ENABLED")
    except Exception as e:
        print(f"✗ Failed to build graph: {e}")
        return 1

    # Get judge LLM
    print("\n[2/3] Initializing judge LLM...")
    try:
        judge_llm = get_judge_llm()
        print("✓ Judge LLM ready")
    except Exception as e:
        print(f"✗ Failed to initialize judge: {e}")
        return 1

    # Run evaluation
    print("\n[3/3] Running evaluation suite...")
    print("-" * 80)

    try:
        summary = await run_evaluation_suite(
            graph=graph,
            judge_llm=judge_llm,
            suite_name=args.suite,
            batch_size=args.batch_size
        )

        print("-" * 80)
        print("\n" + "=" * 80)
        print("EVALUATION COMPLETE - AGENT SEPARATION ARCHITECTURE")
        print("=" * 80)
        print(f"Total tests: {summary['summary']['total_tests']}")
        print(f"Passed: {summary['summary']['passed']} ({summary['summary']['pass_rate']*100:.1f}%)")
        print(f"Failed: {summary['summary']['failed']}")
        print(f"Average score: {summary['summary']['avg_score']:.3f}")
        print("=" * 80)

        # Show category breakdown
        print("\nResults by Category:")
        print("-" * 80)
        for category, data in summary['by_category'].items():
            passed = data['passed']
            total = data['total']
            pass_rate = data['pass_rate'] * 100
            avg_score = data['avg_score']
            print(f"  {category:20s} {passed:2d}/{total:2d} ({pass_rate:5.1f}%) - Avg: {avg_score:.3f}")
        print("=" * 80)

        return 0
    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
