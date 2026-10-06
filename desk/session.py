"""Cash-session window for the desk.

Crypto trades all night. This playbook only treats 10:00–12:30
America/Sao_Paulo as the liquidity window for a new 15m trigger.
Brazil has no daylight-saving time; 10:00 BRT is 13:00 UTC.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
WINDOW_START = time(10, 0)
WINDOW_END = time(12, 30)


def in_liquidity_window(now: datetime | None = None) -> bool:
    """Inclusive of 10:00 and 12:30 local time."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    local = moment.astimezone(SAO_PAULO)
    current = local.time().replace(microsecond=0)
    # time comparison ignores date; the window does not cross midnight.
    return WINDOW_START <= current <= WINDOW_END


def sao_paulo_now(now: datetime | None = None) -> datetime:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return moment.astimezone(SAO_PAULO)
