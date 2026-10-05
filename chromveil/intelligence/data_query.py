"""Select API payloads the user cares about (URL filter + keyword / JSON path hints)."""
from __future__ import annotations

import json
import re
from typing import Any

from .network_capture import CapturedApi


def _walk_json(obj: Any, tokens: list[str], path: str = "") -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            key_low = k.lower()
            if any(t in key_low for t in tokens):
                hits.append({"path": p, "value": v})
            hits.extend(_walk_json(v, tokens, p))
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:50]):
            hits.extend(_walk_json(item, tokens, f"{path}[{i}]"))
    else:
        s = str(obj).lower()
        if any(t in s for t in tokens):
            hits.append({"path": path or "$", "value": obj})
    return hits


def filter_by_url_pattern(entries: list[CapturedApi], pattern: str | None) -> list[CapturedApi]:
    if not pattern:
        return entries
    rx = re.compile(pattern, re.I)
    return [e for e in entries if rx.search(e.url)]


def select_for_user(
    entries: list[CapturedApi],
    *,
    want: str | None = None,
    url_pattern: str | None = None,
    min_relevance: float = 0.0,
    top_n: int = 40,
) -> dict[str, Any]:
    """
    ``want``: comma-separated keywords (e.g. ``odds,events,markets``).
    Returns ranked APIs plus optional JSON path hits inside bodies.
    """
    pool = filter_by_url_pattern(entries, url_pattern)
    pool = [e for e in pool if e.relevance >= min_relevance]
    pool.sort(key=lambda e: e.relevance, reverse=True)
    pool = pool[:top_n]

    tokens = [t.strip().lower() for t in (want or "").split(",") if t.strip()]
    selected: list[dict[str, Any]] = []
    for e in pool:
        row: dict[str, Any] = {
            "url": e.url,
            "method": e.method,
            "status": e.status,
            "relevance": e.relevance,
        }
        if tokens:
            blob = json.dumps(e.body, default=str).lower()
            url_hit = any(t in e.url.lower() for t in tokens)
            body_hit = any(t in blob for t in tokens)
            if not url_hit and not body_hit:
                path_hits = _walk_json(e.body, tokens)
                if not path_hits:
                    continue
                row["matches"] = path_hits[:25]
            else:
                row["matches"] = {"url_hit": url_hit, "body_hit": body_hit}
        row["data"] = e.body
        selected.append(row)

    if not tokens:
        selected = [{"url": e.url, "method": e.method, "status": e.status, "data": e.body} for e in pool]

    return {
        "count": len(selected),
        "total_captured": len(entries),
        "keywords": tokens,
        "apis": selected,
    }
