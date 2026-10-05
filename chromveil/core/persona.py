"""Session identity — stealth defaults and minimal ephemeral browser profiles."""
from __future__ import annotations

import hashlib
import secrets
import shutil
import tempfile
from pathlib import Path

from ..profile import ChromiumProfile

SESSIONS_ROOT = Path.home() / ".chromveil" / "sessions"
PERSISTENT_ROOT = Path.home() / ".chromveil" / "profiles"


def new_minimal_persona_seed() -> str:
    """Short, unique persona for one browser session (ChromiumFish ``--persona-seed``)."""
    return secrets.token_hex(6)


def allocate_ephemeral_user_data_dir() -> Path:
    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=SESSIONS_ROOT))


def remove_ephemeral_user_data_dir(path: str | Path) -> None:
    p = Path(path)
    if not p.exists():
        return
    try:
        resolved = p.resolve()
        sessions_root = SESSIONS_ROOT.resolve()
        if sessions_root in resolved.parents or resolved.parent == sessions_root:
            shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass


def ensure_stealth_defaults(profile: ChromiumProfile) -> None:
    """Stealth and speed tuning stay on unless explicitly disabled via env/profile."""
    if profile.stealth_tuning is not False:
        profile.stealth_tuning = True
    if profile.pure_stealth is not False:
        profile.pure_stealth = True
    if profile.speed_tuning is not False:
        profile.speed_tuning = True


def prepare_session_identity(profile: ChromiumProfile) -> None:
    """
    Materialize persona + user-data before launch.

    Default (``persist_persona=False``): fresh minimal seed and empty temp profile each open.
    Persistent mode: stable seed + ``~/.chromveil/profiles/<hash>``.
    """
    ensure_stealth_defaults(profile)
    from .identity_rotate import apply_rotating_identity

    apply_rotating_identity(profile)

    if profile.persist_persona:
        if profile.persona_seed is None:
            profile.persona_seed = "chromveil-1"
        if not profile.user_data_dir:
            slug = hashlib.sha256(profile.persona_seed.encode("utf-8")).hexdigest()[:16]
            root = PERSISTENT_ROOT / slug
            root.mkdir(parents=True, exist_ok=True)
            profile.user_data_dir = str(root)
        return

    if profile.persona_seed is None:
        profile.persona_seed = new_minimal_persona_seed()
    if not profile.user_data_dir:
        profile.user_data_dir = str(allocate_ephemeral_user_data_dir())
