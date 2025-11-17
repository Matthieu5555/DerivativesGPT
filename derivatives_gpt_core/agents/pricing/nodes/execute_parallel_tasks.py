"""
Execute plan tasks in parallel groups (backward compatibility wrapper).

This module re-exports components for backward compatibility.
The actual implementation has been refactored into:
- workflow/execution/market_data_providers.py: Data provider protocol and YFinance implementation
- workflow/execution/task_executor.py: Individual task execution logic
- workflow/execution/parallel_executor.py: Parallel orchestration with asyncio
"""

from derivatives_gpt_core.workflow.execution.market_data_providers import (
    MarketDataProvider,
    YFinanceProvider
)
from derivatives_gpt_core.workflow.execution.task_executor import execute_task
from derivatives_gpt_core.workflow.execution.parallel_executor import (
    execute_plan,
    execute_parallel_group
)

# Re-export for backward compatibility
__all__ = [
    'MarketDataProvider',
    'YFinanceProvider',
    'execute_task',
    'execute_parallel_group',
    'execute_plan'
]
