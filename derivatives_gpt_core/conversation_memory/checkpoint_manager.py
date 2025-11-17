"""Conversation memory with SQLite checkpointing."""

import json
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pathlib import Path
from derivatives_gpt_core.config import get_settings


# Monkey patch JsonPlusSerializer to add dumps/loads methods
# This fixes a bug in LangGraph 1.0.1-1.0.2 where AsyncSqliteSaver
# tries to call .dumps() and .loads() on JsonPlusSerializer, but those
# methods don't exist (only dumps_typed/loads_typed exist).
if not hasattr(JsonPlusSerializer, 'dumps'):
    def _dumps(self, obj):
        """Serialize object to JSON bytes."""
        return json.dumps(obj).encode('utf-8')

    def _loads(self, data):
        """Deserialize object from JSON bytes."""
        return json.loads(data.decode('utf-8') if isinstance(data, bytes) else data)

    JsonPlusSerializer.dumps = _dumps
    JsonPlusSerializer.loads = _loads


_checkpointer: AsyncSqliteSaver | None = None


async def get_checkpointer() -> AsyncSqliteSaver:
    """
    Get or create async SQLite checkpointer.

    Enables conversation memory across sessions.
    """
    global _checkpointer

    if _checkpointer is None:
        settings = get_settings()
        db_path = Path(settings.checkpoint_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(db_path))
        _checkpointer = AsyncSqliteSaver(conn)

    return _checkpointer
