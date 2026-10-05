"""ChromiumFish native agent + chrome path resolution (WSL / local build)."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def resolve_chrome_executable() -> str | None:
    from .resolve import resolve_executable

    return resolve_executable(download=False)


def native_available() -> bool:
    if os.environ.get("CHROMVEIL_NATIVE", "1") == "0":
        return False
    try:
        import chromiumfish.agent  # noqa: F401
        import websocket  # noqa: F401
    except ImportError:
        return False
    return resolve_chrome_executable() is not None or shutil.which("chromiumfish") is not None


def wsl_mcp_hint() -> str:
    return (
        "Run MCP inside WSL: wsl -d Ubuntu bash /mnt/e/chromveil/scripts/wsl/run-mcp.sh\n"
        "Then point Cursor MCP at wsl.exe (see config/cursor-mcp.json.example)."
    )
