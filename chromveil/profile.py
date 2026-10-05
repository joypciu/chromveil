"""ChromVeil profile — one customizable browser identity, any automation driver."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .stealth import (
    PLAYWRIGHT_IGNORE_DEFAULT_ARGS,
    PURE_STEALTH_FULL_ARGS,
    PURE_STEALTH_LEAN_ARGS,
    SPEED_CHROMIUM_ARGS,
    STEALTH_CHROMIUM_ARGS,
)

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


@dataclass
class ChromiumProfile:
    """
    Single source of truth for *your* Chromium build + persona.

    Any library can either:
    - use ``chromveil.open()`` with driver=playwright|patchright, or
    - spawn via ``chromveil.up()`` / ``chrom_argv()`` and connect over CDP yourself.
    """

    persona_seed: str = "chromveil-1"
    executable: str | None = None
    headless: bool = True
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
    persist_persona: bool = True
    extra_args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    driver: DriverName = "auto"

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
            persona_seed=os.environ.get("CHROMVEIL_PERSONA", "chromveil-1"),
            executable=os.environ.get("CHROMVEIL_EXECUTABLE") or os.environ.get("CHROMVEIL_CHROME"),
            headless=_bool("CHROMVEIL_HEADLESS", True),
            window_size=(int(w), int(h)),
            timezone=os.environ.get("CHROMVEIL_TIMEZONE"),
            user_data_dir=os.environ.get("CHROMVEIL_USER_DATA_DIR"),
            cdp_host=os.environ.get("CHROMVEIL_CDP_HOST", "127.0.0.1"),
            cdp_port=int(port) if port else None,
            lean_gpu_args=_bool("CHROMVEIL_LEAN_GPU", True),
            stealth_tuning=_bool("CHROMVEIL_STEALTH", True),
            pure_stealth=_bool("CHROMVEIL_PURE_STEALTH", True),
            speed_tuning=_bool("CHROMVEIL_SPEED", True),
            persist_persona=_bool("CHROMVEIL_PERSIST_PROFILE", True),
            driver=os.environ.get("CHROMVEIL_DRIVER", "auto"),
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
        """Apply persona profile dir and defaults before launch."""
        import hashlib

        if self.persist_persona and not self.user_data_dir:
            slug = hashlib.sha256(self.persona_seed.encode("utf-8")).hexdigest()[:16]
            root = Path.home() / ".chromveil" / "profiles" / slug
            root.mkdir(parents=True, exist_ok=True)
            self.user_data_dir = str(root)
        return self

    def chromium_argv(self, *, include_cdp: bool = True, for_playwright: bool = False) -> list[str]:
        self.materialize()
        argv: list[str] = []
        if self.lean_gpu_args:
            argv.extend(LEAN_GPU_ARGS)
        argv.append(f"--persona-seed={self.persona_seed}")
        w, h = self.window_size
        argv.append(f"--window-size={w},{h}")
        if self.headless:
            argv.append("--headless=new")
        if self.user_data_dir and not for_playwright:
            argv.append(f"--user-data-dir={self.user_data_dir}")
        if include_cdp and self.cdp_port:
            argv.append(f"--remote-debugging-port={self.cdp_port}")
            argv.append("--remote-debugging-address=0.0.0.0")
        if self.stealth_tuning:
            argv.extend(STEALTH_CHROMIUM_ARGS)
        if self.pure_stealth:
            mode = os.environ.get("CHROMVEIL_PURE_STEALTH_MODE", "lean").lower()
            if mode == "full":
                argv.extend(PURE_STEALTH_FULL_ARGS)
            elif mode != "off":
                argv.extend(PURE_STEALTH_LEAN_ARGS)
        if self.speed_tuning:
            argv.extend(SPEED_CHROMIUM_ARGS)
        argv.extend(self.extra_args)
        return _dedupe_args(argv)

    def playwright_ignore_default_args(self) -> list[str]:
        if not self.stealth_tuning:
            return []
        return list(PLAYWRIGHT_IGNORE_DEFAULT_ARGS)

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
        exe = self.resolve_executable(download=False)
        return {
            "kind": "chromveil/browser-spec",
            "version": 1,
            "persona_seed": self.persona_seed,
            "executable": exe,
            "argv": self.chromium_argv(),
            "env": {k: self.merged_env()[k] for k in ("TZ",) if "TZ" in self.merged_env()},
            "cdp_url": self.cdp_url(),
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
