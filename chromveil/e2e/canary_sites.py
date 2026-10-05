"""Canonical live sportsbook URLs for ChromVeil regression (geo/network required)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanarySite:
    key: str
    label: str
    url: str
    title_fragments: tuple[str, ...]


# Default live canary suite — betonline + bet365 pregame (HO) + bet365 in-play (IP).
CANARY_SPORTSBOOK_SITES: tuple[CanarySite, ...] = (
    CanarySite(
        "betonline_sportsbook",
        "BetOnline sportsbook",
        "https://www.betonline.ag/sportsbook",
        ("betonline", "sportsbook", "sports"),
    ),
    CanarySite(
        "bet365_pregame",
        "bet365 pregame (home)",
        "https://www.bet365.com/#/HO/",
        ("bet365",),
    ),
    CanarySite(
        "bet365_live",
        "bet365 in-play (live)",
        "https://www.bet365.com/#/IP/",
        ("bet365",),
    ),
)


def default_canary_url() -> str:
    """Primary bench URL (bet365 pregame)."""
    return CANARY_SPORTSBOOK_SITES[1].url
