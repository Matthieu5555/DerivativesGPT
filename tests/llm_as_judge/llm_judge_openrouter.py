"""
LLM-as-a-Judge Evaluation (OpenRouter Version)

Uses your OpenRouter API key with your choice of models.
Coexists with llm_judge_langsmith.py (which uses LangSmith's evaluation API).

Default model: Uses OPENROUTER_MODEL from .env (google/gemini-2.5-flash-lite)

Usage:
    # Evaluate a single run
    uv run python tests/evaluation/llm_judge_openrouter.py --run-id <run_id>

    # Evaluate all runs from today
    uv run python tests/evaluation/llm_judge_openrouter.py --batch-today

    # Use specific model
    uv run python tests/evaluation/llm_judge_openrouter.py --batch-today --model google/gemini-2.5-flash-lite
"""

import argparse
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load .env first
load_dotenv()

from langsmith import Client
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Import evaluation prompts from centralized location
from prompts.evaluation.llm_judge_prompts import (
    CORRECTNESS_PROMPT,
    COMPLETENESS_PROMPT,
    CLARITY_PROMPT,
    RAG_QUALITY_PROMPT
)


# ============================================================================
# FREE LLM EVALUATOR
# ============================================================================

def create_llm(model: str = None):
    """Create LLM using your OpenRouter API key"""
    # Use your existing OpenRouter key from .env
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in .env")

    # Default to the same model used in the app
    if not model:
        model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0,
        max_tokens=500
    )


def evaluate_with_llm(
    llm: ChatOpenAI,
    prompt_template: str,
    query: str,
    response: str
) -> Dict[str, Any]:
    """Evaluate using LLM"""
    prompt = prompt_template.format(query=query, response=response)

    messages = [
        SystemMessage(content="You are an expert evaluator. Return ONLY valid JSON."),
        HumanMessage(content=prompt)
    ]

    try:
        result = llm.invoke(messages)
        content = result.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        # Parse JSON
        parsed = json.loads(content)
        return parsed

    except Exception as e:
        print(f"Warning: Failed to parse LLM response: {e}")
        return {"score": 3, "reasoning": f"Evaluation failed: {e}"}


def calculate_timeliness(run) -> Dict[str, Any]:
    """Calculate timeliness score (no LLM needed)"""
    if not run.end_time or not run.start_time:
        return {"score": 0, "reasoning": "Missing timing data"}

    execution_time_ms = (run.end_time - run.start_time).total_seconds() * 1000

    if execution_time_ms < 2000:
        score = 5
        reasoning = f"Very fast ({execution_time_ms:.0f}ms)"
    elif execution_time_ms < 5000:
        score = 4
        reasoning = f"Fast ({execution_time_ms:.0f}ms)"
    elif execution_time_ms < 10000:
        score = 3
        reasoning = f"Acceptable ({execution_time_ms:.0f}ms)"
    elif execution_time_ms < 20000:
        score = 2
        reasoning = f"Slow ({execution_time_ms:.0f}ms)"
    else:
        score = 1
        reasoning = f"Very slow ({execution_time_ms:.0f}ms)"

    return {"score": score, "reasoning": reasoning}


# ============================================================================
# EVALUATION FUNCTIONS
# ============================================================================

def evaluate_single_run(
    run_id: str,
    criteria: List[str] = None,
    model: str = None
) -> Dict[str, Any]:
    """Evaluate a single run using OpenRouter LLM"""
    # Use EU endpoint from .env
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    client = Client(api_url=endpoint)

    # Get run
    try:
        run = client.read_run(run_id)
    except Exception as e:
        return {"error": f"Failed to read run: {e}"}

    # Extract query and response
    try:
        # Handle nested input structure
        if "input" in run.inputs and "messages" in run.inputs["input"]:
            query = run.inputs["input"]["messages"][0]["content"]
        elif "messages" in run.inputs:
            query = run.inputs["messages"][0]["content"]
        else:
            query = ""

        # Handle response
        if run.outputs and "messages" in run.outputs:
            response = run.outputs["messages"][-1]["content"]
        else:
            response = ""
    except Exception as e:
        return {"error": f"Failed to extract query/response: {e}"}

    if not query or not response:
        return {"error": "Missing query or response"}

    # Default to all criteria
    if not criteria:
        criteria = ["correctness", "completeness", "clarity", "rag_quality", "timeliness"]

    # Create LLM
    llm = create_llm(model)

    # Evaluate each criterion
    results = {}

    if "correctness" in criteria:
        print("  Evaluating correctness...")
        results["correctness"] = evaluate_with_llm(llm, CORRECTNESS_PROMPT, query, response)

    if "completeness" in criteria:
        print("  Evaluating completeness...")
        results["completeness"] = evaluate_with_llm(llm, COMPLETENESS_PROMPT, query, response)

    if "clarity" in criteria:
        print("  Evaluating clarity...")
        results["clarity"] = evaluate_with_llm(llm, CLARITY_PROMPT, query, response)

    if "rag_quality" in criteria:
        print("  Evaluating RAG quality...")
        results["rag_quality"] = evaluate_with_llm(llm, RAG_QUALITY_PROMPT, query, response)

    if "timeliness" in criteria:
        print("  Evaluating timeliness...")
        results["timeliness"] = calculate_timeliness(run)

    # Calculate average
    avg_score = sum(r["score"] for r in results.values()) / len(results)

    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "criteria_scores": results,
        "average_score": avg_score,
        "query": query[:100] + "..." if len(query) > 100 else query
    }


def evaluate_batch(
    project_name: str,
    since_hours: int = 24,
    criteria: List[str] = None,
    model: str = None
) -> List[Dict[str, Any]]:
    """Evaluate batch of runs"""
    # Use EU endpoint from .env
    endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    client = Client(api_url=endpoint)

    # Get runs
    since_time = datetime.now() - timedelta(hours=since_hours)

    try:
        runs = list(client.list_runs(
            project_name=project_name,
            start_time=since_time,
            is_root=True
        ))
    except Exception as e:
        print(f"Error listing runs: {e}")
        return []

    print(f"Found {len(runs)} runs to evaluate")

    results = []
    for i, run in enumerate(runs, 1):
        run_id_str = str(run.id)
        print(f"\n[{i}/{len(runs)}] Evaluating run {run_id_str[:8]}...")

        result = evaluate_single_run(run_id_str, criteria, model)

        if "error" in result:
            print(f"  ✗ Failed: {result['error']}")
        else:
            results.append(result)
            print(f"  ✓ Score: {result['average_score']:.2f}/5.0")

    return results


def print_summary(results: List[Dict[str, Any]]):
    """Print summary statistics"""
    if not results:
        print("\nNo results to summarize")
        return

    print("\n" + "="*80)
    print("EVALUATION SUMMARY")
    print("="*80)

    # Overall
    avg_overall = sum(r["average_score"] for r in results) / len(results)
    print(f"\nTotal Runs: {len(results)}")
    print(f"Average Score: {avg_overall:.2f}/5.0")

    # Per-criteria
    print("\nAverage by Criteria:")
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
        if len(results) > 0:
            pct = count / len(results) * 100
            bar = "█" * int(pct / 2)
            print(f"  {score}/5: {bar} {count} ({pct:.1f}%)")

    print("="*80 + "\n")

    # Show best and worst
    if results:
        best = max(results, key=lambda x: x["average_score"])
        worst = min(results, key=lambda x: x["average_score"])

        print("Best Run:")
        print(f"  Score: {best['average_score']:.2f}/5.0")
        print(f"  Query: {best['query']}")

        print("\nWorst Run:")
        print(f"  Score: {worst['average_score']:.2f}/5.0")
        print(f"  Query: {worst['query']}")
        print()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge (OpenRouter version)")
    parser.add_argument("--run-id", type=str, help="Evaluate single run")
    parser.add_argument("--batch-today", action="store_true", help="Evaluate all runs from today")
    parser.add_argument("--batch-hours", type=int, default=24, help="Evaluate last N hours")
    parser.add_argument("--criteria", type=str, help="Comma-separated criteria")
    parser.add_argument("--project", type=str, default="DerivativesGPT-v4", help="Project name")
    parser.add_argument("--model", type=str, help="Model to use (default: from .env OPENROUTER_MODEL)")

    args = parser.parse_args()

    criteria = args.criteria.split(",") if args.criteria else None

    if args.run_id:
        print(f"Evaluating run: {args.run_id}")
        result = evaluate_single_run(args.run_id, criteria, args.model)

        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nResults:")
            print(f"  Average Score: {result['average_score']:.2f}/5.0")
            print(f"  Criteria Scores:")
            for criterion, data in result["criteria_scores"].items():
                print(f"    {criterion:20s}: {data['score']}/5.0 - {data['reasoning']}")

    elif args.batch_today or args.batch_hours:
        hours = 24 if args.batch_today else args.batch_hours
        print(f"Evaluating runs from last {hours} hours...")
        default_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")
        print(f"Using model: {args.model or default_model}")

        results = evaluate_batch(
            project_name=args.project,
            since_hours=hours,
            criteria=criteria,
            model=args.model
        )

        print_summary(results)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
