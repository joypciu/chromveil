"""Resilient navigation — detect soft blocks and retry with a fresh identity."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Callable

from ..core.runtime import BrowserRuntime
from ..drivers.veil_session import VeilSession
from ..profile import ChromiumProfile

BLOCK_RE = re.compile(
    r"access denied|not available in your (country|region)|geo.?restrict|blocked|"
    r"captcha|verify you are human|cloudflare|attention required|forbidden|"
    r"unusual traffic|automated access|bot detected|request blocked",
    re.I,
)


@dataclass
class NavigationResult:
    ok: bool
    url: str | None
    title: str | None
    attempts: int
    block_signals: list[str]
    session: VeilSession | None = None
    page: Any = None


def detect_block_signals(page) -> list[str]:
    signals: list[str] = []
    try:
        title = page.title() or ""
        if BLOCK_RE.search(title):
            signals.append("title")
    except Exception:
        pass
    try:
        text = page.evaluate("() => (document.body && document.body.innerText || '').slice(0, 2000)")
        if text and BLOCK_RE.search(text):
            signals.append("body_text")
    except Exception:
        pass
    # Do not treat thin body alone as a block — SPAs (bet365, etc.) often render outside innerText.
    return signals


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
    attempts = 0
    last_signals: list[str] = []
    session: VeilSession | None = None
    page = None

    while attempts < max_attempts:
        attempts += 1
        prof = base.clone_fresh_session()
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
