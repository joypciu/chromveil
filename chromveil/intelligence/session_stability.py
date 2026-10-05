"""Keep sessions trustworthy to sites: sticky profiles, challenges, block classes."""
from __future__ import annotations

import hashlib
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from ..profile import ChromiumProfile

# Irrecoverable without different IP / manual action.
HARD_BLOCK_RE = re.compile(
    r"access denied|not available in your (country|region)|geo.?restrict|"
    r"request could not be satisfied|403 forbidden|forbidden\b|"
    r"unusual traffic from your|automated access|bot detected|request blocked",
    re.I,
)

# May clear after JS challenge / cookies (Cloudflare, etc.).
CHALLENGE_RE = re.compile(
    r"attention required|just a moment|checking your browser|"
    r"cloudflare|verify you are human|captcha|challenge-platform",
    re.I,
)

SOFT_ERROR_RE = re.compile(r"internal error|error\s*\|\s*", re.I)


def sticky_sessions_enabled() -> bool:
    return os.environ.get("CHROMVEIL_STICKY_SESSION", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def sticky_profile_dir(host: str) -> Path:
    slug = hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:14]
    root = Path.home() / ".chromveil" / "sticky"
    root.mkdir(parents=True, exist_ok=True)
    return root / slug


def apply_sticky_host_profile(profile: ChromiumProfile, url: str) -> None:
    """
    Reuse user-data + stable persona per host so cookies and local state accumulate.
    Sites trust returning browsers more than fresh fingerprints every navigation.
    """
    if not profile.sticky_session or not sticky_sessions_enabled():
        return
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return
    if not host:
        return

    profile.rotate_identity = False
    profile.persist_persona = True
    profile.persona_seed = profile.persona_seed or f"sticky-{host}"
    profile.user_data_dir = str(sticky_profile_dir(host))
    sticky_profile_dir(host).mkdir(parents=True, exist_ok=True)


def page_snapshot(page) -> tuple[str, str]:
    title = ""
    text = ""
    try:
        title = page.title() or ""
    except Exception:
        pass
    try:
        text = page.evaluate(
            "() => (document.body && document.body.innerText || '').slice(0, 2500)"
        ) or ""
    except Exception:
        pass
    return title, text


def classify_page(page) -> str:
    """Return: ok | challenge | hard_block | soft_error"""
    title, text = page_snapshot(page)
    blob = f"{title}\n{text}"
    if HARD_BLOCK_RE.search(blob):
        return "hard_block"
    if CHALLENGE_RE.search(blob) or CHALLENGE_RE.search(title):
        return "challenge"
    if SOFT_ERROR_RE.search(title) or SOFT_ERROR_RE.search(text[:400]):
        return "soft_error"
    return "ok"


def detect_block_signals(page) -> list[str]:
    """Public block hints for collect — challenges are signals but recoverable."""
    state = classify_page(page)
    if state == "hard_block":
        return ["hard_block"]
    if state == "challenge":
        return ["challenge"]
    if state == "soft_error":
        return ["soft_error"]
    return []


def wait_for_challenge_clear(page, timeout_ms: int = 45_000) -> bool:
    """Wait for Cloudflare-style interstitials to finish."""
    try:
        page.wait_for_function(
            """() => {
              const t = document.title || '';
              const b = (document.body && document.body.innerText || '').slice(0, 800);
              const x = (t + ' ' + b).toLowerCase();
              if (x.includes('request could not be satisfied')) return false;
              if (x.includes('attention required') || x.includes('just a moment')
                  || x.includes('checking your browser')) return false;
              return t.length > 2;
            }""",
            timeout=timeout_ms,
        )
    except Exception:
        pass
    deadline = time.time() + max(5.0, timeout_ms / 4000.0)
    while time.time() < deadline:
        state = classify_page(page)
        if state == "ok":
            return True
        if state == "hard_block":
            return False
        time.sleep(0.8)
    return classify_page(page) == "ok"


def prefer_headless_executable(profile: ChromiumProfile) -> ChromiumProfile:
    """System Chrome headless often fares better than bundled Chromium on WAFs."""
    if not profile.headless:
        return profile
    if os.environ.get("CHROMVEIL_HEADLESS_SYSTEM_CHROME", "1").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return profile
    if profile.executable:
        return profile
    from ..chrome_paths import find_system_chrome

    chrome = find_system_chrome()
    if chrome:
        profile.executable = chrome
    return profile
