"""Open a URL, capture APIs + WebSockets, return filtered data for the user."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..core.runtime import BrowserRuntime
from ..profile import ChromiumProfile
from .collect_tuning import (
    capture_limits,
    default_settle_ms,
    export_limits,
    resolve_all_data,
    resolve_capture_websockets,
    trim_extracted_for_export,
)
from .data_query import select_for_user, select_websockets
from .llm_collect import parse_collect_intent, summarize_for_user
from .navigation import detect_block_signals, wait_for_sportsbook_data
from .session_stability import (
    apply_sticky_host_profile,
    prefer_headless_executable,
    wait_for_challenge_clear,
)
from .network_capture import NetworkCapture
from .page_data import extract_page_data, settle_page
from .structured_extract import build_extracted
from .ws_insights import summarize_websocket_frames


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
    settle_ms: int | None = None,
    max_attempts: int = 2,
    capture_websockets: bool | None = None,
    include_page_view: bool = True,
    summarize: bool = True,
    all_data: bool | None = None,
    extract_dom: bool = True,
) -> CollectResult:
    settle_ms = settle_ms if settle_ms is not None else default_settle_ms()
    if all_data is None:
        all_data = resolve_all_data(
            all_flag=False, no_all_flag=bool(want or ask), want=want, ask=ask
        )
    ws_capture = resolve_capture_websockets(url, all_data=all_data, explicit=capture_websockets)
    caps = capture_limits(all_data)
    exports = export_limits(all_data)
    api_top_n = exports["api_top_n"]
    ws_top_n = exports["ws_top_n"]

    intent = parse_collect_intent(ask or "") if ask else {}
    if ask and not want:
        want = intent.get("want") or want
    if ask and not url_pattern and intent.get("url_pattern"):
        url_pattern = intent.get("url_pattern")

    base = profile or ChromiumProfile.from_env()
    apply_sticky_host_profile(base, url)
    prefer_headless_executable(base)
    last_block: list[str] = []
    final_url: str | None = None
    title: str | None = None
    entries = []
    ws_entries = []
    page_view: dict[str, Any] = {}
    attempts = 0

    for attempt in range(1, max(max_attempts, 1) + 1):
        attempts = attempt
        prof = base if base.sticky_session else base.clone_fresh_session()
        session = BrowserRuntime(prof).open(driver=driver)
        page = session.new_page()
        capture = NetworkCapture(
            page,
            capture_websockets=ws_capture,
            max_entries=caps["max_entries"],
            max_ws_frames=caps["max_ws_frames"],
            max_body_bytes=caps["max_body_bytes"],
        )
        capture.attach()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            wait_for_sportsbook_data(page, timeout_ms=min(35_000, settle_ms + 25_000))
            wait_for_challenge_clear(page, timeout_ms=40_000)
            settle_page(page, settle_ms, scroll=all_data)
            final_url = page.url
            title = page.title()
            last_block = detect_block_signals(page)
            if last_block == ["challenge"]:
                wait_for_challenge_clear(page, timeout_ms=25_000)
                last_block = detect_block_signals(page)
            entries = capture.entries()
            ws_entries = capture.websocket_entries()
            page_data: dict[str, Any] = {}
            if extract_dom:
                page_data = extract_page_data(
                    page,
                    max_text_chars=10_000 if all_data else 4_000,
                    deep_pass=True,
                )
            if include_page_view and page_data:
                excerpt = page_data.get("text") or ""
                page_view = {
                    "url": page_data.get("url", final_url),
                    "title": page_data.get("title", title),
                    "text_excerpt": excerpt[:2500],
                    "elements_count": 0,
                }
            if not last_block or last_block == ["soft_error"]:
                extracted_full = build_extracted(entries, ws_entries, page_data or None)
                extracted = trim_extracted_for_export(
                    extracted_full, max_selections=120 if all_data else 80
                )
                selected = select_for_user(
                    entries, want=want, url_pattern=url_pattern, top_n=api_top_n
                )
                ws_sel = (
                    select_websockets(ws_entries, want=want, top_n=ws_top_n)
                    if ws_top_n
                    else []
                )
                ws_summary = (
                    summarize_websocket_frames(ws_sel, max_samples=12)
                    if ws_sel and all_data
                    else None
                )
                payload = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "mode": "all" if all_data else "smart",
                    "noise_filtered_total": len(entries),
                    "websocket_total": len(ws_entries),
                    "websockets": ws_sel,
                    "websocket_insights": ws_summary,
                    "page": page_view,
                    "page_data": page_data or None,
                    "extracted": extracted,
                    "intent": intent if ask else None,
                    **selected,
                }
                summary_prompt = ask or want
                summary = (
                    summarize_for_user(summary_prompt, payload)
                    if (summarize and summary_prompt)
                    else None
                )
                from .display import format_collect_display

                display = format_collect_display(
                    ok=True,
                    url=url,
                    final_url=final_url,
                    title=title,
                    block_signals=[],
                    capture={**payload, "extracted": extracted_full},
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
        time.sleep(0.35)

    selected = select_for_user(entries, want=want, url_pattern=url_pattern, top_n=api_top_n)
    ws_sel = select_websockets(ws_entries, want=want, top_n=ws_top_n) if ws_top_n else []
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "all" if all_data else "smart",
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
