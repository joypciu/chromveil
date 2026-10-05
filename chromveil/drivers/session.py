"""Driver-agnostic browser session."""
from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from ..profile import ChromiumProfile


@dataclass
class VeilSession:
    """One ChromVeil browser — close when done."""

    profile: ChromiumProfile
    driver: str
    cdp_url: str | None
    browser: Any = None
    page: Any = None
    _playwright: Any = None
    _process: subprocess.Popen[str] | None = None
    _extra_close: Callable[[], None] | None = None

    def close(self) -> None:
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass
        if self._extra_close:
            try:
                self._extra_close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def new_page(self) -> Any:
        if self.browser is None:
            raise RuntimeError("No Playwright/Patchright browser attached; use driver=playwright|patchright or connect_over_cdp")
        return self.browser.new_page()

    def __enter__(self) -> VeilSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _pick_driver(name: str) -> str:
    if name != "auto":
        return name
    if _has_patchright():
        return "patchright"
    return "playwright"


def _has_patchright() -> bool:
    try:
        import patchright  # noqa: F401

        return True
    except ImportError:
        return False


def _playwright_module(driver: str):
    if driver == "patchright":
        from patchright.sync_api import sync_playwright

        return sync_playwright
    from playwright.sync_api import sync_playwright

    return sync_playwright


def _wait_cdp(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url.rstrip('/')}/json/version", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"CDP did not become ready: {url}")


def spawn_cdp(profile: ChromiumProfile) -> VeilSession:
    """Launch chrome as subprocess; for Puppeteer, Selenium, raw CDP clients."""
    if not profile.cdp_port:
        profile.cdp_port = 9222
    exe = profile.resolve_executable(download=True)
    if not exe:
        raise FileNotFoundError(
            "No ChromVeil/ChromiumFish chrome binary. Set CHROMVEIL_EXECUTABLE or build/fetch in WSL."
        )
    argv = [exe] + profile.chromium_argv(include_cdp=True)
    proc = subprocess.Popen(
        argv,
        env=profile.merged_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = profile.cdp_url()
    assert url
    _wait_cdp(url)
    return VeilSession(profile=profile, driver="subprocess", cdp_url=url, _process=proc)


def open_browser(profile: ChromiumProfile, driver: str | None = None) -> VeilSession:
    """
    Open browser with the given automation driver.

    - playwright / patchright: launch patched chrome via library (or connect_over_cdp if already up)
    - cdp / subprocess: only spawn process, return cdp_url (no Playwright handle)
    - auto: patchright if installed else playwright
    """
    profile.materialize()
    drv = _pick_driver(driver or profile.driver)
    if drv in ("cdp", "subprocess"):
        return spawn_cdp(profile)

    sync_playwright = _playwright_module(drv)
    exe = profile.resolve_executable(download=True)

    # CDP attach mode: reuse long-lived browser (MCP / chromveil up)
    if profile.cdp_port and os.environ.get("CHROMVEIL_CONNECT_ONLY") == "1":
        url = profile.cdp_url()
        assert url
        _wait_cdp(url, timeout=10)
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(url)
        return VeilSession(profile=profile, driver=drv, cdp_url=url, browser=browser, _playwright=pw)

    pw = sync_playwright().start()
    launch_args = profile.chromium_argv(
        include_cdp=bool(profile.cdp_port),
        for_playwright=True,
    )
    opts: dict[str, Any] = {
        "headless": profile.headless,
        "args": launch_args,
        "env": profile.merged_env(),
    }
    ignore = profile.playwright_ignore_default_args()
    if ignore:
        opts["ignore_default_args"] = ignore
    if exe:
        opts["executable_path"] = exe
    if profile.proxy:
        opts["proxy"] = profile.proxy
    browser = pw.chromium.launch(**opts)
    cdp = profile.cdp_url()
    return VeilSession(profile=profile, driver=drv, cdp_url=cdp, browser=browser, _playwright=pw)
