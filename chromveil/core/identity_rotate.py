"""Per-session identity rotation — fresh fingerprint surface for each browser open."""
from __future__ import annotations

import os
import secrets

from ..profile import ChromiumProfile
from .persona import new_minimal_persona_seed

COMMON_VIEWPORTS: tuple[tuple[int, int], ...] = (
    (1920, 1080),
    (1536, 864),
    (1440, 900),
    (1366, 768),
    (1280, 720),
    (1600, 900),
)

COMMON_LANGS: tuple[str, ...] = ("en-US", "en-GB", "en")


def rotate_identity_enabled() -> bool:
    return os.environ.get("CHROMVEIL_ROTATE_IDENTITY", "1").strip().lower() not in ("0", "false", "no", "off")


def fixed_persona_locked() -> bool:
    return os.environ.get("CHROMVEIL_FIXED_PERSONA", "").strip().lower() in ("1", "true", "yes", "on")


def apply_rotating_identity(profile: ChromiumProfile) -> None:
    """
    Ephemeral sessions: new viewport/lang each open; new persona seed unless locked.

    Set ``CHROMVEIL_FIXED_PERSONA=1`` or ``CHROMVEIL_ROTATE_SEED=0`` with ``CHROMVEIL_PERSONA`` to pin seed.
    """
    if profile.persist_persona or not rotate_identity_enabled() or not profile.rotate_identity:
        return

    profile.window_size = secrets.choice(COMMON_VIEWPORTS)
    lang = secrets.choice(COMMON_LANGS)
    profile.extra_args = [a for a in profile.extra_args if not a.startswith("--lang=")]
    profile.extra_args.append(f"--lang={lang}")

    if fixed_persona_locked():
        return
    if os.environ.get("CHROMVEIL_PERSONA") and os.environ.get("CHROMVEIL_ROTATE_SEED", "1") == "0":
        return
    profile.persona_seed = new_minimal_persona_seed()
