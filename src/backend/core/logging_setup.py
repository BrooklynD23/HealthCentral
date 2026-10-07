"""Correlation IDs on every log record (HC-M07).

A process-wide LogRecord factory, not a handler Filter: alembic.ini's fileConfig
runs at startup and on every vault open and replaces the root handlers (and any
filters on them). The factory survives that. Local-only: no handler, format or
level is changed here, and nothing is sent anywhere.
"""

from __future__ import annotations

import logging

from monitoring.correlation import get_correlation_id

_MARKER = "_asclexis_correlation"


def install_correlation_logging() -> None:
    previous = logging.getLogRecordFactory()
    if getattr(previous, _MARKER, False):
        return

    def factory(*args, **kwargs) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        record.correlation_id = get_correlation_id() or "-"
        return record

    setattr(factory, _MARKER, True)
    logging.setLogRecordFactory(factory)
