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


_CONTROL_MESSAGE = "hc-cls control record (no patient data)"


def _control_record(caplog):
    """Emit a plain record through the same logger and return it.

    A record carries more than the call site put there: caplog's handler
    formats every record at emit (``message``/``asctime``), and
    ``install_correlation_logging()`` (core/logging_setup.py, run by
    main.create_app) stamps ``correlation_id`` on every record process-wide —
    so any earlier test that built the app leaves it set for the rest of the
    suite. A static attribute whitelist pins the environment, not the call
    site; diffing against a control isolates what this call site added.
    """
    logging.getLogger(LOGGER_NAME).warning(_CONTROL_MESSAGE)
    controls = [
        r
        for r in caplog.records
        if r.name == LOGGER_NAME and r.getMessage() == _CONTROL_MESSAGE
    ]
    assert len(controls) == 1, f"control record not captured: {caplog.records!r}"
    return controls[0]


def _assert_critical_record_clean(caplog, record, analyte, direction):
    """Pin the critical-value log record to analyte + direction, nothing more.

    ``record.args == (analyte,)`` fails on any added arg (rounded float,
    threshold); the attrs diff fails on any ``extra=`` payload, which lands on
    this record but not on the control.
    """
    expected = f"Critical value detected: {analyte} {direction} critical threshold"
    assert record.getMessage() == expected
    assert record.args == (analyte,)
    leaked = set(vars(record)) - set(vars(_control_record(caplog)))
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
    _assert_critical_record_clean(caplog, hits[0], "potassium", "below")
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
    _assert_critical_record_clean(caplog, hits[0], "potassium", "above")
    assert result.requires_physician_review is True
    assert (
        result.physician_review_reason
        == "Critical high value: 7.193 is above critical threshold of 6.487"
    )
