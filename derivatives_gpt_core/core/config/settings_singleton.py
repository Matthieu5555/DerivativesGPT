"""
Settings singleton accessor.

Provides thread-safe singleton access to application settings.
Pre-loads .env file to avoid blocking I/O in async contexts.
"""

import threading
from dotenv import load_dotenv
from derivatives_gpt_core.core.config.settings_schema import Settings

# Pre-load .env file to avoid blocking I/O in async context
# This must happen before Settings class instantiation
load_dotenv()

_settings: Settings | None = None
_settings_lock = threading.Lock()


def get_settings() -> Settings:
    """
    Get or create settings singleton (thread-safe).

    Returns:
        Settings instance loaded from environment variables

    Example:
        ```python
        from derivatives_gpt_core.core.config import get_settings

        settings = get_settings()
        api_key = settings.openai_api_key
        ```
    """
    global _settings
    if _settings is None:
        with _settings_lock:
            if _settings is None:
                _settings = Settings()
    return _settings


def reset_settings() -> None:
    """
    Reset settings singleton (for testing only).

    This forces re-initialization of settings on next get_settings() call.
    Useful for testing with different environment configurations.
    """
    global _settings
    with _settings_lock:
        _settings = None
