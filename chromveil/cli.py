"""chromveil up | spec | open drivers | run | serve | mcp | doctor"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .agent import run_task
from .browser import launch, open
from .profile import ChromiumProfile


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="chromveil",
        description="Your customizable Chromium — Playwright, Patchright, CDP, or any client",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("drivers", help="List supported driver backends").set_defaults(cmd="drivers")

    sp = sub.add_parser("spec", help="Export browser spec JSON (executable, argv, cdp_url)")
    sp.add_argument("-f", "--profile", help="JSON profile file")
    sp.add_argument("-o", "--out", help="Write spec to file")

    up = sub.add_parser("up", help="Start long-lived browser on CDP (for Puppeteer, Selenium, etc.)")
    up.add_argument("--port", type=int, default=9222)
    up.add_argument("--persona", default=None)
    up.add_argument("--headed", action="store_true")
    up.add_argument("-f", "--profile", help="JSON profile file")

    op = sub.add_parser("open", help="Open with playwright or patchright driver")
    op.add_argument("--driver", choices=["auto", "playwright", "patchright"], default="auto")
    op.add_argument("--url", default="about:blank")
    op.add_argument("--headed", action="store_true")
    op.add_argument(
        "--smart",
        action="store_true",
        help="After load: capture APIs/WebSockets and print display (auto for sportsbook URLs)",
    )
    op.add_argument("--ask", default=None, help="With --smart: natural language data question")
    op.add_argument("-f", "--profile")

    doc = sub.add_parser("doctor", help="Check browser binary and drivers")
    doc.add_argument("--native", action="store_true")

    rn = sub.add_parser("run", help="LLM agent task (Playwright/Patchright page)")
    rn.add_argument("task")
    rn.add_argument("--url", default="https://example.com")
    rn.add_argument("--headed", action="store_true")
    rn.add_argument("--persona", default=None)
    rn.add_argument("--driver", default="auto")
    rn.add_argument("--max-steps", type=int, default=20)

    sv = sub.add_parser("serve", help="Alias for chromveil up")
    sv.add_argument("--port", type=int, default=9222)
    sv.add_argument("--persona", default=None)
    sv.add_argument("--headless", action="store_true")

    mc = sub.add_parser("mcp", help="MCP server (WSL + ChromiumFish recommended)")
    mc.add_argument("--persona", default=None)

    sub.add_parser("fetch", help="Download ChromiumFish binary if missing").set_defaults(cmd="fetch")

    bc = sub.add_parser("bench", help="Performance comparison vs Patchright")
    bc.add_argument("subcmd", nargs="?", default="compare", choices=["compare", "site"])
    bc.add_argument(
        "--url",
        default=None,
        help="Site URL (bench site); default bet365 pregame #/HO/",
    )
    bc.add_argument(
        "--canary",
        action="store_true",
        help="Run all sportsbook canary URLs (betonline + bet365 pre/live)",
    )
    bc.add_argument("-n", "--runs", type=int, default=3)
    bc.add_argument("--headed", action="store_true")
    bc.add_argument("-o", "--out", default="reports", help="Output directory for JSON+Markdown report")
    bc.set_defaults(cmd="bench")

    vs = sub.add_parser("visit", help="Resilient navigation (rotate identity + retries on block hints)")
    vs.add_argument("url")
    vs.add_argument("--driver", default="auto")
    vs.add_argument("--headed", action="store_true")
    vs.add_argument("--attempts", type=int, default=3)
    vs.add_argument("-f", "--profile")

    co = sub.add_parser(
        "collect",
        help="Open URL, capture API traffic (noise filtered), return data matching --want",
    )
    co.add_argument("url")
    co.add_argument(
        "--want",
        default=None,
        help="Comma keywords: odds,events,markets — filters APIs and JSON fields",
    )
    co.add_argument(
        "--ask",
        default=None,
        help="Natural language question (LLM extracts keywords + summary)",
    )
    co.add_argument("--no-display", action="store_true", help="JSON only, skip markdown display block")
    co.add_argument("--url-pattern", default=None, help="Regex filter on API URLs")
    co.add_argument("--settle-ms", type=int, default=6000, help="Extra wait after load for SPA APIs")
    co.add_argument("--driver", default="auto")
    co.add_argument("--headed", action="store_true")
    co.add_argument("--attempts", type=int, default=2)
    co.add_argument("-o", "--out", help="Write JSON report")
    co.add_argument("-f", "--profile")

    cn = sub.add_parser(
        "canary",
        help="Sportsbook canary suite: betonline.ag + bet365 pregame (#/HO/) + live (#/IP/)",
    )
    cn.add_argument("--driver", default="auto")
    cn.add_argument("--headed", action="store_true")
    cn.add_argument("-o", "--out", help="Write JSON report")

    e2 = sub.add_parser("e2e", help="Stealth + speed end-to-end report (JSON)")
    e2.add_argument("--driver", default="auto")
    e2.add_argument("--headed", action="store_true", help="Headed browser (stricter UA stealth)")
    e2.add_argument("-o", "--out")

    args = ap.parse_args(argv)

    def _profile_from_args() -> ChromiumProfile:
        if getattr(args, "profile", None):
            return ChromiumProfile.from_file(args.profile)
        p = ChromiumProfile.from_env()
        if getattr(args, "persona", None):
            p.persona_seed = args.persona
        if getattr(args, "headed", False):
            p.headless = False
        if getattr(args, "headless", False):
            p.headless = True
        return p

    if args.cmd == "drivers":
        lines = [
            "auto       — patchright if installed, else playwright",
            "playwright — launch/connect via Playwright",
            "patchright — launch/connect via Patchright (undetected Playwright API)",
            "cdp        — subprocess only; use spec.cdp_url with any CDP client",
            "subprocess — same as cdp",
        ]
        print("\n".join(lines))
        return 0

    if args.cmd == "spec":
        prof = _profile_from_args()
        text = prof.to_json()
        if args.out:
            from pathlib import Path

            Path(args.out).write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0

    if args.cmd in ("up", "serve"):
        prof = _profile_from_args()
        prof.cdp_port = args.port
        from .drivers import spawn_cdp

        try:
            sess = spawn_cdp(prof)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 1
        url = sess.cdp_url
        print(json.dumps({"cdp_url": url, "persona": prof.persona_seed, "executable": prof.resolve_executable()}, indent=2))
        print(f"\nExport: set CHROMVEIL_CDP_URL={url}")
        print("Connect Playwright:  chromium.connect_over_cdp(os.environ['CHROMVEIL_CDP_URL'])")
        print("Press Ctrl+C to stop.")
        try:
            while sess._process and sess._process.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            sess.close()
        return 0

    if args.cmd == "open":
        from .intelligence.auto_capture import should_auto_capture
        from .intelligence.smart_open import open_with_capture

        prof = _profile_from_args()
        smart = getattr(args, "smart", False) or should_auto_capture(args.url)
        if smart:
            sess, page, display = open_with_capture(
                prof,
                args.url,
                driver=args.driver,
                smart=True,
                ask=getattr(args, "ask", None),
            )
            if display:
                print(display)
                print()
        else:
            sess = open(prof, driver=args.driver)
            page = sess.new_page()
            page.goto(args.url, wait_until="domcontentloaded")
        print(json.dumps({"driver": sess.driver, "url": page.url, "cdp_url": sess.cdp_url}, indent=2))
        input("Press Enter to close browser...")
        sess.close()
        return 0

    if args.cmd == "doctor":
        from .devmode import dev_status
        from .native import native_available, resolve_chrome_executable, wsl_mcp_hint

        prof = _profile_from_args()
        st = dev_status(prof)
        payload: dict = {
            "dev": st.__dict__,
            "chrome": prof.resolve_executable(download=False),
            "driver": prof.driver,
            "patchright_installed": _has_patchright(),
        }
        if args.native:
            payload["native_agent"] = native_available()
            payload["hint"] = wsl_mcp_hint()
        print(json.dumps(payload, indent=2))
        return 0

    if args.cmd == "bench":
        from pathlib import Path

        if args.subcmd == "site":
            from .bench.site_compare import run_site_comparison, write_site_report
            from .e2e.canary_runner import run_canary_suite
            from .e2e.canary_sites import default_canary_url

            if args.canary:
                prof = _profile_from_args()
                if args.headed:
                    prof.headless = False
                data = run_canary_suite(prof, driver=args.driver)
                text = json.dumps(data, indent=2)
                if args.out:
                    from pathlib import Path

                    Path(args.out).write_text(text, encoding="utf-8")
                else:
                    print(text)
                return 0 if data.get("ok") else 1

            url = args.url or default_canary_url()
            data = run_site_comparison(url, headless=not args.headed)
            jp, mp = write_site_report(data, Path(args.out))
            print(
                json.dumps(
                    {
                        "report_json": str(jp),
                        "report_md": str(mp),
                        "summary": data["summary"],
                        "notes": data["notes"],
                    },
                    indent=2,
                )
            )
            return 0

        from .bench.compare import run_comparison, write_report

        data = run_comparison(runs=args.runs, headless=not args.headed)
        jp, mp = write_report(data, Path(args.out))
        print(json.dumps({"report_json": str(jp), "report_md": str(mp), "winners": data["winners"]}, indent=2))
        return 0

    if args.cmd == "fetch":
        from .binfetch import ensure_binary

        exe = ensure_binary(download=True)
        print(json.dumps({"executable": exe, "ok": bool(exe)}, indent=2))
        return 0 if exe else 1

    if args.cmd == "canary":
        from .e2e.canary_runner import run_canary_suite

        prof = _profile_from_args()
        if args.headed:
            prof.headless = False
        report = run_canary_suite(prof, driver=args.driver)
        text = json.dumps(report, indent=2)
        if args.out:
            from pathlib import Path

            Path(args.out).write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0 if report.get("ok") else 1

    if args.cmd == "collect":
        from .intelligence.collect import collect_from_url

        prof = _profile_from_args()
        if args.headed:
            prof.headless = False
        result = collect_from_url(
            args.url,
            prof,
            driver=args.driver,
            want=args.want,
            ask=args.ask,
            url_pattern=args.url_pattern,
            settle_ms=args.settle_ms,
            max_attempts=args.attempts,
        )
        if args.out:
            from pathlib import Path

            Path(args.out).write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        if not args.no_display and result.display:
            print(result.display)
            print("\n--- JSON metadata: use -o file.json or --no-display for machine output ---\n")
        else:
            print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.ok else 1

    if args.cmd == "visit":
        from .intelligence.navigation import goto_resilient

        prof = _profile_from_args()
        result = goto_resilient(
            args.url,
            prof,
            driver=args.driver,
            max_attempts=args.attempts,
        )
        payload = {
            "ok": result.ok,
            "url": result.url,
            "title": result.title,
            "attempts": result.attempts,
            "block_signals": result.block_signals,
        }
        print(json.dumps(payload, indent=2))
        if result.session:
            result.session.close()
        return 0 if result.ok else 1

    if args.cmd == "e2e":
        from .e2e.runner import run_e2e

        prof = _profile_from_args()
        if args.headed:
            prof.headless = False
        elif os.environ.get("CHROMVEIL_E2E_HEADLESS", "1") != "0":
            prof.headless = True
        report = run_e2e(prof, driver=args.driver)
        text = json.dumps(report, indent=2)
        if args.out:
            from pathlib import Path

            Path(args.out).write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0 if report.get("ok") else 1

    if args.cmd == "mcp":
        from .mcp_server import run_server

        run_server(persona_seed=args.persona or os.environ.get("CHROMVEIL_PERSONA"))
        return 0

    if args.cmd == "run":
        prof = _profile_from_args()
        prof.headless = not args.headed
        sess = launch(
            persona_seed=prof.persona_seed,
            headless=prof.headless,
            executable_path=prof.executable,
            driver=args.driver,
        )
        try:
            page = sess.new_page()
            page.goto(args.url, wait_until="domcontentloaded")
            result = run_task(page, args.task, max_steps=args.max_steps, backend=sess.backend)
            print(
                json.dumps(
                    {
                        "success": result.success,
                        "answer": result.final_text,
                        "steps": result.steps,
                        "backend": result.backend,
                    },
                    indent=2,
                )
            )
            return 0 if result.success else 1
        finally:
            sess.close()

    return 1


def _has_patchright() -> bool:
    try:
        import patchright  # noqa: F401

        return True
    except ImportError:
        return False


if __name__ == "__main__":
    sys.exit(main())
