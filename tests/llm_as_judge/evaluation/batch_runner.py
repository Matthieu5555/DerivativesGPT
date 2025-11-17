"""Batch evaluation runner - functional composition."""

import asyncio
from typing import Any
from langchain_core.messages import HumanMessage

from tests.llm_as_judge.datasets.test_questions import TestQuestion, get_all_test_questions, filter_by_category
from tests.llm_as_judge.judging.judge import evaluate_response


async def evaluate_question_batch(
    questions: list[TestQuestion],
    graph: Any,
    judge_llm: Any,
    batch_size: int = 3
) -> list[dict]:
    """
    Pure orchestration: Evaluate batch of questions in parallel.

    Args:
        questions: List of test questions
        graph: Compiled LangGraph instance
        judge_llm: LLM for judging
        batch_size: Number of questions to run in parallel

    Returns:
        List of evaluation results (no mutation)
    """
    results = []

    for batch in chunk_list(questions, batch_size):
        batch_results = await asyncio.gather(*[
            evaluate_single_question(q, graph, judge_llm)
            for q in batch
        ], return_exceptions=True)

        # Filter out exceptions and add valid results
        for result in batch_results:
            if isinstance(result, dict):
                results.append(result)
            elif isinstance(result, Exception):
                print(f"Error in batch: {result}")

    return results


async def evaluate_single_question(
    question: TestQuestion,
    graph: Any,
    judge_llm: Any
) -> dict:
    """
    Pure async function: Evaluate one question.

    Steps:
    1. Invoke graph with question
    2. Evaluate response with judge
    3. Return result dict

    Args:
        question: Test question
        graph: Compiled graph
        judge_llm: Judge LLM

    Returns:
        Evaluation result dict
    """
    try:
        # Invoke agent with evaluation mode enabled
        agent_response = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=question["question"])],
                "is_evaluation_mode": True  # Enable fail-fast mode for automated testing
            },
            config={
                "configurable": {
                    "thread_id": f"eval_{question['id']}",
                },
                "recursion_limit": 50,
            }
        )

        # Evaluate with judge
        evaluation = await evaluate_response(
            question=question,
            agent_response=agent_response,
            judge_llm=judge_llm,
        )

        return evaluation

    except Exception as e:
        # Return error result
        return {
            "question_id": question["id"],
            "category": question["category"],
            "overall_score": 0.0,
            "category_scores": {},
            "passed": False,
            "judge_feedback": f"Error: {str(e)}",
            "error": str(e)
        }


def chunk_list(items: list, size: int) -> list[list]:
    """Pure function: Split list into chunks."""
    return [items[i:i+size] for i in range(0, len(items), size)]


async def run_evaluation_suite(
    graph: Any,
    judge_llm: Any,
    suite_name: str = "all",
    batch_size: int = 3
) -> dict:
    """
    Pure orchestration: Run evaluation suite and return aggregated metrics.

    Args:
        graph: Compiled graph instance
        judge_llm: Judge LLM
        suite_name: "all" or specific category
        batch_size: Parallel batch size

    Returns:
        Summary dict with metrics
    """
    # Get questions
    all_questions = get_all_test_questions()

    if suite_name != "all":
        questions = filter_by_category(all_questions, suite_name)
    else:
        questions = all_questions

    print(f"Running evaluation on {len(questions)} questions (suite: {suite_name})...")

    # Run evaluations
    results = await evaluate_question_batch(questions, graph, judge_llm, batch_size)

    # Aggregate results (pure function)
    from tests.llm_as_judge.evaluation.aggregators import aggregate_results
    summary = aggregate_results(results)

    # Generate report (pure function)
    from tests.llm_as_judge.evaluation.formatters import format_evaluation_report
    report_text = format_evaluation_report(summary, results)

    # Save report
    from pathlib import Path
    from datetime import datetime

    report_path = Path("tests/llm_as_judge/reports") / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text)

    print(f"[PASS] Evaluation complete! Report saved to: {report_path}")
    print(f" Pass rate: {summary['summary']['pass_rate']*100:.1f}%")
    print(f"[STATS] Average score: {summary['summary']['avg_score']:.3f}")

    return summary
