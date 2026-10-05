"""Fuse visible DOM + structured hints for sportsbook / SPA pages."""
from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page

_ODDS_RE = re.compile(
    r"(?<!\d)(?:\d{1,2}/\d{1,2}|\d+\.\d{2})(?!\d)",
)
_EVENT_VS_RE = re.compile(r"\b.+\s+v\s+.+", re.I)
_DEEP_TEXT_JS = """
() => {
  const out = [];
  const seen = new Set();
  const push = (t) => {
    t = (t || '').replace(/\\s+/g, ' ').trim();
    if (!t || t.length < 2 || seen.has(t)) return;
    seen.add(t);
    out.push(t);
  };
  const walk = (root) => {
    if (!root) return;
    if (root.shadowRoot) walk(root.shadowRoot);
    const kids = root.childNodes || [];
    for (const n of kids) {
      if (n.nodeType === Node.TEXT_NODE) push(n.textContent);
      else if (n.nodeType === Node.ELEMENT_NODE) {
        const el = n;
        if (el.shadowRoot) walk(el.shadowRoot);
        const aria = el.getAttribute && el.getAttribute('aria-label');
        if (aria) push(aria);
        walk(el);
      }
    }
  };
  walk(document.body);
  return out.slice(0, 800);
}
"""

_PAGE_SNAPSHOT_JS = """
() => {
  const deep = [];
  const seen = new Set();
  const push = (t) => {
    t = (t || '').replace(/\\s+/g, ' ').trim();
    if (!t || t.length < 2 || seen.has(t)) return;
    seen.add(t);
    deep.push(t);
  };
  const walk = (root) => {
    if (!root) return;
    if (root.shadowRoot) walk(root.shadowRoot);
    const kids = root.childNodes || [];
    for (const n of kids) {
      if (n.nodeType === Node.TEXT_NODE) push(n.textContent);
      else if (n.nodeType === Node.ELEMENT_NODE) {
        const el = n;
        if (el.shadowRoot) walk(el.shadowRoot);
        const aria = el.getAttribute && el.getAttribute('aria-label');
        if (aria) push(aria);
        walk(el);
      }
    }
  };
  walk(document.body);
  const bodyPlain = (document.body && document.body.innerText || '').slice(0, 14000);
  const oddsRx = /^(\\d{1,2}\\/\\d{1,2}|\\d+\\.\\d{2})$/;
  const rows = [];
  const nodes = document.querySelectorAll(
    '[class*="Odd"], [class*="odd"], [class*="Market"], [class*="Participant"], ' +
    '[data-fixture], [class*="Fixture"], [class*="Event"]'
  );
  for (const el of nodes) {
    const t = (el.innerText || '').replace(/\\s+/g, ' ').trim();
    if (!t || t.length > 400) continue;
    const parts = t.split(/\\s+/).filter(Boolean);
    const odds = parts.filter(p => oddsRx.test(p));
    if (odds.length || (t.length > 8 && t.length < 180)) {
      rows.push({ text: t.slice(0, 200), odds: odds.slice(0, 6) });
    }
    if (rows.length >= 80) break;
  }
  return { deep: deep.slice(0, 800), bodyPlain, bettingRows: rows };
}
"""

_BETTING_ROWS_JS = """
() => {
  const rows = [];
  const oddsRx = /^(\\d{1,2}\\/\\d{1,2}|\\d+\\.\\d{2})$/;
  const nodes = document.querySelectorAll(
    '[class*="Odd"], [class*="odd"], [class*="Market"], [class*="Participant"], ' +
    '[data-fixture], [class*="Fixture"], [class*="Event"]'
  );
  for (const el of nodes) {
    const t = (el.innerText || '').replace(/\\s+/g, ' ').trim();
    if (!t || t.length > 400) continue;
    const parts = t.split(/\\s+/).filter(Boolean);
    const odds = parts.filter(p => oddsRx.test(p));
    if (odds.length || (t.length > 8 && t.length < 180)) {
      rows.push({ text: t.slice(0, 200), odds: odds.slice(0, 6) });
    }
    if (rows.length >= 80) break;
  }
  return rows;
}
"""


def settle_page(page: Page, settle_ms: int, *, scroll: bool = True) -> None:
    import time

    if scroll and settle_ms >= 1500:
        steps = min(4, max(1, settle_ms // 2000))
        for _ in range(steps):
            try:
                page.evaluate("() => window.scrollBy(0, Math.max(400, window.innerHeight * 0.85))")
            except Exception:
                break
            time.sleep(0.35)
        try:
            page.evaluate("() => window.scrollTo(0, 0)")
        except Exception:
            pass
        time.sleep(max(0.5, (settle_ms / 1000.0) * 0.35))
    else:
        time.sleep(settle_ms / 1000.0)


def extract_page_data(
    page: Page,
    *,
    max_text_chars: int = 12_000,
    deep_pass: bool = True,
) -> dict[str, Any]:
    """Best-effort 'everything on screen' for SPAs (includes shadow DOM text)."""
    url = page.url
    title = page.title()
    deep_lines: list[str] = []
    betting_rows: list[dict[str, Any]] = []
    body_plain = ""
    if deep_pass:
        try:
            snap = page.evaluate(_PAGE_SNAPSHOT_JS) or {}
            deep_lines = snap.get("deep") or []
            betting_rows = snap.get("bettingRows") or []
            body_plain = snap.get("bodyPlain") or ""
        except Exception:
            pass
    else:
        try:
            body_plain = page.inner_text("body", timeout=5_000)
        except Exception:
            pass
    body_plain = re.sub(r"\n{3,}", "\n\n", body_plain).strip()

    merged: list[str] = []
    seen: set[str] = set()
    for line in [body_plain] + deep_lines:
        for part in re.split(r"[\n\r]+", line):
            part = part.strip()
            if len(part) < 2 or part in seen:
                continue
            seen.add(part)
            merged.append(part)

    full_text = "\n".join(merged)
    if len(full_text) > max_text_chars:
        full_text = full_text[:max_text_chars] + "…"

    odds_found: list[str] = []
    for m in _ODDS_RE.finditer("\n".join(merged[:400])):
        o = m.group(0)
        if o not in odds_found:
            odds_found.append(o)
        if len(odds_found) >= 120:
            break

    sports_nav = [ln for ln in merged if 3 <= len(ln) <= 48 and ln[0].isupper()][:60]
    events_on_screen = [
        ln for ln in merged if 8 <= len(ln) <= 140 and _EVENT_VS_RE.search(ln)
    ][:40]

    return {
        "url": url,
        "title": title,
        "text_char_count": len(full_text),
        "text": full_text,
        "sports_and_labels": sports_nav[:40],
        "odds_on_screen": odds_found[:80],
        "betting_rows": betting_rows[:50],
        "events_on_screen": events_on_screen,
        "deep_line_count": len(deep_lines),
    }
