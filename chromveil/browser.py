"""Backward-compatible launch() — prefer chromveil.open() or ChromiumProfile."""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

from .drivers import open_browser
from .profile import ChromiumProfile


@dataclass
class BrowserSession:
    playwright: Any
    browser: Any
    backend: str
    veil: Any = None
    _chromiumfish: Any = None

    def close(self) -> None:
        if self.veil is not None:
            self.veil.close()
            return
        try:
            self.browser.close()
        finally:
            if self._chromiumfish is not None:
                self._chromiumfish.close()
            elif self.playwright is not None:
                self.playwright.stop()


def open(profile: ChromiumProfile | None = None, *, driver: str | None = None):
    """Primary API: one profile, any driver (playwright, patchright, cdp, subprocess)."""
    prof = profile or ChromiumProfile.from_env()
    return open_browser(prof, driver=driver)


def launch(
    *,
    persona_seed: str | None = None,
    headless: bool = True,
    executable_path: str | None = None,
    cdp_port: int | None = None,
    extra_args: list[str] | None = None,
    driver: str | None = None,
) -> BrowserSession:
    prof = ChromiumProfile.from_env()
    if persona_seed:
        prof.persona_seed = persona_seed
    prof.headless = headless
    if executable_path:
        prof.executable = executable_path
    if cdp_port:
        prof.cdp_port = cdp_port
    if extra_args:
        prof.extra_args = list(extra_args)

    from .devmode import apply_dev_defaults

    apply_dev_defaults(prof)
    try:
        session = open_browser(prof, driver=driver or prof.driver)
        return BrowserSession(
            playwright=session._playwright,
            browser=session.browser,
            backend=session.driver,
            veil=session,
        )
    except FileNotFoundError as exc:
        warnings.warn(f"{exc}; falling back to stock Playwright chromium.", stacklevel=2)
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=headless, args=prof.chromium_argv(include_cdp=False))
        return BrowserSession(pw, browser, "playwright-fallback")
