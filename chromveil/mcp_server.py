"""ChromVeil MCP — ChromiumFish stealth browser + fast tools + native agent.

Run (prefer WSL):
    python -m chromveil.mcp_server

Requires: pip install "chromveil[native]"
"""
from __future__ import annotations

import atexit
import base64
import json
import os
import threading
from typing import Any, Optional

from .native import native_available, resolve_chrome_executable, wsl_mcp_hint

# Tighter than upstream ChromiumFish MCP default (200) for latency.
_SNAPSHOT_FAST_JS = r"""
(function(){
  function sel(el){
    if (el.id) return '#'+CSS.escape(el.id);
    var nm = el.getAttribute('name');
    if (nm) return el.tagName.toLowerCase()+'[name="'+nm+'"]';
    return el.tagName.toLowerCase();
  }
  function label(el){
    return (el.getAttribute('aria-label')||el.value||el.placeholder||el.innerText||'')
      .trim().replace(/\s+/g,' ').slice(0,60);
  }
  var els=document.querySelectorAll('a,button,input,textarea,select,[role=button]');
  var out=[], n=0;
  for(var i=0;i<els.length && n<48;i++){
    var el=els[i];
    if(!el.getClientRects().length) continue;
    out.push('['+n+'] '+el.tagName.toLowerCase()+' "'+label(el)+'" '+sel(el));
    n++;
  }
  return out.length ? out.join('\n') : '(no interactive elements)';
})()
"""

_SNAPSHOT_JS = r"""
(function(){
  function sel(el){
    if (el.id) return '#'+CSS.escape(el.id);
    var nm = el.getAttribute('name');
    if (nm) return el.tagName.toLowerCase()+'[name="'+nm+'"]';
    var path=[], e=el;
    while(e && e.nodeType===1 && path.length<3){
      var part=e.tagName.toLowerCase();
      path.unshift(part); e=e.parentElement;
    }
    return path.join(' > ');
  }
  function label(el){
    return (el.getAttribute('aria-label')||el.value||el.placeholder||el.innerText||'')
      .trim().replace(/\s+/g,' ').slice(0,80);
  }
  var els=document.querySelectorAll('a,button,input,textarea,select,[role=button],[role=link]');
  var out=[], n=0;
  for(var i=0;i<els.length && n<120;i++){
    var el=els[i];
    if(!el.getClientRects().length) continue;
    var line='['+n+'] '+el.tagName.toLowerCase()+' "'+label(el)+'" '+sel(el);
    if(el.href) line+=' -> '+el.href;
    out.push(line); n++;
  }
  return out.length ? out.join('\n') : '(no visible interactive elements)';
})()
"""


def _require_mcp():
    try:
        from mcp.server.fastmcp import FastMCP, Image
    except ImportError as exc:
        raise RuntimeError(
            'Install MCP deps: pip install "chromveil[native]" (needs mcp>=1.2,<2)'
        ) from exc
    return FastMCP, Image


_CONFIG: dict[str, Any] = {}
_LOCK = threading.Lock()
_SESSION: Optional[tuple[Any, Any]] = None


def _launch_native():
    from chromiumfish.agent import launch_agent

    extra: list[str] = []
    seed = _CONFIG.get("persona_seed") or os.environ.get("CHROMVEIL_PERSONA", "chromveil-1")
    extra.append(f"--persona-seed={seed}")
    if _CONFIG.get("headless", True):
        extra.append("--headless=new")
    w, h = _CONFIG.get("window_size", (1920, 1080))
    extra.append(f"--window-size={w},{h}")
    extra.extend(_CONFIG.get("extra_args") or [])

    chrome = _CONFIG.get("chrome") or resolve_chrome_executable()
    cm = launch_agent(
        port=_CONFIG.get("port", 9222),
        chrome=chrome,
        api_key=_CONFIG.get("api_key") or os.environ.get("OPENAI_API_KEY", ""),
        api_base=_CONFIG.get("api_base") or os.environ.get("OPENAI_API_BASE", ""),
        model=_CONFIG.get("model") or os.environ.get("OPENAI_API_MODEL", ""),
        typing=_CONFIG.get("typing", "human"),
        extra_args=extra,
    )
    return cm, cm.__enter__()


def _client():
    global _SESSION
    with _LOCK:
        if _SESSION is None:
            if not native_available():
                raise RuntimeError(
                    "Native ChromiumFish agent not available. "
                    + wsl_mcp_hint()
                    + '\nInstall: pip install "chromveil[native]" and run chromveil doctor --native in WSL.'
                )
            cm, client = _launch_native()
            _SESSION = (cm, client)
            atexit.register(_shutdown)
        return _SESSION[1]


def _shutdown() -> None:
    global _SESSION
    with _LOCK:
        if _SESSION is not None:
            try:
                _SESSION[0].__exit__(None, None, None)
            except Exception:
                pass
            _SESSION = None


class _Page:
    def __init__(self) -> None:
        from chromiumfish.agent import _CDP

        client = _client()
        self.target_id, ws_url = client._pick_page()
        self.cdp = _CDP(ws_url, client.timeout)

    def __enter__(self) -> "_Page":
        return self

    def __exit__(self, *_exc) -> None:
        self.cdp.close()

    def eval(self, expression: str) -> Any:
        res = self.cdp.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if res.get("exceptionDetails"):
            exc = res["exceptionDetails"]
            raise RuntimeError(exc.get("text", "eval error"))
        return res.get("result", {}).get("value")


def build_server():
    FastMCP, Image = _require_mcp()
    mcp = FastMCP("chromveil")

    @mcp.tool()
    def navigate(url: str, wait: str = "domcontentloaded") -> str:
        """Open URL. wait: domcontentloaded (fast) or load (full)."""
        with _Page() as p:
            p.cdp.send("Page.enable")
            p.cdp.send("Page.navigate", {"url": url})
            if wait == "load":
                p.cdp.wait_event("Page.loadEventFired", 45)
            else:
                p.cdp.wait_event("Page.domContentEventFired", 30)
            title = p.eval("document.title")
            href = p.eval("document.location.href")
        return f"Loaded {href}\nTitle: {title}"

    @mcp.tool()
    def snapshot_fast() -> str:
        """Fast interactive element list (≤48 nodes, short labels). Use for planning."""
        with _Page() as p:
            return p.eval(_SNAPSHOT_FAST_JS) or "(empty)"

    @mcp.tool()
    def snapshot() -> str:
        """Full interactive snapshot with CSS selectors (humanized click/type)."""
        with _Page() as p:
            return p.eval(_SNAPSHOT_JS) or "(empty)"

    @mcp.tool()
    def get_text(max_chars: int = 8000) -> str:
        """Visible body text, truncated for speed."""
        with _Page() as p:
            txt = p.eval("document.body && document.body.innerText || ''") or ""
        return txt[:max_chars]

    @mcp.tool()
    def screenshot():
        """PNG viewport capture."""
        with _Page() as p:
            res = p.cdp.send("Page.captureScreenshot", {"format": "png"}) or {}
        return Image(data=base64.b64decode(res.get("data", "")), format="png")

    @mcp.tool()
    def click(selector: str) -> str:
        """Trusted humanized click (ChromiumFish CDP)."""
        with _Page() as p:
            r = p.cdp.send(
                "Browser.humanizedClickSelector",
                {"targetId": p.target_id, "selector": selector},
            ) or {}
        return f"Clicked {selector!r} at ({r.get('x')}, {r.get('y')})"

    @mcp.tool()
    def type_text(selector: str, text: str, submit: bool = False) -> str:
        """Focus via humanized click, insert text, optional Enter."""
        with _Page() as p:
            p.cdp.send(
                "Browser.humanizedClickSelector",
                {"targetId": p.target_id, "selector": selector},
            )
            p.cdp.send("Input.insertText", {"text": text})
            if submit:
                for kind in ("keyDown", "keyUp"):
                    p.cdp.send(
                        "Input.dispatchKeyEvent",
                        {
                            "type": kind,
                            "key": "Enter",
                            "windowsVirtualKeyCode": 13,
                            "nativeVirtualKeyCode": 13,
                        },
                    )
        return f"Typed into {selector!r}"

    @mcp.tool()
    def run_task(task: str, url: str = "", max_steps: int = 20) -> str:
        """Native in-browser agent (C++ loop). Fast multi-action batches. Needs LLM env."""
        client = _client()
        result = client.run_task(task, url=url or None, max_steps=max_steps)
        return result.final_text or ("(failed)" if not result.success else "(done)")

    @mcp.tool()
    def collect_apis(
        url: str,
        want: str = "",
        ask: str = "",
        settle_ms: int = 6000,
    ) -> str:
        """Open URL with ChromVeil (Playwright path), capture XHR/fetch/WebSocket APIs, filter noise, return display + JSON."""
        from .intelligence.collect import collect_from_url

        result = collect_from_url(
            url,
            want=want or None,
            ask=ask or None,
            settle_ms=settle_ms,
            max_attempts=2,
        )
        if result.display:
            return result.display + "\n\n---\n" + json.dumps(result.to_dict(), indent=2)[:12000]
        return json.dumps(result.to_dict(), indent=2)

    @mcp.tool()
    def browser_status() -> str:
        """Persona, chrome path, native availability."""
        return json.dumps(
            {
                "native": native_available(),
                "chrome": resolve_chrome_executable(),
                "persona": _CONFIG.get("persona_seed") or os.environ.get("CHROMVEIL_PERSONA"),
            },
            indent=2,
        )

    return mcp


def run_server(**config: Any) -> None:
    _CONFIG.clear()
    _CONFIG.update(config)
    server = build_server()
    try:
        server.run(transport="stdio")
    finally:
        _shutdown()


def main() -> None:
    run_server(
        persona_seed=os.environ.get("CHROMVEIL_PERSONA"),
        headless=os.environ.get("CHROMVEIL_HEADLESS", "1") != "0",
        port=int(os.environ.get("CHROMVEIL_CDP_PORT", "9222")),
    )


if __name__ == "__main__":
    main()
