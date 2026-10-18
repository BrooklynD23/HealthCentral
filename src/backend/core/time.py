"""Time helpers that preserve the project's naive-UTC storage semantics."""

from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from pydantic import AfterValidator

# Python 3.10 compatibility: datetime.UTC was added in 3.11.
UTC = timezone.utc


def utcnow() -> datetime:
    """Return a naive UTC datetime without using deprecated utcnow()."""
    return datetime.now(UTC).replace(tzinfo=None)


def utcfromtimestamp(timestamp: float) -> datetime:
    """Naive UTC datetime from a POSIX timestamp.

    The counterpart to ``utcnow`` for filesystem mtimes and similar, without
    the deprecated ``datetime.utcfromtimestamp``. Returns naive so it compares
    directly against ``utcnow()`` and against stored timestamps.
    """
    return datetime.fromtimestamp(timestamp, UTC).replace(tzinfo=None)


def to_naive_utc(value: datetime) -> datetime:
    """Normalise a datetime to the naive-UTC storage form.

    Aware values are converted to UTC; naive values are already UTC by
    convention and are returned unchanged.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


# Client datetimes are stored naive UTC (SQLite drops tzinfo) - MED-UTC, UTC-SWEEP.
NaiveUtcDatetime = Annotated[datetime, AfterValidator(to_naive_utc)]


# Profile time-zone helpers (I-6). Imports sit here, not at the top, so the
# line numbers of the helpers above stay put.
import logging  # noqa: E402
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

_logger = logging.getLogger(__name__)


def safe_zone_name(name: str | None) -> str:
    """Return ``name`` if it is a valid IANA zone, else "UTC"."""
    if not name:
        return "UTC"
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        # Fixed message: the stored value may be user-entered, so never echo it.
        _logger.warning("Invalid profile timezone; falling back to UTC")
        return "UTC"
    return name


def to_local(value: datetime, tz_name: str) -> datetime:
    """Aware datetime in ``tz_name``; a naive value is treated as UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ZoneInfo(tz_name))


def local_day_bounds_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    """Naive-UTC half-open [start, end) of local ``day`` (23h/25h on DST days)."""
    zone = ZoneInfo(tz_name)
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    nxt = day + timedelta(days=1)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=zone)
    return to_naive_utc(start), to_naive_utc(end)


async def profile_timezone_name(profile_db: AsyncSession, profile_id: str) -> str:
    """The profile's safe IANA zone, "UTC" when it has no settings row."""
    from models import (
        UserModelSettings,  # ponytail: lazy import breaks the models -> core.time cycle
    )

    result = await profile_db.execute(
        select(UserModelSettings.timezone).where(UserModelSettings.profile_id == profile_id)
    )
    return safe_zone_name(result.scalar_one_or_none())
