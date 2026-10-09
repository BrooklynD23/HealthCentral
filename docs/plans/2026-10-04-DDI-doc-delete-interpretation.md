# DDI — Document Delete With an Interpretation — Implementation Plan

**Last Updated:** 2026-10-04
**Owner:** repository owner
**Refresh Trigger:** any commit to `src/backend/api/documents.py::delete_document`, `src/backend/models/observation.py` or `src/backend/models/interpretation.py` before this plan runs; P6 (FK pragma listeners) landing first.
**Prerequisites:** `origin/main` contains `90c502a` (Waves 0-2 merged). D9 venv `~/venvs/asclexis-311` exists.
**Status:** PROPOSED — not executed. Wave 3, L1-A, phase 1.
**Review:** Codex round 1 REVISE (2 BLOCKER, 3 MAJOR); round 2 REVISE (1 BLOCKER, 8 MAJOR, 1 MINOR). All round-2 findings resolved in this text except one rejection (merge vs rebase); dispositions in `docs/reviews/2026-09-25/DDI-r1-response.md` and `DDI-r2-response.md`. Round 2 was the last round allowed.

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `DELETE /documents/{id}` succeeds for a document whose observation has a `LabInterpretation`: the document, its observations, their interpretations, chunks, entities and categories are deleted, the encrypted file is removed, the audit row is written — and the file is never destroyed when the database commit fails. Unchanged and retained by design: care-plan tasks (provenance and quote cleared, CARE-QUOTE-001) and `PanelInterpretation` rows (see Out of scope 2).

**Architecture:** Two edits, no schema change.
- **A. ORM cascade.** `Observation.interpretation` gets `cascade="all, delete"`. The existing `Document.observations` cascade (`models/document.py:73-77`, `"all, delete-orphan"`) then reaches the interpretation, so the ORM deletes it instead of nulling its NOT NULL `observation_id`.
- **B. Unlink after commit.** In `delete_document`, the `doc_path.unlink()` block moves from before `profile_db.commit()` to after it. A failed unlink after a successful commit is logged (no path, no filename) and does not stop the audit row.

**Tech Stack:** Python 3.11 (D9 venv), SQLAlchemy 2.x async ORM, FastAPI `TestClient` via `src/backend/tests/support/routes.py::route_client`, pytest + pytest-asyncio.

**Spec:** owner gate **W3-SEC-SCHED** (verbatim, `docs/capstone-report/owner-decisions-2026-09-27.md` row W3-SEC-SCHED, 2026-10-04): "DOC-DELETE-INTERP, RECOVERY-CODE-CACHE. Both get a plan, then a fix phase, in Wave 3. DOC-DELETE-INTERP: ORM cascade + unlink after commit + HTTP test, Codex plan + diff review." Finding text: `docs/capstone-report/implementation-program.md:467` (program owner item DOC-DELETE-INTERP).

## Global Constraints

- **Target Python 3.11.** No 3.12-only syntax. No new timestamps.
- **No schema change, no migration.** No `ForeignKey(..., ondelete=...)` edit, no column change, no file under `src/backend/migrations/`. A design that needs one is a **STOP** (owner gate; dual-migration invariant).
- **Ask-first files are read-only:** `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, `core/security.py`, `core/profile_database.py`, `core/encryption*`.
- **Surgical edits.** Only the hunks in [Files](#files). No reformatting. The reprocess path (`api/documents.py:627-630`) is **not** touched (see [Out of scope](#out-of-scope-reported-not-fixed)).
- **Route tests go through HTTP** (`route_client`), with a real in-memory per-profile DB, as `HC-CAREQ-004` does (`tests/test_documents_api.py:758-837`).
- **Tests never write outside `tmp_path`.** Every new test monkeypatches `settings.app_data_path` to `tmp_path`, as `HC-CAREQ-004` does.
- **Docs that are not edited.** `docs/compliance/data-privacy.md` is owner-gated (W-10 owns it). `docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md` is a historical audit. Neither is edited; Task 3 records their truth value.
- **Count slots (SLOT-RULE).** The commit that changes the collected count rewrites `CLAUDE.md:30`, `CLAUDE.md:35` and `AGENT.md:76` (the collected number only) to the measured `--collect-only` figure. The `AGENT.md:76` pass-count clause is left as is (program item AGENT-PASS-LINE).
- **Staging:** explicit pathspecs only. Never `git add -A`, never `git reset`.
- **Shell:** every bash block is self-contained and starts with `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"`. Test output is saved in full to `$LOG/<step>.txt` before it is tailed. Each commit is chained with `&&` behind the check it depends on. Full backend suites run under `flock /tmp/claude-1000/hc-pytest.lock` (12 GB host).
- **Serial count slots (`docs/agentic/orchestration.md:24`, `implementation-program.md:137-139`).** `CLAUDE.md` / `AGENT.md` slots, `docs/INDEX.md` and `docs/_link_graph.json` are shared with every open PR. If `origin/main` moves before merge: bring the branch up to date (`git merge origin/main`, the current orchestration rule: "each PR after the first merges `origin/main`, re-measures and rewrites the count slots"), regenerate the index, re-measure `--collect-only`, rewrite the slots to the new measured number, re-run Task 3 Step 1.
- **`docs/agentic/recurring-failures.md` is not edited by this phase.** W3-SEC-SCHED does not name it (Codex r2 BLOCKER). The §9 evidence paragraph is proposed to L0 in the wave report instead; L0/owner decides where it lands.

## Review Focus

1. **The commit fails** (disk full, locked vault, IntegrityError from a future child table). Expected: the encrypted file is still on disk, the document row survives, no audit row. Pinned by **HC-DDI-002**.
2. **The unlink fails after a successful commit** (Windows file lock, permission). Expected: rows are gone, response 2xx, audit row written, the failure is logged without the path. Pinned by **HC-DDI-003**.
3. **Interpretation creation keeps working** after the cascade change: `modules/interpret.py:254` and `:1010` create `LabInterpretation(observation_id=...)` without setting the relationship. A `delete-orphan` cascade could treat such an object as an orphan. Expected: creation by FK alone still flushes. Pinned by **HC-DDI-004**; this is why the plan uses `"all, delete"`, not `"all, delete-orphan"`.
4. **Another document's interpretation in the same profile** is untouched. Pinned inside **HC-DDI-001** (a second document with its own interpretation survives). Cross-profile isolation is structural (one SQLCipher vault per profile via `ProfileDbSession`) and not re-tested here.
5. **A document with no interpretation** (the common case) still deletes exactly as before. Pinned by the existing `HC-CAREQ-004`, `HC-ENT-030`, `HC-PIN-011` staying green.

---

## Finding (re-verified on `origin/main@90c502a`, 2026-10-04)

| # | Fact | Evidence |
|---|---|---|
| 1 | `Observation.interpretation` has no `cascade=` | `src/backend/models/observation.py:106-108` @90c502a |
| 2 | `lab_interpretations.observation_id` is NOT NULL, `ondelete="CASCADE"` (DB level only) | `src/backend/models/interpretation.py:50-56` @90c502a |
| 3 | SQLite FK enforcement is off, so `ondelete` is inert | `grep -rn foreign_keys src/backend --include=*.py \| grep -v tests` → one comment only (`api/profiles.py:914`); recurring-failures §8 |
| 4 | `Document.observations` cascades to observations through the ORM | `src/backend/models/document.py:73-77` `cascade="all, delete-orphan"` |
| 5 | The file is unlinked **before** the commit | `src/backend/api/documents.py:1871-1875` (unlink at `:1875`) vs `:1878-1879` (`delete`, `commit`) |
| 6 | The audit row is written only after the profile commit | `src/backend/api/documents.py:1881-1889` |
| 7 | **Measured RED (L1 probe, 2026-10-04, D9 venv, unmodified 90c502a):** delete a document whose observation has a `LabInterpretation` through `AsyncSession.delete` + `commit` | `IntegrityError (sqlite3.IntegrityError) NOT NULL constraint failed: lab_interpretations.observation_id`; after rollback `documents 1, observations 1, lab_interpretations 1` |
| 8 | **Measured GREEN (same probe, `cascade="all, delete"` applied, then reverted):** | `delete commit ok`; `documents 0, observations 0, lab_interpretations 0`; creation by `observation_id` alone: `ok`. Same result with `"all, delete-orphan"` (measured), which the plan still does not use (Review Focus 3) |
| 9 | **Plan pre-validated (L1, 2026-10-04, throwaway detached worktree of 90c502a, since removed):** Task 1 test code appended verbatim, then Task 2 code applied verbatim. Commands: `HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_documents_api.py -k HC_DDI -p no:cacheprovider -q -rf` (fix stashed) and `... -m pytest tests/test_documents_api.py -p no:cacheprovider -q` (fix applied), from `src/backend`. Facts 7-8 came from a scratch probe script (not committed); HC-DDI-001/004 reproduce them in-repo | without the fix: `-k HC_DDI` → `4 failed`; with it: `tests/test_documents_api.py` → `19 passed`. A first draft read ORM attributes after `expire_all()` and raised `MissingGreenlet`; the tests below capture ids as plain strings first |

So today, on the route: the file is destroyed (fact 5), then the commit raises (fact 7) → HTTP 500; the document row, its entity rows, its care-task quote and the interpretation all survive; no audit row (fact 6). The user is left with a document entry whose file is gone.

## Approval scope

Covered by **W3-SEC-SCHED** (quoted in Spec): ORM cascade, unlink after commit, HTTP test. Codex plan + diff review.

**Not licensed:**
1. Any `ondelete` / FK / column / migration change (STOP; owner gate).
2. The reprocess path `api/documents.py:627-630` (core `delete(Observation)`; see Out of scope).
3. `PanelInterpretation` cleanup (see Out of scope).
4. Edits to `docs/compliance/*`, the program, the matrix or `owner-decisions`.
5. Any ask-first file.

## Files

| File | Action | Hunk | Task |
|---|---|---|---|
| `src/backend/tests/test_documents_api.py` | modify | append HC-DDI-001…004 at end of file | 1 |
| `src/backend/models/observation.py` | modify | `:106-108`, add `cascade="all, delete"` | 2 |
| `src/backend/api/documents.py` | modify | `:1871-1879` only (move unlink after commit, guard OSError) | 2 |
| `CLAUDE.md`, `AGENT.md` | modify | collected-count slots `CLAUDE.md:30,:35`, `AGENT.md:76` | 2 |
| `docs/plans/2026-10-04-DDI-doc-delete-interpretation.md` (this file) | modify | "Execution record" only | 3 |
| `docs/INDEX.md`, `docs/_link_graph.json` | regenerate | generator output only | 0, 3 |
| `docs/reviews/2026-09-25/DDI-r<N>-{prompt,codex,response}.md` | create | Codex review records | 0 |

Read-only and asserted unchanged in Task 3: `src/backend/migrations/`, `src/backend/models/interpretation.py`, `src/backend/models/document.py`, `src/backend/core/`, `src/backend/modules/`, `docs/compliance/`.

---

### Task 0: Gate and ancestry checks (L1; no code)

- [ ] **Step 1: ancestry + refresh trigger**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT" && git fetch origin -q && git merge-base --is-ancestor 90c502a origin/main && echo ANCESTOR-OK
git -C "$WT" diff --quiet 90c502a origin/main -- src/backend/api/documents.py src/backend/models/observation.py src/backend/models/interpretation.py src/backend/models/document.py src/backend/tests/test_documents_api.py src/backend/core/database.py src/backend/core/profile_database.py && echo TRIGGER-PATHS-UNCHANGED
```
Expected: `ANCESTOR-OK` and `TRIGGER-PATHS-UNCHANGED`. `core/database.py` / `core/profile_database.py` are P6's FK-listener files (`implementation-program.md:154`); if P6 landed, `PRAGMA foreign_keys=ON` changes delete semantics. If any trigger path changed on `origin/main`, STOP: refresh this plan's line anchors and its Finding table against the new base before any task runs.
- [ ] **Step 2:** Confirm W3-SEC-SCHED is recorded verbatim in owner-decisions (L0 branch `docs/wave3-close`). Missing → STOP.
- [ ] **Step 3:** Codex plan review (≤2 rounds). Amendments are committed as the first commit on the branch, together with this plan, the review records and the regenerated index. The plan and review files are new, so they are staged explicitly first:
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT" && python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph \
  && git add -- docs/plans/2026-10-04-DDI-doc-delete-interpretation.md docs/reviews/2026-09-25/DDI-r1-prompt.md docs/reviews/2026-09-25/DDI-r1-codex.txt docs/reviews/2026-09-25/DDI-r1-response.md \
  && git add -- docs/reviews/2026-09-25/DDI-r2-prompt.md docs/reviews/2026-09-25/DDI-r2-codex.txt docs/reviews/2026-09-25/DDI-r2-response.md \
  && git commit -m "docs(ddi): plan for document delete with an interpretation" -- docs/plans/2026-10-04-DDI-doc-delete-interpretation.md docs/INDEX.md docs/_link_graph.json docs/reviews/2026-09-25/DDI-r1-prompt.md docs/reviews/2026-09-25/DDI-r1-codex.txt docs/reviews/2026-09-25/DDI-r1-response.md docs/reviews/2026-09-25/DDI-r2-prompt.md docs/reviews/2026-09-25/DDI-r2-codex.txt docs/reviews/2026-09-25/DDI-r2-response.md
```
- [ ] **Step 4:** `git -C "$WT" ls-files docs/plans/2026-10-04-DDI-*.md` prints the plan path. Empty → STOP.

### Task 1: Failing tests (RED)

**Files:** Modify `src/backend/tests/test_documents_api.py` (append at end).

**Interfaces:** Consumes existing helpers in that file: `entity_profile_db` fixture (`:547`), `_pin_cleanup_document(profile_id)` (`:447`), `_CommitTrackingMasterDb` (`:743`, `.added`, `.commit_snapshots`), `route_client`, `get_profile_db_session`, `documents_router`, `documents_api`.

- [ ] **Step 1: Append the tests**

```python
# ---------------------------------------------------------------------------
# DOC-DELETE-INTERP (plan docs/plans/2026-10-04-DDI-doc-delete-interpretation.md)
# ---------------------------------------------------------------------------

from sqlalchemy import func  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from models import LabInterpretation, Observation  # noqa: E402


def _ddi_observation(profile_id: str, doc_id: str) -> Observation:
    return Observation(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        doc_id=doc_id,
        analyte_canonical="hemoglobin",
        analyte_raw="Hgb",
        value=14.2,
    )


def _ddi_interpretation(profile_id: str, observation_id: str) -> LabInterpretation:
    # Built by FK only, exactly as modules/interpret.py:254 and :1010 do.
    return LabInterpretation(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        observation_id=observation_id,
        interpretation_text="DDI interpretation text",
        severity_level="normal",
        citations_json="[]",
        model_id="template",
        model_tier="template",
        confidence_score=0.85,
    )


def _ddi_vault_file(tmp_path: Path, profile_id: str, document_id: str) -> Path:
    docs = tmp_path / "vaults" / profile_id / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    path = docs / f"{document_id}.bin"
    path.write_bytes(b"ciphertext")
    return path


async def _ddi_count(db, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for clause in where:
        stmt = stmt.where(clause)
    return (await db.execute(stmt)).scalar_one()


def _ddi_delete_over_http(profile_db, master, document_id: str, profile_id: str):
    with route_client(
        documents_router, "/documents", profile_id=profile_id, master_db=master
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.delete(f"/documents/{document_id}")


@pytest.mark.asyncio
async def test_HC_DDI_001_delete_document_with_interpretation_over_http(
    entity_profile_db, monkeypatch, tmp_path
):
    """HC-DDI-001. A document whose observation has a LabInterpretation must
    delete over HTTP: 2xx, document/observation/interpretation rows gone, the
    encrypted file gone, one committed document.delete audit row. Another
    document's interpretation must survive."""
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    other = _pin_cleanup_document(profile_id)
    obs = _ddi_observation(profile_id, document.id)
    other_obs = _ddi_observation(profile_id, other.id)
    entity_profile_db.add_all([document, other, obs, other_obs])
    await entity_profile_db.commit()
    entity_profile_db.add_all([
        _ddi_interpretation(profile_id, obs.id),
        _ddi_interpretation(profile_id, other_obs.id),
    ])
    await entity_profile_db.commit()
    # Plain strings: after expire_all() an ORM attribute read would lazy-load
    # synchronously and raise MissingGreenlet under AsyncSession.
    doc_id, obs_id, other_obs_id = document.id, obs.id, other_obs.id
    vault_file = _ddi_vault_file(tmp_path, profile_id, doc_id)

    master = _CommitTrackingMasterDb()
    resp = _ddi_delete_over_http(entity_profile_db, master, doc_id, profile_id)
    assert 200 <= resp.status_code < 300, resp.text

    entity_profile_db.expire_all()
    assert await _ddi_count(entity_profile_db, Document, Document.id == doc_id) == 0
    assert await _ddi_count(entity_profile_db, Observation, Observation.doc_id == doc_id) == 0
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == obs_id
    ) == 0, "interpretation outlived its observation"
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == other_obs_id
    ) == 1, "another document's interpretation was deleted"
    assert not vault_file.exists(), "encrypted file survived a successful delete"

    audit = [o for o in master.added if type(o).__name__ == "AuditLog"]
    assert len(audit) == 1 and audit[0].event_type == "document.delete"
    assert audit[0].entity_id == doc_id
    assert master.commit_snapshots and master.commit_snapshots[-1] >= 1


@pytest.mark.asyncio
async def test_HC_DDI_002_failed_commit_keeps_encrypted_file(
    entity_profile_db, monkeypatch, tmp_path
):
    """HC-DDI-002. If the profile-DB commit fails, the encrypted file must
    still be on disk, the document row must survive, and no audit row may be
    written. Today the file is unlinked before the commit."""
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    entity_profile_db.add(document)
    await entity_profile_db.commit()
    doc_id = document.id  # plain string; rollback() expires the ORM object
    vault_file = _ddi_vault_file(tmp_path, profile_id, doc_id)

    async def _failing_commit():
        raise OperationalError("COMMIT", {}, Exception("simulated disk I/O error"))

    monkeypatch.setattr(entity_profile_db, "commit", _failing_commit)
    master = _CommitTrackingMasterDb()
    with pytest.raises(OperationalError):
        _ddi_delete_over_http(entity_profile_db, master, doc_id, profile_id)

    monkeypatch.undo()  # restores commit and app_data_path
    await entity_profile_db.rollback()
    assert vault_file.exists(), "encrypted file destroyed although the commit failed"
    assert await _ddi_count(entity_profile_db, Document, Document.id == doc_id) == 1
    assert not [o for o in master.added if type(o).__name__ == "AuditLog"]


@pytest.mark.asyncio
async def test_HC_DDI_003_unlink_failure_after_commit_still_audits(
    entity_profile_db, monkeypatch, tmp_path
):
    """HC-DDI-003. If the rows are committed but the file cannot be removed
    (Windows lock, permissions), the request still succeeds, the audit row is
    written, and the log line carries neither the path nor the filename."""
    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    entity_profile_db.add(document)
    await entity_profile_db.commit()
    doc_id, doc_source = document.id, document.source  # plain strings (expire_all below)
    vault_file = _ddi_vault_file(tmp_path, profile_id, doc_id)

    def _locked_unlink(self, *args, **kwargs):
        raise PermissionError(13, "locked", str(self))

    monkeypatch.setattr(Path, "unlink", _locked_unlink)
    warnings: list[str] = []
    monkeypatch.setattr(
        documents_api.logger, "warning",
        lambda msg, *a, **k: warnings.append(msg % a if a else msg),
    )
    master = _CommitTrackingMasterDb()
    resp = _ddi_delete_over_http(entity_profile_db, master, doc_id, profile_id)
    assert 200 <= resp.status_code < 300, resp.text

    entity_profile_db.expire_all()
    assert await _ddi_count(entity_profile_db, Document, Document.id == doc_id) == 0
    assert vault_file.exists()  # unlink was blocked
    audit = [o for o in master.added if type(o).__name__ == "AuditLog"]
    assert len(audit) == 1 and audit[0].event_type == "document.delete"
    assert warnings, "a failed unlink after commit must be logged"
    joined = " ".join(warnings)
    assert str(tmp_path) not in joined and doc_source not in joined


@pytest.mark.asyncio
async def test_HC_DDI_004_interpretation_created_by_fk_still_flushes(entity_profile_db):
    """HC-DDI-004. modules/interpret.py builds LabInterpretation with
    observation_id only. The cascade added for DDI must not make such an
    object an orphan on flush."""
    profile_id = "profile-a"
    document = _pin_cleanup_document(profile_id)
    obs = _ddi_observation(profile_id, document.id)
    entity_profile_db.add_all([document, obs])
    await entity_profile_db.commit()
    obs_id = obs.id  # plain string (expire_all below)
    entity_profile_db.add(_ddi_interpretation(profile_id, obs_id))
    await entity_profile_db.commit()
    entity_profile_db.expire_all()
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == obs_id
    ) == 1
    # And the ORM delete of the observation now reaches it.
    loaded = (await entity_profile_db.execute(
        select(Observation).where(Observation.id == obs_id)
    )).scalar_one()
    await entity_profile_db.delete(loaded)
    await entity_profile_db.commit()
    assert await _ddi_count(
        entity_profile_db, LabInterpretation, LabInterpretation.observation_id == obs_id
    ) == 0
```

Notes for the implementer: `select`, `uuid`, `Path`, `pytest`, `Document` are already imported in the file. If `LabInterpretation` / `Observation` are not exported by `models/__init__.py`, import them from `models.interpretation` / `models.observation` instead. If `logger.warning` in Task 2 is called with a different format style, adapt the HC-DDI-003 capture lambda only — never weaken its two assertions.

- [ ] **Step 2: Run, observe RED**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && { $PY -m pytest tests/test_documents_api.py -k HC_DDI -p no:cacheprovider -q -rf > "$LOG/red.txt" 2>&1 || true; } ; grep -E "^FAILED|^E  |passed|failed" "$LOG/red.txt" | tail -30
```
Expected: **001 FAIL** (`IntegrityError ... NOT NULL constraint failed: lab_interpretations.observation_id`), **002 FAIL** (`encrypted file destroyed although the commit failed`), **003 FAIL** (the `PermissionError` escapes before commit → raised through TestClient), **004 FAIL** at the final count (`1 != 0`, or the same IntegrityError on the observation delete). Any test passing here → STOP (it cannot detect the defect).
- [ ] **Step 3:** do not commit yet (Task 2 commits tests + fix together so every commit is green).

### Task 2: Fix (GREEN) + count slots

**Files:** `src/backend/models/observation.py:106-108`, `src/backend/api/documents.py:1871-1879`, `CLAUDE.md:30,:35`, `AGENT.md:76`.

- [ ] **Step 1: ORM cascade** — `models/observation.py`:
```python
    interpretation: Mapped[Optional["LabInterpretation"]] = relationship(
        "LabInterpretation",
        back_populates="observation",
        uselist=False,
        # DOC-DELETE-INTERP: lab_interpretations.observation_id is NOT NULL and
        # SQLite FK enforcement is off, so the DB-level ondelete is inert. Without
        # this the ORM nulls the FK on observation delete -> IntegrityError.
        # Not delete-orphan: modules/interpret.py creates rows by FK alone.
        cascade="all, delete",
    )
```
- [ ] **Step 2: Unlink after commit** — replace `api/documents.py:1871-1879` with:
```python
    # Delete document record from profile database (cascades to observations,
    # their interpretations, and chunks)
    await profile_db.delete(document)
    await profile_db.commit()

    # DOC-DELETE-INTERP: remove the encrypted file only after the rows are
    # committed. A failed commit must never leave a document row whose file
    # is already gone. A failed unlink here leaves only ciphertext under the
    # profile's own vault (swept by profile deletion); log it without the path
    # and still write the audit row below.
    vault_path = Path(settings.app_data_path) / "vaults" / profile_id / "docs"
    doc_path = vault_path / f"{document_id}.bin"
    try:
        if doc_path.exists():
            doc_path.unlink()
    except OSError as exc:
        logger.warning(
            "Document %s deleted but its encrypted file could not be removed: %s",
            document_id,
            type(exc).__name__,
        )
```
- [ ] **Step 3: GREEN**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && rc=0; $PY -m pytest tests/test_documents_api.py -p no:cacheprovider -q > "$LOG/green.txt" 2>&1 || rc=$?; tail -5 "$LOG/green.txt"; echo "rc=$rc"; echo "$rc" > "$LOG/green.rc"
```
Expected: all tests in the file pass (the 4 new plus every existing one).
- [ ] **Step 4: Collected count** — measure, then rewrite the three slots to the printed number (expected 1346 + 4 = **1350**; any other number → STOP and report):
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && $PY -m pytest tests/ --collect-only -q -p no:cacheprovider > "$LOG/collect.txt" 2>&1; tail -1 "$LOG/collect.txt"
```
- [ ] **Step 5: Commit** (only after Step 3 printed `rc=0` and Step 4 printed `1350 tests collected`)
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
[ "$(cat "$LOG/green.rc")" = 0 ] && tail -1 "$LOG/collect.txt" | grep -q "^1350 tests collected" && grep -q "1350" "$WT/CLAUDE.md" && grep -q "1350 collected" "$WT/AGENT.md" && git -C "$WT" commit -m "fix(documents): cascade interpretations and unlink file after commit on delete

DOC-DELETE-INTERP (owner gate W3-SEC-SCHED). Deleting a document whose
observation has a LabInterpretation raised IntegrityError (HTTP 500) after
the encrypted file had already been unlinked. Observation.interpretation
now cascades through the ORM; the file is removed only after the profile
commit. Tests HC-DDI-001..003 drive DELETE over HTTP via route_client;
HC-DDI-004 pins that interpretation creation by FK alone still flushes.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/models/observation.py src/backend/api/documents.py src/backend/tests/test_documents_api.py CLAUDE.md AGENT.md
```

### Task 3: Verification and execution record (L1 runs the acceptance)

- [ ] **Step 1: Full suite** (one at a time on this host):
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rc=0; flock /tmp/claude-1000/hc-pytest.lock $PY -m pytest tests/ -p no:cacheprovider -q -rfE > "$LOG/full.txt" 2>&1 || rc=$?; tail -3 "$LOG/full.txt"; echo "pytest rc=$rc"
UNEXPECTED=$(grep -E "^(FAILED|ERROR) " "$LOG/full.txt" | grep -v "test_api_rag_index_002b" || true); [ -z "$UNEXPECTED" ] && echo "FAILURES-SUBSET-OK" || { echo "$UNEXPECTED"; exit 1; }
```
Acceptance: collected = 1350; failures ⊆ {`test_api_rag_index_002b`} (environmental; never lower its 0.7 threshold).
- [ ] **Step 2: Boot:**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT/src/backend" && $PY -c "from main import app; print('boot ok')"
```
- [ ] **Step 3: Scope** (lists only [Files](#files); the second command exits 0; status is empty):
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT" && git diff --stat origin/main...HEAD
git -C "$WT" diff --exit-code origin/main...HEAD -- src/backend/migrations src/backend/models/interpretation.py src/backend/models/document.py src/backend/core src/backend/modules docs/compliance docs/agentic && echo SCOPE-OK
git -C "$WT" status --short
```
- [ ] **Step 4: Break-it** (at the PR head, by line number; restore with `git checkout`; every command from `cd "$WT/src/backend"` with the header above; run `$PY -m pytest tests/test_documents_api.py -k HC_DDI -p no:cacheprovider -q -rf` after each break):
  - BI-1: `grep -n 'cascade="all, delete"' src/backend/models/observation.py` → delete that line → HC-DDI-001 and 004 must FAIL.
  - BI-2: `grep -n "doc_path.unlink()" src/backend/api/documents.py` → move the unlink block back above `await profile_db.delete(document)` → HC-DDI-002 must FAIL.
  - BI-3: remove the `try/except OSError` (keep the unlink) → HC-DDI-003 must FAIL.
  - After each: `git -C "$WT" checkout -- src/backend/models/observation.py src/backend/api/documents.py`, `git -C "$WT" status --short` empty.
- [ ] **Step 5: recurring-failures §9 — proposed, not edited.** `CLAUDE.md:49-52` asks for new instances to be recorded "in the same commit", but W3-SEC-SCHED does not name `recurring-failures.md` (Codex r2 BLOCKER). The conservative choice is to leave the file alone and put this proposed paragraph in the L1 wave report for L0/owner: "the `Document → Observation` ORM cascade stopped one level short; `LabInterpretation` (NOT NULL FK, inert `ondelete`) turned every delete of an interpreted document into an IntegrityError after the file had already been unlinked; found by security review on PR #24, fixed by DDI. Recheck: when a parent's ORM cascade is relied on, walk every grandchild with a NOT NULL FK."
- [ ] **Step 6: Docs truth value** (no edit; record in Execution record): `docs/compliance/data-privacy.md:183-195` and `docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md:56,59`.
- [ ] **Step 7: Commit**
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-ddi; PY="$HOME/venvs/asclexis-311/bin/python"; export HF_HUB_OFFLINE=1; set -euo pipefail; LOG=/tmp/claude-1000/ddi-logs; mkdir -p "$LOG"
cd "$WT" && python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph \
  && git -C "$WT" commit -m "docs(ddi): execution record

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- docs/plans/2026-10-04-DDI-doc-delete-interpretation.md docs/INDEX.md docs/_link_graph.json
```
- [ ] **Step 8:** Codex adversarial diff review, then open the PR (base `main`).

## Stop gates

- Any HC-DDI test passes in Task 1 Step 2 (cannot detect the defect).
- The fix needs an `ondelete`, FK, column or migration change.
- The collected count after Task 2 is not 1350.
- Any existing test in `tests/test_documents_api.py` or the full suite newly fails.
- Any edit is needed in an ask-first file or outside [Files](#files).
- A Codex or reviewer finding requires widening scope (e.g. the reprocess path).

## Recurring-failures recheck

| § | Applies how | Check |
|---|---|---|
| 1 green suite that cannot fail | new tests must go RED on 90c502a | Task 1 Step 2 + break-its BI-1…3 |
| 2 fix creates the next bug | moving unlink after commit opens "commit ok, unlink fails" | HC-DDI-003; logs without path |
| 3 asserted figures | count 1350 is a prediction | Task 2 Step 4 measures |
| 5 contaminated tree | suite in the phase worktree only | Task 3 Step 3 `status --short` |
| 8 stale guidance | `data-privacy.md:185`, `sql-fk-001:56,59` | Task 3 Step 6 records truth value |
| 9 invariant at one site | reprocess core `delete(Observation)`, `PanelInterpretation` | reported in Out of scope, not fixed |

## Out of scope (reported, not fixed)

1. **REPROCESS-INTERP-ORPHAN (new):** `api/documents.py:627-630` deletes observations with a core `delete(Observation)` on reprocess with `refresh_existing`. Core deletes bypass ORM cascade, and FK enforcement is off, so every `LabInterpretation` of the old observations survives as an orphan row (PHI-derived text, `observation_id` pointing at nothing), still listed by `GET /interpretations` (`api/interpretations.py:631-633`, filters by `profile_id` only). Recurring-failures §9 shape. Owner item.
2. **PANEL-INTERP-STALE (new):** `PanelInterpretation.observation_ids_json` (`models/interpretation.py:159`) is a JSON list, not an FK; panel interpretations naming deleted observations survive document delete. Owner item.

## Rollback

`git revert <fix sha>` restores both edits and the tests together (one commit). No data migration exists to undo; the ORM cascade change has no on-disk effect.

## Execution record

Executed 2026-10-04 by Wave 3 L1-A (L2 implementer `sonnet` for Tasks 1-2; L1 for Task 0 and Task 3). D9 venv, `HF_HUB_OFFLINE=1`.

| Step | Command | Result |
|---|---|---|
| Task 0 Step 1 | ancestry + trigger-path diff vs `90c502a` | `ANCESTOR-OK`, `TRIGGER-PATHS-UNCHANGED` (origin/main = `90c502a`) |
| Task 0 Step 3 | plan commit | `6d76498` |
| Task 1 Step 2 RED | `pytest tests/test_documents_api.py -k HC_DDI -q -rf` | `4 failed, 15 deselected` (001/004 `IntegrityError … lab_interpretations.observation_id`; 002 `encrypted file destroyed although the commit failed`; 003 `PermissionError`) |
| Task 2 Step 3 GREEN | `pytest tests/test_documents_api.py -q` | `19 passed`, rc=0 |
| Task 2 Step 4 | `pytest tests/ --collect-only -q` | before `1346 tests collected`; after `1350 tests collected` |
| Task 2 Step 5 | fix commit | `73ae541` |
| Task 3 Step 1 | full suite under flock | `1350 passed, 67 warnings in 724.08s`, `pytest rc=0`, `FAILURES-SUBSET-OK` (`test_api_rag_index_002b` passed in this environment) |
| Task 3 Step 2 | boot | `boot ok` |
| Task 3 Step 3 | scope | `SCOPE-OK`; `git status --short` empty |
| Task 3 Step 4 BI-1 | `cascade="all, delete"` line (`models/observation.py:114`) deleted | 001, 004 FAIL; 2 passed |
| Task 3 Step 4 BI-2 | unlink block moved above `profile_db.delete` | 002 FAIL; 3 passed |
| Task 3 Step 4 BI-3 | `try/except OSError` removed | 003 FAIL; 3 passed |
| restore | `git checkout -- .` (detached break worktree, removed after) | `4 passed` |

**Docs truth value (Task 3 Step 6, no edit):**
- `docs/compliance/data-privacy.md:185` "Observations and chunks are removed with it (ORM cascade)" — was true for observations and chunks before and after; the claim it was cited for (that derived interpretation rows go too) is now true through `Observation.interpretation`. Not edited (owner-gated, W-10).
- `docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md:56` (P1, ORM cascade works today) — true. `:59` (P4 `lab_interpretations` "Observation delete cascades") describes behaviour "once pragma is ON"; still conditional on P6, and now also true through the ORM. Not edited.

**Reviews:** code-reviewer (opus) APPROVE, 3 MINOR; security-reviewer (opus) APPROVE, 1 LOW introduced (orphan ciphertext after a failed post-commit unlink, swept only by profile delete), 4 MEDIUM + 2 LOW pre-existing. Codex diff review (`docs/reviews/2026-09-25/DDI-diff-codex.txt`): needs-attention, 2 high + 1 medium, all pre-existing and outside W3-SEC-SCHED (reprocess orphans = Out of scope 1; panel = Out of scope 2; audit-after-delete ordering = new owner item DDI-AUDIT-ORDER). No code change from any review.
