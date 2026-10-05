"""Light parsing of bet365-style WebSocket pipe frames (not full decode)."""
from __future__ import annotations

import re
from typing import Any

_PIPE_FIELD_RE = re.compile(r"([A-Z]{2,})=([^;|]+)")


def parse_pipe_fields(payload: str) -> list[dict[str, str]]:
    """Extract key=value segments from F|...| style frames."""
    if not payload or "F|" not in payload:
        return []
    fields: list[dict[str, str]] = []
    for chunk in payload.split("F|"):
        if not chunk.strip():
            continue
        row: dict[str, str] = {}
        for m in _PIPE_FIELD_RE.finditer(chunk):
            row[m.group(1)] = m.group(2)
        if row:
            fields.append(row)
    return fields


def summarize_websocket_frames(frames: list[dict[str, Any]], *, max_samples: int = 25) -> dict[str, Any]:
    by_host: dict[str, int] = {}
    pipe_events: list[dict[str, Any]] = []
    total_bytes = 0
    for f in frames:
        url = str(f.get("url") or "")
        host = url.split("/")[2] if "://" in url else url
        by_host[host] = by_host.get(host, 0) + 1
        total_bytes += int(f.get("size_bytes") or 0)
        payload = f.get("payload")
        if isinstance(payload, str) and "F|" in payload:
            parsed = parse_pipe_fields(payload)
            if parsed:
                pipe_events.append(
                    {
                        "url": url,
                        "direction": f.get("direction"),
                        "fields": parsed[:8],
                        "preview": payload[:120].replace("\x00", ""),
                    }
                )
    return {
        "frame_count": len(frames),
        "total_bytes": total_bytes,
        "hosts": by_host,
        "pipe_samples": pipe_events[:max_samples],
        "note": "Live odds on bet365 are mostly binary/encrypted on premws WebSockets; use page_data.text and HTTP APIs for readable content.",
    }
