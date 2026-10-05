"""OpenAI-compatible chat client (local Ollama, vLLM, OpenAI, etc.)."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

SYSTEM = """You are a browser agent. You receive page state and return ONE JSON object only.
Schema:
{"action":"goto"|"click"|"type"|"press"|"wait"|"done",
 "url":string (goto only),
 "ref":string (element ref e0, e1, ... for click/type),
 "text":string (type only),
 "key":string (press only, e.g. Enter),
 "answer":string (done only),
 "reason":string (short)}
Rules: prefer click/type on refs from the list; use goto for navigation; end with done when the user task is complete."""


def _endpoint() -> tuple[str, str, str]:
    base = os.environ.get("CHROMVEIL_LLM_URL", os.environ.get("OPENAI_API_BASE", "http://127.0.0.1:11434/v1"))
    base = base.rstrip("/")
    model = os.environ.get("CHROMVEIL_LLM_MODEL", os.environ.get("OPENAI_MODEL", "llama3.2"))
    key = os.environ.get("CHROMVEIL_LLM_KEY", os.environ.get("OPENAI_API_KEY", "ollama"))
    return base, model, key


def plan(user_task: str, page_block: str, history: list[dict[str, str]]) -> dict[str, Any]:
    base, model, key = _endpoint()
    messages = [{"role": "system", "content": SYSTEM}]
    messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": f"Task: {user_task}\n\n--- Page ---\n{page_block}\n\nRespond with JSON only.",
        }
    )
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    url = f"{base}/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(content)
