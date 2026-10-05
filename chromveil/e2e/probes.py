"""In-page stealth / consistency probes (file:// or https)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROBE_HTML = Path(__file__).parent / "fixtures" / "stealth_probe.html"

COLLECT_JS = """
() => ({
  webdriver: navigator.webdriver,
  userAgent: navigator.userAgent,
  languages: [...navigator.languages],
  platform: navigator.platform,
  hardwareConcurrency: navigator.hardwareConcurrency,
  deviceMemory: navigator.deviceMemory || null,
  chromeRuntime: !!(window.chrome && window.chrome.runtime),
  cdcKeys: Object.keys(window).filter(k => /^cdc_|^\\$cdc_/.test(k)),
  permissionsQuery: typeof navigator.permissions?.query === 'function',
  outerWidth: window.outerWidth,
  outerHeight: window.outerHeight,
  innerWidth: window.innerWidth,
  innerHeight: window.innerHeight,
})
"""


@dataclass
class StealthReport:
    patched_build: bool
    driver: str
    executable: str | None
    probes: dict[str, Any]
    checks: dict[str, bool]
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "patched_build": self.patched_build,
            "driver": self.driver,
            "executable": self.executable,
            "probes": self.probes,
            "checks": self.checks,
            "score": self.score,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def evaluate_checks(probes: dict[str, Any], *, patched: bool) -> dict[str, bool]:
    checks = {
        "no_cdc_globals": len(probes.get("cdcKeys") or []) == 0,
        "webdriver_false": probes.get("webdriver") is False,
        "languages_non_empty": bool(probes.get("languages")),
        "viewport_sane": (probes.get("outerWidth") or 0) >= (probes.get("innerWidth") or 0),
    }
    if patched:
        checks["webdriver_false_strict"] = probes.get("webdriver") is False
    return checks


def score_checks(checks: dict[str, bool]) -> float:
    if not checks:
        return 0.0
    return sum(1 for v in checks.values() if v) / len(checks)


def run_probes_on_page(page, *, patched: bool, driver: str, executable: str | None) -> StealthReport:
    url = PROBE_HTML.resolve().as_uri()
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    raw = page.evaluate(COLLECT_JS)
    checks = evaluate_checks(raw, patched=patched)
    return StealthReport(
        patched_build=patched,
        driver=driver,
        executable=executable,
        probes=raw,
        checks=checks,
        score=score_checks(checks),
    )
