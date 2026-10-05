"""Perceive → plan → act loop."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import Page

from .llm import plan
from .perceive import perceive, ref_to_selector


@dataclass
class AgentResult:
    success: bool
    final_text: str
    steps: int
    backend: str
    trace: list[dict[str, Any]] = field(default_factory=list)


def _act(page: Page, action: dict[str, Any], elements: list[dict]) -> None:
    kind = action.get("action")
    if kind == "goto":
        page.goto(action["url"], wait_until="domcontentloaded", timeout=60_000)
        return
    if kind == "click":
        ref = action.get("ref", "")
        sel = ref_to_selector(ref, elements)
        if sel:
            page.locator(sel).first.click(timeout=15_000)
        else:
            page.get_by_text(action.get("text", ""), exact=False).first.click(timeout=15_000)
        return
    if kind == "type":
        ref = action.get("ref", "")
        text = action.get("text", "")
        sel = ref_to_selector(ref, elements)
        loc = page.locator(sel).first if sel else page.locator("input, textarea").first
        loc.fill(text, timeout=15_000)
        return
    if kind == "press":
        page.keyboard.press(action.get("key", "Enter"))
        return
    if kind == "wait":
        time.sleep(float(action.get("seconds", 2)))
        return
    if kind == "done":
        return
    raise ValueError(f"Unknown action: {kind}")


def run_task(
    page: Page,
    task: str,
    *,
    max_steps: int = 25,
    backend: str = "unknown",
) -> AgentResult:
    history: list[dict[str, str]] = []
    trace: list[dict[str, Any]] = []

    for step in range(max_steps):
        view = perceive(page)
        block = view.to_prompt_block()
        action = plan(task, block, history)
        trace.append({"step": step, "action": action, "url": view.url})

        if action.get("action") == "done":
            return AgentResult(
                success=True,
                final_text=str(action.get("answer", action.get("reason", ""))),
                steps=step + 1,
                backend=backend,
                trace=trace,
            )

        _act(page, action, view.elements)
        history.append({"role": "assistant", "content": str(action)})
        page.wait_for_timeout(500)

    return AgentResult(
        success=False,
        final_text="Max steps reached without done.",
        steps=max_steps,
        backend=backend,
        trace=trace,
    )
