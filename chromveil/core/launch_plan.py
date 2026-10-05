"""Immutable launch contract: binary + argv + driver hints."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LaunchPlan:
    """
    Everything needed to start *our* Chromium once.

    Drivers consume this; they do not re-derive flags from scattered profile fields.
    """

    persona_seed: str
    engine_tier: str
    executable: str | None
    argv: tuple[str, ...]
    env: dict[str, str]
    headless: bool
    ignore_default_args: tuple[str, ...] = ()
    proxy: dict[str, Any] | None = None
    cdp_url: str | None = None
    user_data_dir: str | None = None

    def argv_list(self) -> list[str]:
        return list(self.argv)

    def subprocess_argv(self) -> list[str]:
        if not self.executable:
            raise FileNotFoundError("LaunchPlan has no executable for subprocess launch")
        return [self.executable, *self.argv_list()]

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_seed": self.persona_seed,
            "engine_tier": self.engine_tier,
            "executable": self.executable,
            "argv": self.argv_list(),
            "cdp_url": self.cdp_url,
            "headless": self.headless,
            "user_data_dir": self.user_data_dir,
        }
