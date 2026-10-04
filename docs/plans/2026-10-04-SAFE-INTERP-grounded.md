# SAFE-INTERP-GROUNDED — Escalate Prohibited Grounded Answers, Audit Interpretation Routes — Implementation Plan

**Last Updated:** 2026-10-04
**Owner:** repository owner
**Refresh Trigger:** any commit to `src/backend/api/interpretations.py`, `src/backend/modules/rag.py::validate_response` / `ValidatedResponse`, `src/backend/core/audit.py` or `modules/agent/guardrails/templates.py` before this plan runs; SAFE-CHAT PR #44 merging (its `rag.py` hunk is identical — see Global Constraints).
**Prerequisites:** `origin/main` contains `90c502a`. D9 venv `~/venvs/asclexis-311`.
**Status:** PROPOSED — not executed. Wave 3, L1-A, phase 4.
**Review:** Codex plan r1 REVISE (1 BLOCKER, 3 MAJOR, 1 MINOR): all accepted and fixed (`audit/2026-09-25/reviews/SAFEINTERP-r1-response.md`).

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `POST /interpretations/observations/{id}/interpret-grounded` never returns a grounded answer that matches a prohibited medical-advice pattern (it returns `ESCALATE_TEMPLATE` instead), and every interpretation route that reads or writes profile data writes a fail-closed audit row with ids, counts and enums only.

**Architecture:**
- **A. Flag.** `ValidatedResponse.prohibited_advice` in `modules/rag.py` — **byte-identical** to SAFE-CHAT `f5961e7`'s hunk, so whichever of #44 / this PR merges second merges cleanly (Task 3 Step 5 checks it with `git merge-tree`).
- **B. Grounded route.** `interpretation.grounded` is written **right after `interpret_observation` succeeds and before `rag.query`**, because that call may already have written a `LabInterpretation` (`modules/interpret.py:278-279`) and `rag.query` can still end in 501 (`ModelUnavailableError`). After the response parts are built, if `rag_result.prohibited_advice`: replace `grounded_segments`, `full_response`, `verification`, and write `interpretation.prohibited_blocked` (`{reason: prohibited_pattern, decision: escalate}`).
- **Error exits.** 404/403 exits happen before any profile data is returned or written (they compare the requested observation's ownership); they are recorded per request by `SecurityAuditMiddleware` (`security/audit_middleware.py:60-75`) and get no interpretation audit row. Every exit **after** a profile write or a returned profile read is audited.
- **C. Audit.** One private helper `_audit_interpretation` in `api/interpretations.py` calling `core.audit.audit_and_commit(create_audit_log, …)` with `action == event_type` (silent path in `_scrub_action`, `core/audit.py:173-192`) — `core/audit.py` is not edited. Routes and events:

| Route | Event | entity | details |
|---|---|---|---|
| `POST /observations/{id}/interpret` | `interpretation.generate` | observation / id | — |
| `POST /observations/{id}/interpret-grounded` | `interpretation.grounded` (+ `interpretation.prohibited_blocked`) | observation / id | block row: `reason`, `decision` |
| `GET /observations/{id}/interpretation` | `interpretation.view` | observation / id | — |
| `POST /panels/{panel}/interpret` | `interpretation.panel_generate` | panel_interpretation / interpretation id (panel name is clinical content, not recorded) | — |
| `GET /recent` | `interpretation.list_recent` | — | `count`, `limit` |
| `POST /batch` | `interpretation.batch_generate` | — | `observation_ids`, `count`, `skipped_count` |
| `GET /knowledge/biomarker/{analyte}` | **none** — public master-DB reference data, no profile data (`api/interpretations.py:640-670`) | | |

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, pytest-asyncio, `route_client`.

**Spec:** owner decision **SAFE-INTERP-GROUNDED** (chat 2026-10-04, owner-decisions on `docs/wave3-close`), verbatim: "Swap in ESCALATE_TEMPLATE on a prohibited match, plus audit rows on the interpretation routes. HTTP tests and Codex review. interpret_safety.py not edited." Template confirmed by **SAFE-CHAT-TPL** ("ESCALATE_TEMPLATE confirmed").

## Global Constraints

- Python 3.11. No new timestamps (the existing `datetime.utcnow()` at `get_interpretation` is untouched; P5 owns it).
- **Read-only:** `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, `core/audit.py`, `core/auth.py`, `core/security.py`, `core/profile_database.py`, `modules/interpret.py` (not needed, see Finding 4), `modules/agent/`, `src/frontend`.
- No new patient-facing copy; `ESCALATE_TEMPLATE` imported.
- Audit rows: no analyte, panel name, question or answer text. Fail-closed (`audit_and_commit` raises → request fails).
- `rag.py` hunk must stay byte-identical to `git -C ../hc-safechat show f5961e7 -- src/backend/modules/rag.py`.
- Count slots: rewrite `CLAUDE.md:30,:35`, `AGENT.md:76` to the measured number; serial at merge (program ground rule 8). If `origin/main` moved, `git merge origin/main`, regenerate the index, re-measure and re-run Task 3 Step 1 (`orchestration.md:24`).
- **Shared-file order.** `api/interpretations.py` is listed as P5 → W-7 (`implementation-program.md:149`); this phase adds itself **before P5** (Wave 4, not open). P5 Task 3 edits only the `from datetime import datetime` import and the `datetime.utcnow()` at `get_interpretation` (`audit/2026-09-25/plans/05-utcnow-migration.md:193-209`), lines this plan does not touch; P5 and W-7 rebase onto it. W-7 F-3 already records the 0-audit-call gap (`docs/plans/2026-09-27-W07-tiered-interpretation-via-modelrunner.md:101`); this phase closes it for the existing 6 routes.
- Staging by explicit pathspec; `git add --` new files first. Shell header for every block: `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"`.

## Review Focus

1. **Verification metadata leaks the answer** (`claims_with_issues`) → reset; HC-SAFEINTERP-001 (marker absent from the whole body).
2. **Audit failure** → request fails, nothing returned: HC-SAFEINTERP-003 (grounded), 005 (view). No route catches it, so FastAPI returns 500; `TestClient` re-raises, which the tests assert.
6. **Model unavailable after the interpretation was written** → 501, and the `interpretation.grounded` row exists: HC-SAFEINTERP-006.
3. **Clean grounded answer untouched**, single `interpretation.grounded` row: 002.
4. **Audit rows carry no clinical text** (analyte "LDL", panel "lipid"): 001, 004.
5. **Persisted interpretations** — template/KB text, not model output; not swapped (Finding 4).

---

## Finding (re-verified on `origin/main@90c502a`, 2026-10-04)

| # | Fact | Evidence |
|---|---|---|
| 1 | The grounded route returns `full_response`, segments and `verification.issues` verbatim, with only `is_valid` | `src/backend/api/interpretations.py:443-505` |
| 2 | The UI renders it regardless | `src/frontend/src/pages/LabInterpreter.tsx:92,288`; `is_valid` only switches a badge (`:184`) (security-reviewer, PR #44) |
| 3 | No interpretation route writes an audit row | `grep -c -i audit src/backend/api/interpretations.py` → `0` |
| 4 | **The grounded RAG answer is not persisted.** The persisted `LabInterpretation` comes from `interpret_module.interpret_observation`, which builds **template/KB text** (`modules/interpret.py:193-196` → `_generate_interpretation` `:555-649`); the LLM path `interpret_with_model` (`:877`) has no caller (`grep -rn interpret_with_model src/backend --include=*.py` → definition only) | so "persisted interpretation holds the template" is already true for model output; nothing to swap in storage |
| 5 | **Swapping persisted template text on a pattern match would replace correct reference text:** 7 of 60 seeded KB fields match a prohibited pattern — 6 on the word "certain" ("certain medications"), 1 on "you have a cut" | L1 measurement, 2026-10-04, command in [KB scan](#kb-scan-command-and-output) |
| 6 | **Plan pre-validated** (throwaway detached worktree of `90c502a`, removed; re-run after Codex r1): test file below + code below, from `src/backend` with `HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest … -p no:cacheprovider -q` | RED `10 failed`; GREEN with `test_rag_pipeline.py test_biomarker_assistant.py test_interpret_history_units.py test_interpret_safety_adversarial.py test_audit_phi_minimization.py`: `121 passed`; collect `1356 tests collected`. BI-1 → 001 red; BI-2 → 001 red; BI-3 (view audit removed) → 004[view], 005 red; BI-5 (grounded audit moved after `rag.query`) → 006 red |

## KB scan command and output

From `src/backend` on `90c502a` (read-only):
```bash
HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python - <<'EOF'
import importlib.util, re, sys
sys.path.insert(0, ".")
from modules.interpret_safety import InterpretationSafetyGuard as G
spec = importlib.util.spec_from_file_location("seed", "scripts/seed_knowledge_base.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pats = [(re.compile(p, re.I), n) for p, n in G.PROHIBITED_PATTERNS]
fields = ["description", "clinical_significance", "normal_interpretation", "high_interpretation", "low_interpretation"]
total = hits = 0
for row in m.BIOMARKER_DATA:
    for f in fields:
        t = row.get(f) or ""
        if not t:
            continue
        total += 1
        for rx, n in pats:
            mm = rx.search(t)
            if mm:
                hits += 1; print((row["analyte_canonical"], f, n, mm.group(0))); break
print("KB fields scanned", total, "matching a prohibited pattern", hits)
EOF
```
Output:
```
('total_cholesterol', 'low_interpretation', 'certainty_claims', 'certain')
('glucose_fasting', 'low_interpretation', 'certainty_claims', 'certain')
('wbc', 'low_interpretation', 'certainty_claims', 'certain')
('platelets', 'description', 'diagnostic_language', 'you have a')
('platelets', 'clinical_significance', 'certainty_claims', 'certain')
('platelets', 'low_interpretation', 'certainty_claims', 'certain')
('vitamin_d', 'description', 'certainty_claims', 'certain')
KB fields scanned 60 matching a prohibited pattern 7
```

## Out of scope (reported)

- Persisted template interpretations matching patterns (Finding 5) — pattern false positives; feeds PROHIBITED-PARAPHRASE.
- `GET /knowledge/biomarker/…` audit — public data.
- Agent path / chat — SAFE-CHAT (#44) and SAFE-CHAT-AGENT.

## Files

| File | Action | Task |
|---|---|---|
| `src/backend/tests/test_safe_interp_grounded.py` | create (HC-SAFEINTERP-001…006; 10 collected) | 1 |
| `src/backend/modules/rag.py` | modify (identical to #44) | 2 |
| `src/backend/api/interpretations.py` | modify (imports, helper, 6 routes; `master_db` dependency added to `get_interpretation` and `get_recent_interpretations`) | 2 |
| `CLAUDE.md`, `AGENT.md` | collected slots | 2 |
| this plan, `docs/INDEX.md`, `docs/_link_graph.json`, `audit/2026-09-25/reviews/SAFEINTERP-*` | docs | 0, 3 |

---

### Task 0: Gates and plan commit (L1)

- [ ] **Step 1:**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
cd "$WT" && [ "$(git rev-parse --show-toplevel)" = "$WT" ] && [ "$(git branch --show-current)" = fix/safe-interp-grounded ] || { echo WRONG-WORKTREE; exit 1; }
git fetch origin -q; git merge-base --is-ancestor 90c502a origin/main || { echo ANCESTOR-FAIL; exit 1; }; echo ANCESTOR-OK
git diff --quiet 90c502a origin/main -- src/backend/api/interpretations.py src/backend/modules/rag.py src/backend/core/audit.py src/backend/modules/agent/guardrails/templates.py || { echo TRIGGER-PATHS-CHANGED; exit 1; }; echo TRIGGER-PATHS-UNCHANGED
rc=0; git grep -n -i "safeinterp\|interpretation.prohibited_blocked" -- src || rc=$?; [ "$rc" = 1 ] && echo NO-COLLISION || { echo "COLLISION rc=$rc"; exit 1; }
```
- [ ] **Step 2:** Codex plan review (≤2 rounds). Commit:
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
cd "$WT" && python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph \
 && P="docs/plans/2026-10-04-SAFE-INTERP-grounded.md docs/INDEX.md docs/_link_graph.json audit/2026-09-25/reviews/SAFEINTERP-r1-prompt.md audit/2026-09-25/reviews/SAFEINTERP-r1-codex.txt audit/2026-09-25/reviews/SAFEINTERP-r1-response.md" \
 && git add -- $P && git diff --cached --name-only && git commit -m "docs(safe-interp): plan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- $P
```

### Task 1: Failing tests (RED)

- [ ] **Step 1:** create `src/backend/tests/test_safe_interp_grounded.py`:

```python
"""SAFE-INTERP-GROUNDED — interpretation routes: a prohibited grounded answer
is replaced with ESCALATE_TEMPLATE, and every route that reads or writes
profile data writes a text-free audit row.

Plan: docs/plans/2026-10-04-SAFE-INTERP-grounded.md
Owner decision SAFE-INTERP-GROUNDED (2026-10-04).

All tests go through HTTP via tests/support/routes.py::route_client with a
real in-memory master DB (audit rows) and a real in-memory profile DB; for
the grounded route only RAG retrieval and generation are stubbed, so the
real RAGModule.validate_response runs.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.interpretations as I
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
import models  # noqa: F401  register every table on both bases
from models import LabInterpretation, Observation
from models.audit import AuditLog
from modules.agent.guardrails.templates import ESCALATE_TEMPLATE
from modules.rag import ModelUnavailableError, RetrievedChunk, VerificationMetadata
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
ANALYTE = "ldl"
MARKER = "SAFEINTERP-PROHIBITED-3c9d"
PROHIBITED_ANSWER = (
    "REPORT FACTS:\nYour LDL is 190 mg/dL [cite:1].\n\n"
    "IMPLICATIONS:\nThis means you have hyperlipidemia and you should take "
    f"20 mg atorvastatin daily {MARKER}."
)
CLEAN_MARKER = "SAFEINTERP-CLEAN-5e1a"
CLEAN_ANSWER = f"REPORT FACTS:\nYour LDL result is listed as 120 mg/dL [cite:1]. {CLEAN_MARKER}"
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)


async def _engine_session(base):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


@pytest_asyncio.fixture
async def dbs():
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    obs = Observation(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
        analyte_canonical=ANALYTE, analyte_raw="LDL Cholesterol", value=120.0,
        unit="mg/dL", ref_low=0.0, ref_high=130.0, collected_at=COLLECTED,
    )
    profile_db.add(obs)
    await profile_db.commit()
    try:
        yield profile_db, master_db, obs.id
    finally:
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


def _rag(answer: str):
    with patch("modules.rag.get_model_runner") as runner, patch("modules.rag.EmbeddingsModule"):
        runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        from modules.rag import RAGModule

        rag = RAGModule(enable_verification=True)
    rag.retrieve_context = AsyncMock(return_value=[
        RetrievedChunk(
            chunk_id="c1", source_type="reference", doc_id=None, doc_title="LDL reference",
            page=None, text="LDL cholesterol reference text.", relevance_score=0.9,
        )
    ])
    rag._generate_with_runner = AsyncMock(return_value=answer)
    rag._run_verification_pipeline = MagicMock(return_value=VerificationMetadata(
        verification_enabled=True, total_claims=1, verified_claims=0, failed_claims=1,
        claims_with_issues=[f"you have hyperlipidemia {MARKER}"],
        faithfulness_score=0.9, authority_score=0.5, verification_summary="stub",
    ))
    return rag


def _call(profile_db, master_db, method: str, url: str, **kwargs):
    with route_client(
        interpretations_router, "/interpretations", profile_id=PROFILE_ID, master_db=master_db
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


async def _audit_rows(master_db) -> list[AuditLog]:
    master_db.expire_all()
    return list((await master_db.execute(select(AuditLog))).scalars().all())


def _row_blob(row: AuditLog) -> str:
    return " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)


@pytest.mark.asyncio
async def test_hc_safeinterp_001_prohibited_grounded_answer_replaced_and_audited(dbs):
    profile_db, master_db, obs_id = dbs
    with patch.object(I, "get_rag_module", return_value=_rag(PROHIBITED_ANSWER)):
        resp = _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert MARKER not in json.dumps(body), "prohibited answer text reached the client"
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert [s["content"] for s in body["grounded_segments"]] == [ESCALATE_TEMPLATE]
    assert body["grounded_segments"][0]["citations"] == []
    assert body["verification"]["issues"] == []
    assert body["is_valid"] is False
    profile_db.expire_all()
    stored = (await profile_db.execute(select(LabInterpretation))).scalars().all()
    assert all(MARKER not in (i.interpretation_text + (i.advice_text or "")) for i in stored)
    rows = await _audit_rows(master_db)
    assert sorted(r.event_type for r in rows) == [
        "interpretation.grounded", "interpretation.prohibited_blocked",
    ]
    for row in rows:
        assert row.profile_id == PROFILE_ID
        blob = _row_blob(row)
        assert MARKER not in blob and "Explain my lab result" not in blob
        assert "LDL" not in blob and ANALYTE not in json.dumps(row.details_json or "")
    blocked = next(r for r in rows if r.event_type == "interpretation.prohibited_blocked")
    assert json.loads(blocked.details_json) == {
        "reason": "prohibited_pattern", "decision": "escalate",
    }


@pytest.mark.asyncio
async def test_hc_safeinterp_002_clean_grounded_answer_untouched(dbs):
    profile_db, master_db, obs_id = dbs
    with patch.object(I, "get_rag_module", return_value=_rag(CLEAN_ANSWER)):
        resp = _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")
    assert resp.status_code == 201, resp.text
    assert CLEAN_MARKER in resp.json()["full_response"]
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.grounded"]


@pytest.mark.asyncio
async def test_hc_safeinterp_003_grounded_audit_failure_fails_closed(dbs):
    profile_db, master_db, obs_id = dbs

    async def _failing_commit():
        raise RuntimeError("simulated master DB failure")

    # No handler catches it, so TestClient re-raises the server error (in
    # production: HTTP 500). Either way nothing is returned to the client.
    with patch.object(I, "get_rag_module", return_value=_rag(PROHIBITED_ANSWER)), \
         patch.object(master_db, "commit", _failing_commit), \
         pytest.raises(RuntimeError, match="simulated master DB failure"):
        _call(profile_db, master_db, "POST",
              f"/interpretations/observations/{obs_id}/interpret-grounded")


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["interpret", "view", "panel", "recent", "batch"])
async def test_hc_safeinterp_004_profile_data_routes_write_audit_row(dbs, route):
    profile_db, master_db, obs_id = dbs
    if route == "view":
        # Something to view: generate first, then drop that audit row.
        _call(profile_db, master_db, "POST", f"/interpretations/observations/{obs_id}/interpret")
        for row in await _audit_rows(master_db):
            await master_db.delete(row)
        await master_db.commit()
    calls = {
        "interpret": ("POST", f"/interpretations/observations/{obs_id}/interpret", {},
                      "interpretation.generate"),
        "view": ("GET", f"/interpretations/observations/{obs_id}/interpretation", {},
                 "interpretation.view"),
        "panel": ("POST", "/interpretations/panels/lipid/interpret",
                  {"params": {"collected_at": COLLECTED.isoformat()}},
                  "interpretation.panel_generate"),
        "recent": ("GET", "/interpretations/recent", {}, "interpretation.list_recent"),
        "batch": ("POST", "/interpretations/batch",
                  {"json": {"observation_ids": [obs_id]}}, "interpretation.batch_generate"),
    }
    method, url, kwargs, event_type = calls[route]
    resp = _call(profile_db, master_db, method, url, **kwargs)
    assert 200 <= resp.status_code < 300, resp.text
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == [event_type], [r.event_type for r in rows]
    assert rows[0].profile_id == PROFILE_ID
    blob = _row_blob(rows[0])
    assert "LDL" not in blob and "lipid" not in blob.lower()


@pytest.mark.asyncio
async def test_hc_safeinterp_005_view_audit_failure_fails_closed(dbs):
    profile_db, master_db, obs_id = dbs
    _call(profile_db, master_db, "POST", f"/interpretations/observations/{obs_id}/interpret")

    async def _failing_commit():
        raise RuntimeError("simulated master DB failure")

    with patch.object(master_db, "commit", _failing_commit), \
         pytest.raises(RuntimeError, match="simulated master DB failure"):
        _call(profile_db, master_db, "GET",
              f"/interpretations/observations/{obs_id}/interpretation")


@pytest.mark.asyncio
async def test_hc_safeinterp_006_model_unavailable_after_write_still_audited(dbs):
    """interpret_observation has already written the LabInterpretation when
    rag.query raises ModelUnavailableError (501): that write must be audited."""
    profile_db, master_db, obs_id = dbs
    rag = _rag(CLEAN_ANSWER)
    rag._generate_with_runner = AsyncMock(side_effect=ModelUnavailableError("no model"))
    with patch.object(I, "get_rag_module", return_value=rag):
        resp = _call(profile_db, master_db, "POST",
                     f"/interpretations/observations/{obs_id}/interpret-grounded")
    assert resp.status_code == 501, resp.text
    profile_db.expire_all()
    stored = (await profile_db.execute(select(LabInterpretation))).scalars().all()
    assert len(stored) == 1
    rows = await _audit_rows(master_db)
    assert [r.event_type for r in rows] == ["interpretation.grounded"]
```

- [ ] **Step 2: RED**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && { $PY -m pytest tests/test_safe_interp_grounded.py -p no:cacheprovider -q -rf > "$LOG/red.txt" 2>&1 || true; }; grep -E "^FAILED|passed|failed" "$LOG/red.txt"
```
Expected `10 failed` (001 "prohibited answer text reached the client"; 002 `[] == ['interpretation.grounded']`; 003/005 `DID NOT RAISE`; 004×5 empty audit list; 006 `[] == ['interpretation.grounded']`). Any pass → STOP.

### Task 2: Fix (GREEN) + count

- [ ] **Step 1: `modules/rag.py`** — apply exactly this hunk (identical to SAFE-CHAT `f5961e7`):
```diff
diff --git a/src/backend/modules/rag.py b/src/backend/modules/rag.py
index ac5c87b..c8cfa7b 100644
--- a/src/backend/modules/rag.py
+++ b/src/backend/modules/rag.py
@@ -109,6 +109,8 @@ class ValidatedResponse:
     insufficient_reasons: list[str] = field(default_factory=list)
     # Phase 4: Verification metadata
     verification: VerificationMetadata = field(default_factory=VerificationMetadata)
+    # SAFE-CHAT: True when a PROHIBITED_PATTERNS match fired in validate_response.
+    prohibited_advice: bool = False
 
 
 class RAGModule:
@@ -811,6 +813,7 @@ I was unable to fully process your question within the time limit. Please try as
         - (Phase 4) Claims are verified against sources
         """
         errors = []
+        prohibited_advice = False
 
         # Parse response into segments
         segments = self._parse_response_segments(response)
@@ -836,6 +839,7 @@ I was unable to fully process your question within the time limit. Please try as
         for pattern in self._compiled_prohibited_patterns:
             if pattern.search(response):
                 errors.append("Response contains prohibited medical advice")
+                prohibited_advice = True
                 break
 
         # Build validated segments with citations
@@ -869,6 +873,7 @@ I was unable to fully process your question within the time limit. Please try as
             is_valid=len(errors) == 0,
             validation_errors=errors,
             verification=verification_metadata,
+            prohibited_advice=prohibited_advice,
         )
 
     def _build_validated_segments(
```
- [ ] **Step 2: `api/interpretations.py` imports** — after `from core.auth import RequireAuth, Session, ProfileDbSession` add `from core.audit import audit_and_commit, create_audit_log`; after `from api.assistant import get_rag_module` add `from modules.agent.guardrails.templates import ESCALATE_TEMPLATE`.
- [ ] **Step 3: helper** — directly after `logger = logging.getLogger(__name__)`:
```python


async def _audit_interpretation(
    master_db: AsyncSession,
    event: str,
    profile_id: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Fail-closed audit row for an interpretation route (CLAUDE.md: audit
    logging on every route that touches observations or profile data).

    Ids, counts and enums only: never the analyte, panel name, question or
    any interpretation text (AUDIT-PHI-001; core.audit scrubs details too).
    """
    event_type = f"interpretation.{event}"
    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type=event_type,
        action=event_type,
        profile_id=profile_id,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
```
- [ ] **Step 4: routes** — insert each block immediately before the route's final `return`:
  - `generate_interpretation`: `await _audit_interpretation(master_db, "generate", session.profile_id, entity_type="observation", entity_id=observation_id)`.
  - `generate_grounded_interpretation`, (a) directly after the `if not interp_result.success or not interp_result.interpretation: raise …` block and before `rag = get_rag_module()`:
```python
    # The interpretation may already be written (modules/interpret.py commits
    # it), and rag.query below can still end in 501: audit now, fail-closed.
    await _audit_interpretation(
        master_db, "grounded", session.profile_id,
        entity_type="observation", entity_id=observation_id,
    )

```
    (b) after `verification = GroundedVerificationResponse(...)`, before the return:
```python
    # SAFE-INTERP-GROUNDED (owner decision 2026-10-04): a prohibited-pattern
    # match must never reach the client. Replace the grounded answer with the
    # fixed escalation template (same as /assistant/chat, SAFE-CHAT) and drop
    # verification detail, which carries claim text from the answer. The
    # grounded answer is not persisted anywhere; audit fail-closed before
    # returning, with no answer or question text.
    if rag_result.prohibited_advice:
        grounded_segments = [
            GroundedSegmentResponse(segment_type="uncertainty", content=ESCALATE_TEMPLATE, citations=[])
        ]
        full_response = ESCALATE_TEMPLATE
        verification = GroundedVerificationResponse()
        await _audit_interpretation(
            master_db, "prohibited_blocked", session.profile_id,
            entity_type="observation", entity_id=observation_id,
            details={"reason": "prohibited_pattern", "decision": "escalate"},
        )
```
  - `get_interpretation`: add parameter `master_db: AsyncSession = Depends(get_db),` after `profile_db`; before the return: `await _audit_interpretation(master_db, "view", session.profile_id, entity_type="observation", entity_id=observation_id)`.
  - `generate_panel_interpretation`: comment `# The panel name is clinical content: record the interpretation id only.` then `await _audit_interpretation(master_db, "panel_generate", session.profile_id, entity_type="panel_interpretation", entity_id=result.interpretation.id)`.
  - `get_recent_interpretations`: add `master_db: AsyncSession = Depends(get_db),` after `profile_db`; before the return: `await _audit_interpretation(master_db, "list_recent", session.profile_id, details={"count": len(interpretations), "limit": limit})`.
  - `batch_generate_interpretations`: `await _audit_interpretation(master_db, "batch_generate", session.profile_id, details={"observation_ids": successful, "count": len(successful), "skipped_count": len(failed)})`.
- [ ] **Step 5: GREEN**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && rc=0; $PY -m pytest tests/test_safe_interp_grounded.py tests/test_rag_pipeline.py tests/test_biomarker_assistant.py tests/test_interpret_history_units.py tests/test_interpret_safety_adversarial.py tests/test_audit_phi_minimization.py -p no:cacheprovider -q > "$LOG/green.txt" 2>&1 || rc=$?; tail -3 "$LOG/green.txt"; echo "$rc" > "$LOG/green.rc"; echo "rc=$rc"
```
Expected `121 passed`, rc=0.
- [ ] **Step 6: Count** — `cd "$WT/src/backend" && $PY -m pytest tests/ --collect-only -q -p no:cacheprovider > "$LOG/collect.txt" 2>&1 || exit 1; tail -1 "$LOG/collect.txt"`. Expected 1346 + 10 = **1356** on `90c502a`. Other → STOP. Rewrite the 3 slots. Never write `$LOG` files by hand.
- [ ] **Step 7: Commit** (gated on `green.rc` = 0 and the measured number in both files):
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
N=$(tail -1 "$LOG/collect.txt" | grep -oE '^[0-9]+')
[ "$(cat "$LOG/green.rc")" = 0 ] && grep -q "$N backend tests collected" "$WT/CLAUDE.md" && grep -q "$N collected" "$WT/AGENT.md" \
 && git -C "$WT" add -- src/backend/tests/test_safe_interp_grounded.py \
 && git -C "$WT" commit -m "fix(interpretations): escalate prohibited grounded answers; audit interpretation routes" -m "SAFE-INTERP-GROUNDED (owner decision 2026-10-04). HC-SAFEINTERP-001..005." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/modules/rag.py src/backend/api/interpretations.py src/backend/tests/test_safe_interp_grounded.py CLAUDE.md AGENT.md
```

### Task 3: Verification (L1)

- [ ] **Step 1: Full suite**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rc=0; flock /tmp/claude-1000/hc-pytest.lock $PY -m pytest tests/ -p no:cacheprovider -q -rfE > "$LOG/full.txt" 2>&1 || rc=$?; tail -3 "$LOG/full.txt"; echo "pytest rc=$rc"
U=$(grep -E "^(FAILED|ERROR) " "$LOG/full.txt" | grep -v test_api_rag_index_002b || true); [ -z "$U" ] && echo FAILURES-SUBSET-OK || { echo "$U"; exit 1; }
```
- [ ] **Step 2: Boot**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && $PY -c "from main import app; print('boot ok')"
```
- [ ] **Step 3: Scope**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
git -C "$WT" diff --exit-code origin/main...HEAD -- src/backend/modules/interpret_safety.py src/backend/modules/interpret.py src/backend/modules/redaction.py src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/core src/backend/modules/agent src/frontend >/dev/null && echo SCOPE-OK; git -C "$WT" status --short
```
- [ ] **Step 4: Break-it** in a disposable detached worktree (never the phase worktree):
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safeinterp-logs; mkdir -p "$LOG"
BK=/mnt/c/Users/DangT/Documents/GitHub/hc-safeinterp-break; [ ! -e "$BK" ] || { echo "BK exists"; exit 1; }
git -C "$WT" worktree add --detach "$BK" HEAD && [ "$(git -C "$BK" rev-parse HEAD)" = "$(git -C "$WT" rev-parse HEAD)" ] && cd "$BK/src/backend"
grep -n 'if rag_result.prohibited_advice:\|verification = GroundedVerificationResponse()\|master_db, "view"\|master_db, "batch_generate"\|master_db, "grounded"' api/interpretations.py
# apply ONE break at the printed lines, then:
$PY -m pytest tests/test_safe_interp_grounded.py -p no:cacheprovider -q -rf | grep -E "^FAILED|passed|failed"
git -C "$BK" checkout -- . && git -C "$BK" status --short
# after the last break:
cd / && git -C "$WT" worktree remove --force "$BK"
```
Breaks and expected reds: BI-1 the `if rag_result.prohibited_advice:` block removed → 001; BI-2 `verification = GroundedVerificationResponse()` removed → 001; BI-3 the `"view"` call removed → 004[view], 005; BI-4 the `"batch_generate"` call removed → 004[batch]; BI-5 the `"grounded"` call moved below the response build → 006.
- [ ] **Step 5: rag.py identity with #44** — `diff <(git -C "$WT" diff origin/main...HEAD -- src/backend/modules/rag.py | tail -n +3) <(git -C /mnt/c/Users/DangT/Documents/GitHub/hc-safechat diff 90c502a f5961e7 -- src/backend/modules/rag.py | tail -n +3) && echo RAG-HUNK-IDENTICAL`; and `git merge-tree --write-tree origin/fix/safe-chat-legacy-abstain HEAD` exits 0 apart from the count-slot / index files.
- [ ] **Step 6:** Codex adversarial diff review; execution record; PR.

## Stop gates

Any HC-SAFEINTERP test passes at RED; an edit in a read-only file; collected ≠ 1356 on `90c502a`; the `rag.py` hunk differs from #44; a reviewer finding needs the persisted template text swapped (owner item, Finding 5).

## Recurring-failures recheck

| § | Check |
|---|---|
| 1 | RED 9/9 first; HTTP via `route_client`; real master + profile DBs; real `validate_response`; break-its BI-1…4 |
| 2 | fail-closed paths pinned (003, 005); clean path pinned (002); the `rag.py` change is shared with #44 and kept identical |
| 3 | counts measured |
| 8 | L0's "persisted interpretation must hold the template" checked against the code (Finding 4) |
| 9 | the audit rule applied to every interpretation route, not one |

## Rollback

`git revert <fix sha>`. No schema change; audit rows written stay.

## Execution record

_(filled in by Task 3)_
