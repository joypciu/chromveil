"""ChromVeil profile — one customizable browser identity, any automation driver."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any


# GPU-less defaults aligned with ChromiumFish launcher (safe on Linux/WSL headless).
LEAN_GPU_ARGS: tuple[str, ...] = (
    "--no-sandbox",
    "--no-zygote",
    "--disable-dev-shm-usage",
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
)

DriverName = str  # playwright | patchright | cdp | subprocess | auto


def default_driver_name() -> str:
    """Patchright when installed (bet365-style sites); else playwright."""
    try:
        import patchright  # noqa: F401

        return "patchright"
    except ImportError:
        return "playwright"


@dataclass
class ChromiumProfile:
    """
    Single source of truth for *your* Chromium build + persona.

    Any library can either:
    - use ``chromveil.open()`` with driver=playwright|patchright, or
    - spawn via ``chromveil.up()`` / ``chrom_argv()`` and connect over CDP yourself.
    """

    persona_seed: str | None = None
    executable: str | None = None
    headless: bool = False
    window_size: tuple[int, int] = (1920, 1080)
    proxy: dict[str, Any] | None = None
    timezone: str | None = None  # IANA zone, or "auto" (ChromiumFish ip2tz when available)
    user_data_dir: str | None = None
    cdp_host: str = "127.0.0.1"
    cdp_port: int | None = None
    lean_gpu_args: bool = True
    stealth_tuning: bool = True
    pure_stealth: bool = True
    speed_tuning: bool = True
    persist_persona: bool = False
    extra_args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    driver: DriverName = "patchright"

    @classmethod
    def from_env(cls) -> ChromiumProfile:
        def _bool(key: str, default: bool) -> bool:
            v = os.environ.get(key)
            if v is None:
                return default
            return v.strip().lower() in ("1", "true", "yes", "on")

        port = os.environ.get("CHROMVEIL_CDP_PORT") or os.environ.get("CHROMIUMFISH_CDP_PORT")
        w = os.environ.get("CHROMVEIL_WINDOW_WIDTH", "1920")
        h = os.environ.get("CHROMVEIL_WINDOW_HEIGHT", "1080")
        return cls(
            persona_seed=os.environ.get("CHROMVEIL_PERSONA"),
            executable=os.environ.get("CHROMVEIL_EXECUTABLE") or os.environ.get("CHROMVEIL_CHROME"),
            headless=_bool("CHROMVEIL_HEADLESS", False),
            window_size=(int(w), int(h)),
            timezone=os.environ.get("CHROMVEIL_TIMEZONE"),
            user_data_dir=os.environ.get("CHROMVEIL_USER_DATA_DIR"),
            cdp_host=os.environ.get("CHROMVEIL_CDP_HOST", "127.0.0.1"),
            cdp_port=int(port) if port else None,
            lean_gpu_args=_bool("CHROMVEIL_LEAN_GPU", True),
            stealth_tuning=_bool("CHROMVEIL_STEALTH", True),
            pure_stealth=_bool("CHROMVEIL_PURE_STEALTH", True),
            speed_tuning=_bool("CHROMVEIL_SPEED", True),
            persist_persona=_bool("CHROMVEIL_PERSIST_PROFILE", False),
            driver=os.environ.get("CHROMVEIL_DRIVER") or default_driver_name(),
        )

    @classmethod
    def from_file(cls, path: str | Path) -> ChromiumProfile:
        p = Path(path)
        raw = json.loads(p.read_text(encoding="utf-8"))
        if "window_size" in raw and isinstance(raw["window_size"], list):
            raw["window_size"] = tuple(raw["window_size"])
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in allowed})

    def resolve_executable(self, download: bool = False) -> str | None:
        if self.executable and Path(self.executable).exists():
            return self.executable
        from .devmode import apply_dev_defaults
        from .resolve import resolve_executable

        apply_dev_defaults(self)
        return resolve_executable(download=download)

    def materialize(self) -> ChromiumProfile:
        """Stealth defaults + ephemeral or persistent session profile."""
        from .core.persona import prepare_session_identity

        prepare_session_identity(self)
        return self

    def chromium_argv(self, *, include_cdp: bool = True, for_playwright: bool = False) -> list[str]:
        from .core.builder import LaunchContext, build_launch_plan

        plan = build_launch_plan(
            self,
            LaunchContext(include_cdp=include_cdp, for_playwright=for_playwright),
        )
        return plan.argv_list()

    def playwright_ignore_default_args(self) -> list[str]:
        from .core.builder import LaunchContext, build_launch_plan

        plan = build_launch_plan(self, LaunchContext(for_playwright=True))
        return list(plan.ignore_default_args)

    def launch_plan(self, **ctx_kwargs):
        from .core.builder import LaunchContext, build_launch_plan

        return build_launch_plan(self, LaunchContext(**ctx_kwargs))

    def merged_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.update(self.env)
        if self.timezone and self.timezone != "auto":
            env["TZ"] = self.timezone
        return env

    def cdp_url(self) -> str | None:
        if not self.cdp_port:
            return None
        return f"http://{self.cdp_host}:{self.cdp_port}"

    def to_spec(self) -> dict[str, Any]:
        from .core.builder import LaunchContext, build_launch_plan

        plan = build_launch_plan(self, LaunchContext(resolve_binary=False))
        return {
            "kind": "chromveil/browser-spec",
            "version": 2,
            "persona_seed": self.persona_seed,
            "engine_tier": plan.engine_tier,
            "executable": plan.executable,
            "argv": plan.argv_list(),
            "env": {k: plan.env[k] for k in ("TZ",) if k in plan.env},
            "cdp_url": plan.cdp_url,
            "driver_hint": self.driver,
            "connect": {
                "playwright": "playwright.chromium.connect_over_cdp(cdp_url)",
                "patchright": "patchright.chromium.connect_over_cdp(cdp_url)",
                "puppeteer": "puppeteer.connect({ browserURL: cdp_url })",
                "selenium": "options.debugger_address = host:port",
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_spec(), indent=indent)


def _dedupe_args(argv: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for a in argv:
        key = a.split("=", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def is_patched_build(executable: str | None) -> bool:
    from .resolve import browser_tier

    if os.environ.get("CHROMVEIL_EXPECT_PATCHED", "").lower() in ("1", "true", "yes"):
        return True
    return browser_tier(executable) in ("patched", "chromiumfish", "custom")
