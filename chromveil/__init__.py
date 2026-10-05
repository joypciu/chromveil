"""
ChromVeil — your Chromium build, any automation library.

One profile (persona, binary, flags) drives Playwright, Patchright, raw CDP, or a subprocess.
"""

from .browser import launch, open
from .drivers import VeilSession, open_browser, spawn_cdp
from .profile import ChromiumProfile, LEAN_GPU_ARGS

__version__ = "0.2.0"

__all__ = [
    "ChromiumProfile",
    "LEAN_GPU_ARGS",
    "VeilSession",
    "launch",
    "open",
    "open_browser",
    "spawn_cdp",
    "__version__",
]
