"""Driver-agnostic browser session (thin layer over core runtime)."""
from __future__ import annotations

from ..core.runtime import BrowserRuntime
from ..profile import ChromiumProfile
from .veil_session import VeilSession

__all__ = ["VeilSession", "open_browser", "spawn_cdp"]


def spawn_cdp(profile: ChromiumProfile) -> VeilSession:
    """Launch chrome as subprocess; for Puppeteer, Selenium, raw CDP clients."""
    return BrowserRuntime(profile).open(driver="subprocess")


def open_browser(profile: ChromiumProfile, driver: str | None = None) -> VeilSession:
    return BrowserRuntime(profile).open(driver=driver)
