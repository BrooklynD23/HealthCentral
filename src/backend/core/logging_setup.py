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


class _AccessLogQueryScrub(logging.Filter):
    """Drop the query string from uvicorn's access record (SEARCH-LOG-SCRUB).

    uvicorn logs `'%s - "%s %s HTTP/%s" %d'` with the path *and* query string as the
    third arg, so `GET /api/v1/search/?q=<term>` would write the patient's search term
    to disk. scope["path"] is URL-quoted, so the first `?` is the query delimiter.
    The record is always kept: method, path and status stay in the line.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str):
            path, sep, _query = args[2].partition("?")
            if sep:
                record.args = (args[0], args[1], path, *args[3:])
        return True


def install_access_log_query_scrub() -> None:
    """Attach the scrub to the `uvicorn.access` logger, once.

    On the logger, not a handler: uvicorn's dictConfig and alembic's fileConfig
    replace handlers, but a filter on a logger survives both. No handler, format or
    level is changed.
    """
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _AccessLogQueryScrub) for f in access_logger.filters):
        access_logger.addFilter(_AccessLogQueryScrub())
