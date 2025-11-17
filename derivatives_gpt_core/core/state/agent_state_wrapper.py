"""
Agent State Wrapper - Full Implementation
==========================================
Wraps BaseAgentState with enforced agent-aware access control.

This is the core of the agent separation architecture, enforcing field boundaries
between educational and pricing agents.
"""

from typing import Any, Dict, Optional, Set, Literal, List
from functools import lru_cache
import logging
import time
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)

# Define agent types
AgentType = Literal["educational", "pricing", "unified"]


# ============================================================================
# FIELD CATEGORIZATION
# ============================================================================

@lru_cache(maxsize=1)
def get_shared_fields() -> Set[str]:
    """
    Fields accessible by all agents.
    These are core conversation and classification fields needed for routing.
    """
    return {
        # Conversation
        "messages",

        # Initial Classification (binary option-related check)
        "is_option_related",
        "initial_reasoning",
        "extracted_ticker",

        # Detailed Classification (response type determination)
        "can_price",
        "product_type",
        "features_detected",
        "asset_class",
        "response_type",
        "reasoning",

        # Post-Augmentation Classification
        "asset_type_classified",
        "option_type_classified",
        "clarification_context",

        # Shared metadata
        "ticker",  # Shared - both agents need ticker context
        "is_evaluation_mode",  # Shared - affects routing behavior
        "chart_generated",  # Shared - affects UI state

        # Agent context (new fields)
        "detected_agent_type",
        "agent_confidence",
        "agent_reasoning",
        "current_agent",

        # Conversation context
        "last_agent",
        "last_topic",
        "conversation_depth",
        "is_follow_up",

        # Loop Protection (moved to BaseAgentState)
        "extraction_attempts",
        "max_extraction_attempts",
        "clarification_attempts",
        "max_clarification_attempts",
        "extraction_successful",  # Needed for routing
        "spot_price",  # Moved from pricing-only to shared
        "strike_price",  # Needed for routing logic in old launcher
        "execution_plan",  # Needed for execution in old launcher
        "time_to_expiry_days",  # Needed for pricing execution
        "volatility",  # Needed for pricing execution
        "risk_free_rate",  # Needed for pricing execution
        "option_type",  # Needed for pricing execution
        "strategy_type",  # Needed for pricing execution
        "multi_leg",  # Needed for pricing execution
    }


@lru_cache(maxsize=1)
def get_educational_fields() -> Set[str]:
    """
    Fields exclusive to the educational agent.
    Used for explanation generation, quality assessment, and adaptive learning.
    """
    return {
        # Explanation Content
        "explanation_text",
        "explanation_quality_score",
        "explanation_attempt_count",
        "explanation_critique",

        # User Assessment
        "verification_questions",
        "user_understanding_score",
        "user_comprehension_assessment",
        "user_confusion_signals",
        "adaptive_difficulty_level",

        # Conversation Tracking (orthogonal module)
        "educational_context",

        # Educational RAG
        # Note: rag_sources, rag_query, reformulated_rag can be used by both
        # but educational agent has exclusive read/write
    }


@lru_cache(maxsize=1)
def get_pricing_fields() -> Set[str]:
    """
    Fields exclusive to the pricing agent.
    Used for parameter extraction, validation, execution, and pricing.
    """
    return {
        # Single Asset Parameters
        # "spot_price",  # Now in shared
        # "strike_price",  # Now in shared
        # "time_to_expiry_days",  # Now in shared
        # "volatility",  # Now in shared
        # "risk_free_rate",  # Now in shared
        # "option_type",  # Now in shared

        # Multi-Asset Parameters
        "is_multi_asset",
        "num_assets",
        "assets",

        # Multi-Leg Strategy
        # "strategy_type",  # Now in shared
        # "multi_leg",  # Now in shared
        "legs",

        # Exotic Parameters
        "barrier_level",
        "barrier_type",
        "averaging_type",
        "averaging_period_days",
        "lookback_type",
        "exotic_tickers",
        "asset_weights",
        "basket_type",
        "compound_type",
        "underlying_strike",
        "compound_strike",
        "variance_strike",
        "volatility_strike",

        # Execution
        # "execution_plan",  # Now in shared
        "plan_generated",
        "can_execute",
        "execution_results",

        # Extraction (moved to BaseAgentState as shared fields)
        "ticker_extraction_successful",
        # "extraction_successful",  # Now in shared
        # "extraction_attempts",  # Now in shared
        # "max_extraction_attempts",  # Now in shared

        # Validation
        "validation_errors",
        "validation_warnings",
        "validation_attempt",
        "max_validation_retries",

        # Clarification (moved to BaseAgentState as shared fields)
        # "clarification_attempts",  # Now in shared
        # "max_clarification_attempts",  # Now in shared

        # Human Approval (legacy)
        "human_approved",
        "human_feedback",

        # Pricing Results
        "option_price",
        "price_breakdown",
    }


@lru_cache(maxsize=1)
def get_rag_fields() -> Set[str]:
    """
    RAG fields that can be accessed by both agents.
    Each agent may use RAG differently (educational vs pricing context).
    """
    return {
        "rag_sources",
        "rag_query",
        "reformulated_rag",
        "web_search_results",
        "web_search_query",
    }


def get_allowed_fields(agent_type: AgentType, operation: str = "read") -> Set[str]:
    """
    Get the set of fields allowed for an agent type and operation.

    Args:
        agent_type: The agent requesting access
        operation: 'read' or 'write'

    Returns:
        Set of allowed field names
    """
    shared = get_shared_fields()
    rag = get_rag_fields()

    if agent_type == "unified":
        # Unified agent has access to everything
        return shared | rag | get_educational_fields() | get_pricing_fields()

    elif agent_type == "educational":
        # Educational agent: shared + rag + educational fields
        allowed = shared | rag | get_educational_fields()

        # Educational can READ certain pricing fields for context
        # but cannot WRITE them
        if operation == "read":
            allowed |= {
                "spot_price",  # For context in explanations
                "option_price",  # For explaining price
                "execution_results",  # For explaining results
            }

        return allowed

    elif agent_type == "pricing":
        # Pricing agent: shared + rag + pricing fields
        return shared | rag | get_pricing_fields()

    else:
        logger.error(f"Unknown agent type: {agent_type}")
        return shared  # Fallback to shared only


# ============================================================================
# AGENT STATE WRAPPER
# ============================================================================

class AgentStateWrapper:
    """
    Wraps BaseAgentState with enforced agent-aware access control.

    This wrapper:
    - Enforces field access boundaries between agents
    - Logs all field access attempts
    - Raises exceptions on unauthorized access (when enforce=True)
    - Provides safe get/set methods with agent context

    Usage:
        state = BaseAgentState()
        wrapped = AgentStateWrapper(state, agent_type="educational")

        # Allowed
        wrapped.get_field("explanation_text")  # [OK]
        wrapped.set_field("explanation_text", "...")  # [OK]

        # Denied
        wrapped.get_field("spot_price")  # [ERR] AccessViolationError
        wrapped.set_field("execution_plan", {...})  # [ERR] AccessViolationError
    """

    def __init__(
        self,
        state: Any,  # BaseAgentState
        agent_type: AgentType,
        enforce: bool = True,
        log_access: bool = True
    ):
        """
        Initialize agent state wrapper.

        Args:
            state: The underlying BaseAgentState object
            agent_type: The agent type accessing the state
            enforce: If True, raise exceptions on violations. If False, just log warnings.
            log_access: If True, log all field access attempts
        """
        self._state = state
        self._agent_type = agent_type
        self._enforce = enforce
        self._log_access = log_access
        self._access_log: List[Dict[str, Any]] = []
        self._violations: List[Dict[str, Any]] = []

        # Store agent type in state for reference
        if not hasattr(state, "current_agent"):
            state.current_agent = agent_type

        logger.debug(f"Created AgentStateWrapper for {agent_type} agent (enforce={enforce})")

    def is_field_allowed(
        self,
        field_name: str,
        operation: str = "read"
    ) -> bool:
        """
        Check if a field is allowed for the current agent.

        Args:
            field_name: The field to check
            operation: 'read' or 'write'

        Returns:
            True if allowed, False otherwise
        """
        allowed_fields = get_allowed_fields(self._agent_type, operation)
        return field_name in allowed_fields

    def _log_field_access(
        self,
        field_name: str,
        operation: str,
        allowed: bool,
        value: Any = None
    ):
        """Log a field access attempt."""
        if not self._log_access:
            return

        access_record = {
            "timestamp": time.time(),
            "agent": self._agent_type,
            "field": field_name,
            "operation": operation,
            "allowed": allowed,
        }

        self._access_log.append(access_record)

        if not allowed:
            self._violations.append(access_record)

            if self._log_access:
                logger.warning(
                    f"🚨 ACCESS VIOLATION: {self._agent_type} agent attempted "
                    f"{operation} on unauthorized field '{field_name}'"
                )

    def get_field(
        self,
        field_name: str,
        default: Any = None,
        bypass_check: bool = False
    ) -> Any:
        """
        Get a field value with access control.

        Args:
            field_name: The field to read
            default: Default value if field doesn't exist
            bypass_check: If True, skip access check (use with caution!)

        Returns:
            Field value or default

        Raises:
            AccessViolationError: If agent not allowed to read field (when enforce=True)
        """
        if not bypass_check:
            allowed = self.is_field_allowed(field_name, "read")
            self._log_field_access(field_name, "read", allowed)

            if not allowed:
                if self._enforce:
                    raise AccessViolationError(
                        f"{self._agent_type} agent cannot read field '{field_name}'"
                    )
                return default

        return getattr(self._state, field_name, default)

    def set_field(
        self,
        field_name: str,
        value: Any,
        bypass_check: bool = False
    ) -> bool:
        """
        Set a field value with access control.

        Args:
            field_name: The field to write
            value: The value to set
            bypass_check: If True, skip access check (use with caution!)

        Returns:
            True if value was set, False if denied

        Raises:
            AccessViolationError: If agent not allowed to write field (when enforce=True)
        """
        if not bypass_check:
            allowed = self.is_field_allowed(field_name, "write")
            self._log_field_access(field_name, "write", allowed, value)

            if not allowed:
                if self._enforce:
                    raise AccessViolationError(
                        f"{self._agent_type} agent cannot write field '{field_name}'"
                    )
                return False

        setattr(self._state, field_name, value)
        return True

    def get_multiple(
        self,
        field_names: List[str],
        defaults: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get multiple fields at once.

        Args:
            field_names: List of field names to retrieve
            defaults: Optional dict of default values per field

        Returns:
            Dict mapping field names to values
        """
        defaults = defaults or {}
        result = {}

        for field_name in field_names:
            result[field_name] = self.get_field(
                field_name,
                default=defaults.get(field_name)
            )

        return result

    def set_multiple(
        self,
        field_values: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Set multiple fields at once.

        Args:
            field_values: Dict mapping field names to values

        Returns:
            Dict mapping field names to success status
        """
        result = {}

        for field_name, value in field_values.items():
            result[field_name] = self.set_field(field_name, value)

        return result

    def get_filtered_messages(self) -> List[BaseMessage]:
        """
        Get messages filtered for this agent.

        In future, this could filter messages based on agent metadata.
        For now, returns all messages.
        """
        messages = self.get_field("messages", [])

        # Future: filter by agent type
        # return [msg for msg in messages if should_include_for_agent(msg, self._agent_type)]

        return messages

    def update_from_dict(
        self,
        updates: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Update state from a dictionary (typical node return value).

        Args:
            updates: Dict of field updates

        Returns:
            Dict mapping field names to success status
        """
        return self.set_multiple(updates)

    def to_dict(
        self,
        include_all: bool = False
    ) -> Dict[str, Any]:
        """
        Convert state to dictionary.

        Args:
            include_all: If True, include all state fields. If False, only allowed fields.

        Returns:
            Dictionary representation of state
        """
        if include_all:
            # Return all fields (bypass access control)
            return self._state.model_dump()

        # Return only allowed fields for this agent
        allowed_fields = get_allowed_fields(self._agent_type, "read")
        result = {}

        for field_name in allowed_fields:
            value = getattr(self._state, field_name, None)
            if value is not None:
                result[field_name] = value

        return result

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all access violations recorded for this wrapper."""
        return self._violations.copy()

    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get complete access log for this wrapper."""
        return self._access_log.copy()

    def get_violation_summary(self) -> str:
        """Get a formatted summary of violations."""
        if not self._violations:
            return "[OK] No access violations"

        lines = [f"[WARN] {len(self._violations)} Access Violations:"]

        # Group by field
        field_violations = {}
        for v in self._violations:
            field = v["field"]
            op = v["operation"]
            key = f"{field} ({op})"
            field_violations[key] = field_violations.get(key, 0) + 1

        for field_op, count in sorted(field_violations.items(), key=lambda x: -x[1]):
            lines.append(f"  - {field_op}: {count}x")

        return "\n".join(lines)

    @property
    def agent_type(self) -> AgentType:
        """Get the current agent type."""
        return self._agent_type

    @property
    def underlying_state(self) -> Any:
        """Get the underlying state object (use with caution!)."""
        return self._state


# ============================================================================
# EXCEPTIONS
# ============================================================================

class AccessViolationError(PermissionError):
    """Raised when an agent attempts unauthorized field access."""
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_agent_wrapper(
    state: Any,
    agent_type: Optional[AgentType] = None,
    enforce: bool = True
) -> AgentStateWrapper:
    """
    Factory function to create an agent state wrapper.

    Args:
        state: The BaseAgentState object
        agent_type: Agent type, or None to detect from state
        enforce: Whether to enforce access control

    Returns:
        AgentStateWrapper instance
    """
    if agent_type is None:
        # Try to detect from state
        agent_type = getattr(state, "detected_agent_type", "unified")

        if agent_type not in ["educational", "pricing", "unified"]:
            logger.warning(f"Invalid agent type '{agent_type}', defaulting to 'unified'")
            agent_type = "unified"

    return AgentStateWrapper(state, agent_type, enforce=enforce)


def get_field_category(field_name: str) -> str:
    """
    Determine which category a field belongs to.

    Returns:
        "shared", "educational", "pricing", "rag", or "unknown"
    """
    if field_name in get_shared_fields():
        return "shared"
    elif field_name in get_educational_fields():
        return "educational"
    elif field_name in get_pricing_fields():
        return "pricing"
    elif field_name in get_rag_fields():
        return "rag"
    else:
        return "unknown"
