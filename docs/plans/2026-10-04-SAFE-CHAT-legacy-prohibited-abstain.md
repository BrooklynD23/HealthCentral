# SAFE-CHAT — Legacy Chat Path Replaces a Prohibited Answer — Implementation Plan

**Last Updated:** 2026-10-04
**Owner:** repository owner
**Refresh Trigger:** any commit to `src/backend/api/assistant.py::chat`, `src/backend/modules/rag.py::validate_response` / `ValidatedResponse`, or `src/backend/modules/agent/guardrails/templates.py` before this plan runs.
**Prerequisites:** `origin/main` contains `90c502a`. D9 venv `~/venvs/asclexis-311` exists.
**Status:** PROPOSED — not executed. Wave 3, L1-A, phase 2 (worked after DOC-DELETE-INTERP, before G-C3b; L0 work order, not a merge dependency: the two PRs share only the count slots and `docs/INDEX.md` / `docs/_link_graph.json`).
**Review:** Codex plan r1 REVISE (5 MAJOR): 4 accepted and fixed, 1 partly rejected (`docs/reviews/2026-09-25/SAFECHAT-r1-response.md`).

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the legacy `POST /assistant/chat` path (`rag.query`) produces an answer that matches a prohibited medical-advice pattern, the user never receives it and it is never persisted: the route returns and stores the existing fixed escalation template instead, and writes an audit row that carries no answer text.

**Architecture:** Two small edits, no schema change.
- **A. A typed flag, not a string match.** `ValidatedResponse` (`modules/rag.py:102-111`) gets `prohibited_advice: bool = False`. `validate_response` sets it where it already appends "Response contains prohibited medical advice" (`modules/rag.py:836-838`). The pattern list itself (`InterpretationSafetyGuard.PROHIBITED_PATTERNS`, ask-first) is read, never edited.
- **B. Replace before persist/return.** In `api/assistant.py::chat`, right after the legacy result is unpacked (`:869-870`) and before `_append_turns` (`:873`): if `result.prohibited_advice`, replace `segments`, `full_response` and `verification` with the fixed template, and write a fail-closed audit row via `core.audit.audit_and_commit(create_audit_log, ...)` with allowlisted keys only. `is_valid` (False) and `validation_errors` (generic strings, no answer text) are returned unchanged so the client contract still says the validator fired.

**Tech Stack:** Python 3.11 (D9 venv), FastAPI, SQLAlchemy async, pytest + pytest-asyncio, `src/backend/tests/support/routes.py::route_client`.

**Spec:** owner decision **SAFE-CHAT** (chat 2026-10-04, recorded in `docs/capstone-report/owner-decisions-2026-09-27.md` on L0 branch `docs/wave3-close`), verbatim: "When a prohibited pattern matches, replace the answer with the existing abstain/fallback template before persisting or returning it, and audit-log it. HTTP route test, Codex plan + diff review. Does not edit interpret_safety.py."

## Global Constraints

- **Target Python 3.11.** No new timestamps.
- **Ask-first files are read-only:** `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, `core/security.py`, `core/profile_database.py`, and **`core/audit.py`** (program item AUDIT-KEYS-DROPPED marks it ask-first). The audit row therefore uses only keys already in `STRING_DETAIL_KEYS` (`core/audit.py:68-75`) and an `action` equal to `event_type` (`_scrub_action` returns it silently, `core/audit.py:173-192`).
- **No new patient-facing copy.** The replacement text is an existing constant imported from `modules/agent/guardrails/templates.py`. Its copy is not edited.
- **Persisted turn holds the template, never the prohibited answer.** Audit row holds no answer text, no question text.
- **Route tests go through HTTP** (`route_client`) with a real in-memory per-profile DB.
- **Count slots (SLOT-RULE):** the commit that changes the collected count rewrites `CLAUDE.md:30`, `CLAUDE.md:35`, `AGENT.md:76` (collected number only) to the measured figure. If `origin/main` has moved (e.g. DDI PR #41 merged, 1350), measure on the merged tree: `git merge origin/main` first (`docs/agentic/orchestration.md:24`).
- **Staging:** explicit pathspecs; `git add -- <new files>` before a pathspec commit. Never `git add -A`, never `git reset`.
- **Shell:** every bash block starts with `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"`. Test output is saved to `$LOG/<step>.txt` before tailing. Full suites run under `flock /tmp/claude-1000/hc-pytest.lock`.

## Template choice (assumption, flagged to L0)

The decision says "the existing abstain/fallback template". Two fixed templates exist in `modules/agent/guardrails/templates.py`:
- `ESCALATE_TEMPLATE` (`:12-16`): "This is a question for your doctor or pharmacist. … can't advise on diagnosis, treatment, or medication decisions…". The agent guard returns exactly this when its advice gate fires (`modules/agent/guardrails/guard.py:111-118`).
- `ABSTAIN_TEMPLATE` (`:20-24`): "There isn't enough verified information in your record to explain this yet…". That statement is false here: retrieval succeeded and the answer was blocked for advice.

**This plan uses `ESCALATE_TEMPLATE`** so both chat paths answer the same condition with the same text. L0 was asked on 2026-10-04; if the owner picks `ABSTAIN_TEMPLATE`, Task 2 Step 2 swaps the one import and HC-SAFECHAT-001's expected constant. Both templates are checked by HC-SAFECHAT-003 not to trip the prohibited patterns themselves.

## Review Focus

1. **Verification metadata leaks the answer.** `VerificationMetadata.claims_with_issues` (`modules/rag.py:96`) holds claim text extracted from the prohibited answer and was returned as `verification.issues`. Expected: reset to an empty `VerificationInfo()`. Pinned by **HC-SAFECHAT-001** (marker absent from the whole JSON body).
2. **The audit write fails.** Expected: fail-closed — 500, no turn persisted, nothing returned. The audit runs before `_append_turns`. Pinned by **HC-SAFECHAT-004**.
3. **A clean answer is untouched** (most chats). Expected: same text, no audit row. Pinned by **HC-SAFECHAT-002**.
4. **The template itself trips the patterns** (a loop or a false "invalid"). Pinned by **HC-SAFECHAT-003**.
5. **Agent path, cache, grounded-interpretation route.** Not covered by this decision; see [Other paths](#other-paths-checked-reported-not-fixed).

---

## Finding (re-verified on `origin/main@90c502a`, 2026-10-04)

| # | Fact | Evidence |
|---|---|---|
| 1 | The prohibited check only appends an error string | `src/backend/modules/rag.py:835-839` |
| 2 | `is_valid` is the only consequence | `modules/rag.py:867-872` |
| 3 | `rag.query` returns the validated answer unchanged | `modules/rag.py:1270-1273` |
| 4 | The chat route persists `full_response` and returns it | `api/assistant.py:829-833` (build), `:869-870` (unpack), `:873-880` (`_append_turns`), `:893-903` (`ChatResponse`) |
| 5 | The chat UI does not read `is_valid` | `grep -rn is_valid src/frontend/src --include=*.ts*` → `services/assistant.ts:87`, `services/types.ts:347` (types), `pages/LabInterpreter.tsx:94` (the only consumer, interpretations page) |
| 6 | Patterns come from the ask-first guard | `modules/rag.py:176-179` reads `InterpretationSafetyGuard.PROHIBITED_PATTERNS` (`modules/interpret_safety.py:49-68`) |
| 7 | **Plan pre-validated (L1, 2026-10-04, throwaway detached worktree of 90c502a, removed):** Task 1 file and Task 2 code applied verbatim, from `src/backend` with `HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest … -p no:cacheprovider -q` | RED: `2 failed, 3 passed` (001 "prohibited answer text reached the client", 004 status 200). GREEN with `tests/test_chat_sessions.py tests/test_agent_cache_isolation.py tests/test_audit_phi_minimization.py`: `59 passed`. BI-2 → 001 FAIL; BI-3 (block after the turn commit) → 001 + 004 FAIL; restored → `5 passed` |

## Other paths checked (reported, not fixed)

| Path | Gap? | Evidence | Disposition |
|---|---|---|---|
| Streaming chat | none exists | `grep -n -i stream src/backend/api/assistant.py` → no streaming route | n/a |
| Agent path (`_serve_via_agent`, default on) | **different gate**: the guard's advice gate uses `classify_advice` (`modules/agent/guardrails/classifier.py`, question-shaped patterns), not `PROHIBITED_PATTERNS`. A drafted statement like "you have diabetes" or "take 20 mg" is not matched by `classify_advice`'s patterns and is gated only by groundedness. UNMEASURED end-to-end | `guard.py:103-118`, `classifier.py:30-67` | owner item **SAFE-CHAT-AGENT**; wider than the decision |
| Agent semantic cache | serves a stored terminal; inherits the agent gate | `api/assistant.py:693-702` | with SAFE-CHAT-AGENT |
| `POST /api/v1/observations/{observation_id}/interpret-grounded` (`api/interpretations.py:383-470`; interpretations router) | same `rag.query`, returns segments + `is_valid`; UI reads `is_valid` (`LabInterpreter.tsx:94`) — UNMEASURED whether it hides the text | `api/interpretations.py:443` | owner item **SAFE-INTERP-GROUNDED** |
| `ModelUnavailableError` fallback | templated knowledge text, not model output | `api/assistant.py:906-924` | n/a |

## Approval scope

Covered: legacy `/assistant/chat` replacement before persist/return, audit row, HTTP test, Codex plan + diff review. **Not licensed:** editing `interpret_safety.py` or any ask-first file; template copy changes; the agent path, cache, or interpretations route; frontend changes.

## Files

| File | Action | Hunk | Task |
|---|---|---|---|
| `src/backend/tests/test_safe_chat_prohibited.py` | create | HC-SAFECHAT-001…004 | 1 |
| `src/backend/modules/rag.py` | modify | `ValidatedResponse` +1 field (`:102-111`); `validate_response` set flag (`:813`, `:835-839`, `:867-872`) | 2 |
| `src/backend/api/assistant.py` | modify | imports (+2 lines near `:15-25`); one block after `:870` | 2 |
| `CLAUDE.md`, `AGENT.md` | modify | collected-count slots | 2 |
| this plan | modify | Execution record | 3 |
| `docs/INDEX.md`, `docs/_link_graph.json` | regenerate | generator output | 0, 3 |
| `docs/reviews/2026-09-25/SAFECHAT-*` | create | Codex records | 0, 3 |

---

### Task 0: Gates and plan commit (L1)

- [ ] **Step 1:**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"
cd "$WT" && [ "$(git rev-parse --show-toplevel)" = "$WT" ] && [ "$(git branch --show-current)" = fix/safe-chat-legacy-abstain ] || { echo "WRONG-WORKTREE"; exit 1; }
git fetch origin -q
git merge-base --is-ancestor 90c502a origin/main || { echo "ANCESTOR-FAIL"; exit 1; }; echo ANCESTOR-OK
git diff --quiet 90c502a origin/main -- src/backend/api/assistant.py src/backend/modules/rag.py src/backend/modules/agent/guardrails/templates.py || { echo "TRIGGER-PATHS-CHANGED: refresh anchors"; exit 1; }; echo TRIGGER-PATHS-UNCHANGED
rc=0; git grep -n -i "safechat\|SAFE-CHAT\|prohibited_advice" -- src || rc=$?
[ "$rc" = 1 ] && echo NO-COLLISION || { echo "COLLISION-OR-GREP-ERROR rc=$rc"; exit 1; }
```
Expected: `ANCESTOR-OK`, `TRIGGER-PATHS-UNCHANGED`, `NO-COLLISION`. Any other line exits nonzero → STOP.
- [ ] **Step 2:** SAFE-CHAT recorded verbatim in owner-decisions (L0 branch). Missing → STOP.
- [ ] **Step 3:** Codex plan review (≤2 rounds, `docs/reviews/2026-09-25/SAFECHAT-r<N>-{prompt.md,codex.txt,response.md}`), then commit plan + exact review paths + regenerated index (`git add --` the new files first, then `git commit … -- <exact paths>`), gated on `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`.

### Task 1: Failing tests (RED)

**Files:** create `src/backend/tests/test_safe_chat_prohibited.py`.

- [ ] **Step 1: Write the file**

```python
"""SAFE-CHAT — the legacy chat path must never return or persist an answer
that matches a prohibited medical-advice pattern.

Plan: docs/plans/2026-10-04-SAFE-CHAT-legacy-prohibited-abstain.md
Owner decision SAFE-CHAT (2026-10-04).

HC-SAFECHAT-001/002/004 drive POST /assistant/chat over HTTP through
tests/support/routes.py::route_client with a real in-memory profile DB and the
real RAGModule.validate_response; only retrieval and generation are stubbed.
"""

from __future__ import annotations

import json
import re
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import chat_session, document, model_settings, observation  # noqa: F401
from models.chat_session import ChatTurn
from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from modules.interpret_safety import InterpretationSafetyGuard
from modules.rag import RetrievedChunk, VerificationMetadata
from tests.support.routes import route_client

MARKER = "SAFECHAT-PROHIBITED-7f3a"
PROHIBITED_ANSWER = (
    "REPORT FACTS:\nYour LDL is 190 mg/dL [cite:1].\n\n"
    f"IMPLICATIONS:\nThis means you have hyperlipidemia and you should take "
    f"20 mg atorvastatin daily {MARKER}."
)
CLEAN_MARKER = "SAFECHAT-CLEAN-91b2"
CLEAN_ANSWER = (
    f"REPORT FACTS:\nYour LDL result is listed as 120 mg/dL [cite:1]. {CLEAN_MARKER}"
)


class _RecordingMasterDb:
    """Master-DB double: records added rows and commit calls."""

    def __init__(self, fail_commit: bool = False) -> None:
        self.added: list = []
        self.commits = 0
        self._fail_commit = fail_commit

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        if self._fail_commit:
            raise RuntimeError("simulated master DB failure")
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def execute(self, *_a, **_k):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result


async def _profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


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
    # Verification output carrying the answer's own claim text: a leak vector.
    rag._run_verification_pipeline = MagicMock(return_value=VerificationMetadata(
        verification_enabled=True, total_claims=1, verified_claims=0, failed_claims=1,
        claims_with_issues=[f"you have hyperlipidemia {MARKER}"],
        faithfulness_score=0.9, authority_score=0.5, verification_summary="stub",
    ))
    return rag


async def _post_chat(answer: str, master) -> tuple[object, list[ChatTurn]]:
    profile_id = "profile-a"  # route_client's default session
    profile_db, engine = await _profile_db()
    try:
        with patch.object(A, "get_rag_module", return_value=_rag(answer)), \
             patch.object(A, "is_agent_enabled", return_value=False):
            with route_client(
                assistant_router, "/assistant", profile_id=profile_id, master_db=master
            ) as client:

                async def _override_profile_db():
                    return profile_db

                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                resp = client.post("/assistant/chat", json={"question": "what is my ldl?"})
        profile_db.expire_all()
        turns = (await profile_db.execute(select(ChatTurn))).scalars().all()
        return resp, list(turns)
    finally:
        await profile_db.close()
        await engine.dispose()


def _audit_rows(master) -> list:
    return [o for o in master.added if type(o).__name__ == "AuditLog"]


@pytest.mark.asyncio
async def test_hc_safechat_001_prohibited_answer_replaced_persisted_and_audited():
    master = _RecordingMasterDb()
    resp, turns = await _post_chat(PROHIBITED_ANSWER, master)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert MARKER not in json.dumps(body), "prohibited answer text reached the client"
    assert body["full_response"] == ESCALATE_TEMPLATE
    assert [s["content"] for s in body["segments"]] == [ESCALATE_TEMPLATE]
    assert body["verification"]["issues"] == []
    assert body["is_valid"] is False
    assistant_turns = [t for t in turns if t.role == "assistant"]
    assert [t.content for t in assistant_turns] == [ESCALATE_TEMPLATE]
    assert all(MARKER not in t.content for t in turns), "prohibited answer persisted"
    rows = _audit_rows(master)
    assert len(rows) == 1 and rows[0].event_type == "assistant.prohibited_blocked"
    assert rows[0].profile_id == "profile-a"
    blob = " ".join(str(getattr(rows[0], c.name)) for c in rows[0].__table__.columns)
    assert MARKER not in blob and "what is my ldl" not in blob
    assert json.loads(rows[0].details_json) == {
        "reason": "prohibited_pattern", "decision": "escalate",
    }
    assert master.commits >= 1


@pytest.mark.asyncio
async def test_hc_safechat_002_clean_answer_untouched_and_not_audited():
    master = _RecordingMasterDb()
    resp, turns = await _post_chat(CLEAN_ANSWER, master)
    assert resp.status_code == 200, resp.text
    assert CLEAN_MARKER in resp.json()["full_response"]
    assert any(CLEAN_MARKER in t.content for t in turns if t.role == "assistant")
    assert _audit_rows(master) == []


@pytest.mark.parametrize("template", [ESCALATE_TEMPLATE, ABSTAIN_TEMPLATE])
def test_hc_safechat_003_templates_do_not_trip_prohibited_patterns(template):
    for pattern, name in InterpretationSafetyGuard.PROHIBITED_PATTERNS:
        assert not re.search(pattern, template, re.IGNORECASE), name


@pytest.mark.asyncio
async def test_hc_safechat_004_audit_failure_fails_closed():
    master = _RecordingMasterDb(fail_commit=True)
    resp, turns = await _post_chat(PROHIBITED_ANSWER, master)
    assert resp.status_code == 500
    assert MARKER not in resp.text
    assert turns == [], "a turn was persisted although the audit write failed"
```

Notes: if the `ChatTurn` role column is not `role`, read `models/chat_session.py` and use its name; never weaken an assertion. `HC-SAFECHAT-003` is parametrized (2 collected items).

- [ ] **Step 2: RED**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && { $PY -m pytest tests/test_safe_chat_prohibited.py -p no:cacheprovider -q -rf > "$LOG/red.txt" 2>&1 || true; } ; grep -E "^FAILED|passed|failed" "$LOG/red.txt"
```
Expected: **001 FAIL** (`prohibited answer text reached the client`), **004 FAIL** (status 200, not 500), **002 PASS**, **003 PASS ×2** (controls). If 001 or 004 passes → STOP.

### Task 2: Fix (GREEN) + count slots

- [ ] **Step 1: `modules/rag.py`.** In `ValidatedResponse` add, after `verification: …` (`:111`):
```python
    # SAFE-CHAT: True when a PROHIBITED_PATTERNS match fired in validate_response.
    prohibited_advice: bool = False
```
In `validate_response`, after `errors = []` (`:813`) add `prohibited_advice = False`; in the prohibited loop (`:836-839`) set it:
```python
        for pattern in self._compiled_prohibited_patterns:
            if pattern.search(response):
                errors.append("Response contains prohibited medical advice")
                prohibited_advice = True
                break
```
and pass `prohibited_advice=prohibited_advice,` in the final `ValidatedResponse(...)` (`:867-872`).
- [ ] **Step 2: `api/assistant.py`.** Add imports beside the other `core` / `modules.agent` imports:
```python
from core.audit import audit_and_commit, create_audit_log
from modules.agent.guardrails.templates import ESCALATE_TEMPLATE
```
After `validation_errors = result.validation_errors` (`:870`), inside the legacy branch, add:
```python
            # SAFE-CHAT (owner decision 2026-10-04): a prohibited-pattern match
            # must never be returned or persisted. Replace the answer with the
            # fixed escalation template the agent guard uses for advice, drop
            # verification detail (it carries claim text from the answer), and
            # audit fail-closed before the turn is written. No answer or
            # question text reaches the audit row.
            if result.prohibited_advice:
                segments = [ResponseSegment(segment_type="uncertainty", content=ESCALATE_TEMPLATE)]
                full_response = ESCALATE_TEMPLATE
                verification = VerificationInfo()
                await audit_and_commit(
                    db,
                    create_audit_log,
                    event_type="assistant.prohibited_blocked",
                    action="assistant.prohibited_blocked",
                    profile_id=session.profile_id,
                    entity_type="chat_session",
                    entity_id=chat_session.id,
                    details={"reason": "prohibited_pattern", "decision": "escalate"},
                )
```
- [ ] **Step 3: GREEN**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && rc=0; $PY -m pytest tests/test_safe_chat_prohibited.py tests/test_chat_sessions.py tests/test_agent_cache_isolation.py tests/test_audit_phi_minimization.py -p no:cacheprovider -q > "$LOG/green.txt" 2>&1 || rc=$?; tail -3 "$LOG/green.txt"; echo "$rc" > "$LOG/green.rc"; echo "rc=$rc"
```
Expected `rc=0`.
- [ ] **Step 4: Count.**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && $PY -m pytest tests/ --collect-only -q -p no:cacheprovider > "$LOG/collect.txt" 2>&1 || { tail -20 "$LOG/collect.txt"; exit 1; }; tail -1 "$LOG/collect.txt"
```
Expected start + 5 (1346 → **1351** on `90c502a`). Any other delta → STOP. Rewrite the three slots to the measured number.
- [ ] **Step 4b: Serial count slots.** If `origin/main` moved after the branch point (e.g. DDI #41, 1350, merged first): `git -C "$WT" merge origin/main` (`orchestration.md:24`), resolve the slot conflict to the number re-measured by Step 4 on the merged tree (expected 1355), regenerate the index, and re-run Task 3 Step 1. The PR body names which PR must merge first.
- [ ] **Step 5: Commit** (gated on `green.rc` = 0 and the measured number appearing in both files):
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; LOG=/tmp/claude-1000/safechat-logs; set -euo pipefail
N=$(tail -1 "$LOG/collect.txt" | grep -oE '^[0-9]+')
[ "$(cat "$LOG/green.rc")" = 0 ] && grep -q "$N backend tests collected" "$WT/CLAUDE.md" && grep -q "$N collected" "$WT/AGENT.md" \
 && git -C "$WT" add -- src/backend/tests/test_safe_chat_prohibited.py \
 && git -C "$WT" commit -m "fix(assistant): replace prohibited legacy chat answers with the escalation template

SAFE-CHAT (owner decision 2026-10-04). A legacy rag.query answer matching
a prohibited medical-advice pattern was persisted and returned with only
is_valid=False. It is now replaced with ESCALATE_TEMPLATE before persist
and return, verification detail is dropped, and a fail-closed audit row
with no answer text is written. HC-SAFECHAT-001..004.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/modules/rag.py src/backend/api/assistant.py src/backend/tests/test_safe_chat_prohibited.py CLAUDE.md AGENT.md
```

### Task 3: Verification (L1)

- [ ] **Step 1: Full suite**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rc=0; flock /tmp/claude-1000/hc-pytest.lock $PY -m pytest tests/ -p no:cacheprovider -q -rfE > "$LOG/full.txt" 2>&1 || rc=$?; tail -3 "$LOG/full.txt"; echo "pytest rc=$rc"
UNEXPECTED=$(grep -E "^(FAILED|ERROR) " "$LOG/full.txt" | grep -v "test_api_rag_index_002b" || true); [ -z "$UNEXPECTED" ] && echo FAILURES-SUBSET-OK || { echo "$UNEXPECTED"; exit 1; }
```
- [ ] **Step 2: Boot**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && $PY -c "from main import app; print('boot ok')"
```
- [ ] **Step 3: Scope:** `git diff --exit-code origin/main...HEAD -- src/backend/modules/interpret_safety.py src/backend/modules/redaction.py src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/core src/backend/modules/agent src/frontend` exits 0; `git status --short` empty.
- [ ] **Step 4: Break-it** in a disposable detached worktree; the phase worktree is never edited:
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/safechat-logs; mkdir -p "$LOG"
BK=/mnt/c/Users/DangT/Documents/GitHub/hc-safechat-break
[ ! -e "$BK" ] || { echo "BK exists"; exit 1; }
git -C "$WT" worktree add --detach "$BK" HEAD && cd "$BK/src/backend" && [ "$(git rev-parse HEAD)" = "$(git -C "$WT" rev-parse HEAD)" ]
grep -n "if result.prohibited_advice:\|verification = VerificationInfo()\|prohibited_advice = True" api/assistant.py modules/rag.py
# apply ONE break below with the editor/sed at the printed line, then:
$PY -m pytest tests/test_safe_chat_prohibited.py -p no:cacheprovider -q -rf | grep -E "^FAILED|passed|failed"
git -C "$BK" checkout -- . && git -C "$BK" status --short   # empty before the next break
# after the last break:
cd / && git -C "$WT" worktree remove --force "$BK" && git -C "$WT" status --short
```
  - BI-1: delete the `if result.prohibited_advice:` block → 001 and 004 FAIL.
  - BI-2: delete `verification = VerificationInfo()` → 001 FAIL (issues carry the marker).
  - BI-3: move the block after `_append_turns(...)`/`commit` → 001 FAIL (persisted) or 004 FAIL.
  - BI-4: delete `prohibited_advice = True` in `rag.py` → 001 FAIL.
- [ ] **Step 5:** Codex adversarial diff review; execution record; commit (plan, index, `SAFECHAT-diff-codex.txt`); PR.

## Stop gates

- 001 or 004 passes in Task 1 Step 2.
- Any edit needed in an ask-first file (incl. `core/audit.py`) or outside [Files](#files).
- Collected delta ≠ +5.
- The owner chooses a template that does not exist, or new copy.
- A reviewer finding requires the agent path, cache or interpretations route (report as owner items).

## Recurring-failures recheck

| § | Check |
|---|---|
| 1 | 001/004 RED first; break-its BI-1…4; route test through HTTP; the real `validate_response` runs (only retrieval/generation stubbed) |
| 2 | the replacement runs before persist; audit failure path pinned (004); clean path pinned (002) |
| 3 | count measured |
| 8 | "abstain/fallback template" read against the real templates; the choice and its reason are recorded above |
| 9 | the same rule is enforced at one site only: agent path and interpretations route reported as owner items |

## Rollback

`git revert <fix sha>`. No schema, no data migration; persisted escalation turns stay as ordinary turns.

## Execution record

Executed 2026-10-04 by Wave 3 L1-A (L2 implementer `sonnet` for Tasks 1-2 and review loop 1; L1 for Tasks 0 and 3). D9 venv, `HF_HUB_OFFLINE=1`.

| Step | Result |
|---|---|
| Task 0 | `ANCESTOR-OK`, `TRIGGER-PATHS-UNCHANGED`, grep rc=1 (no collision); plan commit `ba5a2e0` |
| Task 1 RED | `2 failed, 3 passed` (001, 004 FAIL) |
| Task 2 GREEN | 4 files: `59 passed`, rc=0; fix commit `f5961e7` |
| Count | `1351 tests collected` (L1 re-measured; +5 from 1346). Slots `CLAUDE.md:30,:35`, `AGENT.md:76` |
| Review loop 1 | `45c15a9`: `core.audit` import regrouped; 001 asserts `citations == []` (code-reviewer MINOR-1/2) |
| Full suite at `f5961e7` (flock) | `1351 passed, 63 warnings in 171.23s`, rc=0, `FAILURES-SUBSET-OK` |
| Re-check at `45c15a9` | collect `1351`; safe-chat + chat_sessions + cache isolation + audit + `tests/agent`: `142 passed`; `boot ok` |
| Scope | `SCOPE-OK` (ask-first modules, `core/`, `modules/agent/`, `src/frontend` unchanged) |
| BI-1 block removed | 001, 004 FAIL |
| BI-2 `verification = VerificationInfo()` removed (`api/assistant.py:882`) | 001 FAIL |
| BI-3 block moved after the turn commit | 001, 004 FAIL |
| BI-4 `prohibited_advice = True` removed (`modules/rag.py:842`) | 001, 004 FAIL |
| restore | `5 passed`; break worktree removed |

**Reviews.** code-reviewer (opus) APPROVE, 4 MINOR (2 fixed in loop 1; `validation_errors` vs reset verification is cosmetic; test double has no rollback model) plus the template question for the owner. security-reviewer (opus) APPROVE; 2 HIGH, 1 MEDIUM, 2 LOW pre-existing, 1 LOW introduced (cosmetic `validation_errors`). Codex plan r1 REVISE (5 MAJOR, procedural; dispositions in `SAFECHAT-r1-response.md`). Codex diff (`SAFECHAT-diff-codex.txt`) needs-attention, 1 high: the no-model knowledge fallback is not gated. **Rejected for this PR:** that fallback returns fixed seeded reference text, not a model answer (`api/assistant.py:1380`, `scripts/seed_knowledge_base.py:376`); the match ("when you have a cut") is a pattern false positive, and replacing reference text widens the decision. Reported as owner item SAFE-CHAT-FALLBACK.
