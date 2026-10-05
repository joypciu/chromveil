"""Ensure ChromiumFish / custom binary is present."""
from __future__ import annotations

import os

from .resolve import browser_tier, resolve_executable


def ensure_binary(download: bool = True) -> str | None:
    exe = resolve_executable(download=False)
    if exe:
        return exe
    if not download:
        return None
    if os.environ.get("CHROMVEIL_AUTO_FETCH", "1") == "0":
        return None
    try:
        from chromiumfish.fetch import binary_path

        return binary_path(download=True)
    except Exception as exc:
        import sys

        hint = (
            "ChromiumFish binary download failed. On Windows the win-x64 release may be "
            "missing (HTTP 404) — use WSL + `chromiumfish fetch`, or set CHROMVEIL_EXECUTABLE."
        )
        print(hint, file=sys.stderr)
        print(f"Detail: {exc}", file=sys.stderr)
    from .resolve import resolve_executable as _resolve

    return _resolve(download=False)
