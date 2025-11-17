"""Pure functions for user feedback handling - functional approach."""

from typing import Any, Dict, Literal
from datetime import datetime


FeedbackCategory = Literal[
    "incorrect_price",
    "wrong_parameters",
    "slow_response",
    "good",
    "other"
]


def create_feedback_entry(
    score: float,
    category: FeedbackCategory | None = None,
    comment: str | None = None
) -> Dict[str, Any]:
    """
    Pure function: Create feedback entry.

    Args:
        score: 0.0 (negative) or 1.0 (positive)
        category: Feedback category
        comment: User comment

    Returns:
        Feedback dict ready for LangSmith
    """
    return {
        "key": "user_rating",
        "score": score,
        "comment": comment or category,
        "category": category,
        "timestamp": datetime.utcnow().isoformat()
    }


def log_feedback_to_langsmith(
    run_id: str,
    feedback: Dict[str, Any]
) -> None:
    """
    Side effect: Send feedback to LangSmith.

    Args:
        run_id: LangSmith run ID
        feedback: Feedback entry from create_feedback_entry()
    """
    try:
        from langsmith import Client

        client = Client()
        client.create_feedback(
            run_id=run_id,
            key=feedback["key"],
            score=feedback["score"],
            comment=feedback.get("comment"),
            metadata={"category": feedback.get("category")}
        )
    except Exception:
        # Silently fail - feedback shouldn't break app
        pass
