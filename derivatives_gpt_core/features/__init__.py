"""
Features package - each feature owns its vertical slice.

Features are self-contained modules that handle specific option types.
Each feature contains:
- pricing.py: Pure pricing formulas
- (future) validation.py: Parameter validation
- (future) tools.py: LangChain tool integration
"""

__all__ = ["vanilla", "american", "digital", "asian"]
