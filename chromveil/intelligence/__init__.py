"""Adaptive navigation and block-aware retries."""
from .navigation import detect_block_signals, goto_resilient

__all__ = ["detect_block_signals", "goto_resilient"]
