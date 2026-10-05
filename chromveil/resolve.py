"""Resolve ChromVeil / ChromiumFish chrome binary."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _scan_cache(root: Path) -> str | None:
    if not root.exists():
        return None
    names = ("chromiumfish.exe", "chrome.exe", "chromiumfish", "chrome")
    for name in names:
        for p in root.rglob(name):
            if p.is_file():
                return str(p)
    return None


def resolve_executable(download: bool = False) -> str | None:
    for key in ("CHROMVEIL_EXECUTABLE", "CHROMVEIL_CHROME", "CHROMIUMFISH_CHROME"):
        val = os.environ.get(key)
        if val and Path(val).exists():
            return val

    try:
        from chromiumfish.fetch import binary_path

        path = binary_path(download=download)
        if path and Path(path).exists():
            return path
    except Exception:
        pass

    try:
        from chromiumfish.fetch import cache_root

        found = _scan_cache(cache_root())
        if found:
            return found
    except Exception:
        pass

    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "chromiumfish"
        found = _scan_cache(local)
        if found:
            return found

    wsl_distro = os.environ.get("CHROMVEIL_WSL_DISTRO", "Ubuntu")
    base = Path(f"\\\\wsl$\\{wsl_distro}\\home")
    if base.exists():
        for home in base.iterdir():
            if not home.is_dir():
                continue
            found = _scan_cache(home / ".cache" / "chromiumfish")
            if found:
                return found
    return None


def browser_tier(executable: str | None) -> str:
    if not executable:
        return "fallback"
    low = executable.lower().replace("\\", "/")
    if "/out/release/" in low or "chromveil" in low:
        return "patched"
    if "chromiumfish" in low:
        return "chromiumfish"
    return "custom"
