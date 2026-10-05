"""Interactive open with optional live API/WebSocket capture."""
from __future__ import annotations

import time
from typing import Any, Tuple

from ..core.runtime import BrowserRuntime
from ..perceive import perceive
from ..profile import ChromiumProfile
from .auto_capture import should_auto_capture
from .data_query import select_for_user, select_websockets
from .display import format_collect_display
from .llm_collect import parse_collect_intent, summarize_for_user
from .network_capture import NetworkCapture


def needs_smart_capture(url: str, explicit: bool) -> bool:
    return explicit or should_auto_capture(url)


def _build_display(
    page,
    url: str,
    entries,
    ws_entries,
    *,
    ask: str | None,
    want: str | None,
) -> str:
    intent = parse_collect_intent(ask or "") if ask else {}
    if ask and not want:
        want = intent.get("want") or want
    selected = select_for_user(entries, want=want)
    ws_sel = select_websockets(ws_entries, want=want)
    page_view: dict[str, Any] = {}
    try:
        pv = perceive(page, max_chars=2000)
        page_view = {"text_excerpt": pv.text_excerpt, "title": pv.title}
    except Exception:
        pass
    payload = {
        "noise_filtered_total": len(entries),
        "websocket_total": len(ws_entries),
        "websockets": ws_sel,
        "page": page_view,
        **selected,
    }
    summary = summarize_for_user(ask or want or "page data", payload) if (ask or want) else None
    return format_collect_display(
        ok=True,
        url=url,
        final_url=page.url,
        title=page.title(),
        block_signals=[],
        capture=payload,
        summary=summary,
    )


def open_with_capture(
    profile: ChromiumProfile,
    url: str,
    *,
    driver: str | None = None,
    smart: bool = False,
    ask: str | None = None,
    settle_ms: int = 5000,
) -> Tuple[Any, Any, str | None]:
    """Returns (session, page, optional_display_markdown)."""
    session = BrowserRuntime(profile).open(driver=driver)
    page = session.new_page()
    display = None

    if needs_smart_capture(url, smart):
        capture = NetworkCapture(page, capture_websockets=True)
        capture.attach()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            try:
                page.wait_for_load_state("networkidle", timeout=20_000)
            except Exception:
                pass
            time.sleep(settle_ms / 1000.0)
            display = _build_display(
                page,
                url,
                capture.entries(),
                capture.websocket_entries(),
                ask=ask,
                want=None,
            )
        finally:
            capture.detach()
    else:
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)

    return session, page, display
