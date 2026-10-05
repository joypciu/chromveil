"""Run resilient navigation across all canary sportsbook URLs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..intelligence.navigation import goto_resilient
from ..profile import ChromiumProfile
from .canary_sites import CANARY_SPORTSBOOK_SITES, CanarySite


def _title_ok(site: CanarySite, title: str | None) -> bool:
    if not title:
        return False
    low = title.lower()
    return any(frag.lower() in low for frag in site.title_fragments)


def run_canary_suite(profile: ChromiumProfile | None = None, *, driver: str | None = None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    all_ok = True
    for site in CANARY_SPORTSBOOK_SITES:
        result = goto_resilient(site.url, profile, driver=driver, max_attempts=3)
        ok = result.ok and _title_ok(site, result.title)
        all_ok = all_ok and ok
        row = {
            "key": site.key,
            "label": site.label,
            "url": site.url,
            "ok": ok,
            "final_url": result.url,
            "title": result.title,
            "attempts": result.attempts,
            "block_signals": result.block_signals,
        }
        if result.session:
            result.session.close()
        results.append(row)
    return {
        "kind": "chromveil/canary-suite",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sites": [s.key for s in CANARY_SPORTSBOOK_SITES],
        "ok": all_ok,
        "results": results,
    }


def main_json(profile: ChromiumProfile | None = None, *, driver: str | None = None) -> str:
    return json.dumps(run_canary_suite(profile, driver=driver), indent=2)
