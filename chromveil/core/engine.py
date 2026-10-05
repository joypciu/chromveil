"""Browser engine resolution — custom chrome binary and capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..profile import ChromiumProfile
from ..resolve import browser_tier, resolve_executable
from .types import EngineTier


@dataclass(frozen=True)
class BrowserEngine:
    """Resolved Chromium engine (binary + tier)."""

    path: str | None
    tier: EngineTier

    @property
    def has_native_agent(self) -> bool:
        return self.tier in (EngineTier.CHROMIUMFISH, EngineTier.PATCHED, EngineTier.CUSTOM)

    @property
    def production_stealth_ready(self) -> bool:
        return self.tier != EngineTier.FALLBACK

    @classmethod
    def from_profile(cls, profile: ChromiumProfile, *, download: bool = False) -> BrowserEngine:
        if profile.executable and Path(profile.executable).exists():
            path = profile.executable
        else:
            from ..devmode import apply_dev_defaults

            apply_dev_defaults(profile)
            path = resolve_executable(download=download)
        tier_name = browser_tier(path)
        try:
            tier = EngineTier(tier_name)
        except ValueError:
            tier = EngineTier.FALLBACK if not path else EngineTier.CUSTOM
        if not path:
            tier = EngineTier.FALLBACK
        return cls(path=path, tier=tier)
