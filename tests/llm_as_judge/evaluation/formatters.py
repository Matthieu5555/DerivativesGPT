"""Report formatters - pure functions."""

from datetime import datetime


def format_evaluation_report(summary: dict, results: list[dict]) -> str:
    """
    Pure function: Format evaluation summary as markdown.

    Args:
        summary: Summary dict from aggregators
        results: Raw evaluation results

    Returns:
        Markdown string
    """
    report_sections = [
        format_header(),
        format_summary_table(summary["summary"]),
        format_category_table(summary["by_category"]),
        format_failed_tests(summary["failed_tests"]),
    ]

    return "\n\n".join(report_sections)


def format_header() -> str:
    """Pure function: Format report header."""
    return f"""# DerivativesGPT Evaluation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
"""


def format_summary_table(summary: dict) -> str:
    """Pure function: Format summary as markdown table."""
    return f"""## Overall Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {summary['total_tests']} |
| **Passed** | {summary['passed']} |
| **Failed** | {summary['failed']} |
| **Pass Rate** | {summary['pass_rate']*100:.1f}% |
| **Average Score** | {summary['avg_score']:.3f} |

{_get_status_emoji(summary['pass_rate'])}
"""


def format_category_table(by_category: dict) -> str:
    """Pure function: Format category stats as markdown table."""
    if not by_category:
        return "## By Category\n\nNo category data available."

    rows = [
        f"| {cat} | {stats['passed']}/{stats['total']} | {stats['pass_rate']*100:.1f}% | {stats['avg_score']:.3f} |"
        for cat, stats in by_category.items()
    ]

    return f"""## Results by Category

| Category | Passed/Total | Pass Rate | Avg Score |
|----------|--------------|-----------|-----------|
{chr(10).join(rows)}
"""


def format_failed_tests(failed: list[dict]) -> str:
    """Pure function: Format failed tests as markdown list."""
    if not failed:
        return "## Failed Tests\n\n[PASS] **No failed tests!** All tests passed."

    items = [
        f"### {test['id']} ({test['category']})\n- **Score:** {test['score']:.2f}\n- **Reason:** {test['reason']}"
        for test in failed
    ]

    return f"""## Failed Tests

{chr(10).join(items)}
"""


def _get_status_emoji(pass_rate: float) -> str:
    """Pure function: Get status emoji based on pass rate."""
    if pass_rate >= 0.9:
        return "[PASS] **Excellent performance!**"
    elif pass_rate >= 0.75:
        return "✓ **Good performance**"
    elif pass_rate >= 0.5:
        return "[WARNING] **Needs improvement**"
    else:
        return "[FAIL] **Critical issues detected**"
