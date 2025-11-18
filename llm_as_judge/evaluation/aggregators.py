"""Result aggregators - pure functions."""

from itertools import groupby


def aggregate_results(results: list[dict]) -> dict:
    """
    Pure function: Aggregate evaluation results into summary.

    Args:
        results: List of individual evaluation results

    Returns:
        Summary statistics dict
    """
    total = len(results)
    passed = sum(1 for r in results if r.get("passed", False))

    category_groups = group_by_category(results)
    category_stats = {
        cat: calculate_category_stats(items)
        for cat, items in category_groups.items()
    }

    failed_tests = [
        {
            "id": r["question_id"],
            "category": r.get("category", "unknown"),
            "score": r["overall_score"],
            "reason": r.get("judge_feedback", "")[:200]
        }
        for r in results
        if not r.get("passed", False)
    ]

    return {
        "summary": {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "avg_score": calculate_avg_score(results),
            "pass_rate": passed / total if total > 0 else 0.0
        },
        "by_category": category_stats,
        "failed_tests": failed_tests
    }


def group_by_category(results: list[dict]) -> dict[str, list[dict]]:
    """Pure function: Group results by category."""
    sorted_results = sorted(results, key=lambda r: r.get("category", "unknown"))
    return {
        cat: list(items)
        for cat, items in groupby(sorted_results, key=lambda r: r.get("category", "unknown"))
    }


def calculate_category_stats(results: list[dict]) -> dict:
    """Pure function: Calculate stats for a category."""
    total = len(results)
    passed = sum(1 for r in results if r.get("passed", False))

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total > 0 else 0.0,
        "avg_score": calculate_avg_score(results)
    }


def calculate_avg_score(results: list[dict]) -> float:
    """Pure function: Calculate average score."""
    if not results:
        return 0.0
    return sum(r.get("overall_score", 0.0) for r in results) / len(results)
