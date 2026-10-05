"""Generic JSON walking for odds / events (non-pipe sportsbooks)."""
from __future__ import annotations

from typing import Any

_ODDS_KEYS = frozenset(
    {
        "odds",
        "price",
        "decimal",
        "decimalodds",
        "americanodds",
        "fractional",
        "line",
        "handicap",
    }
)
_NAME_KEYS = frozenset({"name", "label", "title", "description", "participant", "runner"})
_EVENT_KEYS = frozenset({"event", "eventname", "fixture", "match", "game", "contest"})
_MARKET_KEYS = frozenset({"market", "marketname", "bettype", "type"})


def _pick(d: dict[str, Any], keys: frozenset[str]) -> str | None:
    for k, v in d.items():
        if k.lower() in keys and v is not None:
            s = str(v).strip()
            if s:
                return s
    return None


def _odds_from_dict(d: dict[str, Any]) -> str | None:
    for k, v in d.items():
        kl = k.lower()
        if kl in _ODDS_KEYS and v is not None:
            if isinstance(v, dict):
                for sub in ("decimal", "american", "fractional", "display"):
                    if sub in v and v[sub]:
                        return str(v[sub])
            return str(v)
    return None


def extract_betting_from_json(obj: Any, *, source: str = "", depth: int = 0) -> list[dict[str, Any]]:
    if depth > 14:
        return []
    rows: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        odds = _odds_from_dict(obj)
        if odds:
            rows.append(
                {
                    "event": _pick(obj, _EVENT_KEYS),
                    "market": _pick(obj, _MARKET_KEYS),
                    "selection": _pick(obj, _NAME_KEYS),
                    "odds": odds,
                    "competition": obj.get("competition") or obj.get("league") or obj.get("sport"),
                    "fixture_id": obj.get("id") or obj.get("fixtureId") or obj.get("eventId"),
                    "segment": "json",
                    "source": source,
                }
            )
        for v in obj.values():
            rows.extend(extract_betting_from_json(v, source=source, depth=depth + 1))
    elif isinstance(obj, list):
        for item in obj[:200]:
            rows.extend(extract_betting_from_json(item, source=source, depth=depth + 1))
    return rows
