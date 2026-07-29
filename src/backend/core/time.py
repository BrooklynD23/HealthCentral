"""Time helpers that preserve the project's naive-UTC storage semantics."""

from datetime import datetime, timezone

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
