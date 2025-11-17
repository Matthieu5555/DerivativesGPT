"""
Prompt Engineering Audit Tool
==============================

Audits all prompts against the 26 MBZUAI prompt engineering principles
to ensure best practices and workflow consistency.

The 26 MBZUAI Rules:
1. No politeness needed - get straight to the point
2. Integrate intended audience in prompt
3. Break down complex tasks into simpler prompts
4. Use affirmative directives (do, must) not negative (don't)
5. Use clarity phrases for explanations
6. Add incentive ("$xxx tip") [Optional for production]
7. Implement example-driven prompting (few-shot)
8. Format with ###Instruction###, ###Example###, ###Question###
9. Use phrases "Your task is" and "You MUST"
10. Use phrase "You will be penalized" [Optional]
11. Use phrase "Answer in a natural, human-like manner"
12. Use leading words like "think step by step"
13. Add "Ensure answer is unbiased and avoids stereotypes"
14. Allow model to ask questions to elicit requirements
15. Use "Teach me X and include a test" pattern
16. Assign a role to the LLM
17. Use delimiters
18. Repeat key words/phrases for emphasis
19. Combine Chain-of-Thought with few-shot
20. Use output primers (end with start of desired output)
21. For detailed content: "Write a detailed [type] on [topic]"
22. For revision: Specify grammar/vocab improvements without style changes
23. For multi-file code: Generate script to create files
24. For continuation: "Finish based on provided beginning"
25. Clearly state requirements (keywords, regulations, instructions)
26. For mimicking style: "Use same language as provided sample"
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
import importlib.util


# MBZUAI Rule Definitions
RULES = {
    "RULE_1_NO_POLITENESS": {
        "name": "No politeness needed",
        "check": lambda text: not any(word in text.lower() for word in ["please", "if you don't mind", "thank you", "i would like to", "could you"]),
        "severity": "LOW",
        "recommendation": "Remove politeness phrases - be direct"
    },
    "RULE_2_AUDIENCE": {
        "name": "Specify intended audience",
        "check": lambda text: any(phrase in text.lower() for phrase in ["you are an expert", "expert in", "you are a", "as an expert", "as a"]),
        "severity": "HIGH",
        "recommendation": "Add audience specification (e.g., 'You are an expert in derivatives pricing')"
    },
    "RULE_4_AFFIRMATIVE": {
        "name": "Use affirmative directives",
        "check": lambda text: text.lower().count("do ") + text.lower().count("must") > text.lower().count("don't") + text.lower().count("do not"),
        "severity": "MEDIUM",
        "recommendation": "Use 'do' instead of 'don't', positive instructions instead of negative"
    },
    "RULE_7_FEW_SHOT": {
        "name": "Example-driven prompting",
        "check": lambda text: "example" in text.lower() or "for instance" in text.lower() or '"""' in text or "```" in text,
        "severity": "HIGH",
        "recommendation": "Add few-shot examples to guide LLM behavior"
    },
    "RULE_8_FORMATTING": {
        "name": "Structured formatting",
        "check": lambda text: any(marker in text for marker in ["###", "**", "INSTRUCTION:", "EXAMPLE:", "QUESTION:", "OUTPUT:"]),
        "severity": "MEDIUM",
        "recommendation": "Use clear section markers (###Instruction###, ###Example###, etc.)"
    },
    "RULE_9_TASK_MUST": {
        "name": "Use 'Your task is' and 'You MUST'",
        "check": lambda text: "your task" in text.lower() or "you must" in text.lower(),
        "severity": "HIGH",
        "recommendation": "Add 'Your task is' or 'You MUST' for clarity"
    },
    "RULE_12_STEP_BY_STEP": {
        "name": "Leading words (step by step)",
        "check": lambda text: any(phrase in text.lower() for phrase in ["step by step", "think step by step", "step-by-step", "systematically"]),
        "severity": "MEDIUM",
        "recommendation": "Add 'think step by step' for complex reasoning"
    },
    "RULE_16_ROLE": {
        "name": "Assign role to LLM",
        "check": lambda text: any(phrase in text.lower() for phrase in ["you are", "act as", "as a", "you create", "you analyze", "you generate"]),
        "severity": "CRITICAL",
        "recommendation": "Start with clear role assignment (e.g., 'You are an expert financial analyst')"
    },
    "RULE_17_DELIMITERS": {
        "name": "Use delimiters",
        "check": lambda text: any(delimiter in text for delimiter in ['"""', "'''", "```", "###", "---", "====", "{{", "}}"]),
        "severity": "MEDIUM",
        "recommendation": "Use delimiters to separate sections and data"
    },
    "RULE_20_OUTPUT_PRIMER": {
        "name": "Output primers",
        "check": lambda text: text.strip().endswith(":") or text.strip().endswith("{{") or "respond with" in text.lower(),
        "severity": "LOW",
        "recommendation": "End prompt with beginning of desired output format"
    },
    "RULE_25_CLEAR_REQUIREMENTS": {
        "name": "Clear requirements stated",
        "check": lambda text: any(word in text.upper() for word in ["CRITICAL", "IMPORTANT", "REQUIRED", "MUST", "OUTPUT"]),
        "severity": "HIGH",
        "recommendation": "Explicitly state all requirements and constraints"
    }
}


def extract_prompts_from_file(filepath: Path) -> List[Tuple[str, str]]:
    """Extract all prompt strings from a Python file.

    Returns:
        List of (variable_name, prompt_text) tuples
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        prompts = []

        # Pattern 1: Multi-line string assignments ("""...""" or '''...''')
        pattern1 = r'(\w+)\s*=\s*"""(.*?)"""'
        for match in re.finditer(pattern1, content, re.DOTALL):
            var_name = match.group(1)
            prompt_text = match.group(2)
            if len(prompt_text.strip()) > 50:  # Only non-trivial prompts
                prompts.append((var_name, prompt_text))

        # Pattern 2: f-strings with """..."""
        pattern2 = r'(\w+)\s*=\s*f"""(.*?)"""'
        for match in re.finditer(pattern2, content, re.DOTALL):
            var_name = match.group(1)
            prompt_text = match.group(2)
            if len(prompt_text.strip()) > 50:
                prompts.append((var_name, prompt_text))

        # Pattern 3: Function that builds prompts (def build_*_prompt)
        pattern3 = r'def\s+(build_\w+_prompt|get_\w+_prompt)\s*\([^)]*\):\s*"""([^"]+)"""'
        for match in re.finditer(pattern3, content, re.DOTALL):
            func_name = match.group(1)
            docstring = match.group(2)
            # Extract prompt from function body
            func_start = content.find(f"def {func_name}")
            func_end = content.find("\n\ndef ", func_start + 1)
            if func_end == -1:
                func_end = len(content)
            func_body = content[func_start:func_end]

            # Find return statement with prompt
            return_match = re.search(r'return\s+f?"""(.*?)"""', func_body, re.DOTALL)
            if return_match:
                prompt_text = return_match.group(1)
                if len(prompt_text.strip()) > 50:
                    prompts.append((func_name, prompt_text))

        return prompts

    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []


def audit_prompt(prompt_text: str, prompt_name: str, filename: str) -> Dict:
    """Audit a single prompt against MBZUAI rules.

    Returns:
        Dict with audit results
    """
    results = {
        "prompt_name": prompt_name,
        "file": filename,
        "passed": [],
        "failed": [],
        "warnings": []
    }

    for rule_id, rule_def in RULES.items():
        passed = rule_def["check"](prompt_text)

        if passed:
            results["passed"].append({
                "rule": rule_id,
                "name": rule_def["name"]
            })
        else:
            failure = {
                "rule": rule_id,
                "name": rule_def["name"],
                "severity": rule_def["severity"],
                "recommendation": rule_def["recommendation"]
            }

            if rule_def["severity"] in ["CRITICAL", "HIGH"]:
                results["failed"].append(failure)
            else:
                results["warnings"].append(failure)

    return results


def audit_all_prompts() -> Dict:
    """Audit all prompts in the codebase."""
    cwd = Path.cwd()
    prompts_dir = cwd / "prompts"
    all_results = []

    # Find all Python files
    prompt_files = list(prompts_dir.rglob("*.py"))

    print(f"\n{'=' * 80}")
    print(f"PROMPT ENGINEERING AUDIT")
    print(f"{'=' * 80}")
    print(f"Auditing {len(prompt_files)} prompt files against 26 MBZUAI rules\n")

    for filepath in prompt_files:
        if filepath.name == "__init__.py":
            continue

        print(f"\n{'─' * 80}")
        print(f"File: {filepath.relative_to(cwd)}")
        print(f"{'─' * 80}")

        prompts = extract_prompts_from_file(filepath)

        if not prompts:
            print(f"  WARNING: No prompts found in this file")
            continue

        print(f"  Found {len(prompts)} prompt(s)\n")

        for prompt_name, prompt_text in prompts:
            result = audit_prompt(prompt_text, prompt_name, str(filepath.relative_to(cwd)))
            all_results.append(result)

            # Print summary for this prompt
            passed_count = len(result["passed"])
            failed_count = len(result["failed"])
            warning_count = len(result["warnings"])

            status = "[PASS]" if failed_count == 0 else "[FAIL]"
            print(f"  {status} {prompt_name}")
            print(f"     Passed: {passed_count} | Failed: {failed_count} | Warnings: {warning_count}")

            # Show critical/high failures
            if result["failed"]:
                for failure in result["failed"]:
                    print(f"     [{failure['severity']}] {failure['name']}")
                    print(f"        -> {failure['recommendation']}")

    # Print overall summary
    print(f"\n{'=' * 80}")
    print(f"AUDIT SUMMARY")
    print(f"{'=' * 80}")

    total_prompts = len(all_results)
    prompts_with_failures = sum(1 for r in all_results if r["failed"])
    prompts_with_warnings = sum(1 for r in all_results if r["warnings"] and not r["failed"])
    clean_prompts = total_prompts - prompts_with_failures - prompts_with_warnings

    print(f"\nTotal prompts audited: {total_prompts}")
    print(f"  [CLEAN] No issues: {clean_prompts}")
    print(f"  [WARN] Warnings only: {prompts_with_warnings}")
    print(f"  [FAIL] Critical/High failures: {prompts_with_failures}")

    # Aggregate most common failures
    print(f"\n{'─' * 80}")
    print(f"MOST COMMON ISSUES")
    print(f"{'─' * 80}")

    failure_counts = {}
    for result in all_results:
        for failure in result["failed"]:
            rule_name = failure["name"]
            failure_counts[rule_name] = failure_counts.get(rule_name, 0) + 1

    if failure_counts:
        for rule_name, count in sorted(failure_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"  - {rule_name}: {count} prompts")
    else:
        print(f"  No critical issues found!")

    # Workflow consistency check
    print(f"\n{'─' * 80}")
    print(f"WORKFLOW CONSISTENCY")
    print(f"{'─' * 80}")
    print(f"Checking that prompts don't contradict workflow...\n")

    # Check for specific anti-patterns
    workflow_issues = []

    for filepath in prompt_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Anti-pattern 1: Using deprecated option_type instead of product_type
        if "option_type" in content and "product_type" not in content:
            if "execution_planning" in str(filepath) or "parameter_extraction" in str(filepath):
                workflow_issues.append({
                    "file": str(filepath.relative_to(cwd)),
                    "issue": "Uses 'option_type' without mentioning 'product_type'",
                    "fix": "Update to use full product_type (american_put, digital_call, etc.)"
                })

        # Anti-pattern 2: LaTeX in educational prompts
        if "educational" in str(filepath) and ("\\frac" in content or "\\Delta" in content or "\\partial" in content):
            workflow_issues.append({
                "file": str(filepath.relative_to(cwd)),
                "issue": "Contains LaTeX formatting",
                "fix": "Use plain text notation (Delta = dV/dS, not $\\Delta = \\frac{dV}{dS}$)"
            })

        # Anti-pattern 3: Encouraging politeness
        if any(phrase in content.lower() for phrase in ["be polite", "polite language", "courteous"]):
            workflow_issues.append({
                "file": str(filepath.relative_to(cwd)),
                "issue": "Encourages politeness (contradicts Rule 1)",
                "fix": "Remove politeness requirements - LLMs don't need to be polite"
            })

    if workflow_issues:
        for issue in workflow_issues:
            print(f"  [WARNING] {issue['file']}")
            print(f"     Issue: {issue['issue']}")
            print(f"     Fix: {issue['fix']}\n")
    else:
        print(f"  [PASS] No workflow contradictions found!\n")

    return all_results


if __name__ == "__main__":
    audit_all_prompts()
