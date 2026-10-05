"""Fuse DOM, HTTP APIs, and WebSockets into one `extracted` bundle."""
from __future__ import annotations

from typing import Any

from .network_capture import CapturedApi, CapturedWebSocket
from .pipe_extract import (
    dedupe_selections,
    extract_from_api_entries,
    extract_pipe_text,
    should_parse_websocket_payload,
)
from .json_extract import extract_betting_from_json


def _sports_from_leftnav(body: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(body, dict):
        return names

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k in ("name", "Name", "displayName", "title"):
                v = node.get(k)
                if isinstance(v, str) and 2 < len(v) < 60:
                    names.append(v)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node[:120]:
                walk(item)

    walk(body)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out[:80]


def build_extracted(
    entries: list[CapturedApi],
    ws_entries: list[CapturedWebSocket],
    page_data: dict[str, Any] | None,
) -> dict[str, Any]:
    selections = extract_from_api_entries(entries)
    api_count = len(selections)

    if api_count < 5:
        for ws in ws_entries:
            payload = ws.payload
            if isinstance(payload, str) and should_parse_websocket_payload(ws.url, payload):
                selections.extend(
                    extract_pipe_text(payload, source=ws.url.split("?")[0])
                )
            elif isinstance(payload, dict):
                selections.extend(extract_betting_from_json(payload, source=ws.url))

    selections = dedupe_selections(selections)

    events = sorted({s["event"] for s in selections if s.get("event")})
    fixture_ids = {s["fixture_id"] for s in selections if s.get("fixture_id")}
    competitions = sorted({s["competition"] for s in selections if s.get("competition")})

    sports_menu: list[str] = []
    for e in entries:
        if "allsportsmenu" in e.url.lower() or "sportsmenu" in e.url.lower():
            sports_menu = _sports_from_leftnav(e.body)
            break

    pd = page_data or {}
    dom_events = pd.get("events_on_screen") or []
    dom_odds = pd.get("odds_on_screen") or []

    return {
        "selections": selections,
        "selection_count": len(selections),
        "events": events[:60],
        "event_count": len(events) or len(fixture_ids),
        "fixture_ids": sorted(fixture_ids)[:80],
        "competitions": competitions[:40],
        "sports_menu": sports_menu,
        "dom_events": dom_events[:40],
        "dom_odds": dom_odds[:80],
        "sources": {
            "api_entries": len(entries),
            "websocket_frames": len(ws_entries),
            "pipe_selections": sum(1 for s in selections if s.get("segment") in ("MA", "MG", "PA")),
            "json_selections": sum(1 for s in selections if s.get("segment") == "json"),
        },
    }


def compact_capture_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Smaller JSON export: drop raw WS bodies, keep structured extract + API index."""
    out = dict(payload)
    apis = out.get("apis") or []
    out["apis_index"] = [
        {
            "url": a.get("url"),
            "method": a.get("method"),
            "status": a.get("status"),
            "size_bytes": len(str(a.get("data"))) if a.get("data") is not None else 0,
        }
        for a in apis
    ]
    out.pop("apis", None)
    out.pop("websockets", None)
    if out.get("page_data") and isinstance(out["page_data"], dict):
        pd = dict(out["page_data"])
        if len(pd.get("text") or "") > 4000:
            pd["text"] = (pd["text"][:4000] + "…") if pd.get("text") else ""
        out["page_data"] = pd
    return out
