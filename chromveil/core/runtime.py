"""BrowserRuntime — façade from profile to live session."""
from __future__ import annotations

from ..drivers.registry import get_adapter, resolve_driver
from ..drivers.veil_session import VeilSession
from ..profile import ChromiumProfile
from .builder import LaunchContext, build_launch_plan
from .types import DriverKind


class BrowserRuntime:
    """
    Single entry for opening a browser:

        runtime = BrowserRuntime(profile)
        session = runtime.open(driver=\"patchright\")
    """

    def __init__(self, profile: ChromiumProfile) -> None:
        self.profile = profile

    def launch_plan(
        self,
        *,
        for_playwright: bool = False,
        include_cdp: bool = True,
        resolve_binary: bool = False,
    ):
        return build_launch_plan(
            self.profile,
            LaunchContext(
                include_cdp=include_cdp,
                for_playwright=for_playwright,
                resolve_binary=resolve_binary,
            ),
        )

    def open(self, driver: str | None = None) -> VeilSession:
        drv = resolve_driver(driver or self.profile.driver)
        if drv in (DriverKind.CDP.value, DriverKind.SUBPROCESS.value):
            plan = build_launch_plan(
                self.profile,
                LaunchContext(include_cdp=True, resolve_binary=True),
            )
        else:
            plan = build_launch_plan(
                self.profile,
                LaunchContext(
                    include_cdp=bool(self.profile.cdp_port),
                    for_playwright=True,
                    resolve_binary=True,
                ),
            )
        return get_adapter(drv).open(self.profile, plan)
