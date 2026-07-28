"""AUDIT-PHI-001 Phase A — audit-log PHI minimization.

Audit rows land in the *unencrypted* master DB: it is the one place
patient-linked data escapes the SQLCipher boundary. These tests pin the
allowlist scrubber inside ``create_audit_log`` — the single choke point every
``log_*_event`` helper and every agent audit event funnels through.

Test IDs: HC-AUD-0NN.
"""

from __future__ import annotations

import json
import logging

import pytest

from core import audit as audit_module
from core.audit import (
    ALLOWED_ACTIONS,
    ALLOWED_DETAIL_KEYS,
    COUNT_MAP_DETAIL_KEYS,
    ID_LIST_DETAIL_KEYS,
    STRING_DETAIL_KEYS,
    _scrub_action,
    _scrub_details,
    create_audit_log,
    log_auth_event,
    log_care_task_event,
    log_document_event,
    log_export_event,
    log_observation_event,
    log_pinboard_event,
    log_profile_event,
)


class _FakeDb:
    """Minimal stand-in for AsyncSession — create_audit_log only calls .add()."""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)


async def _write(**kwargs) -> object:
    db = _FakeDb()
    return await create_audit_log(db=db, **kwargs)


def _details_of(row: object) -> dict:
    return json.loads(row.details_json) if row.details_json else {}


# --------------------------------------------------------------------------
# HC-AUD-001 — free-text and PHI-shaped keys are dropped
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_aud_001_poisoned_details_keys_are_dropped():
    row = await _write(
        event_type="document.import",
        action="Imported document",
        details={
            "filename": "LabCorp_2026_glucose_JohnDoe.pdf",
            "analyte": "Hemoglobin A1c",
            "medication_name": "Metformin 500mg",
            "note": "patient reports chest pain",
            "count": 3,
        },
    )
    details = _details_of(row)

    assert details["count"] == 3
    for leaked in ("filename", "analyte", "medication_name", "note"):
        assert leaked not in details
    # The row records that scrubbing happened, without recording what was scrubbed.
    assert details["_scrubbed"] == 4


# --------------------------------------------------------------------------
# HC-AUD-002 — the nested observation-edit shape never persists
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_aud_002_nested_change_dict_never_persists():
    """api/observations.py used to write {"changes": {"value": {"old":.., "new":..}}},
    i.e. verbatim lab values, units and reference ranges into the plaintext DB."""
    row = await _write(
        event_type="observation.verify",
        action="Verified observation",
        details={
            "changes": {
                "value": {"old": 94.0, "new": 5.22},
                "unit": {"old": "mg/dL", "new": "mmol/L"},
            }
        },
    )
    details = _details_of(row)

    assert "changes" not in details
    assert "94" not in json.dumps(details)
    assert "mg/dL" not in json.dumps(details)


@pytest.mark.asyncio
async def test_hc_aud_002b_changed_fields_replacement_shape_survives():
    """The approved replacement — field *names* only, never values."""
    row = await _write(
        event_type="observation.verify",
        action="Verified observation",
        details={"changed_fields": ["value", "unit"]},
    )
    assert _details_of(row)["changed_fields"] == ["value", "unit"]


# --------------------------------------------------------------------------
# HC-AUD-003 — interpolated actions are replaced
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_aud_003_interpolated_action_is_replaced_by_event_type():
    row = await _write(
        event_type="document.import",
        action="Imported document 'LabCorp_2026_glucose_JohnDoe.pdf'",
    )
    assert row.action == "document.import"
    assert "LabCorp" not in row.action


@pytest.mark.asyncio
async def test_hc_aud_003b_registered_action_passes_through():
    row = await _write(event_type="document.import", action="Imported document")
    assert row.action == "Imported document"


# --------------------------------------------------------------------------
# HC-AUD-004 — every helper emits a registered action (anti-regression gate)
# --------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("helper", "events", "kwargs"),
    [
        (
            log_profile_event,
            ["create", "unlock", "lock", "delete", "update",
             "recovery_code_generated", "recovered", "recovery_failed"],
            {"profile_id": "p1", "profile_name": "Jane Doe"},
        ),
        (
            log_document_event,
            ["import", "view", "delete", "parse", "verify"],
            {"profile_id": "p1", "document_id": "d1", "filename": "secret.pdf"},
        ),
        (
            log_observation_event,
            ["verify", "edit", "delete", "view"],
            {"profile_id": "p1", "observation_id": "o1", "analyte": "Glucose"},
        ),
        (
            log_care_task_event,
            ["view", "create", "update"],
            {"profile_id": "p1", "task_id": "t1"},
        ),
        (
            log_pinboard_event,
            ["view", "create", "update", "delete", "item_add", "item_remove", "export"],
            {"profile_id": "p1", "pinboard_id": "b1"},
        ),
        (
            log_auth_event,
            ["login", "logout", "failed", "session_expired"],
            {"profile_id": "p1"},
        ),
    ],
)
async def test_hc_aud_004_all_log_helpers_emit_registered_actions(helper, events, kwargs):
    for event in events:
        row = await helper(db=_FakeDb(), event=event, **kwargs)
        assert row.action in ALLOWED_ACTIONS, (
            f"{helper.__name__}({event!r}) produced unregistered action {row.action!r}"
        )


@pytest.mark.asyncio
async def test_hc_aud_004b_export_helper_emits_registered_action():
    row = await log_export_event(db=_FakeDb(), profile_id="p1", export_type="fhir")
    assert row.action in ALLOWED_ACTIONS
    # export_type is an enum-shaped value and belongs in details, not the action string
    assert _details_of(row)["export_type"] == "fhir"


@pytest.mark.asyncio
async def test_hc_aud_004c_helpers_never_persist_the_names_they_accept():
    """The helpers still take filename/analyte/profile_name for call-site
    compatibility, but none of them may reach the database."""
    rows = [
        await log_profile_event(
            db=_FakeDb(), event="create", profile_id="p1", profile_name="Jane Doe"
        ),
        await log_document_event(
            db=_FakeDb(), event="import", profile_id="p1",
            document_id="d1", filename="LabCorp_JohnDoe.pdf",
        ),
        await log_observation_event(
            db=_FakeDb(), event="verify", profile_id="p1",
            observation_id="o1", analyte="Hemoglobin A1c",
        ),
    ]
    for row in rows:
        blob = f"{row.action} {row.details_json or ''}"
        for secret in ("Jane Doe", "LabCorp", "JohnDoe", "Hemoglobin"):
            assert secret not in blob


# --------------------------------------------------------------------------
# HC-AUD-005 — allowlisted ids, counts, enums and booleans survive
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_aud_005_allowlisted_values_survive():
    row = await _write(
        event_type="care_task.view",
        action="Viewed care plan tasks",
        details={
            "action": "accept",          # asserted by existing tests — must survive
            "count": 7,
            "status": "open",
            "verified": True,
            "limit": 50,
            "observation_ids": ["o1", "o2"],
            "resource_counts": {"Observation": 4, "Patient": 1},
        },
    )
    details = _details_of(row)

    assert details["action"] == "accept"
    assert details["count"] == 7
    assert details["status"] == "open"
    assert details["verified"] is True
    assert details["limit"] == 50
    assert details["observation_ids"] == ["o1", "o2"]
    assert details["resource_counts"] == {"Observation": 4, "Patient": 1}
    assert "_scrubbed" not in details


@pytest.mark.asyncio
async def test_hc_aud_005b_free_text_in_an_allowlisted_key_is_still_dropped():
    """Allowlisting a key does not allowlist arbitrary prose in its value."""
    row = await _write(
        event_type="agent.plan",
        action="Agent planned a step",
        details={"abstain_reason": "patient asked about chest pain and dizziness"},
    )
    details = _details_of(row)
    assert "abstain_reason" not in details
    assert details["_scrubbed"] == 1


@pytest.mark.asyncio
async def test_hc_aud_005c_long_id_lists_collapse_to_a_count():
    row = await _write(
        event_type="agent.act",
        action="Agent used a tool",
        details={"chunk_ids": [f"c{i}" for i in range(120)]},
    )
    details = _details_of(row)
    assert "chunk_ids" not in details
    assert details["chunk_ids_count"] == 120


@pytest.mark.asyncio
async def test_hc_aud_005d_none_details_stays_none():
    row = await _write(event_type="auth.login", action="User logged in", details=None)
    assert row.details_json is None


# --------------------------------------------------------------------------
# HC-AUD-006 — seeded-flow dump carries no free text
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_aud_006_seeded_flow_audit_dump_has_no_free_text():
    """Every value written across a representative flow must be an id, a count,
    a boolean or a spaceless enum — free prose is what leaks PHI."""
    rows = [
        await log_document_event(
            db=_FakeDb(), event="import", profile_id="p1", document_id="d1",
            filename="LabCorp_2026_glucose.pdf",
            details={"doc_type": "lab_csv", "observations_extracted": 12},
        ),
        await log_observation_event(
            db=_FakeDb(), event="verify", profile_id="p1", observation_id="o1",
            analyte="Hemoglobin A1c", details={"changed_fields": ["value"]},
        ),
        await log_export_event(
            db=_FakeDb(), profile_id="p1", export_type="fhir",
            details={"redaction_count": 3, "resource_counts": {"Observation": 9}},
        ),
    ]

    for row in rows:
        assert row.action in ALLOWED_ACTIONS
        for key, value in _details_of(row).items():
            if isinstance(value, str):
                assert " " not in value, f"free text in {key}: {value!r}"


# --------------------------------------------------------------------------
# HC-AUD-007 — the application log line is scrubbed too
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_aud_007_app_logger_line_uses_scrubbed_action(caplog):
    """The logger.info line previously echoed the raw interpolated action into
    the plaintext application log — a second copy of the same leak."""
    with caplog.at_level(logging.INFO, logger=audit_module.__name__):
        await _write(
            event_type="document.import",
            action="Imported document 'LabCorp_2026_glucose_JohnDoe.pdf'",
        )
    assert "LabCorp" not in caplog.text
    assert "document.import" in caplog.text


# --------------------------------------------------------------------------
# HC-AUD-008 — allowlist self-consistency
# --------------------------------------------------------------------------

def test_hc_aud_008_allowlist_subsets_are_consistent():
    """Every typed sub-set must itself be allowlisted, or its keys can never
    be reached — a silent misconfiguration."""
    for subset, name in (
        (STRING_DETAIL_KEYS, "STRING_DETAIL_KEYS"),
        (ID_LIST_DETAIL_KEYS, "ID_LIST_DETAIL_KEYS"),
        (COUNT_MAP_DETAIL_KEYS, "COUNT_MAP_DETAIL_KEYS"),
    ):
        assert subset <= ALLOWED_DETAIL_KEYS, f"{name} has keys outside ALLOWED_DETAIL_KEYS"


def test_hc_aud_008b_known_phi_keys_are_not_allowlisted():
    """A regression tripwire: these keys were the actual leaks found in the
    2026-07 call-site inventory. Re-adding any of them must fail loudly."""
    for phi_key in (
        "filename", "analyte", "analyte_filter", "medication_name",
        "changes", "section_titles", "output_dir", "query_match", "profile_name",
    ):
        assert phi_key not in ALLOWED_DETAIL_KEYS


def test_hc_aud_008c_scrubbers_never_raise():
    """Audit is fail-closed on GET routes: a scrubber exception would 500 a
    read route. Hostile input must degrade, not raise."""
    assert _scrub_details({"count": object()}) == {"_scrubbed": 1}
    assert _scrub_details({}) is None
    assert _scrub_details(None) is None
    assert _scrub_action("anything at all", "some.event") == "some.event"


# --------------------------------------------------------------------------
# HC-AUD-009 — agent events keep their identity without growing the allowlist
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_aud_009_agent_events_use_registered_static_actions():
    """Agent nodes and tools pass their own identity as `action` (e.g.
    "query_timeline"). Persisting that verbatim would mean registering every
    tool name and silently degrading each new tool's rows until someone
    remembered to. emit_audit_event maps to a static per-node template instead.
    """
    from modules.agent.audit import AGENT_NODE_ACTIONS, AgentAuditEvent, emit_audit_event

    for node, expected_action in AGENT_NODE_ACTIONS.items():
        db = _FakeDb()
        await emit_audit_event(
            AgentAuditEvent(
                run_id="run-1",
                node=node,
                profile_id="p1",
                event_type=f"agent.{node}",
                action="query_timeline",
                step_index=0,
                details={"tool_name": "query_timeline", "count": 3},
            ),
            db=db,
        )
        row = db.added[0]
        assert row.action == expected_action
        assert row.action in ALLOWED_ACTIONS

        # Identity is preserved as allowlisted enum data, not lost.
        details = _details_of(row)
        assert details["node"] == node
        assert details["action"] == "query_timeline"
        assert details["tool_name"] == "query_timeline"
        assert details["count"] == 3


@pytest.mark.asyncio
async def test_hc_aud_009b_a_new_tool_needs_no_allowlist_change():
    """The point of the mapping: an unknown tool name still lands in a
    registered action rather than degrading to a bare event type."""
    from modules.agent.audit import AgentAuditEvent, emit_audit_event

    db = _FakeDb()
    await emit_audit_event(
        AgentAuditEvent(
            run_id="run-2",
            node="act",
            profile_id="p1",
            event_type="agent.act",
            action="some_future_tool",
            step_index=1,
            details={"tool_name": "some_future_tool"},
        ),
        db=db,
    )
    row = db.added[0]
    assert row.action == "Agent used a tool"
    assert _details_of(row)["tool_name"] == "some_future_tool"
