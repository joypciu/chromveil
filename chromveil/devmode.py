"""Development without a custom Chromium build yet."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .profile import ChromiumProfile
from .resolve import browser_tier, resolve_executable


@dataclass
class DevStatus:
    tier: str  # patched | chromiumfish-binary | driver-fallback
    message: str
    executable: str | None
    ready_for_production_stealth: bool


def apply_dev_defaults(profile: ChromiumProfile) -> ChromiumProfile:
    """Maximize what we can control before the fork binary ships."""
    profile.stealth_tuning = True
    profile.pure_stealth = True
    profile.speed_tuning = True
    if os.environ.get("CHROMVEIL_DEV", "1") != "0":
        profile.driver = profile.driver or "auto"
    return profile


def dev_status(profile: ChromiumProfile | None = None) -> DevStatus:
    prof = apply_dev_defaults(profile or ChromiumProfile.from_env())
    exe = resolve_executable(download=False)
    tier = browser_tier(exe)

    if tier == "patched":
        return DevStatus(
            tier="patched",
            message="Custom/patched Chromium available.",
            executable=exe,
            ready_for_production_stealth=True,
        )
    if tier == "chromiumfish":
        return DevStatus(
            tier="chromiumfish-binary",
            message="ChromiumFish prebuild — good stealth; native agent when LLM configured.",
            executable=exe,
            ready_for_production_stealth=True,
        )
    if tier == "custom" and exe:
        return DevStatus(
            tier="system-chrome",
            message=(
                "Using installed Chrome with ChromVeil stealth launch + rotating ephemeral profiles. "
                "Set CHROMVEIL_EXECUTABLE for patched/ChromiumFish builds for engine-level hardening."
            ),
            executable=exe,
            ready_for_production_stealth=False,
        )
    return DevStatus(
        tier="driver-fallback",
        message=(
            "No Chromium binary resolved — bundled Playwright/Patchright + ChromVeil tuning only. "
            "On Windows enable auto system Chrome (default) or set CHROMVEIL_EXECUTABLE / WSL build."
        ),
        executable=None,
        ready_for_production_stealth=False,
    )
