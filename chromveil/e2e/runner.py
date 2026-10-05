"""End-to-end stealth + speed runner."""
from __future__ import annotations

import json
import os
from typing import Any

from ..drivers import open_browser
from ..profile import ChromiumProfile, is_patched_build
from .probes import run_probes_on_page
from .speed import bench_session


def run_e2e(profile: ChromiumProfile | None = None, driver: str | None = None) -> dict[str, Any]:
    prof = profile or ChromiumProfile.from_env()
    if profile is None:
        prof.headless = os.environ.get("CHROMVEIL_HEADLESS", "0") != "0"
    exe = prof.resolve_executable(download=False)
    patched = is_patched_build(exe)

    session = open_browser(prof, driver=driver)
    try:
        page = session.new_page()
        stealth = run_probes_on_page(
            page,
            patched=patched,
            driver=session.driver,
            executable=exe,
        )
        speed = bench_session(session, session.driver)
    finally:
        session.close()

    report = {
        "stealth": stealth.to_dict(),
        "speed": speed.to_dict(),
        "thresholds": {
            "navigate_ms_max": float(os.environ.get("CHROMVEIL_E2E_NAV_MS", "8000")),
            "stealth_score_min": float(os.environ.get("CHROMVEIL_E2E_SCORE_MIN", "0.75")),
        },
    }
    report["ok"] = (
        report["stealth"]["score"] >= report["thresholds"]["stealth_score_min"]
        and report["speed"]["navigate_ms"] <= report["thresholds"]["navigate_ms_max"]
    )
    if patched:
        report["ok"] = report["ok"] and report["stealth"]["checks"].get("webdriver_false", False)
    return report


def main_json() -> str:
    return json.dumps(run_e2e(), indent=2)
