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
