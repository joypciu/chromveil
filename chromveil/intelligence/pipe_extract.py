"""Decode bet365-style pipe streams (F|…;KEY=val;|) into structured betting rows."""
from __future__ import annotations

import re
from typing import Any

from .network_capture import CapturedApi

_PIPE_KV_RE = re.compile(r"([A-Z][A-Z0-9]{0,2})=([^;|]*)")
_JS_BLOB_RE = re.compile(r"^\s*\(\(\)\s*=>|^\s*var\s+SITE_ROOT", re.I)
_VALID_ODDS_RE = re.compile(r"^(\d+/\d+|\d+\.\d{1,3})$")
_PREMWS_HOST_RE = re.compile(r"premws-|pshudws\.", re.I)


def is_pipe_payload(text: str) -> bool:
    if not text or len(text) < 8:
        return False
    if _JS_BLOB_RE.search(text[:80]):
        return False
    if "F|" not in text:
        return False
    return bool(
        re.search(r"(N2|MN|CC|NA|FI|BI)=", text) or re.search(r"OD=\d+/\d+", text)
    )


def should_parse_websocket_payload(url: str, text: str) -> bool:
    """premws streams are mostly encrypted; avoid false KV matches on binary."""
    if not is_pipe_payload(text):
        return False
    if _PREMWS_HOST_RE.search(url):
        return "N2=" in text or "MN=" in text or bool(re.search(r"OD=\d+/\d+", text))
    return True


def parse_pipe_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for raw in re.split(r"\|+", text):
        chunk = re.sub(r"^[\x00-\x08]+", "", raw.strip())
        if not chunk or len(chunk) < 2:
            continue
        seg_type: str | None = None
        body = chunk
        if re.match(r"^[A-Z]{2,4};", chunk):
            seg_type, body = chunk.split(";", 1)
        fields: dict[str, str] = {}
        for m in _PIPE_KV_RE.finditer(body):
            fields[m.group(1)] = m.group(2)
        if seg_type:
            fields["_segment"] = seg_type
        if fields:
            records.append(fields)
    return records


def records_to_selections(
    records: list[dict[str, str]],
    *,
    source: str = "",
) -> list[dict[str, Any]]:
    """Turn MA/MG/PA rows with odds into normalized selection objects."""
    out: list[dict[str, Any]] = []
    for r in records:
        odds = r.get("OD") or r.get("OX") or r.get("OT")
        if not odds or not _VALID_ODDS_RE.match(odds.strip()):
            continue
        name = r.get("NA") or r.get("N2") or r.get("MN")
        if not name and not r.get("N2"):
            continue
        if name and "/" in name and " " not in name and name.startswith("/"):
            continue
        row = {
            "event": r.get("N2") or None,
            "market": r.get("MN") or None,
            "selection": r.get("NA") if r.get("NA") else None,
            "odds": odds,
            "competition": r.get("CC") or r.get("CT") or None,
            "fixture_id": r.get("FI") or r.get("BI") or r.get("ID") or None,
            "segment": r.get("_segment"),
            "source": source,
        }
        if row["selection"] and row["event"] and row["selection"] == row["event"]:
            row["selection"] = None
        if row["event"] or row["market"] or row["selection"]:
            out.append(row)
    return out


def dedupe_selections(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for r in rows:
        key = (
            r.get("event"),
            r.get("market"),
            r.get("selection"),
            r.get("odds"),
            r.get("competition"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def extract_pipe_text(text: str, *, source: str = "") -> list[dict[str, Any]]:
    if not is_pipe_payload(text):
        return []
    return dedupe_selections(records_to_selections(parse_pipe_records(text), source=source))


def extract_from_api_entries(entries: list[CapturedApi]) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    for e in entries:
        body = e.body
        source = e.url.split("?")[0]
        if isinstance(body, str):
            all_rows.extend(extract_pipe_text(body, source=source))
        elif isinstance(body, dict):
            from .json_extract import extract_betting_from_json

            all_rows.extend(extract_betting_from_json(body, source=source))
    return dedupe_selections(all_rows)
