"""Compact page state for the agent (no vision model required)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from playwright.sync_api import Page

_INTERACTIVE_JS = """
() => {
  const sel = 'a, button, input, textarea, select, [role=button], [role=link], [onclick]';
  const nodes = [...document.querySelectorAll(sel)];
  return nodes.slice(0, 80).map((el, idx) => {
    const r = el.getBoundingClientRect();
    const label = (el.getAttribute('aria-label') || el.innerText || el.value || el.name || '').trim().slice(0, 120);
    return {
      ref: 'e' + idx,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      label,
      href: el.href || '',
      visible: r.width > 0 && r.height > 0,
    };
  }).filter(x => x.label || x.tag === 'input');
}
"""


@dataclass
class PageView:
    url: str
    title: str
    text_excerpt: str
    elements: list[dict]

    def to_prompt_block(self) -> str:
        lines = [f"URL: {self.url}", f"Title: {self.title}", "", "Visible text (excerpt):", self.text_excerpt, "", "Interactive elements:"]
        for el in self.elements:
            if not el.get("visible", True):
                continue
            href = f" href={el['href']}" if el.get("href") else ""
            lines.append(f"  [{el['ref']}] <{el['tag']}{href}> {el.get('label', '')[:100]}")
        return "\n".join(lines)


def perceive(page: Page, max_chars: int = 3500) -> PageView:
    title = page.title()
    url = page.url
    body = page.inner_text("body", timeout=10_000)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    excerpt = body[:max_chars] + ("…" if len(body) > max_chars else "")
    elements = page.evaluate(_INTERACTIVE_JS)
    return PageView(url=url, title=title, text_excerpt=excerpt, elements=elements)


def ref_to_selector(ref: str, elements: list[dict]) -> str | None:
    if not ref.startswith("e"):
        return None
    try:
        idx = int(ref[1:])
    except ValueError:
        return None
    for el in elements:
        if el.get("ref") == ref:
            # Playwright nth-match via JS index stored at perceive time
            return f"css=a, button, input, textarea, select, [role=button], [role=link], [onclick] >> nth={idx}"
    return None
