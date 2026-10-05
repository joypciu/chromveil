"""Session handle — kept separate from adapters to avoid import cycles."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from ..profile import ChromiumProfile


@dataclass
class VeilSession:
    """One ChromVeil browser — close when done."""

    profile: ChromiumProfile
    driver: str
    cdp_url: str | None
    browser: Any = None
    _context: Any = None
    page: Any = None
    _playwright: Any = None
    _ephemeral_user_data_dir: str | None = None
    _process: subprocess.Popen[str] | None = None
    _extra_close: Callable[[], None] | None = None

    def close(self) -> None:
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass
        if self._ephemeral_user_data_dir:
            from ..core.persona import remove_ephemeral_user_data_dir

            remove_ephemeral_user_data_dir(self._ephemeral_user_data_dir)
            self._ephemeral_user_data_dir = None
        if self._extra_close:
            try:
                self._extra_close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def new_page(self) -> Any:
        if self._context is not None:
            return self._context.new_page()
        if self.browser is not None:
            return self.browser.new_page()
        raise RuntimeError(
            "No Playwright/Patchright browser attached; use driver=playwright|patchright or connect_over_cdp"
        )

    def __enter__(self) -> VeilSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
