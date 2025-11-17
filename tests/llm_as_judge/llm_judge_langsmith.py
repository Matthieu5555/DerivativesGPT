"""
LLM-as-a-Judge Evaluation for DerivativesGPT-v4

Uses LangSmith's evaluator API to assess answer quality using LLM judges.

Evaluation Criteria:
1. Correctness - Is the calculated price accurate?
2. Completeness - Are all required parameters extracted?
3. Clarity - Is the explanation clear and well-structured?
4. Timeliness - Was the response generated in reasonable time?
5. RAG Quality - Are cited sources relevant and accurate?

Usage:
    # Evaluate a single run
    uv run python tests/evaluation/llm_judge_evaluation.py --run-id <run_id>

    # Evaluate all runs from today
    uv run python tests/evaluation/llm_judge_evaluation.py --batch-today

    # Evaluate with custom criteria
    uv run python tests/evaluation/llm_judge_evaluation.py --criteria correctness,clarity
"""

import argparse
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from langsmith import Client
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Run, Example


# ============================================================================
# EVALUATION CRITERIA DEFINITIONS
# ============================================================================

CORRECTNESS_PROMPT = """
You are an expert options pricing analyst evaluating the correctness of option price calculations.

Given:
- User Query: {input}
- System Response: {prediction}
- Expected Behavior: The system should correctly price options using appropriate models

Evaluate the correctness on a scale of 1-5:
- 5: Price is accurate (within 2% of theoretical value), correct model used
- 4: Price is mostly accurate (within 5%), minor methodology issues
- 3: Price has moderate errors (5-10%), some methodology concerns
- 2: Price has major errors (>10%), wrong model or parameters
- 1: Price is completely wrong or missing

Score: [1-5]
Reasoning: [Explain your assessment]

Output format:
{{
  "score": <1-5>,
  "reasoning": "<explanation>"
}}
"""

COMPLETENESS_PROMPT = """
You are an expert evaluating parameter extraction completeness.

Given:
- User Query: {input}
- System Response: {prediction}
- Required Parameters: ticker, strike, expiry, option_type

Evaluate completeness on a scale of 1-5:
- 5: All parameters correctly extracted, no clarification needed
- 4: All parameters extracted, minor clarification used
- 3: Most parameters extracted, some clarification needed
- 2: Missing critical parameters, extensive clarification needed
- 1: Failed to extract parameters, unable to price

Score: [1-5]
Reasoning: [Explain what was extracted/missing]

Output format:
{{
  "score": <1-5>,
  "reasoning": "<explanation>"
}}
"""

CLARITY_PROMPT = """
You are an expert evaluating explanation clarity and user experience.

Given:
- User Query: {input}
- System Response: {prediction}

Evaluate clarity on a scale of 1-5:
- 5: Exceptionally clear, well-structured, easy to understand
- 4: Clear and understandable, minor structural improvements possible
- 3: Somewhat clear, but could be better organized
- 2: Confusing structure, hard to follow
- 1: Incomprehensible or missing explanation

Score: [1-5]
Reasoning: [Explain clarity assessment]

Output format:
{{
  "score": <1-5>,
  "reasoning": "<explanation>"
}}
"""

RAG_QUALITY_PROMPT = """
You are an expert evaluating RAG (Retrieval-Augmented Generation) source quality.

Given:
- User Query: {input}
- System Response: {prediction}
- Retrieved Sources: Check if sources are cited

Evaluate RAG quality on a scale of 1-5:
- 5: Highly relevant sources, accurately cited, adds value
- 4: Relevant sources, properly cited, somewhat helpful
- 3: Sources present but marginally relevant
- 2: Sources cited but not relevant or inaccurate
- 1: No sources cited or completely irrelevant

Score: [1-5]
Reasoning: [Explain source relevance]

Output format:
{{
  "score": <1-5>,
  "reasoning": "<explanation>"
}}
"""

TIMELINESS_PROMPT = """
You are an expert evaluating response timeliness.

Given:
- User Query: {input}
- System Response: {prediction}
- Execution Time: {execution_time_ms} ms

Evaluate timeliness on a scale of 1-5:
- 5: Very fast (<2 seconds)
- 4: Fast (2-5 seconds)
- 3: Acceptable (5-10 seconds)
- 2: Slow (10-20 seconds)
- 1: Very slow (>20 seconds)

Score: [1-5]
Reasoning: [Explain timing assessment]

Output format:
{{
  "score": <1-5>,
  "reasoning": "<explanation>"
}}
"""


# ============================================================================
# EVALUATOR FUNCTIONS
# ============================================================================

def create_correctness_evaluator():
    """Create LLM evaluator for correctness"""
    return LangChainStringEvaluator(
        "criteria",
        config={
            "criteria": {
                "correctness": "Is the option price calculation correct and using appropriate models?"
            },
            "llm": {"model": "gpt-4", "temperature": 0},
        },
        prepare_data=lambda run, example: {
            "input": run.inputs["messages"][0].content if run.inputs else "",
            "prediction": run.outputs["messages"][-1].content if run.outputs else "",
        }
    )


def create_completeness_evaluator():
    """Create LLM evaluator for parameter completeness"""
    return LangChainStringEvaluator(
        "criteria",
        config={
            "criteria": {
                "completeness": "Are all required parameters (ticker, strike, expiry, option_type) extracted?"
            },
            "llm": {"model": "gpt-4", "temperature": 0},
        },
        prepare_data=lambda run, example: {
            "input": run.inputs["messages"][0].content if run.inputs else "",
            "prediction": run.outputs["messages"][-1].content if run.outputs else "",
        }
    )


def create_clarity_evaluator():
    """Create LLM evaluator for clarity"""
    return LangChainStringEvaluator(
        "criteria",
        config={
            "criteria": {
                "clarity": "Is the explanation clear, well-structured, and easy to understand?"
            },
            "llm": {"model": "gpt-4", "temperature": 0},
        },
        prepare_data=lambda run, example: {
            "input": run.inputs["messages"][0].content if run.inputs else "",
            "prediction": run.outputs["messages"][-1].content if run.outputs else "",
        }
    )


def create_rag_quality_evaluator():
    """Create LLM evaluator for RAG source quality"""
    return LangChainStringEvaluator(
        "criteria",
        config={
            "criteria": {
                "rag_quality": "Are the retrieved sources relevant, accurate, and properly cited?"
            },
            "llm": {"model": "gpt-4", "temperature": 0},
        },
        prepare_data=lambda run, example: {
            "input": run.inputs["messages"][0].content if run.inputs else "",
            "prediction": run.outputs["messages"][-1].content if run.outputs else "",
        }
    )


def create_timeliness_evaluator():
    """Create evaluator for response timeliness"""
    def timeliness_metric(run: Run, example: Example = None) -> Dict[str, Any]:
        """Calculate timeliness score based on execution time"""
        if not run.end_time or not run.start_time:
            return {"score": 0, "reasoning": "Missing timing data"}

        execution_time_ms = (run.end_time - run.start_time).total_seconds() * 1000

        if execution_time_ms < 2000:
            score = 5
            reasoning = f"Very fast response ({execution_time_ms:.0f}ms)"
        elif execution_time_ms < 5000:
            score = 4
            reasoning = f"Fast response ({execution_time_ms:.0f}ms)"
        elif execution_time_ms < 10000:
            score = 3
            reasoning = f"Acceptable response time ({execution_time_ms:.0f}ms)"
        elif execution_time_ms < 20000:
            score = 2
            reasoning = f"Slow response ({execution_time_ms:.0f}ms)"
        else:
            score = 1
            reasoning = f"Very slow response ({execution_time_ms:.0f}ms)"

        return {
            "key": "timeliness",
            "score": score,
            "reasoning": reasoning
        }

    return timeliness_metric


# ============================================================================
# EVALUATION RUNNERS
# ============================================================================

def evaluate_single_run(
    run_id: str,
    criteria: List[str] = None
) -> Dict[str, Any]:
    """
    Evaluate a single LangSmith run.

    Args:
        run_id: LangSmith run ID
        criteria: List of criteria to evaluate (default: all)

    Returns:
        Dict with evaluation scores
    """
    client = Client()

    # Get run
    run = client.read_run(run_id)

    # Default to all criteria
    if not criteria:
        criteria = ["correctness", "completeness", "clarity", "rag_quality", "timeliness"]

    # Create evaluators
    evaluators = []
    if "correctness" in criteria:
        evaluators.append(create_correctness_evaluator())
    if "completeness" in criteria:
        evaluators.append(create_completeness_evaluator())
    if "clarity" in criteria:
        evaluators.append(create_clarity_evaluator())
    if "rag_quality" in criteria:
        evaluators.append(create_rag_quality_evaluator())
    if "timeliness" in criteria:
        evaluators.append(create_timeliness_evaluator())

    # Run evaluation
    results = {}
    for evaluator in evaluators:
        if callable(evaluator):
            # Custom metric function
            result = evaluator(run)
            results[result["key"]] = {
                "score": result["score"],
                "reasoning": result["reasoning"]
            }
        else:
            # LangChain evaluator
            result = evaluator.evaluate_run(run)
            results[result.key] = {
                "score": result.score,
                "reasoning": result.comment
            }

    # Calculate average score
    avg_score = sum(r["score"] for r in results.values()) / len(results)

    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "criteria_scores": results,
        "average_score": avg_score
    }


def evaluate_batch(
    project_name: str,
    since_hours: int = 24,
    criteria: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate all runs from a project within a time window.

    Args:
        project_name: LangSmith project name
        since_hours: Evaluate runs from last N hours
        criteria: List of criteria to evaluate

    Returns:
        List of evaluation results
    """
    client = Client()

    # Get runs from last N hours
    since_time = datetime.now() - timedelta(hours=since_hours)

    runs = client.list_runs(
        project_name=project_name,
        start_time=since_time,
        is_root=True  # Only root runs
    )

    results = []
    for run in runs:
        try:
            result = evaluate_single_run(run.id, criteria)
            results.append(result)
            print(f"✓ Evaluated run {run.id}: avg score {result['average_score']:.2f}")
        except Exception as e:
            print(f"✗ Failed to evaluate run {run.id}: {e}")

    return results


# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

def print_summary(results: List[Dict[str, Any]]):
    """Print evaluation summary statistics"""
    if not results:
        print("No results to summarize")
        return

    print("\n" + "="*80)
    print("EVALUATION SUMMARY")
    print("="*80)

    # Overall stats
    avg_overall = sum(r["average_score"] for r in results) / len(results)
    print(f"\nTotal Runs Evaluated: {len(results)}")
    print(f"Average Overall Score: {avg_overall:.2f}/5.0")

    # Per-criteria averages
    print("\nAverage Scores by Criteria:")
    criteria_scores = {}
    for result in results:
        for criterion, data in result["criteria_scores"].items():
            if criterion not in criteria_scores:
                criteria_scores[criterion] = []
            criteria_scores[criterion].append(data["score"])

    for criterion, scores in criteria_scores.items():
        avg = sum(scores) / len(scores)
        print(f"  {criterion:20s}: {avg:.2f}/5.0")

    # Distribution
    print("\nScore Distribution:")
    for score in [5, 4, 3, 2, 1]:
        count = sum(1 for r in results if round(r["average_score"]) == score)
        pct = count / len(results) * 100
        bar = "█" * int(pct / 2)
        print(f"  {score}/5: {bar} {count} ({pct:.1f}%)")

    print("="*80 + "\n")


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge Evaluation")
    parser.add_argument("--run-id", type=str, help="Evaluate single run by ID")
    parser.add_argument("--batch-today", action="store_true", help="Evaluate all runs from today")
    parser.add_argument("--batch-hours", type=int, default=24, help="Evaluate runs from last N hours")
    parser.add_argument(
        "--criteria",
        type=str,
        help="Comma-separated criteria (correctness,completeness,clarity,rag_quality,timeliness)"
    )
    parser.add_argument("--project", type=str, default="DerivativesGPT-v4", help="LangSmith project name")

    args = parser.parse_args()

    # Parse criteria
    criteria = args.criteria.split(",") if args.criteria else None

    if args.run_id:
        # Evaluate single run
        print(f"Evaluating run: {args.run_id}")
        result = evaluate_single_run(args.run_id, criteria)
        print(f"\nResults:")
        print(f"  Average Score: {result['average_score']:.2f}/5.0")
        print(f"  Criteria Scores:")
        for criterion, data in result["criteria_scores"].items():
            print(f"    {criterion:20s}: {data['score']}/5.0 - {data['reasoning']}")

    elif args.batch_today or args.batch_hours:
        # Evaluate batch
        hours = 24 if args.batch_today else args.batch_hours
        print(f"Evaluating all runs from last {hours} hours...")

        results = evaluate_batch(
            project_name=args.project,
            since_hours=hours,
            criteria=criteria
        )

        print_summary(results)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
