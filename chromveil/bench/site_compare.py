"""Compare automation stacks on a real site (navigation + in-page signals)."""
from __future__ import annotations

import json
import os
import re
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..drivers.registry import _playwright_module
from ..drivers.session import VeilSession, open_browser
from ..e2e.probes import COLLECT_JS, evaluate_checks, score_checks
from ..profile import ChromiumProfile, is_patched_build
from ..chrome_paths import find_system_chrome
from ..resolve import resolve_executable

BLOCK_PATTERNS = re.compile(
    r"access denied|not available|geo.?restrict|blocked|captcha|verify you are human|"
    r"cloudflare|attention required|forbidden|unusual traffic",
    re.I,
)


@dataclass
class SiteVariant:
    key: str
    label: str
    driver: str
    executable: str | None = None
    chromveil_tuned: bool = False


@dataclass
class SiteRunResult:
    variant: str
    label: str
    driver: str
    executable: str | None
    navigate_ms: float
    final_url: str | None
    title: str | None
    body_chars: int
    blocked_hint: str | None
    stealth_score: float
    stealth_checks: dict[str, bool]
    probes: dict[str, Any]
    error: str | None = None


def default_bet365_variants() -> list[SiteVariant]:
    custom = resolve_executable(download=False)
    manual = find_system_chrome()
    return [
        SiteVariant("playwright_stock", "Playwright stock Chromium", "playwright"),
        SiteVariant("patchright_stock", "Patchright stock Chromium", "patchright"),
        SiteVariant(
            "patchright_manual_chrome",
            "Patchright + system Google Chrome",
            "patchright",
            executable=manual,
        ),
        SiteVariant(
            "chromveil_playwright",
            "ChromVeil launch tuning + Playwright",
            "playwright",
            executable=custom,
            chromveil_tuned=True,
        ),
        SiteVariant(
            "chromveil_patchright",
            "ChromVeil launch tuning + Patchright",
            "patchright",
            executable=custom,
            chromveil_tuned=True,
        ),
    ]


def _stock_session(profile: ChromiumProfile, driver: str, executable: str | None) -> VeilSession:
    sync_playwright = _playwright_module(driver)
    pw = sync_playwright().start()
    opts: dict[str, Any] = {"headless": profile.headless}
    if executable:
        opts["executable_path"] = executable
    browser = pw.chromium.launch(**opts)
    tag = f"{driver}-stock" if not executable else f"{driver}-manual-chrome"
    return VeilSession(profile=profile, driver=tag, cdp_url=None, browser=browser, _playwright=pw)


def _chromveil_session(profile: ChromiumProfile, driver: str) -> VeilSession:
    if profile.executable:
        profile.executable = profile.resolve_executable(download=False) or profile.executable
    return open_browser(profile, driver=driver)


def _base_profile(headless: bool) -> ChromiumProfile:
    p = ChromiumProfile.from_env()
    p.headless = headless
    p.persist_persona = False
    return p


def _tuned_profile(headless: bool, executable: str | None, driver: str) -> ChromiumProfile:
    p = _base_profile(headless)
    p.stealth_tuning = True
    p.pure_stealth = True
    p.speed_tuning = True
    p.driver = driver
    if executable:
        p.executable = executable
    return p


def _stock_profile(headless: bool) -> ChromiumProfile:
    return ChromiumProfile(
        persona_seed="site-bench",
        headless=headless,
        stealth_tuning=False,
        pure_stealth=False,
        speed_tuning=False,
        lean_gpu_args=False,
        persist_persona=False,
    )


def _open_variant(variant: SiteVariant, headless: bool) -> VeilSession:
    if variant.chromveil_tuned:
        prof = _tuned_profile(headless, variant.executable, variant.driver)
        return _chromveil_session(prof, variant.driver)
    prof = _stock_profile(headless)
    return _stock_session(prof, variant.driver, variant.executable)


def _page_signals(page) -> dict[str, Any]:
    try:
        body_len = page.evaluate("() => (document.body && document.body.innerText || '').length")
    except Exception:
        body_len = 0
    try:
        snippet = page.evaluate(
            "() => (document.body && document.body.innerText || '').slice(0, 500)"
        )
    except Exception:
        snippet = ""
    blocked = None
    if snippet and BLOCK_PATTERNS.search(snippet):
        blocked = "body_text_match"
    title = page.title() if page else ""
    if title and BLOCK_PATTERNS.search(title):
        blocked = blocked or "title_match"
    return {
        "body_chars": int(body_len or 0),
        "body_snippet": (snippet or "")[:280],
        "blocked_hint": blocked,
    }


def run_site_variant(
    variant: SiteVariant,
    url: str,
    *,
    headless: bool,
    timeout_ms: int = 120_000,
) -> SiteRunResult:
    session: VeilSession | None = None
    driver_tag = variant.driver
    t_nav = 0.0
    final_url: str | None = None
    title: str | None = None
    signals: dict[str, Any] = {}
    probes: dict[str, Any] = {}
    checks: dict[str, bool] = {}
    score = 0.0
    err: str | None = None

    if variant.key == "patchright_manual_chrome" and not variant.executable:
        return SiteRunResult(
            variant=variant.key,
            label=variant.label,
            driver=variant.driver,
            executable=None,
            navigate_ms=0,
            final_url=None,
            title=None,
            body_chars=0,
            blocked_hint=None,
            stealth_score=0,
            stealth_checks={},
            probes={},
            error="Google Chrome not found (patchright_manual_chrome skipped)",
        )

    try:
        session = _open_variant(variant, headless)
        driver_tag = session.driver
        page = session.new_page()
        t0 = time.perf_counter()
        resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=min(30_000, timeout_ms))
        except Exception:
            pass
        page.wait_for_timeout(2500)
        t_nav = (time.perf_counter() - t0) * 1000
        final_url = page.url
        title = page.title()
        if resp and resp.status >= 400:
            err = f"http_{resp.status}"
        signals = _page_signals(page)
        probes = page.evaluate(COLLECT_JS)
        patched = is_patched_build(variant.executable or resolve_executable(False))
        checks = evaluate_checks(probes, strict=patched)
        score = score_checks(checks)
        page.close()
    except Exception as exc:
        err = str(exc)
    finally:
        if session:
            session.close()

    return SiteRunResult(
        variant=variant.key,
        label=variant.label,
        driver=driver_tag,
        executable=variant.executable,
        navigate_ms=t_nav,
        final_url=final_url,
        title=title,
        body_chars=int(signals.get("body_chars") or 0),
        blocked_hint=signals.get("blocked_hint"),
        stealth_score=score,
        stealth_checks=checks,
        probes=probes,
        error=err,
    )


def run_site_comparison(
    url: str,
    *,
    headless: bool = False,
    variants: list[SiteVariant] | None = None,
    pause_s: float = 2.0,
) -> dict[str, Any]:
    variants = variants or default_bet365_variants()
    results: list[SiteRunResult] = []
    for v in variants:
        results.append(run_site_variant(v, url, headless=headless))
        time.sleep(pause_s)

    custom_exe = resolve_executable(download=False)
    summary_rows = []
    variant_meta = {v.key: v for v in variants}
    for r in results:
        v = variant_meta[r.variant]
        exe_label = r.executable
        if not exe_label and v.chromveil_tuned:
            exe_label = custom_exe or "bundled+tuned"
        elif not exe_label:
            exe_label = "bundled"
        summary_rows.append(
            {
                "variant": r.variant,
                "label": r.label,
                "executable": exe_label,
                "navigate_ms": round(r.navigate_ms, 1),
                "stealth_score": round(r.stealth_score, 3),
                "webdriver_false": r.stealth_checks.get("webdriver_false"),
                "ua_no_headless": r.stealth_checks.get("ua_no_headless_token"),
                "title": (r.title or "")[:80],
                "final_url": (r.final_url or "")[:120],
                "body_chars": r.body_chars,
                "blocked_hint": r.blocked_hint,
                "error": r.error,
            }
        )

    scores = [r.stealth_score for r in results if r.error is None]
    navs = [r.navigate_ms for r in results if r.error is None and r.navigate_ms > 0]

    return {
        "kind": "chromveil/site-comparison",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "headless": headless,
        "custom_chrome_configured": bool(custom_exe),
        "custom_chrome_path": custom_exe,
        "system_chrome_path": find_system_chrome(),
        "summary": summary_rows,
        "variants": {r.variant: _result_dict(r) for r in results},
        "notes": _comparison_notes(results, custom_exe),
        "aggregate": {
            "median_navigate_ms": statistics.median(navs) if navs else None,
            "median_stealth_score": statistics.median(scores) if scores else None,
        },
    }


def _result_dict(r: SiteRunResult) -> dict[str, Any]:
    return {
        "label": r.label,
        "driver": r.driver,
        "executable": r.executable,
        "navigate_ms": r.navigate_ms,
        "final_url": r.final_url,
        "title": r.title,
        "body_chars": r.body_chars,
        "blocked_hint": r.blocked_hint,
        "stealth_score": r.stealth_score,
        "stealth_checks": r.stealth_checks,
        "probes": {k: r.probes.get(k) for k in ("userAgent", "webdriver", "cdcKeys", "pluginsLength")},
        "error": r.error,
    }


def _comparison_notes(results: list[SiteRunResult], custom_exe: str | None) -> list[str]:
    notes: list[str] = []
    if not custom_exe:
        notes.append(
            "CHROMVEIL_EXECUTABLE is unset — “ChromVeil” variants use bundled Chromium with stealth launch argv only, not a patched engine binary."
        )
    by_key = {r.variant: r for r in results}
    pw = by_key.get("playwright_stock")
    pr = by_key.get("patchright_stock")
    if pw and pr and pw.stealth_score != pr.stealth_score:
        notes.append(
            f"Playwright vs Patchright stock stealth: {pw.stealth_score:.2f} vs {pr.stealth_score:.2f}."
        )
    cv_p = by_key.get("chromveil_patchright")
    if pr and cv_p:
        notes.append(
            f"Patchright stock vs ChromVeil+Patchright stealth: {pr.stealth_score:.2f} vs {cv_p.stealth_score:.2f}; "
            f"nav {pr.navigate_ms:.0f}ms vs {cv_p.navigate_ms:.0f}ms."
        )
    loaded = [r for r in results if r.body_chars > 200 and not r.error]
    blocked = [r for r in results if r.blocked_hint or (r.body_chars < 100 and not r.error)]
    if blocked and not loaded:
        notes.append("All variants show thin body or block hints — site may geo-block, challenge, or require interaction.")
    elif loaded:
        notes.append(f"Variants with substantial body text: {', '.join(r.variant for r in loaded)}.")
    return notes


def render_site_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# Site stack comparison",
        "",
        f"URL: {data.get('url')}",
        f"Generated: {data.get('generated_at')} UTC",
        f"Headless: {data.get('headless')}",
        "",
        "## Summary",
        "",
        "| variant | navigate_ms | stealth | webdriver_false | executable |",
        "|---------|-------------|---------|-----------------|------------|",
    ]
    for row in data.get("summary", []):
        lines.append(
            f"| {row['variant']} | {row['navigate_ms']} | {row['stealth_score']} | "
            f"{row.get('webdriver_false')} | {row.get('executable')} |"
        )
    lines.extend(["", "## Notes", ""])
    for note in data.get("notes", []):
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def write_site_report(data: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    host = re.sub(r"[^\w.-]+", "_", data.get("url", "site"))[:40]
    json_path = out_dir / f"site-{host}-{stamp}.json"
    md_path = out_dir / f"site-{host}-{stamp}.md"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md_path.write_text(render_site_markdown(data), encoding="utf-8")
    return json_path, md_path
