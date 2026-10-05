"""Head-to-head: ChromVeil (custom/tuned chrome) vs Patchright stock."""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..binfetch import ensure_binary
from ..drivers.session import VeilSession, _playwright_module, open_browser
from ..e2e.probes import run_probes_on_page
from ..e2e.speed import SNAPSHOT_JS, SpeedReport
from ..profile import ChromiumProfile, is_patched_build


@dataclass
class VariantResult:
    name: str
    label: str
    executable: str | None
    driver: str
    stealth_score: float
    stealth_checks: dict[str, bool]
    probes: dict[str, Any]
    speed_cold_launch_ms: list[float] = field(default_factory=list)
    speed_navigate_ms: list[float] = field(default_factory=list)
    speed_snapshot_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def median_speed(self) -> dict[str, float]:
        def med(xs: list[float]) -> float:
            return statistics.median(xs) if xs else 0.0

        return {
            "cold_launch_ms": med(self.speed_cold_launch_ms),
            "navigate_ms": med(self.speed_navigate_ms),
            "snapshot_ms": med(self.speed_snapshot_ms),
        }


def _stock_patchright_session(profile: ChromiumProfile) -> VeilSession:
    """Patchright default launch — no ChromVeil stealth/speed argv."""
    sync_playwright = _playwright_module("patchright")
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=profile.headless)
    return VeilSession(profile=profile, driver="patchright-stock", cdp_url=None, browser=browser, _playwright=pw)


def _chromveil_session(profile: ChromiumProfile) -> VeilSession:
    exe = profile.resolve_executable(download=False)
    if exe:
        profile.executable = exe
    return open_browser(profile, driver="patchright")


def _one_run(
    opener: Callable[[ChromiumProfile], VeilSession],
    profile: ChromiumProfile,
    variant: VariantResult,
) -> None:
    session = opener(profile)
    try:
        t0 = time.perf_counter()
        page = session.new_page()
        cold = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        page.goto("https://example.com", wait_until="domcontentloaded", timeout=90_000)
        nav = (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        page.evaluate(SNAPSHOT_JS)
        snap = (time.perf_counter() - t2) * 1000

        variant.speed_cold_launch_ms.append(cold)
        variant.speed_navigate_ms.append(nav)
        variant.speed_snapshot_ms.append(snap)
        variant.driver = session.driver

        strict = is_patched_build(profile.executable or profile.resolve_executable(False))
        report = run_probes_on_page(
            page,
            patched=strict,
            driver=session.driver,
            executable=profile.executable,
            strict=strict,
        )
        variant.stealth_score = report.score
        variant.stealth_checks = report.checks
        variant.probes = report.probes
        page.close()
    except Exception as exc:
        variant.errors.append(str(exc))
    finally:
        session.close()


def run_comparison(runs: int = 3, headless: bool = True) -> dict[str, Any]:
    import os

    if os.environ.get("CHROMVEIL_AUTO_FETCH", "1") != "0":
        try:
            ensure_binary(download=True)
        except Exception:
            pass
    base = ChromiumProfile.from_env()
    base.headless = headless
    base.persist_persona = False  # fair cold-ish launches

    chromveil_profile = ChromiumProfile.from_env()
    chromveil_profile.headless = headless
    chromveil_profile.stealth_tuning = True
    chromveil_profile.pure_stealth = True
    chromveil_profile.speed_tuning = True
    chromveil_profile.persist_persona = False
    chromveil_profile.driver = "patchright"
    chromveil_profile.executable = ensure_binary(download=False)

    stock_profile = ChromiumProfile(
        persona_seed="stock",
        headless=headless,
        stealth_tuning=False,
        pure_stealth=False,
        speed_tuning=False,
        lean_gpu_args=False,
        persist_persona=False,
        driver="patchright",
    )

    variants = [
        VariantResult(
            name="chromveil",
            label="ChromVeil (tuned launch + ChromiumFish/custom binary when present)",
            executable=chromveil_profile.executable,
            driver="patchright",
            stealth_score=0.0,
            stealth_checks={},
            probes={},
        ),
        VariantResult(
            name="patchright_stock",
            label="Patchright stock (default launch, no ChromVeil flags)",
            executable=None,
            driver="patchright-stock",
            stealth_score=0.0,
            stealth_checks={},
            probes={},
        ),
    ]

    for i in range(max(1, runs)):
        _one_run(_chromveil_session, chromveil_profile, variants[0])
        time.sleep(0.5)
        _one_run(_stock_patchright_session, stock_profile, variants[1])
        time.sleep(0.5)

    return _build_report(variants, runs=runs)


def _build_report(variants: list[VariantResult], runs: int) -> dict[str, Any]:
    cv, st = variants[0], variants[1]
    cv_med = cv.median_speed()
    st_med = st.median_speed()

    def winner(metric: str) -> str:
        a, b = cv_med[metric], st_med[metric]
        if a <= 0 and b <= 0:
            return "n/a"
        return "chromveil" if a <= b else "patchright_stock"

    stealth_winner = "chromveil" if cv.stealth_score >= st.stealth_score else "patchright_stock"

    findings = []
    if cv.stealth_score > st.stealth_score:
        findings.append("ChromVeil wins on stealth probe score (launch tuning + binary when available).")
    elif cv.stealth_score < st.stealth_score:
        findings.append("Patchright stock scored higher on probes — review overlapping flags or headless UA.")
    else:
        findings.append("Stealth scores tied on local probes.")

    for metric, label in (
        ("cold_launch_ms", "cold launch"),
        ("navigate_ms", "navigation"),
        ("snapshot_ms", "DOM snapshot"),
    ):
        w = winner(metric)
        if w == "chromveil":
            findings.append(f"ChromVeil faster on {label} ({cv_med[metric]:.0f}ms vs {st_med[metric]:.0f}ms median).")
        elif w == "patchright_stock":
            findings.append(
                f"Patchright stock faster on {label} ({st_med[metric]:.0f}ms vs {cv_med[metric]:.0f}ms) — trim launch argv."
            )

    recommendations = _recommendations(cv, st, cv_med, st_med)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_per_variant": runs,
        "variants": {
            cv.name: {
                "label": cv.label,
                "executable": cv.executable,
                "driver": cv.driver,
                "stealth_score": cv.stealth_score,
                "stealth_checks": cv.stealth_checks,
                "probes": cv.probes,
                "speed_median": cv_med,
                "speed_runs": {
                    "cold_launch_ms": cv.speed_cold_launch_ms,
                    "navigate_ms": cv.speed_navigate_ms,
                    "snapshot_ms": cv.speed_snapshot_ms,
                },
                "errors": cv.errors,
            },
            st.name: {
                "label": st.label,
                "executable": st.executable,
                "driver": st.driver,
                "stealth_score": st.stealth_score,
                "stealth_checks": st.stealth_checks,
                "probes": st.probes,
                "speed_median": st_med,
                "speed_runs": {
                    "cold_launch_ms": st.speed_cold_launch_ms,
                    "navigate_ms": st.speed_navigate_ms,
                    "snapshot_ms": st.speed_snapshot_ms,
                },
                "errors": st.errors,
            },
        },
        "winners": {
            "stealth_score": stealth_winner,
            "cold_launch_ms": winner("cold_launch_ms"),
            "navigate_ms": winner("navigate_ms"),
            "snapshot_ms": winner("snapshot_ms"),
        },
        "findings": findings,
        "recommendations": recommendations,
    }


def _recommendations(
    cv: VariantResult,
    st: VariantResult,
    cv_med: dict[str, float],
    st_med: dict[str, float],
) -> list[str]:
    rec: list[str] = []
    if not cv.executable:
        rec.append("Run `chromveil fetch` or set CHROMVEIL_EXECUTABLE — benchmark used tuned Patchright only.")
    if st_med["cold_launch_ms"] < cv_med["cold_launch_ms"] * 0.98:
        rec.append("Use CHROMVEIL_PURE_STEALTH_MODE=lean (default) or off for cold-launch parity.")
    if cv_med["navigate_ms"] < st_med["navigate_ms"] * 0.85:
        rec.append("Keep CHROMVEIL_SPEED=1 — navigation gains from renderer throttling disabled.")
    if cv.probes.get("userAgent", "").lower().find("headlesschrome") >= 0:
        rec.append("Use headed mode or ChromiumFish binary for ua_no_headless_token in production.")
    if not cv.stealth_checks.get("webdriver_false", True):
        rec.append("Ensure ignore_default_args and custom binary are both active.")
    if st.stealth_checks.get("webdriver_false") and not cv.stealth_checks.get("webdriver_false"):
        rec.append("ChromVeil launch is worse than stock on webdriver — audit duplicate or conflicting flags.")
    rec.append("Re-run after WSL build with fork patches applied for engine-level gains.")
    return rec


def write_report(data: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"benchmark-{stamp}.json"
    md_path = out_dir / f"benchmark-{stamp}.md"
    import json

    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(data), encoding="utf-8")
    return json_path, md_path


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# ChromVeil vs Patchright benchmark",
        "",
        f"Generated: {data['generated_at']} UTC",
        f"Runs per variant: {data['runs_per_variant']}",
        "",
        "## Summary",
        "",
    ]
    for f in data.get("findings", []):
        lines.append(f"- {f}")
    lines.extend(["", "## Winners", ""])
    for k, v in data.get("winners", {}).items():
        lines.append(f"- **{k}**: `{v}`")
    lines.extend(["", "## Recommendations", ""])
    for r in data.get("recommendations", []):
        lines.append(f"- {r}")

    for name, block in data.get("variants", {}).items():
        lines.extend(
            [
                "",
                f"## {name}",
                "",
                f"- {block['label']}",
                f"- executable: `{block.get('executable')}`",
                f"- stealth score: **{block.get('stealth_score')}**",
                "",
                "### Speed (median ms)",
                "",
                f"| metric | ms |",
                f"|--------|-----|",
            ]
        )
        for m, v in block.get("speed_median", {}).items():
            lines.append(f"| {m} | {v:.2f} |")
        lines.extend(["", "### Stealth checks", ""])
        for ck, ok in block.get("stealth_checks", {}).items():
            lines.append(f"- {ck}: {'pass' if ok else '**FAIL**'}")
    return "\n".join(lines) + "\n"
