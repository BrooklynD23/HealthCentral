"""Sprint 1 — First tool, end-to-end. Stories S1-1..S1-4."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from modules.agent.tools.query_observations import (
    ObservationRow,
    QueryObservationsInput,
    QueryObservationsTool,
)


# --- live: typed-registry / tool contracts (FR-2, FR-3) ---------------------

def test_s1_1_malformed_tool_args_rejected_by_validation():
    """S1-1: bad input fails Pydantic validation; it never reaches the tool body."""
    with pytest.raises(ValidationError):
        QueryObservationsInput(limit=999)  # le=100


def test_s1_2_output_row_can_only_represent_verified():
    """S1-2: ObservationRow pins verified=True — unverified rows can't be returned."""
    with pytest.raises(ValidationError):
        ObservationRow(
            observation_id="o1", analyte="LDL", value=1.0,
            collected_at="2025-12-01T00:00:00", verified=False,
        )


def test_query_observations_tool_declares_read_only_schemas():
    assert QueryObservationsTool.name == "query_observations"
    assert QueryObservationsTool.InputModel is QueryObservationsInput


# --- skip: behavior that lands when S1 is implemented ------------------------

@pytest.mark.skip(reason="S1-2 scaffold: query returns only verified rows for current profile")
def test_s1_2_returns_only_verified_rows():
    ...


@pytest.mark.skip(reason="S1-3 scaffold: flag-on plan->act->answer yields >=1 citation")
def test_s1_3_flag_on_answer_has_citation():
    ...


@pytest.mark.skip(reason="S1-4 scaffold: plan/act/answer each emit an audit event")
def test_s1_4_audit_event_per_node():
    ...
