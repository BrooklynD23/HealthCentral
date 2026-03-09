"""Time helpers that preserve the project's naive-UTC storage semantics."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return a naive UTC datetime without using deprecated utcnow()."""
    return datetime.now(UTC).replace(tzinfo=None)
