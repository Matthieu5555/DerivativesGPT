"""
Proof-of-Concept: Field Access Tracker
=======================================
Tracks which state fields are accessed by each agent to validate separation logic.
This POC helps us understand field usage patterns before enforcing strict isolation.
"""

from typing import Set, Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging
from .agent_detection import AgentType

logger = logging.getLogger(__name__)


# Import field definitions from agent_state_wrapper for consistency
from .agent_state_wrapper import (
    get_shared_fields,
    get_educational_fields,
    get_pricing_fields,
    get_rag_fields,
    get_allowed_fields
)

# Expose field sets for compatibility
SHARED_FIELDS = get_shared_fields()
EDUCATIONAL_FIELDS = get_educational_fields()
PRICING_FIELDS = get_pricing_fields()
RAG_FIELDS = get_rag_fields()


@dataclass
class FieldAccessLog:
    """Log entry for a field access"""
    field_name: str
    agent_type: AgentType
    operation: str  # 'read' or 'write'
    allowed: bool
    timestamp: float


@dataclass
class FieldAccessTracker:
    """
    Tracks field access patterns to validate agent separation.

    This is a POC tool that monitors which fields each agent accesses,
    helping us identify violations before enforcing strict boundaries.
    """

    # Track all access attempts
    access_log: List[FieldAccessLog] = field(default_factory=list)

    # Track violations (agent accessing wrong fields)
    violations: List[FieldAccessLog] = field(default_factory=list)

    # Summary statistics
    access_counts: Dict[AgentType, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )

    def is_field_allowed(self, field_name: str, agent_type: AgentType, operation: str = "read") -> bool:
        """
        Check if a field is allowed for the given agent.

        Args:
            field_name: The state field being accessed
            agent_type: The agent attempting access
            operation: 'read' or 'write' (defaults to 'read')

        Returns:
            True if access is allowed, False otherwise
        """
        # Use centralized access control logic
        allowed_fields = get_allowed_fields(agent_type, operation)
        return field_name in allowed_fields

    def track_access(
        self,
        field_name: str,
        agent_type: AgentType,
        operation: str = "read",
        timestamp: float = None
    ) -> bool:
        """
        Track a field access attempt.

        Args:
            field_name: The state field being accessed
            agent_type: The agent attempting access
            operation: 'read' or 'write'
            timestamp: When the access occurred (defaults to current time)

        Returns:
            True if access is allowed, False if it's a violation
        """
        import time
        if timestamp is None:
            timestamp = time.time()

        allowed = self.is_field_allowed(field_name, agent_type)

        # Create log entry
        log_entry = FieldAccessLog(
            field_name=field_name,
            agent_type=agent_type,
            operation=operation,
            allowed=allowed,
            timestamp=timestamp
        )

        # Add to logs
        self.access_log.append(log_entry)

        # Track violations
        if not allowed:
            self.violations.append(log_entry)
            logger.warning(
                f"🚨 VIOLATION: {agent_type} agent attempted {operation} "
                f"on unauthorized field '{field_name}'"
            )

        # Update statistics
        self.access_counts[agent_type][field_name] += 1

        return allowed

    def get_violations_by_agent(self, agent_type: AgentType) -> List[FieldAccessLog]:
        """Get all violations for a specific agent"""
        return [v for v in self.violations if v.agent_type == agent_type]

    def get_field_category(self, field_name: str) -> str:
        """Determine which category a field belongs to"""
        from .agent_state_wrapper import get_field_category as _get_category
        return _get_category(field_name)

    def generate_report(self) -> str:
        """
        Generate a summary report of field access patterns.

        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 60,
            "FIELD ACCESS TRACKING REPORT",
            "=" * 60,
            ""
        ]

        # Summary statistics
        report_lines.append(f"Total Accesses: {len(self.access_log)}")
        report_lines.append(f"Total Violations: {len(self.violations)}")
        report_lines.append("")

        # Per-agent statistics
        for agent_type in ["educational", "pricing", "unified"]:
            agent_accesses = [log for log in self.access_log if log.agent_type == agent_type]
            agent_violations = [log for log in self.violations if log.agent_type == agent_type]

            if not agent_accesses:
                continue

            report_lines.append(f"{agent_type.upper()} Agent:")
            report_lines.append(f"  Total accesses: {len(agent_accesses)}")
            report_lines.append(f"  Violations: {len(agent_violations)}")

            if agent_violations:
                report_lines.append("  Violated fields:")
                violated_fields = defaultdict(int)
                for v in agent_violations:
                    violated_fields[v.field_name] += 1

                for field_name, count in sorted(violated_fields.items(), key=lambda x: -x[1]):
                    category = self.get_field_category(field_name)
                    report_lines.append(f"    - {field_name} ({category}): {count}x")

            report_lines.append("")

        # Field usage summary
        report_lines.append("Field Usage Summary:")
        all_fields = set()
        for agent_fields in self.access_counts.values():
            all_fields.update(agent_fields.keys())

        for field_name in sorted(all_fields):
            category = self.get_field_category(field_name)
            accesses = []
            for agent_type in ["educational", "pricing", "unified"]:
                count = self.access_counts[agent_type].get(field_name, 0)
                if count > 0:
                    accesses.append(f"{agent_type}={count}")

            access_str = ", ".join(accesses)
            report_lines.append(f"  {field_name:30} [{category:12}] {access_str}")

        report_lines.append("")
        report_lines.append("=" * 60)

        return "\n".join(report_lines)


# Global tracker instance for POC
_global_tracker: FieldAccessTracker | None = None


def get_field_tracker() -> FieldAccessTracker:
    """Get or create the global field tracker instance"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = FieldAccessTracker()
    return _global_tracker


def reset_field_tracker():
    """Reset the global tracker (useful for testing)"""
    global _global_tracker
    _global_tracker = FieldAccessTracker()


def track_field_access(
    field_name: str,
    agent_type: AgentType,
    operation: str = "read"
) -> bool:
    """
    Convenience function to track field access.

    Args:
        field_name: The state field being accessed
        agent_type: The agent attempting access
        operation: 'read' or 'write'

    Returns:
        True if access is allowed, False if it's a violation
    """
    tracker = get_field_tracker()
    return tracker.track_access(field_name, agent_type, operation)
