"""
Code Audits - Functional implementation.

Automated code quality checks using pure functional programming.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import argparse


# ============================================================================
# DATA STRUCTURES (immutable)
# ============================================================================

def create_issue(
    severity: str,
    category: str,
    file_path: str,
    line_number: int,
    description: str,
    suggestion: str = ""
) -> Dict[str, Any]:
    """Create audit issue dict."""
    return {
        "severity": severity,
        "category": category,
        "file_path": file_path,
        "line_number": line_number,
        "description": description,
        "suggestion": suggestion
    }


# ============================================================================
# STATE SCHEMA EXTRACTION
# ============================================================================

def extract_state_fields(state_schema_file: Path) -> Set[str]:
    """Extract field names from OptionPricingState schema."""
    if not state_schema_file.exists():
        return set()

    with open(state_schema_file, 'r') as f:
        tree = ast.parse(f.read())

    fields = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "OptionPricingState":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
            break

    return fields


# ============================================================================
# DOCSTRING AUDITS
# ============================================================================

def audit_docstrings_in_file(file_path: Path, project_root: Path) -> List[Dict[str, Any]]:
    """Audit docstring coverage in a file."""
    issues = []

    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return issues

    rel_path = str(file_path.relative_to(project_root))

    for node in ast.walk(tree):
        # Check functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip private functions
            if node.name.startswith("_") and not node.name.startswith("__"):
                continue

            docstring = ast.get_docstring(node)

            if not docstring:
                issues.append(create_issue(
                    severity="warning",
                    category="docstring",
                    file_path=rel_path,
                    line_number=node.lineno,
                    description=f"Function '{node.name}' missing docstring",
                    suggestion="Add docstring with Args, Returns, and description"
                ))
            elif len(docstring) < 20:
                issues.append(create_issue(
                    severity="info",
                    category="docstring",
                    file_path=rel_path,
                    line_number=node.lineno,
                    description=f"Function '{node.name}' has minimal docstring ({len(docstring)} chars)",
                    suggestion="Expand docstring with more detail"
                ))

        # Check classes
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                docstring = ast.get_docstring(node)
                if not docstring:
                    issues.append(create_issue(
                        severity="warning",
                        category="docstring",
                        file_path=rel_path,
                        line_number=node.lineno,
                        description=f"Class '{node.name}' missing docstring",
                        suggestion="Add class docstring"
                    ))

    return issues


def audit_docstrings(core_dir: Path, project_root: Path) -> Tuple[List[Dict], Dict[str, int]]:
    """Audit docstrings across all files."""
    print("[INFO] Auditing docstrings...")

    all_issues = []
    stats = defaultdict(int)

    for py_file in core_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        issues = audit_docstrings_in_file(py_file, project_root)
        all_issues.extend(issues)

        for issue in issues:
            if "missing docstring" in issue["description"].lower():
                if "function" in issue["description"].lower():
                    stats["missing_docstrings"] += 1
                else:
                    stats["missing_class_docstrings"] += 1
            elif "minimal" in issue["description"].lower():
                stats["minimal_docstrings"] += 1

    return all_issues, dict(stats)


# ============================================================================
# TYPING AUDITS
# ============================================================================

def audit_typing_in_file(file_path: Path, project_root: Path) -> List[Dict[str, Any]]:
    """Audit type annotations in a file."""
    issues = []

    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return issues

    rel_path = str(file_path.relative_to(project_root))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip private and test functions
            if node.name.startswith("_"):
                continue

            # Check return type
            if node.returns is None:
                issues.append(create_issue(
                    severity="info",
                    category="typing",
                    file_path=rel_path,
                    line_number=node.lineno,
                    description=f"Function '{node.name}' missing return type annotation",
                    suggestion="Add -> Type annotation"
                ))

            # Check argument types
            for arg in node.args.args:
                if arg.arg in ("self", "cls"):
                    continue

                if arg.annotation is None:
                    issues.append(create_issue(
                        severity="info",
                        category="typing",
                        file_path=rel_path,
                        line_number=node.lineno,
                        description=f"Argument '{arg.arg}' in '{node.name}' missing type annotation",
                        suggestion=f"Add type hint for {arg.arg}"
                    ))

    return issues


def audit_typing(core_dir: Path, project_root: Path) -> Tuple[List[Dict], Dict[str, int]]:
    """Audit type annotations across all files."""
    print("🔤 Auditing type annotations...")

    all_issues = []
    stats = defaultdict(int)

    for py_file in core_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        issues = audit_typing_in_file(py_file, project_root)
        all_issues.extend(issues)

        for issue in issues:
            if "return type" in issue["description"]:
                stats["missing_return_types"] += 1
            elif "argument" in issue["description"].lower():
                stats["missing_arg_types"] += 1

    return all_issues, dict(stats)


# ============================================================================
# STATE FIELD AUDITS
# ============================================================================

def extract_state_field_accesses(file_path: Path) -> List[Tuple[str, int]]:
    """Extract state field accesses from file."""
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return []

    accesses = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "state":
                accesses.append((node.attr, node.lineno))

    return accesses


def audit_state_fields(
    core_dir: Path,
    project_root: Path,
    schema_fields: Set[str]
) -> Tuple[List[Dict], Dict[str, int]]:
    """Audit state field usage."""
    print(" Auditing state field usage...")

    if not schema_fields:
        print("   [WARNING]  No schema fields loaded, skipping")
        return [], {}

    all_issues = []
    field_usage = defaultdict(list)
    stats = defaultdict(int)

    nodes_dir = core_dir / "graph_nodes"

    for py_file in nodes_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        rel_path = str(py_file.relative_to(project_root))
        accesses = extract_state_field_accesses(py_file)

        for field_name, line_no in accesses:
            field_usage[field_name].append((py_file.name, line_no))

            # Check if field exists in schema
            if field_name not in schema_fields:
                all_issues.append(create_issue(
                    severity="error",
                    category="state",
                    file_path=rel_path,
                    line_number=line_no,
                    description=f"Field 'state.{field_name}' not in OptionPricingState schema",
                    suggestion=f"Add '{field_name}' to state schema or fix typo"
                ))
                stats["undefined_state_fields"] += 1

    # Check for unused fields
    used_fields = set(field_usage.keys())
    always_used = {"messages", "model_config"}
    unused_fields = schema_fields - used_fields - always_used

    for field in unused_fields:
        all_issues.append(create_issue(
            severity="info",
            category="state",
            file_path="derivatives_gpt_core/graph_state_schema.py",
            line_number=0,
            description=f"State field '{field}' defined but never used",
            suggestion="Remove if truly unused, or verify usage"
        ))
        stats["unused_state_fields"] += 1

    return all_issues, dict(stats)


# ============================================================================
# ERROR HANDLING AUDITS
# ============================================================================

def audit_error_handling_in_file(file_path: Path, project_root: Path) -> List[Dict[str, Any]]:
    """Audit error handling in a file."""
    issues = []

    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return issues

    rel_path = str(file_path.relative_to(project_root))

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Bare except
            if node.type is None:
                issues.append(create_issue(
                    severity="warning",
                    category="error_handling",
                    file_path=rel_path,
                    line_number=node.lineno,
                    description="Bare 'except:' clause catches all exceptions",
                    suggestion="Catch specific exception types (e.g., except ValueError:)"
                ))

            # Check for logging
            has_logging = any(
                isinstance(stmt, ast.Call) and
                isinstance(stmt.func, ast.Attribute) and
                stmt.func.attr in ["error", "warning", "exception"]
                for stmt in ast.walk(node)
            )

            if not has_logging and node.type:
                issues.append(create_issue(
                    severity="info",
                    category="error_handling",
                    file_path=rel_path,
                    line_number=node.lineno,
                    description="Exception caught but not logged",
                    suggestion="Add logger.error() or logger.exception()"
                ))

    return issues


def audit_error_handling(core_dir: Path, project_root: Path) -> Tuple[List[Dict], Dict[str, int]]:
    """Audit error handling across all files."""
    print("[WARNING]  Auditing error handling...")

    all_issues = []
    stats = defaultdict(int)

    for py_file in core_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        issues = audit_error_handling_in_file(py_file, project_root)
        all_issues.extend(issues)

        for issue in issues:
            if "bare" in issue["description"].lower():
                stats["bare_except"] += 1
            elif "not logged" in issue["description"]:
                stats["unlogged_exceptions"] += 1

    return all_issues, dict(stats)


# ============================================================================
# TEST COVERAGE AUDITS
# ============================================================================

def audit_test_coverage(core_dir: Path, tests_dir: Path, project_root: Path) -> Tuple[List[Dict], Dict[str, int]]:
    """Audit test coverage."""
    print("🧪 Auditing test coverage...")

    # Get implementation files
    impl_files = set()
    for py_file in core_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        impl_files.add(py_file.stem)

    # Get test files
    test_files = set()
    if tests_dir.exists():
        for test_file in tests_dir.glob("test_*.py"):
            tested_module = test_file.stem.replace("test_", "")
            test_files.add(tested_module)

    # Find untested modules
    skip_modules = {"__init__", "config", "constants", "exceptions"}
    untested = impl_files - test_files - skip_modules

    issues = []
    for module in sorted(untested):
        issues.append(create_issue(
            severity="info",
            category="test",
            file_path=f"derivatives_gpt_core/*/{module}.py",
            line_number=0,
            description=f"Module '{module}' has no corresponding test file",
            suggestion=f"Create tests/test_{module}.py"
        ))

    stats = {"untested_modules": len(untested)}

    return issues, stats


# ============================================================================
# REPORT GENERATION
# ============================================================================

def merge_stats(stats_list: List[Dict[str, int]]) -> Dict[str, int]:
    """Merge multiple stats dicts."""
    merged = defaultdict(int)
    for stats in stats_list:
        for key, value in stats.items():
            merged[key] += value
    return dict(merged)


def group_issues_by_category(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """Group issues by category."""
    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue["category"]].append(issue)
    return dict(grouped)


def group_issues_by_severity(issues: List[Dict]) -> Dict[str, List[Dict]]:
    """Group issues by severity."""
    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue["severity"]].append(issue)
    return dict(grouped)


def generate_report(all_issues: List[Dict], all_stats: Dict[str, int]) -> Dict[str, Any]:
    """Generate audit report."""
    by_category = group_issues_by_category(all_issues)
    by_severity = group_issues_by_severity(all_issues)

    return {
        "summary": {
            "total_issues": len(all_issues),
            "errors": len(by_severity.get("error", [])),
            "warnings": len(by_severity.get("warning", [])),
            "info": len(by_severity.get("info", [])),
            "stats": all_stats
        },
        "issues_by_category": by_category,
        "issues_by_severity": by_severity
    }


# ============================================================================
# OUTPUT
# ============================================================================

def print_report(report: Dict[str, Any]):
    """Print human-readable report."""
    summary = report["summary"]

    print("\n" + "=" * 60)
    print("📋 AUDIT REPORT")
    print("=" * 60)

    print(f"\n Total Issues: {summary['total_issues']}")
    print(f"   [ERROR] Errors:   {summary['errors']}")
    print(f"   [WARNING]  Warnings: {summary['warnings']}")
    print(f"   [INFO]  Info:     {summary['info']}")

    print("\n[STATS] Statistics:")
    for stat, count in sorted(summary["stats"].items()):
        print(f"   {stat.replace('_', ' ').title()}: {count}")

    print("\n" + "-" * 60)
    print("ISSUES BY CATEGORY")
    print("-" * 60)

    for category, issues in report["issues_by_category"].items():
        print(f"\n{category.upper()} ({len(issues)} issues):")

        for issue in issues[:5]:
            severity_icon = {"error": "[ERROR]", "warning": "[WARNING]", "info": "[INFO]"}.get(issue["severity"], "•")
            print(f"\n  {severity_icon} {issue['file_path']}:{issue['line_number']}")
            print(f"     {issue['description']}")
            if issue.get("suggestion"):
                print(f"     [TIP] {issue['suggestion']}")

        if len(issues) > 5:
            print(f"\n  ... and {len(issues) - 5} more {category} issues")

    print("\n" + "=" * 60)


def save_report(report: Dict[str, Any], output_path: Path, format: str = "json"):
    """Save report to file."""
    if format == "json":
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"[SUCCESS] Saved to {output_path}")


# ============================================================================
# MAIN AUDIT ORCHESTRATION
# ============================================================================

def run_all_audits(project_root: Path) -> Dict[str, Any]:
    """Run all audit checks - pure functional orchestration."""
    print("[INFO] Running code audits...")

    core_dir = project_root / "derivatives_gpt_core"
    tests_dir = project_root / "tests"
    state_schema_path = core_dir / "graph_state_schema.py"

    # Load state schema
    print("📖 Loading state schema...")
    schema_fields = extract_state_fields(state_schema_path)
    print(f"   Found {len(schema_fields)} state fields")

    # Run audits (all pure functions)
    docstring_issues, docstring_stats = audit_docstrings(core_dir, project_root)
    typing_issues, typing_stats = audit_typing(core_dir, project_root)
    state_issues, state_stats = audit_state_fields(core_dir, project_root, schema_fields)
    error_issues, error_stats = audit_error_handling(core_dir, project_root)
    test_issues, test_stats = audit_test_coverage(core_dir, tests_dir, project_root)

    # Combine results
    all_issues = docstring_issues + typing_issues + state_issues + error_issues + test_issues
    all_stats = merge_stats([docstring_stats, typing_stats, state_stats, error_stats, test_stats])

    # Generate report
    return generate_report(all_issues, all_stats)


def run_specific_audit(audit_type: str, project_root: Path) -> Dict[str, Any]:
    """Run specific audit check."""
    core_dir = project_root / "derivatives_gpt_core"
    tests_dir = project_root / "tests"
    state_schema_path = core_dir / "graph_state_schema.py"

    if audit_type == "docstrings":
        issues, stats = audit_docstrings(core_dir, project_root)
    elif audit_type == "typing":
        issues, stats = audit_typing(core_dir, project_root)
    elif audit_type == "state":
        schema_fields = extract_state_fields(state_schema_path)
        print(f"   Found {len(schema_fields)} state fields")
        issues, stats = audit_state_fields(core_dir, project_root, schema_fields)
    elif audit_type == "errors":
        issues, stats = audit_error_handling(core_dir, project_root)
    elif audit_type == "tests":
        issues, stats = audit_test_coverage(core_dir, tests_dir, project_root)
    else:
        return {"summary": {"total_issues": 0}, "issues_by_category": {}, "issues_by_severity": {}}

    return generate_report(issues, stats)


# ============================================================================
# CLI
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run code quality audits")
    parser.add_argument("--check", default="all",
                        choices=["all", "docstrings", "typing", "state", "errors", "tests"])
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--format", "-f", default="json", choices=["json", "text"])
    parser.add_argument("--quiet", "-q", action="store_true", help="No console output")

    args = parser.parse_args()

    # Project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Run audits
    if args.check == "all":
        report = run_all_audits(project_root)
    else:
        report = run_specific_audit(args.check, project_root)

    # Print unless quiet
    if not args.quiet:
        print_report(report)

    # Save if requested
    if args.output:
        output_path = project_root / args.output
        save_report(report, output_path, args.format)


if __name__ == "__main__":
    main()
