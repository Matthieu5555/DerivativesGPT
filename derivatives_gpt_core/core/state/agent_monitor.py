"""
Proof-of-Concept: Agent Monitoring
===================================
Lightweight monitoring infrastructure for agent separation POC.
Provides observability into agent routing and field access patterns.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import time
from .agent_detection import AgentType, detect_agent_type, AgentDetectionResult
from .field_tracker import get_field_tracker, track_field_access

logger = logging.getLogger(__name__)


@dataclass
class AgentSession:
    """Tracks agent context for a conversation session"""
    session_id: str
    current_agent: AgentType
    detection_result: AgentDetectionResult
    start_time: float = field(default_factory=time.time)
    node_executions: list = field(default_factory=list)
    field_accesses: list = field(default_factory=list)


# Global session storage for POC
_active_sessions: Dict[str, AgentSession] = {}


class AgentMonitor:
    """
    Lightweight monitoring for agent separation POC.

    Usage in nodes:
        monitor = AgentMonitor(state, node_name="classify_intent")
        monitor.log_node_entry()

        # Track field access
        value = monitor.read_field("spot_price", state.spot_price)

        monitor.log_node_exit()
    """

    def __init__(
        self,
        state: Any,
        node_name: str,
        session_id: Optional[str] = None
    ):
        self.state = state
        self.node_name = node_name
        self.session_id = session_id or "default"
        self.current_agent = self._get_or_detect_agent()
        self.start_time = time.time()

    def _get_or_detect_agent(self) -> AgentType:
        """Get current agent or detect from latest message"""
        # Try to get from state first
        if hasattr(self.state, "current_agent") and self.state.current_agent:
            return self.state.current_agent

        # Try to get from active session
        if self.session_id in _active_sessions:
            return _active_sessions[self.session_id].current_agent

        # Detect from latest message
        if hasattr(self.state, "messages") and self.state.messages:
            last_message = self.state.messages[-1]
            message_content = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )

            detection_result = detect_agent_type(message_content)

            # Create or update session
            _active_sessions[self.session_id] = AgentSession(
                session_id=self.session_id,
                current_agent=detection_result.agent_type,
                detection_result=detection_result
            )

            return detection_result.agent_type

        # Default to unified
        return "unified"

    def log_node_entry(self):
        """Log entry into a node"""
        logger.info(
            f"[{self.current_agent.upper()}] Entering node: {self.node_name}"
        )

        if self.session_id in _active_sessions:
            _active_sessions[self.session_id].node_executions.append({
                "node": self.node_name,
                "agent": self.current_agent,
                "timestamp": self.start_time,
                "status": "started"
            })

    def log_node_exit(self, status: str = "completed"):
        """Log exit from a node"""
        duration = time.time() - self.start_time
        logger.info(
            f"[{self.current_agent.upper()}] Exiting node: {self.node_name} "
            f"({status}, {duration:.2f}s)"
        )

        if self.session_id in _active_sessions:
            session = _active_sessions[self.session_id]
            if session.node_executions:
                session.node_executions[-1].update({
                    "status": status,
                    "duration": duration
                })

    def read_field(self, field_name: str, value: Any) -> Any:
        """
        Track a field read operation.

        Args:
            field_name: Name of the field being read
            value: The value being read

        Returns:
            The value (pass-through)
        """
        allowed = track_field_access(field_name, self.current_agent, "read")

        if not allowed:
            logger.warning(
                f"[{self.current_agent.upper()}] Unauthorized read of '{field_name}' "
                f"in node '{self.node_name}'"
            )

        # Track in session
        if self.session_id in _active_sessions:
            _active_sessions[self.session_id].field_accesses.append({
                "field": field_name,
                "operation": "read",
                "agent": self.current_agent,
                "node": self.node_name,
                "allowed": allowed,
                "timestamp": time.time()
            })

        return value

    def write_field(self, field_name: str, value: Any) -> Any:
        """
        Track a field write operation.

        Args:
            field_name: Name of the field being written
            value: The value being written

        Returns:
            The value (pass-through)
        """
        allowed = track_field_access(field_name, self.current_agent, "write")

        if not allowed:
            logger.warning(
                f"[{self.current_agent.upper()}] Unauthorized write to '{field_name}' "
                f"in node '{self.node_name}'"
            )

        # Track in session
        if self.session_id in _active_sessions:
            _active_sessions[self.session_id].field_accesses.append({
                "field": field_name,
                "operation": "write",
                "agent": self.current_agent,
                "node": self.node_name,
                "allowed": allowed,
                "timestamp": time.time()
            })

        return value

    def log_routing_decision(self, next_node: str, reason: str = ""):
        """Log a routing decision"""
        logger.info(
            f"[{self.current_agent.upper()}] Routing: {self.node_name} → {next_node}"
            + (f" ({reason})" if reason else "")
        )


def get_session_report(session_id: str) -> Optional[str]:
    """
    Generate a report for a specific session.

    Args:
        session_id: The session to report on

    Returns:
        Formatted report string or None if session not found
    """
    if session_id not in _active_sessions:
        return None

    session = _active_sessions[session_id]

    lines = [
        "=" * 60,
        f"AGENT SESSION REPORT: {session_id}",
        "=" * 60,
        "",
        f"Current Agent: {session.current_agent.upper()}",
        f"Detection Confidence: {session.detection_result.confidence:.0%}",
        f"Detection Reasoning: {session.detection_result.reasoning}",
        f"Session Duration: {time.time() - session.start_time:.2f}s",
        "",
        "Node Executions:",
    ]

    for i, execution in enumerate(session.node_executions, 1):
        duration = execution.get("duration", 0)
        lines.append(
            f"  {i}. {execution['node']} "
            f"[{execution['agent']}] "
            f"({execution['status']}, {duration:.2f}s)"
        )

    lines.append("")
    lines.append("Field Accesses:")

    # Group by field
    field_groups = {}
    for access in session.field_accesses:
        field = access["field"]
        if field not in field_groups:
            field_groups[field] = []
        field_groups[field].append(access)

    for field, accesses in sorted(field_groups.items()):
        reads = sum(1 for a in accesses if a["operation"] == "read")
        writes = sum(1 for a in accesses if a["operation"] == "write")
        violations = sum(1 for a in accesses if not a["allowed"])

        status = "[OK]" if violations == 0 else f"[ERR] ({violations} violations)"
        lines.append(f"  {status} {field}: {reads}R / {writes}W")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def reset_monitoring():
    """Reset all monitoring state (useful for testing)"""
    global _active_sessions
    _active_sessions = {}
    from .field_tracker import reset_field_tracker
    reset_field_tracker()
