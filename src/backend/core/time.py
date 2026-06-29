"""Time helpers that preserve the project's naive-UTC storage semantics."""

from datetime import datetime, timezone

# Python 3.10 compatibility: datetime.UTC was added in 3.11.
UTC = timezone.utc


def utcnow() -> datetime:
    """Return a naive UTC datetime without using deprecated utcnow()."""
    return datetime.now(UTC).replace(tzinfo=None)
