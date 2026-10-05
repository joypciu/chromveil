"""Open a URL, capture APIs + WebSockets, return filtered data for the user."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..core.runtime import BrowserRuntime
from ..perceive import perceive
from ..profile import ChromiumProfile
from .data_query import select_for_user, select_websockets
from .llm_collect import parse_collect_intent, summarize_for_user
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
    display: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = {
            "ok": self.ok,
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "block_signals": self.block_signals,
            "attempts": self.attempts,
            **self.capture,
        }
        if self.display:
            out["display"] = self.display
        return out


def collect_from_url(
    url: str,
    profile: ChromiumProfile | None = None,
    *,
    driver: str | None = None,
    want: str | None = None,
    ask: str | None = None,
    url_pattern: str | None = None,
    settle_ms: int = 6000,
    max_attempts: int = 2,
    capture_websockets: bool = True,
    include_page_view: bool = True,
    summarize: bool = True,
) -> CollectResult:
    intent = parse_collect_intent(ask or "") if ask else {}
    if ask and not want:
        want = intent.get("want") or want
    if ask and not url_pattern and intent.get("url_pattern"):
        url_pattern = intent.get("url_pattern")

    base = profile or ChromiumProfile.from_env()
    last_block: list[str] = []
    final_url: str | None = None
    title: str | None = None
    entries = []
    ws_entries = []
    page_view: dict[str, Any] = {}
    attempts = 0

    for attempt in range(1, max(max_attempts, 1) + 1):
        attempts = attempt
        prof = base.clone_fresh_session()
        session = BrowserRuntime(prof).open(driver=driver)
        page = session.new_page()
        capture = NetworkCapture(page, capture_websockets=capture_websockets)
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
            ws_entries = capture.websocket_entries()
            if include_page_view:
                try:
                    pv = perceive(page, max_chars=2500)
                    page_view = {
                        "url": pv.url,
                        "title": pv.title,
                        "text_excerpt": pv.text_excerpt,
                        "elements_count": len(pv.elements),
                    }
                except Exception:
                    page_view = {}
            if not last_block:
                selected = select_for_user(entries, want=want, url_pattern=url_pattern)
                ws_sel = select_websockets(ws_entries, want=want)
                payload = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "noise_filtered_total": len(entries),
                    "websocket_total": len(ws_entries),
                    "websockets": ws_sel,
                    "page": page_view,
                    "intent": intent if ask else None,
                    **selected,
                }
                summary = summarize_for_user(ask or want or "API data", payload) if (summarize and (ask or want)) else None
                from .display import format_collect_display

                display = format_collect_display(
                    ok=True,
                    url=url,
                    final_url=final_url,
                    title=title,
                    block_signals=[],
                    capture=payload,
                    summary=summary,
                )
                result = CollectResult(
                    ok=True,
                    url=url,
                    final_url=final_url,
                    title=title,
                    block_signals=[],
                    capture=payload,
                    attempts=attempts,
                    display=display,
                )
                session.close()
                return result
        except Exception as exc:
            last_block = [f"error:{exc}"]
        finally:
            capture.detach()
            session.close()
        time.sleep(0.5)

    selected = select_for_user(entries, want=want, url_pattern=url_pattern)
    ws_sel = select_websockets(ws_entries, want=want)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "noise_filtered_total": len(entries),
        "websocket_total": len(ws_entries),
        "websockets": ws_sel,
        "page": page_view,
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
