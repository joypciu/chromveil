"""Natural-language intent for API collect (--ask)."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

_COLLECT_SYSTEM = """You help extract structured API search hints from a user question about a web page.
Return ONE JSON object only:
{"want":"comma,separated,keywords","url_pattern":null or "regex","answer_focus":"short phrase"}
Keywords should match likely JSON field names or API path segments (odds, events, markets, balance, user)."""


def _llm_endpoint() -> tuple[str, str, str]:
    import os

    base = os.environ.get("CHROMVEIL_LLM_URL", os.environ.get("OPENAI_API_BASE", "http://127.0.0.1:11434/v1"))
    base = base.rstrip("/")
    model = os.environ.get("CHROMVEIL_LLM_MODEL", os.environ.get("OPENAI_MODEL", "llama3.2"))
    key = os.environ.get("CHROMVEIL_LLM_KEY", os.environ.get("OPENAI_API_KEY", "ollama"))
    return base, model, key


def _heuristic_intent(ask: str) -> dict[str, Any]:
    stop = {
        "what",
        "show",
        "give",
        "tell",
        "from",
        "this",
        "page",
        "site",
        "data",
        "need",
        "want",
        "about",
        "with",
        "that",
        "have",
        "does",
        "the",
        "and",
        "for",
    }
    words = [w for w in re.findall(r"[a-z0-9_]+", ask.lower()) if len(w) > 2 and w not in stop]
    return {
        "want": ",".join(list(dict.fromkeys(words))[:12]),
        "url_pattern": None,
        "answer_focus": ask.strip()[:200],
    }


def parse_collect_intent(ask: str, *, use_llm: bool = True) -> dict[str, Any]:
    if not ask.strip():
        return _heuristic_intent("")
    if use_llm and __import__("os").environ.get("CHROMVEIL_COLLECT_LLM", "1") != "0":
        try:
            base, model, key = _llm_endpoint()
            messages = [
                {"role": "system", "content": _COLLECT_SYSTEM},
                {"role": "user", "content": ask},
            ]
            with httpx.Client(timeout=60.0) as client:
                r = client.post(
                    f"{base}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": 0.1},
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(content)
            if isinstance(data, dict) and data.get("want"):
                return data
        except Exception:
            pass
    return _heuristic_intent(ask)


def summarize_for_user(ask: str, capture: dict[str, Any]) -> str:
    """Short natural-language summary of captured APIs (LLM if available)."""
    apis = capture.get("apis") or []
    preview = json.dumps(apis[:5], default=str)[:6000]
    if __import__("os").environ.get("CHROMVEIL_COLLECT_LLM", "1") == "0":
        return f"Captured {capture.get('count', 0)} API(s). Top URLs: " + ", ".join(
            (a.get("url") or "")[:60] for a in apis[:5]
        )
    try:
        base, model, key = _llm_endpoint()
        messages = [
            {
                "role": "system",
                "content": "Summarize API capture results for the user in 3-8 bullet points. Be factual; cite URLs briefly.",
            },
            {
                "role": "user",
                "content": f"Question: {ask}\n\nAPI sample:\n{preview}",
            },
        ]
        with httpx.Client(timeout=90.0) as client:
            r = client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.3},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return f"Captured {capture.get('count', 0)} matching API response(s)."
