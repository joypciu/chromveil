"""Core type aliases for ChromVeil architecture."""
from __future__ import annotations

from enum import Enum


class EngineTier(str, Enum):
    """Which Chromium binary backs the session."""

    FALLBACK = "fallback"  # driver default browser, no custom exe
    CHROMIUMFISH = "chromiumfish"  # prebuilt patched binary
    PATCHED = "patched"  # local out/Release or chromveil fork build
    CUSTOM = "custom"  # user-supplied path


class DriverKind(str, Enum):
    AUTO = "auto"
    PLAYWRIGHT = "playwright"
    PATCHRIGHT = "patchright"
    CDP = "cdp"
    SUBPROCESS = "subprocess"
