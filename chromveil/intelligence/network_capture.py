"""Capture XHR/fetch JSON and WebSocket frames while the page loads."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .api_filter import is_api_candidate, is_noise_url, score_api_relevance


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
class CapturedWebSocket:
    url: str
    direction: str
    payload: Any
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "direction": self.direction,
            "payload": self.payload,
            "size_bytes": self.size_bytes,
        }


@dataclass
class NetworkCapture:
    page: Any
    max_body_bytes: int = 512_000
    max_entries: int = 250
    max_ws_frames: int = 120
    capture_websockets: bool = True
    _entries: list[CapturedApi] = field(default_factory=list)
    _ws_entries: list[CapturedWebSocket] = field(default_factory=list)
    _seen: set[str] = field(default_factory=set)
    _attached: bool = False
    _ws_handler: Any = None

    def attach(self) -> None:
        if self._attached:
            return
        self.page.on("response", self._on_response)
        if self.capture_websockets:
            self._ws_handler = self._on_websocket
            self.page.on("websocket", self._ws_handler)
        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return
        try:
            self.page.remove_listener("response", self._on_response)
            if self._ws_handler:
                self.page.remove_listener("websocket", self._ws_handler)
        except Exception:
            pass
        self._attached = False

    def entries(self) -> list[CapturedApi]:
        return list(self._entries)

    def websocket_entries(self) -> list[CapturedWebSocket]:
        return list(self._ws_entries)

    def _on_websocket(self, ws) -> None:
        url = ws.url
        if is_noise_url(url):
            return

        def frame_received(payload) -> None:
            self._push_ws(url, "received", payload)

        def frame_sent(payload) -> None:
            self._push_ws(url, "sent", payload)

        try:
            ws.on("framereceived", frame_received)
            ws.on("framesent", frame_sent)
        except Exception:
            pass

    def _push_ws(self, url: str, direction: str, payload) -> None:
        if len(self._ws_entries) >= self.max_ws_frames:
            return
        try:
            if isinstance(payload, bytes):
                text = payload.decode("utf-8", errors="replace")
            elif isinstance(payload, str):
                text = payload
            elif hasattr(payload, "payload"):
                raw = payload.payload
                text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
            else:
                text = str(payload)
            body: Any = text
            if text.strip().startswith(("{", "[")):
                try:
                    body = json.loads(text)
                except Exception:
                    pass
            if len(text) > self.max_body_bytes:
                body = text[: self.max_body_bytes] + "…"
            self._ws_entries.append(
                CapturedWebSocket(
                    url=url,
                    direction=direction,
                    payload=body,
                    size_bytes=len(text),
                )
            )
        except Exception:
            return

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
