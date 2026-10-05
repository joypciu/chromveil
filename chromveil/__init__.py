"""
ChromVeil — your Chromium build, any automation library.

One profile (persona, binary, flags) drives Playwright, Patchright, raw CDP, or a subprocess.
"""

from .browser import launch, open
from .core import BrowserEngine, BrowserRuntime, LaunchPlan, build_launch_plan
from .drivers import VeilSession, open_browser, spawn_cdp
from .profile import ChromiumProfile, LEAN_GPU_ARGS

__version__ = "0.3.0"

__all__ = [
    "BrowserEngine",
    "BrowserRuntime",
    "ChromiumProfile",
    "LaunchPlan",
    "LEAN_GPU_ARGS",
    "VeilSession",
    "build_launch_plan",
    "launch",
    "open",
    "open_browser",
    "spawn_cdp",
    "__version__",
]
