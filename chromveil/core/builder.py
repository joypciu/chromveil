"""Build LaunchPlan from ChromiumProfile (single composition root)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..profile import ChromiumProfile, LEAN_GPU_ARGS, _dedupe_args
from ..stealth import (
    PLAYWRIGHT_IGNORE_DEFAULT_ARGS,
    PURE_STEALTH_FULL_ARGS,
    PURE_STEALTH_LEAN_ARGS,
    SPEED_CHROMIUM_ARGS,
    STEALTH_CHROMIUM_ARGS,
)
from .engine import BrowserEngine
from .launch_plan import LaunchPlan


@dataclass(frozen=True)
class LaunchContext:
    """How the plan will be consumed."""

    include_cdp: bool = True
    for_playwright: bool = False
    resolve_binary: bool = False


def build_launch_plan(profile: ChromiumProfile, ctx: LaunchContext | None = None) -> LaunchPlan:
    ctx = ctx or LaunchContext()
    profile.materialize()
    engine = BrowserEngine.from_profile(profile, download=ctx.resolve_binary)

    argv: list[str] = []
    if profile.lean_gpu_args:
        argv.extend(LEAN_GPU_ARGS)
    argv.append(f"--persona-seed={profile.persona_seed}")
    w, h = profile.window_size
    argv.append(f"--window-size={w},{h}")
    if profile.headless:
        argv.append("--headless=new")
    # user-data-dir is applied by Playwright via launch_persistent_context; subprocess uses argv.
    if profile.user_data_dir and not ctx.for_playwright:
        argv.append(f"--user-data-dir={profile.user_data_dir}")
    if ctx.include_cdp and profile.cdp_port:
        argv.append(f"--remote-debugging-port={profile.cdp_port}")
        argv.append("--remote-debugging-address=0.0.0.0")
    if profile.stealth_tuning:
        argv.extend(STEALTH_CHROMIUM_ARGS)
    if profile.pure_stealth:
        mode = os.environ.get("CHROMVEIL_PURE_STEALTH_MODE", "lean").lower()
        if mode == "full":
            argv.extend(PURE_STEALTH_FULL_ARGS)
        elif mode != "off":
            argv.extend(PURE_STEALTH_LEAN_ARGS)
    if profile.speed_tuning:
        argv.extend(SPEED_CHROMIUM_ARGS)
    argv.extend(profile.extra_args)

    ignore: tuple[str, ...] = ()
    if profile.stealth_tuning and ctx.for_playwright:
        ignore = tuple(PLAYWRIGHT_IGNORE_DEFAULT_ARGS)

    assert profile.persona_seed is not None
    return LaunchPlan(
        persona_seed=profile.persona_seed,
        engine_tier=engine.tier.value,
        executable=engine.path,
        argv=tuple(_dedupe_args(argv)),
        env=profile.merged_env(),
        headless=profile.headless,
        ignore_default_args=ignore,
        proxy=profile.proxy,
        cdp_url=profile.cdp_url(),
        user_data_dir=profile.user_data_dir,
    )
