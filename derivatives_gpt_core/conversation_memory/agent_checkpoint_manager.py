"""
Agent-Aware Checkpoint Manager
===============================
Manages checkpoints with agent separation, maintaining separate conversation
state for educational and pricing agents.
"""

import json
import aiosqlite
import sqlite3
from typing import Optional, Dict, Any, Literal
from pathlib import Path
from datetime import datetime
import logging

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from derivatives_gpt_core.core.state.agent_state_wrapper import AgentType
from derivatives_gpt_core.config import get_settings

logger = logging.getLogger(__name__)


class AgentCheckpointManager:
    """
    Manages agent-aware checkpoints with hierarchical thread IDs.

    Thread ID structure: {base_thread_id}.{agent_type}

    Examples:
        - session_123.educational
        - session_123.pricing
        - session_123 (unified/orchestrator)

    This allows each agent to maintain its own conversation state while
    sharing a common base session ID.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize agent checkpoint manager.

        Args:
            db_path: Path to SQLite database, or None to use settings
        """
        if db_path is None:
            settings = get_settings()
            db_path = settings.checkpoint_db_path

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize metadata table (synchronously)
        self._init_metadata_table()

        logger.info(f"Initialized AgentCheckpointManager with db: {self.db_path}")

    def _init_metadata_table(self):
        """Initialize agent metadata table in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_checkpoint_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    base_thread_id TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    agent_thread_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    last_message_preview TEXT,
                    UNIQUE(base_thread_id, agent_type)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_base_thread
                ON agent_checkpoint_metadata(base_thread_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_thread
                ON agent_checkpoint_metadata(agent_thread_id)
            """)

            logger.debug("Agent metadata table initialized")

    def format_agent_thread_id(
        self,
        base_thread_id: str,
        agent_type: AgentType
    ) -> str:
        """
        Format thread ID for specific agent.

        Args:
            base_thread_id: Base session/thread ID
            agent_type: Agent type

        Returns:
            Formatted thread ID: {base}.{agent}
        """
        if agent_type == "unified":
            return base_thread_id  # Unified uses base ID
        else:
            return f"{base_thread_id}.{agent_type}"

    def parse_agent_thread_id(
        self,
        thread_id: str
    ) -> tuple[str, AgentType]:
        """
        Parse thread ID into base and agent type.

        Args:
            thread_id: Full thread ID

        Returns:
            Tuple of (base_thread_id, agent_type)
        """
        if "." not in thread_id:
            return thread_id, "unified"

        base, agent = thread_id.rsplit(".", 1)

        if agent in ["educational", "pricing"]:
            return base, agent  # type: ignore
        else:
            return thread_id, "unified"

    async def track_agent_checkpoint(
        self,
        base_thread_id: str,
        agent_type: AgentType,
        message_count: int = 0,
        last_message_preview: Optional[str] = None
    ):
        """
        Track agent checkpoint metadata.

        Args:
            base_thread_id: Base session ID
            agent_type: Agent type
            message_count: Number of messages in conversation
            last_message_preview: Preview of last message
        """
        agent_thread_id = self.format_agent_thread_id(base_thread_id, agent_type)
        now = datetime.utcnow().isoformat()

        async with aiosqlite.connect(self.db_path) as conn:
            # Insert or update metadata
            await conn.execute("""
                INSERT INTO agent_checkpoint_metadata
                (base_thread_id, agent_type, agent_thread_id, created_at, updated_at,
                 message_count, last_message_preview)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(base_thread_id, agent_type) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    message_count = excluded.message_count,
                    last_message_preview = excluded.last_message_preview
            """, (
                base_thread_id,
                agent_type,
                agent_thread_id,
                now,
                now,
                message_count,
                last_message_preview
            ))

            await conn.commit()

        logger.debug(
            f"Tracked checkpoint: {agent_thread_id} ({message_count} messages)"
        )

    async def get_agent_metadata(
        self,
        base_thread_id: str,
        agent_type: Optional[AgentType] = None
    ) -> Dict[str, Any]:
        """
        Get metadata for agent checkpoint(s).

        Args:
            base_thread_id: Base session ID
            agent_type: Specific agent, or None for all agents

        Returns:
            Dict with agent metadata
        """
        async with aiosqlite.connect(self.db_path) as conn:
            if agent_type:
                query = """
                    SELECT * FROM agent_checkpoint_metadata
                    WHERE base_thread_id = ? AND agent_type = ?
                """
                params = (base_thread_id, agent_type)
            else:
                query = """
                    SELECT * FROM agent_checkpoint_metadata
                    WHERE base_thread_id = ?
                    ORDER BY updated_at DESC
                """
                params = (base_thread_id,)

            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()

            # Convert to dict
            if not rows:
                return {}

            columns = [desc[0] for desc in cursor.description]
            result = {}

            for row in rows:
                row_dict = dict(zip(columns, row))
                agent = row_dict["agent_type"]
                result[agent] = row_dict

            return result

    async def list_active_sessions(
        self,
        limit: int = 50
    ) -> list[Dict[str, Any]]:
        """
        List recently active sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session metadata
        """
        async with aiosqlite.connect(self.db_path) as conn:
            query = """
                SELECT DISTINCT base_thread_id,
                       MAX(updated_at) as last_updated,
                       COUNT(*) as agent_count,
                       SUM(message_count) as total_messages
                FROM agent_checkpoint_metadata
                GROUP BY base_thread_id
                ORDER BY last_updated DESC
                LIMIT ?
            """

            async with conn.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    async def cleanup_old_checkpoints(
        self,
        days_to_keep: int = 30
    ) -> int:
        """
        Clean up old checkpoint metadata.

        Args:
            days_to_keep: Keep checkpoints from last N days

        Returns:
            Number of checkpoints cleaned up
        """
        cutoff_date = datetime.utcnow().replace(
            day=datetime.utcnow().day - days_to_keep
        ).isoformat()

        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                DELETE FROM agent_checkpoint_metadata
                WHERE updated_at < ?
            """, (cutoff_date,))

            deleted = cursor.rowcount
            await conn.commit()

        logger.info(f"Cleaned up {deleted} old checkpoints (older than {days_to_keep} days)")
        return deleted

    def get_config_for_agent(
        self,
        base_thread_id: str,
        agent_type: AgentType
    ) -> Dict[str, Any]:
        """
        Get LangGraph config for specific agent.

        This creates the config dict that should be passed to graph.ainvoke()
        or graph.astream() to ensure proper checkpoint routing.

        Args:
            base_thread_id: Base session ID
            agent_type: Agent type

        Returns:
            Config dict with agent-specific thread_id
        """
        agent_thread_id = self.format_agent_thread_id(base_thread_id, agent_type)

        return {
            "configurable": {
                "thread_id": agent_thread_id,
                "checkpoint_ns": "",  # Default namespace
            },
            "metadata": {
                "base_thread_id": base_thread_id,
                "agent_type": agent_type,
            }
        }

    async def merge_agent_conversations(
        self,
        base_thread_id: str,
        target_agent: AgentType = "unified"
    ) -> Optional[Dict[str, Any]]:
        """
        Merge conversations from all agents into a unified view.

        Useful for getting complete conversation history across agents.

        Args:
            base_thread_id: Base session ID
            target_agent: Target agent type for merged view

        Returns:
            Merged conversation metadata or None
        """
        metadata = await self.get_agent_metadata(base_thread_id)

        if not metadata:
            return None

        # Combine message counts and previews
        total_messages = sum(m["message_count"] for m in metadata.values())
        agents_active = list(metadata.keys())
        last_updated = max(m["updated_at"] for m in metadata.values())

        return {
            "base_thread_id": base_thread_id,
            "agents_active": agents_active,
            "total_messages": total_messages,
            "last_updated": last_updated,
            "agent_metadata": metadata,
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_agent_checkpoint_manager: Optional[AgentCheckpointManager] = None


async def get_agent_checkpoint_manager() -> AgentCheckpointManager:
    """
    Get or create global agent checkpoint manager.

    Returns:
        AgentCheckpointManager instance
    """
    global _agent_checkpoint_manager

    if _agent_checkpoint_manager is None:
        _agent_checkpoint_manager = AgentCheckpointManager()

    return _agent_checkpoint_manager


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_agent_config(
    base_thread_id: str,
    agent_type: AgentType
) -> Dict[str, Any]:
    """
    Create LangGraph config for agent execution.

    This is a synchronous convenience function.

    Args:
        base_thread_id: Base session ID
        agent_type: Agent type

    Returns:
        Config dict with agent-specific thread_id
    """
    manager = AgentCheckpointManager()
    return manager.get_config_for_agent(base_thread_id, agent_type)


async def track_agent_interaction(
    base_thread_id: str,
    agent_type: AgentType,
    message_count: int,
    last_message: Optional[str] = None
):
    """
    Track an agent interaction asynchronously.

    Args:
        base_thread_id: Base session ID
        agent_type: Agent type
        message_count: Number of messages
        last_message: Preview of last message
    """
    manager = await get_agent_checkpoint_manager()
    await manager.track_agent_checkpoint(
        base_thread_id,
        agent_type,
        message_count,
        last_message[:100] if last_message else None
    )
