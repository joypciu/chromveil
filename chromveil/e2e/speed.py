"""Speed benchmarks for ChromVeil sessions."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class SpeedReport:
    cold_launch_ms: float
    navigate_ms: float
    snapshot_ms: float
    driver: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cold_launch_ms": round(self.cold_launch_ms, 2),
            "navigate_ms": round(self.navigate_ms, 2),
            "snapshot_ms": round(self.snapshot_ms, 2),
            "driver": self.driver,
        }


SNAPSHOT_JS = "() => document.querySelectorAll('a,button,input').length"


def bench_session(session, driver: str) -> SpeedReport:
    t0 = time.perf_counter()
    page = session.new_page()
    cold = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    page.goto("https://example.com", wait_until="domcontentloaded", timeout=60_000)
    nav = (time.perf_counter() - t1) * 1000

    t2 = time.perf_counter()
    page.evaluate(SNAPSHOT_JS)
    snap = (time.perf_counter() - t2) * 1000

    page.close()
    return SpeedReport(cold_launch_ms=cold, navigate_ms=nav, snapshot_ms=snap, driver=driver)
