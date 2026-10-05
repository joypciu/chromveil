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

    e2 = sub.add_parser("e2e", help="Stealth + speed end-to-end report (JSON)")
    e2.add_argument("--driver", default="auto")
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
        prof = _profile_from_args()
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

    if args.cmd == "e2e":
        from .e2e.runner import run_e2e

        prof = _profile_from_args()
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
            page = sess.browser.new_page()
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
