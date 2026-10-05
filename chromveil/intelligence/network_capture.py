"""Capture XHR/fetch JSON while the page loads."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .api_filter import is_api_candidate, score_api_relevance


@dataclass
class CapturedApi:
    url: str
    method: str
    status: int
    resource_type: str
    content_type: str
    body: Any
    size_bytes: int
    relevance: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "status": self.status,
            "resource_type": self.resource_type,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "relevance": self.relevance,
            "body": self.body,
        }


@dataclass
class NetworkCapture:
    page: Any
    max_body_bytes: int = 512_000
    max_entries: int = 250
    _entries: list[CapturedApi] = field(default_factory=list)
    _seen: set[str] = field(default_factory=set)
    _attached: bool = False

    def attach(self) -> None:
        if self._attached:
            return
        self.page.on("response", self._on_response)
        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return
        try:
            self.page.remove_listener("response", self._on_response)
        except Exception:
            pass
        self._attached = False

    def entries(self) -> list[CapturedApi]:
        return list(self._entries)

    def _on_response(self, response) -> None:
        if len(self._entries) >= self.max_entries:
            return
        try:
            request = response.request
            url = response.url
            if url in self._seen:
                return
            resource_type = request.resource_type
            headers = response.headers
            content_type = headers.get("content-type", "")
            if not is_api_candidate(url, resource_type, content_type):
                return
            body = self._read_body(response, content_type)
            if body is None:
                return
            size = len(json.dumps(body, default=str)) if not isinstance(body, (str, bytes)) else len(body)
            rec = CapturedApi(
                url=url,
                method=request.method,
                status=response.status,
                resource_type=resource_type,
                content_type=content_type,
                body=body,
                size_bytes=size,
                relevance=score_api_relevance(url, body),
            )
            self._seen.add(url)
            self._entries.append(rec)
        except Exception:
            return

    def _read_body(self, response, content_type: str) -> Any:
        try:
            if "json" in content_type.lower() or content_type == "":
                raw = response.body()
                if len(raw) > self.max_body_bytes:
                    return {"_truncated": True, "preview": raw[:2000].decode("utf-8", errors="replace")}
                return response.json()
        except Exception:
            pass
        try:
            text = response.text()
            if len(text) > self.max_body_bytes:
                return text[: self.max_body_bytes] + "…"
            if text.strip().startswith(("{", "[")):
                return json.loads(text)
            return text[:8000] if len(text) > 8000 else text
        except Exception:
            return None
