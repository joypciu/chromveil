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

    lines.append(f"APIs captured (noise-filtered): {capture.get('noise_filtered_total', 0)}")
    lines.append(f"Matched for you: {capture.get('count', 0)}")
    ws = capture.get("websockets") or []
    if ws:
        lines.append(f"WebSocket frames matched: {len(ws)} (total {capture.get('websocket_total', 0)})")
    lines.append("")

    page = capture.get("page") or {}
    if page.get("text_excerpt"):
        lines.extend(["## On-screen text (excerpt)", "", page["text_excerpt"][:2000], ""])

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
