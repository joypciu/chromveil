#!/usr/bin/env python3
"""Batch collect smoke test for multiple odds/sportsbook URLs."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Run from repo root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("CHROMVEIL_AUTO_FETCH", "0")
os.environ.setdefault("CHROMVEIL_COLLECT_LLM", "0")

from chromveil.intelligence.collect import collect_from_url
from chromveil.profile import ChromiumProfile

SITES = [
    ("fanduel", "https://sportsbook.fanduel.com/"),
    ("betonline", "https://www.betonline.ag/sportsbook"),
    ("bet365_ho", "https://www.bet365.com/#/HO/"),
    ("courtside", "https://www.courtside.app/"),
    ("wagertalk", "https://www.wagertalk.com/odds?sport=today"),
    ("vsin_linetracker", "https://data.vsin.com/vegas-odds-linetracker/?sportid=nfl"),
    ("prophetx", "https://www.prophetx.co/?currency=cash"),
]


def main() -> int:
    headed = "--headed" in sys.argv
    out_dir = ROOT / "reports" / "site-bench"
    out_dir.mkdir(parents=True, exist_ok=True)
    prof = ChromiumProfile.from_env()
    prof.headless = not headed

    rows: list[dict] = []
    for key, url in SITES:
        t0 = time.perf_counter()
        err = None
        result = None
        try:
            result = collect_from_url(
                url,
                prof,
                driver="auto",
                settle_ms=8000,
                max_attempts=1,
                summarize=False,
                all_data=False,
            )
        except Exception as exc:
            err = str(exc)
        elapsed = round(time.perf_counter() - t0, 1)
        cap = result.capture if result else {}
        ex = cap.get("extracted") or {}
        row = {
            "key": key,
            "url": url,
            "ok": result.ok if result else False,
            "error": err,
            "elapsed_s": elapsed,
            "final_url": result.final_url if result else None,
            "title": (result.title or "")[:80] if result else None,
            "block_signals": result.block_signals if result else [],
            "apis": cap.get("noise_filtered_total", 0),
            "selections": ex.get("selection_count", 0),
            "events": ex.get("event_count", 0),
            "dom_odds": len(ex.get("dom_odds") or []),
            "mode": cap.get("mode"),
        }
        rows.append(row)
        if result and result.ok:
            compact = {
                "key": key,
                "extracted": ex,
                "apis_index": [
                    {"url": a.get("url"), "status": a.get("status")}
                    for a in (cap.get("apis") or [])[:15]
                ],
            }
            (out_dir / f"{key}.json").write_text(
                json.dumps(compact, indent=2), encoding="utf-8"
            )
        print(
            f"{key}: ok={row['ok']} apis={row['apis']} sel={row['selections']} "
            f"events={row['events']} {elapsed}s"
            + (f" block={row['block_signals']}" if row["block_signals"] else "")
            + (f" err={err}" if err else "")
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "headed": headed,
        "results": rows,
    }
    report_path = out_dir / "summary.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {report_path}")
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
