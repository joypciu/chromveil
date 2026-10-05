"""Human-readable display for collect results."""
from __future__ import annotations

import json
from typing import Any


def format_collect_display(
    *,
    ok: bool,
    url: str,
    final_url: str | None,
    title: str | None,
    block_signals: list[str],
    capture: dict[str, Any],
    summary: str | None = None,
) -> str:
    lines = [
        f"# {title or '(no title)'}",
        f"URL: {final_url or url}",
        f"Status: {'OK' if ok else 'BLOCKED / INCOMPLETE'}",
        "",
    ]
    if block_signals:
        lines.append(f"Block signals: {', '.join(block_signals)}")
        lines.append("")

    ex = capture.get("extracted") or {}
    if ex.get("selection_count"):
        lines.append(
            f"Structured: {ex['selection_count']} selections, "
            f"{ex.get('event_count', 0)} events, "
            f"{len(ex.get('competitions') or [])} competitions"
        )
    lines.append(f"APIs captured (noise-filtered): {capture.get('noise_filtered_total', 0)}")
    lines.append(f"Matched for you: {capture.get('count', 0)}")
    ws = capture.get("websockets") or []
    if ws:
        lines.append(f"WebSocket frames matched: {len(ws)} (total {capture.get('websocket_total', 0)})")
    lines.append("")

    page = capture.get("page") or {}
    if page.get("text_excerpt"):
        lines.extend(["## On-screen text (excerpt)", "", page["text_excerpt"][:2000], ""])

    if ex.get("selections"):
        lines.extend(["## Extracted markets (API + DOM)", ""])
        for i, s in enumerate(ex["selections"][:25], 1):
            ev = s.get("event") or "—"
            mk = s.get("market") or ""
            sel = s.get("selection") or s.get("event") or "—"
            odds = s.get("odds") or "?"
            comp = s.get("competition") or ""
            tail = f" [{comp}]" if comp else ""
            if mk:
                lines.append(f"{i}. **{ev}** — {mk}: {sel} @ **{odds}**{tail}")
            else:
                lines.append(f"{i}. {sel} @ **{odds}**{tail}")
        if ex.get("selection_count", 0) > 25:
            lines.append(f"\n… +{ex['selection_count'] - 25} more in `extracted.selections`.")
        lines.append("")

    pd = capture.get("page_data") or {}
    if pd.get("text"):
        lines.extend(
            [
                "## Page data (fused)",
                "",
                f"Characters: {pd.get('text_char_count', 0)} | "
                f"Odds on screen: {len(pd.get('odds_on_screen') or [])} | "
                f"Events: {len(pd.get('events_on_screen') or [])} | "
                f"Betting rows: {len(pd.get('betting_rows') or [])}",
                "",
                pd["text"][:3500] + ("…" if len(pd["text"]) > 3500 else ""),
                "",
            ]
        )
        events = pd.get("events_on_screen") or []
        if events:
            lines.append("Events: " + " | ".join(events[:10]))
            lines.append("")
        odds = pd.get("odds_on_screen") or []
        if odds:
            lines.append("Sample odds: " + ", ".join(odds[:24]))
            lines.append("")

    ws_ins = capture.get("websocket_insights") or {}
    if ws_ins.get("pipe_samples"):
        lines.append("## WebSocket (pipe samples)")
        for i, s in enumerate(ws_ins["pipe_samples"][:8], 1):
            fields = s.get("fields") or []
            flat = "; ".join(f"{k}={v}" for row in fields for k, v in row.items())[:200]
            lines.append(f"{i}. {flat or s.get('preview', '')[:120]}")
        lines.append("")

    if summary:
        lines.extend(["## Answer", "", summary, ""])

    lines.append("## APIs")
    for i, api in enumerate((capture.get("apis") or [])[:15], 1):
        u = api.get("url", "")
        lines.append(f"{i}. `{u[:100]}` ({api.get('method')}, {api.get('status')})")
        body = api.get("data")
        if body is not None:
            snippet = json.dumps(body, default=str)
            if len(snippet) > 400:
                snippet = snippet[:400] + "…"
            lines.append(f"   ```json\n   {snippet}\n   ```")
    if (capture.get("count") or 0) > 15:
        lines.append(f"\n… and {capture['count'] - 15} more (see JSON export).")
    return "\n".join(lines)
