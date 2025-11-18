"""
Developer tools for DerivativesGPT maintenance and documentation.

This package provides utilities for:
- Workflow structure extraction and documentation
- Code quality auditing
- Static analysis and consistency checks
"""

from pathlib import Path

__version__ = "1.0.0"
__all__ = ["WorkflowExplorer", "CodeAuditor"]

# Optional: Make tools importable
try:
    from dev_tools.dev_tool_explorer_workflow import WorkflowExplorer
    from dev_tools.dev_tool_audits import CodeAuditor
except ImportError:
    # Tools can still be run as scripts
    pass
