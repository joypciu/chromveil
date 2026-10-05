"""Resilient navigation — detect soft blocks and retry with a fresh identity."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from ..core.runtime import BrowserRuntime
from ..drivers.veil_session import VeilSession
from ..profile import ChromiumProfile

from .session_stability import apply_sticky_host_profile, detect_block_signals, wait_for_challenge_clear


@dataclass
class NavigationResult:
    ok: bool
    url: str | None
    title: str | None
    attempts: int
    block_signals: list[str]
    session: VeilSession | None = None
    page: Any = None


_SPORTSBOOK_DATA_HINTS = (
    "pullpodapi",
    "allsportsmenu",
    "sports-configuration",
    "matchmarkets",
    "sportsbook",
    "/api/",
    "linetracker",
    "wagertalk",
    "vsin.com",
    "prophetx",
    "odds",
)


def wait_for_sportsbook_data(page, timeout_ms: int = 45_000) -> bool:
    """Wait until a typical sportsbook data XHR/fetch fires (bet365, betonline, etc.)."""

    def _match(response) -> bool:
        u = (response.url or "").lower()
        return any(h in u for h in _SPORTSBOOK_DATA_HINTS)

    try:
        page.wait_for_response(_match, timeout=timeout_ms)
        return True
    except Exception:
        return False


def goto_resilient(
    url: str,
    profile: ChromiumProfile | None = None,
    *,
    driver: str | None = None,
    max_attempts: int = 3,
    timeout_ms: int = 120_000,
    on_retry: Callable[[int, list[str]], None] | None = None,
) -> NavigationResult:
    """
    Open browser and navigate; on block hints, discard session and retry with fresh rotated identity.
    """
    base = profile or ChromiumProfile.from_env()
    apply_sticky_host_profile(base, url)
    attempts = 0
    last_signals: list[str] = []
    session: VeilSession | None = None
    page = None

    while attempts < max_attempts:
        attempts += 1
        prof = base if base.sticky_session else base.clone_fresh_session()
        if session:
            session.close()
        session = BrowserRuntime(prof).open(driver=driver)
        page = session.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=min(25_000, timeout_ms))
            except Exception:
                pass
        except Exception as exc:
            last_signals = [f"error:{exc}"]
            if on_retry:
                on_retry(attempts, last_signals)
            time.sleep(0.8)
            continue

        wait_for_challenge_clear(page, timeout_ms=35_000)
        last_signals = detect_block_signals(page)
        if last_signals == ["challenge"]:
            wait_for_challenge_clear(page, timeout_ms=20_000)
            last_signals = detect_block_signals(page)
        if not last_signals or last_signals == ["soft_error"]:
            if last_signals == ["soft_error"]:
                time.sleep(2.0)
                last_signals = detect_block_signals(page)
            if not last_signals:
                return NavigationResult(
                    ok=True,
                    url=page.url,
                    title=page.title(),
                    attempts=attempts,
                    block_signals=[],
                    session=session,
                    page=page,
                )
        if on_retry:
            on_retry(attempts, last_signals)

    if session:
        session.close()
    return NavigationResult(
        ok=False,
        url=page.url if page else None,
        title=page.title() if page else None,
        attempts=attempts,
        block_signals=last_signals,
        session=None,
        page=None,
    )
