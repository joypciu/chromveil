"""Heuristics to drop analytics/ads/static noise from API capture."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

# Host/path fragments typical of telemetry, ads, and static assets (not app data).
NOISE_HOST_RE = re.compile(
    r"google-analytics|googletagmanager|doubleclick|facebook\.net|hotjar|sentry\.io|"
    r"segment\.(io|com)|mixpanel|fullstory|cloudflareinsights|bat\.bing|adservice|"
    r"amazon-adsystem|scorecardresearch|newrelic|datadoghq|optimizely|clarity\.ms|"
    r"criteo|taboola|outbrain|twitter\.com/i/ads|linkedin\.com/px",
    re.I,
)

NOISE_PATH_RE = re.compile(
    r"/(collect|beacon|pixel|analytics|ads?/|track(ing)?|telemetry|metrics|log(s)?)(/|$|\?)|"
    r"\.(png|jpe?g|gif|webp|svg|ico|woff2?|ttf|css|js)(\?|$)",
    re.I,
)

API_RESOURCE_TYPES = frozenset({"xhr", "fetch"})
JSON_CONTENT_RE = re.compile(r"application/(json|graphql)|text/json", re.I)


def is_noise_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return True
    host = p.netloc or ""
    path = p.path or ""
    if NOISE_HOST_RE.search(host):
        return True
    if NOISE_PATH_RE.search(path + "?" + (p.query or "")):
        return True
    return False


def is_api_candidate(
    url: str,
    resource_type: str,
    content_type: str | None,
) -> bool:
    if is_noise_url(url):
        return False
    rt = (resource_type or "").lower()
    ct = content_type or ""
    if rt in API_RESOURCE_TYPES:
        return True
    if JSON_CONTENT_RE.search(ct):
        return True
    if "/api/" in url.lower() or "graphql" in url.lower():
        return True
    return False


def score_api_relevance(url: str, body: Any) -> float:
    """Higher = more likely user-facing app data."""
    score = 1.0
    low = url.lower()
    if any(k in low for k in ("api", "graphql", "rest", "v1/", "v2/", "sportsbook", "odds", "event")):
        score += 2.0
    if isinstance(body, dict):
        score += min(len(body) * 0.05, 3.0)
    elif isinstance(body, list):
        score += min(len(body) * 0.1, 3.0)
    return score
