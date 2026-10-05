"""Locate installed Chromium-based browsers on the host."""
from __future__ import annotations

import os
from pathlib import Path


def find_system_chrome() -> str | None:
    """Google Chrome stable (Windows / common paths)."""
    roots = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")),
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")),
        Path(os.environ.get("LOCALAPPDATA", "")),
    ]
    for root in roots:
        if not root:
            continue
        candidate = root / "Google" / "Chrome" / "Application" / "chrome.exe"
        if candidate.is_file():
            return str(candidate)
    return None
