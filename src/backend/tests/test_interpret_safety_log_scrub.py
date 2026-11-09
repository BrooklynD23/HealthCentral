"""CRIT-LOG-SCRUB: the critical-value log line names analyte and direction only.

`check_critical_value` returns the patient's value and threshold in
`physician_review_reason` (stored in the encrypted profile DB), but it must not
write either to the application log.
"""

import logging

from modules.interpret_safety import InterpretationSafetyGuard

LOGGER_NAME = "modules.interpret_safety"


def _guard_records(caplog):
    return [r for r in caplog.records if r.name == LOGGER_NAME]


def _assert_values_absent(caplog, forbidden):
    assert caplog.records, "caplog captured nothing; absence assertions would be vacuous"
    for r in caplog.records:
        text = r.getMessage()
        args = str(r.args)
        for needle in forbidden:
            assert needle not in text, f"{needle} leaked into log message: {text!r}"
            assert needle not in args, f"{needle} leaked into log args: {args!r}"


# Attributes logging.LogRecord.__init__ sets on Python 3.11+ (taskName is 3.12+,
# harmless to whitelist here). Anything else in vars(record) arrived via extra=
# or was injected by a Formatter.
_STANDARD_LOG_RECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "taskName",
    }
)

# Formatter.format() sets record.message (always) and record.asctime (when the
# fmt string uses %(asctime)s) after the record is emitted, so caplog records
# carry them. extra= can never write either name: Logger.makeRecord raises
# KeyError("Attempt to overwrite ...") for both, so whitelisting them keeps the
# extra= check lossless.
_FORMATTER_INJECTED_ATTRS = frozenset({"message", "asctime"})


def _assert_critical_record_clean(record, analyte, direction):
    """Pin the critical-value log record to analyte + direction, nothing more."""
    expected = f"Critical value detected: {analyte} {direction} critical threshold"
    assert record.getMessage() == expected
    assert record.args == (analyte,)
    leaked = (
        set(vars(record)) - _STANDARD_LOG_RECORD_ATTRS - _FORMATTER_INJECTED_ATTRS
    )
    assert leaked == set(), f"unexpected record attributes (extra= payload?): {leaked}"


def test_hc_cls_001_critical_low_log_carries_no_value(caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    result = InterpretationSafetyGuard().check_critical_value(
        "potassium", 1.937, critical_low=2.513
    )

    _assert_values_absent(caplog, ["1.937", "2.513"])
    hits = [
        r
        for r in _guard_records(caplog)
        if r.levelno == logging.WARNING
        and "potassium" in r.getMessage()
        and "below critical threshold" in r.getMessage()
    ]
    assert len(hits) == 1
    assert result.requires_physician_review is True
    assert (
        result.physician_review_reason
        == "Critical low value: 1.937 is below critical threshold of 2.513"
    )


def test_hc_cls_002_critical_high_log_carries_no_value(caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    result = InterpretationSafetyGuard().check_critical_value(
        "potassium", 7.193, critical_high=6.487
    )

    _assert_values_absent(caplog, ["7.193", "6.487"])
    hits = [
        r
        for r in _guard_records(caplog)
        if r.levelno == logging.WARNING
        and "potassium" in r.getMessage()
        and "above critical threshold" in r.getMessage()
    ]
    assert len(hits) == 1
    assert result.requires_physician_review is True
    assert (
        result.physician_review_reason
        == "Critical high value: 7.193 is above critical threshold of 6.487"
    )


def test_hc_cls_003_non_critical_value_logs_nothing(caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    result = InterpretationSafetyGuard().check_critical_value("potassium", 4.2)

    assert _guard_records(caplog) == []
    assert "value_not_critical" in result.checks_passed


def test_hc_cls_004_critical_low_record_is_analyte_only(caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    result = InterpretationSafetyGuard().check_critical_value(
        "potassium", 1.937, critical_low=2.513
    )

    hits = [
        r
        for r in _guard_records(caplog)
        if r.levelno == logging.WARNING
        and "below critical threshold" in r.getMessage()
    ]
    assert len(hits) == 1
    _assert_critical_record_clean(hits[0], "potassium", "below")
    assert result.requires_physician_review is True
    assert (
        result.physician_review_reason
        == "Critical low value: 1.937 is below critical threshold of 2.513"
    )


def test_hc_cls_005_critical_high_record_is_analyte_only(caplog):
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    result = InterpretationSafetyGuard().check_critical_value(
        "potassium", 7.193, critical_high=6.487
    )

    hits = [
        r
        for r in _guard_records(caplog)
        if r.levelno == logging.WARNING
        and "above critical threshold" in r.getMessage()
    ]
    assert len(hits) == 1
    _assert_critical_record_clean(hits[0], "potassium", "above")
    assert result.requires_physician_review is True
    assert (
        result.physician_review_reason
        == "Critical high value: 7.193 is above critical threshold of 6.487"
    )
