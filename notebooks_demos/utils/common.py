"""Common utilities for notebooks."""

import sys
from pathlib import Path
import time
from typing import Any, Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

def timer(func):
    """Simple timer decorator."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"⏱️ Execution: {elapsed*1000:.1f}ms")
        return result
    return wrapper