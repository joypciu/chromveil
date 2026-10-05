"""Driver adapters — Playwright-family vs raw subprocess."""
from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from typing import Any, Callable, Protocol

from ..core.launch_plan import LaunchPlan
from ..core.types import DriverKind
from ..profile import ChromiumProfile
from .veil_session import VeilSession


class DriverAdapter(Protocol):
    name: str

    def open(self, profile: ChromiumProfile, plan: LaunchPlan) -> VeilSession: ...


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


def _playwright_module(driver: str):
    if driver == "patchright":
        from patchright.sync_api import sync_playwright

        return sync_playwright
    from playwright.sync_api import sync_playwright

    return sync_playwright


class PlaywrightFamilyAdapter:
    def __init__(self, driver_id: str) -> None:
        self.name = driver_id

    def open(self, profile: ChromiumProfile, plan: LaunchPlan) -> VeilSession:
        if profile.cdp_port and os.environ.get("CHROMVEIL_CONNECT_ONLY") == "1":
            url = plan.cdp_url
            assert url
            _wait_cdp(url, timeout=10)
            pw = _playwright_module(self.name)().start()
            browser = pw.chromium.connect_over_cdp(url)
            return VeilSession(profile=profile, driver=self.name, cdp_url=url, browser=browser, _playwright=pw)

        pw = _playwright_module(self.name)().start()
        opts: dict[str, Any] = {
            "headless": plan.headless,
            "args": plan.argv_list(),
            "env": plan.env,
        }
        if plan.ignore_default_args:
            opts["ignore_default_args"] = list(plan.ignore_default_args)
        if plan.executable:
            opts["executable_path"] = plan.executable
        if plan.proxy:
            opts["proxy"] = plan.proxy

        ephemeral_dir = None
        if plan.user_data_dir and not profile.persist_persona:
            ephemeral_dir = plan.user_data_dir

        if plan.user_data_dir:
            context = pw.chromium.launch_persistent_context(plan.user_data_dir, **opts)
            if profile.stealth_tuning:
                context.add_init_script(
                    """
                    try {
                      if (navigator.webdriver)
                        Object.defineProperty(navigator, 'webdriver', { get: () => false });
                    } catch (e) {}
                    """
                )
            return VeilSession(
                profile=profile,
                driver=self.name,
                cdp_url=plan.cdp_url,
                _context=context,
                _playwright=pw,
                _ephemeral_user_data_dir=ephemeral_dir,
            )

        browser = pw.chromium.launch(**opts)
        return VeilSession(
            profile=profile,
            driver=self.name,
            cdp_url=plan.cdp_url,
            browser=browser,
            _playwright=pw,
        )


class SubprocessCdpAdapter:
    name = "subprocess"

    def open(self, profile: ChromiumProfile, plan: LaunchPlan) -> VeilSession:
        if not profile.cdp_port:
            profile.cdp_port = 9222
        if not plan.executable:
            raise FileNotFoundError(
                "No ChromVeil/ChromiumFish chrome binary. Set CHROMVEIL_EXECUTABLE or build/fetch in WSL."
            )
        proc = subprocess.Popen(
            plan.subprocess_argv(),
            env=plan.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        url = plan.cdp_url or profile.cdp_url()
        assert url
        _wait_cdp(url)
        ephemeral_dir = plan.user_data_dir if plan.user_data_dir and not profile.persist_persona else None
        return VeilSession(
            profile=profile,
            driver=self.name,
            cdp_url=url,
            _process=proc,
            _ephemeral_user_data_dir=ephemeral_dir,
        )


_REGISTRY: dict[str, DriverAdapter] = {
    DriverKind.PLAYWRIGHT.value: PlaywrightFamilyAdapter("playwright"),
    DriverKind.PATCHRIGHT.value: PlaywrightFamilyAdapter("patchright"),
    DriverKind.SUBPROCESS.value: SubprocessCdpAdapter(),
    DriverKind.CDP.value: SubprocessCdpAdapter(),
}


def resolve_driver(name: str) -> str:
    if name != DriverKind.AUTO.value:
        return name
    try:
        import patchright  # noqa: F401

        return DriverKind.PATCHRIGHT.value
    except ImportError:
        return DriverKind.PLAYWRIGHT.value


def get_adapter(driver: str) -> DriverAdapter:
    key = resolve_driver(driver)
    if key not in _REGISTRY:
        raise ValueError(f"Unknown driver: {driver}")
    return _REGISTRY[key]
