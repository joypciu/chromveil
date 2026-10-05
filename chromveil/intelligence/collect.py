"""Open a URL, capture APIs, return filtered data for the user."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..core.runtime import BrowserRuntime
from ..profile import ChromiumProfile
from .data_query import select_for_user
from .navigation import detect_block_signals
from .network_capture import NetworkCapture


@dataclass
class CollectResult:
    ok: bool
    url: str
    final_url: str | None
    title: str | None
    block_signals: list[str]
    capture: dict[str, Any]
    attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "block_signals": self.block_signals,
            "attempts": self.attempts,
            **self.capture,
        }


def collect_from_url(
    url: str,
    profile: ChromiumProfile | None = None,
    *,
    driver: str | None = None,
    want: str | None = None,
    url_pattern: str | None = None,
    settle_ms: int = 6000,
    max_attempts: int = 2,
) -> CollectResult:
    """
    Navigate with ChromVeil stealth, record API traffic (capture starts before navigation),
    filter noise, apply ``want`` keywords.
    """
    base = profile or ChromiumProfile.from_env()
    last_block: list[str] = []
    final_url: str | None = None
    title: str | None = None
    entries = []
    attempts = 0

    for attempt in range(1, max(max_attempts, 1) + 1):
        attempts = attempt
        prof = base.clone_fresh_session()
        session = BrowserRuntime(prof).open(driver=driver)
        page = session.new_page()
        capture = NetworkCapture(page)
        capture.attach()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            try:
                page.wait_for_load_state("networkidle", timeout=min(30_000, settle_ms + 20_000))
            except Exception:
                pass
            time.sleep(settle_ms / 1000.0)
            final_url = page.url
            title = page.title()
            last_block = detect_block_signals(page)
            entries = capture.entries()
            if not last_block:
                selected = select_for_user(entries, want=want, url_pattern=url_pattern)
                payload = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "noise_filtered_total": len(entries),
                    **selected,
                }
                session.close()
                return CollectResult(
                    ok=True,
                    url=url,
                    final_url=final_url,
                    title=title,
                    block_signals=[],
                    capture=payload,
                    attempts=attempts,
                )
        except Exception as exc:
            last_block = [f"error:{exc}"]
        finally:
            capture.detach()
            session.close()
        time.sleep(0.5)

    selected = select_for_user(entries, want=want, url_pattern=url_pattern)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "noise_filtered_total": len(entries),
        **selected,
    }
    return CollectResult(
        ok=False,
        url=url,
        final_url=final_url,
        title=title,
        block_signals=last_block,
        capture=payload,
        attempts=attempts,
    )
