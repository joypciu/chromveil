"""Navigation, API capture, and user-focused data selection."""
from .collect import collect_from_url
from .navigation import detect_block_signals, goto_resilient

__all__ = ["collect_from_url", "detect_block_signals", "goto_resilient"]
