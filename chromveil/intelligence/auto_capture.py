"""When to auto-capture network traffic for a navigation."""
from __future__ import annotations

import os
from urllib.parse import urlparse

# Domains / paths where API capture is almost always valuable.
_SMART_HOST_HINTS = (
    "bet365",
    "betonline",
    "sportsbook",
    "bovada",
    "draftkings",
    "fanduel",
)


def auto_capture_enabled() -> bool:
    return os.environ.get("CHROMVEIL_AUTO_CAPTURE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def should_auto_capture(url: str) -> bool:
    if not auto_capture_enabled():
        return False
    if not url or url.startswith("about:"):
        return False
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = (p.netloc or "").lower()
    path = (p.path or "").lower()
    if any(h in host or h in path for h in _SMART_HOST_HINTS):
        return True
    if os.environ.get("CHROMVEIL_AUTO_CAPTURE_ALL", "").lower() in ("1", "true", "yes"):
        return True
    return False
