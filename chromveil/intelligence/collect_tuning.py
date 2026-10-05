"""Fast / light defaults for collect without losing structured intelligence."""
from __future__ import annotations

import os
from typing import Any
from .auto_capture import should_auto_capture


def light_mode_enabled() -> bool:
    return os.environ.get("CHROMVEIL_LIGHT", "1").strip().lower() in ("1", "true", "yes", "on")


def default_settle_ms() -> int:
    raw = os.environ.get("CHROMVEIL_SETTLE_MS")
    if raw and raw.isdigit():
        return int(raw)
    return 3500 if light_mode_enabled() else 6000


def resolve_all_data(
    *,
    all_flag: bool,
    no_all_flag: bool,
    want: str | None,
    ask: str | None,
) -> bool:
    if all_flag:
        return True
    if no_all_flag or want or ask:
        return False
    # Smart default: structured extract uses full in-memory APIs; export stays capped.
    if os.environ.get("CHROMVEIL_COLLECT_ALL", "").lower() in ("1", "true", "yes"):
        return True
    return False


def resolve_capture_websockets(url: str, *, all_data: bool, explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    if os.environ.get("CHROMVEIL_CAPTURE_WS", "").lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("CHROMVEIL_CAPTURE_WS", "").lower() in ("0", "false", "no"):
        return False
    # WS rarely adds structured value vs pullpod HTTP; enable only in --all mode.
    return all_data and should_auto_capture(url)


def capture_limits(all_data: bool) -> dict[str, int]:
    if all_data:
        return {"max_entries": 220, "max_ws_frames": 80, "max_body_bytes": 384_000}
    return {"max_entries": 120, "max_ws_frames": 0, "max_body_bytes": 256_000}


def export_limits(all_data: bool) -> dict[str, int]:
    return {"api_top_n": 60 if all_data else 25, "ws_top_n": 40 if all_data else 0}


def trim_extracted_for_export(extracted: dict[str, Any], *, max_selections: int = 80) -> dict[str, Any]:
    """Smaller JSON footprint; full list still used for display when needed."""
    if not extracted or extracted.get("selection_count", 0) <= max_selections:
        return extracted
    out = dict(extracted)
    sels = list(extracted.get("selections") or [])
    out["selections"] = sels[:max_selections]
    out["selection_count"] = len(sels)
    out["selections_truncated"] = len(sels) - max_selections
    return out

