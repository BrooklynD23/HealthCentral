# Reconciliation — exploration vs. inherited planning bundle

**Last Updated:** 2026-06-24
**Owner:** [Owner] (solo client/engineer — final approver)
**Refresh Trigger:** A new conflict is found between live code and an inherited
artifact, or the human resolves an open item below

> **Rule of precedence:** inherited decisions (AGILE_PLAN, the four skills, the
> audience reports) **win** unless the human explicitly overrides. This file lists
> every place the live repo or the environment disagrees with the bundle, plus the
> recommended resolution. Nothing here was silently "fixed" — each needs a human nod.

---

## Conflicts requiring a human decision

### R-1 — Branch name mismatch
- **Bundle says:** develop on `fix/agent-overhaul`.
- **Environment says:** develop on `claude/agent-overhaul-prd-sprints-2vgb5h` (the
  only feature branch present; `fix/agent-overhaul` does not exist in this clone).
- **Action taken:** Worked on `claude/agent-overhaul-prd-sprints-2vgb5h`, treating it
  as the same logical workstream. `main` untouched.
- **Needs you to:** Confirm this is the intended branch, or create/rename to
  `fix/agent-overhaul` before merge. The eval-CI gate in Phase 6 is written to
  trigger on `fix/agent-overhaul` per the evals skill — **update the workflow
  branch filter to whatever the final branch name is.**

### R-2 — Proof-bundle venv is Windows-pathed
- **Bundle says:** run the proof bundle via
  `PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest ...`.
- **Reality:** `.wsl-pytest-venv/pyvenv.cfg` points at a Windows-host path
  (`/mnt/c/Users/<user>/Documents/GitHub/HealthCentral/.wsl-pytest-venv`) and
  `/usr/bin/python3.12`, neither of which exists in this Linux container. The venv
  cannot execute here.
- **Action taken:** Validated the committed scaffolds by (a) `py_compile` over all
  new agent modules and (b) `pytest --collect-only` against `tests/agent/` using a
  throwaway `pydantic`/`pytest` install. The full maintained bundle was **not** run.
- **Needs you to:** Re-run the real proof bundle on your WSL host before merge. The
  scaffolds are deliberately self-contained (stdlib + pydantic only) so they collect
  without the full backend dependency tree.

### R-3 — `agent_overhaul_plan.md` referenced but absent
- **Bundle says:** derive phases from `agent_overhaul_plan.md` (architecture +
  6-phase breakdown + six-layer skill mapping).
- **Reality:** that file is not in the repo or the uploaded bundle.
- **Action taken:** Derived the eight phase docs from the **authoritative**
  substitutes that *are* present — AGILE_PLAN §4 (epics E1–E6), §5 (releases R1–R3),
  §6 (sprints S0–S7), and the four skills. The phase→release→epic→sprint mapping is
  recorded in each phase doc and in the README index.
- **Needs you to:** If `agent_overhaul_plan.md` exists elsewhere, drop it in and I'll
  reconcile any phase-boundary differences. Until then the AGILE_PLAN IDs are the
  spine and phases map 1:1 to sprints.

### R-8 — `agent_enabled` has no persisted column or migration yet
- **Status:** Open — needs a human nod on timing (proposed resolution below).
- **Owner:** [Owner]
- **Date found:** 2026-06-24 (S0 close-out reconciliation pass, post commit 3e63df2)
- **Bundle says:** Phase 0's data-shape contract says `agent_enabled: bool` lives
  in model settings, default `False`, profile-scoped, "no schema migration needed
  if stored in existing settings JSON; if a column is added, ship both
  master+profile migrations only where the column lands."
- **Reality:** `UserModelSettings` ORM (`src/backend/models/model_settings.py`)
  has no `agent_enabled` column, and no Alembic migration adds one.
  `is_agent_enabled` (`src/backend/modules/agent/settings.py`) works correctly
  today — it falls through to the `AGENT_ENABLED_DEFAULT` (`False`) via
  `getattr`/`.get()` on whatever shape it's handed — but because no persisted
  field exists yet, no live caller can turn the flag ON via stored settings.
  S0-2's AC ("flag defaults off; `/assistant/` path unchanged when off") is
  satisfied either way, since OFF is exactly what happens whether the column is
  missing or present-and-false.
- **Action taken:** None yet — flagged here rather than silently adding a
  column/migration outside of a scoped story.
- **Recommended resolution:** The S5 cutover sprint (S5-1, which flips the
  default and wires `/assistant/` to read a real settings object) should add the
  `agent_enabled` column + Alembic migration at that point, when there's an
  actual caller to wire it to. Reference the existing
  `user_ocr_preference_enabled` pattern in `core/config.py` (defaults the
  preference, doesn't require the column to exist for the helper to be safe) —
  `is_agent_enabled` already follows that same shape; only the column is missing.
- **Needs you to:** Confirm S5-1 is the right sprint to own the migration (vs.
  pulling it earlier into S1 if a story needs to actually persist a non-default
  value sooner).

### R-9 — `ToolContext` Protocol extended with `run_id`/`step_index` for audit correlation
- **Status:** Open — needs a human nod on the mechanism (proposed resolution below).
- **Owner:** [Owner]
- **Date found:** 2026-06-24 (S1 close-out reconciliation pass, post commit 0f09cd3)
- **Bundle says:** Phase 0's `ToolContext` Protocol (`modules/agent/state.py`)
  was scoped to `profile_id`/`db_session` only — enough for a tool to run a
  scoped query, nothing about correlating its audit event to a specific run/step.
- **Reality:** S1 needed each tool (and each node) to self-emit one
  `agent.act`/`agent.plan`/`agent.answer` event correlated to the run that
  produced it, so `state.py`'s `ToolContext` Protocol was extended
  additively with `run_id: str` and `step_index: int`. `query_observations.run`
  and the plan/act/draft nodes now read these off `ctx` to stamp their
  self-emitted events, rather than the caller passing `run_id`/`step_index` in
  as explicit parameters alongside `ctx`.
- **Action taken:** Extended `ToolContext` additively (no existing field
  removed or retyped) and wired `graph.run_agent`'s mutable `RunContext` to
  satisfy the extended Protocol. Not treated as a breaking change since every
  existing caller shape (profile_id/db_session) still satisfies the Protocol;
  only callers that need correlated audit events need to populate the two new
  fields.
- **Recommended resolution:** Confirm carrying `run_id`/`step_index` *on* the
  context object is the intended audit-correlation mechanism for the
  remaining sprints (S2's multi-step reflect loop will mutate `step_index`
  every iteration; S3's guard node will read both off the same `ctx`), versus
  passing them as explicit parameters alongside `ctx` on every node/tool
  call. The context-carried approach keeps node/tool signatures stable as
  more steps are added (S2-1's four new tools, the reflect loop) at the cost
  of widening what's implicitly available off `ctx` — worth a deliberate
  human call before S2 builds more on top of it.
- **Needs you to:** Confirm `ToolContext`-carried correlation is the pattern
  to keep, or redirect to explicit parameters before S2-1 adds four more tools
  against the same Protocol.

### R-10 — `lookup_reference` reads the master DB directly, bypassing the profile-scoped `ToolContext`
- **Status:** Open — needs a human nod on the pattern (proposed resolution below).
- **Owner:** [Owner]
- **Date found:** 2026-06-24 (S2 close-out reconciliation pass, post commit fbb4fe7)
- **Bundle says:** Phase 0's `ToolContext` Protocol (`modules/agent/state.py`)
  exposes `db_session` as the profile-scoped session a tool should use for its
  reads (extended in R-9 with `run_id`/`step_index` for audit correlation, but
  still profile-scoped for data access).
- **Reality:** `lookup_reference` needs `BiomarkerKnowledge`, which lives in the
  **master** DB, not any profile DB. `ctx.db_session` can't reach it, so the new
  `modules/agent/knowledge_lookup.py` adapter opens its own session via
  `core.database.async_session_maker` directly, independent of `ctx`. It degrades
  gracefully (`reference=None`, stable handle still returned) if the master DB
  isn't reachable, rather than crashing.
- **Action taken:** Implemented the direct master-DB read as a self-contained
  adapter module rather than extending `ToolContext` again, since `run_id` (R-9)
  was an additive correlation field and this is a different kind of need (a
  second data source, not more metadata on the same one).
- **Recommended resolution:** Confirm whether master-DB reads should keep going
  through ad hoc adapters like `knowledge_lookup.py` (one per tool that needs
  master-DB data) or whether `ToolContext` should grow a second, explicit
  `master_db_session` field so the pattern is visible in the Protocol itself.
  Worth deciding before S3+ tools need master-DB data too — better to pick one
  shape now than have a third pattern appear.
- **Needs you to:** Confirm the intended pattern for master-DB-reading tools
  (ad hoc adapter vs. extending `ToolContext`) before more tools need it.

### R-11 — `retrieve_chunks` falls back to deterministic text-match instead of the RAG vector retriever
- **Status:** Open — needs a human nod on golden-fixture scope (proposed
  resolution below).
- **Owner:** [Owner]
- **Date found:** 2026-06-24 (S2 close-out reconciliation pass, post commit fbb4fe7)
- **Bundle says:** Phase 2's `retrieve_chunks` contract returns `chunks:
  list[ChunkRef]` restricted to chunks whose parent `Document.status ==
  "verified"` (R-5), implying retrieval goes through the existing RAG vector
  path (`modules/rag.py`).
- **Reality:** The real vector retriever requires an `Embedding` row per chunk,
  produced by the ingest pipeline. Golden cases and unit fixtures don't generate
  embeddings, so `retrieve_chunks` instead uses a deterministic, typed,
  read-only, audited substring-match-over-verified-chunks fallback (falling
  back further to most-recent verified chunks if no text match), so the tool is
  exercisable in tests without standing up the embedding pipeline.
- **Action taken:** Shipped the text-match fallback as the only path for now;
  did not wire the real vector retriever or add embedding-seeding to golden
  fixtures, since neither was in S2-1's scoped AC.
- **Recommended resolution:** Decide whether S4 or S6 golden cases should start
  seeding `Embedding` rows so the real vector-retrieval path gets exercised by
  evals (closer to production behavior), or whether the text-match fallback is
  judged acceptable for eval purposes indefinitely (simpler, deterministic,
  no embedding-model dependency in CI). This decision should land before S6
  builds the CI eval gate on top of whichever path is authoritative.
- **Needs you to:** Confirm whether S4/S6 golden cases should seed embeddings to
  exercise the real vector path, or whether the text-match fallback is
  acceptable for evals going forward.

## Observations from exploration (no conflict, but worth your eye)

### R-4 — Read-only audit coverage gap
`SecurityAuditMiddleware` only logs **mutating** requests (POST/PUT/PATCH/DELETE);
GET is skipped. The agent's read-only tool calls are GETs in spirit. The agent must
therefore emit its per-node audit events **explicitly** via `core.audit.create_audit_log`
(it does not get them for free from middleware). Wired this way in the scaffolds.

### R-5 — `Chunk` has no own `verified` flag
Verified status for retrieved chunks is inherited from `Document.status == "verified"`.
The `retrieve_chunks` tool contract therefore filters on the parent document's status,
not a chunk column. Flagged so groundedness mapping never treats an unverified-document
chunk as a valid source handle.

### R-6 — Response-shape change is frontend-visible
Adding `abstain | escalate` terminals to `/assistant/chat` changes the response union
the frontend (`src/frontend/src/services/assistant.ts`, `pages/ExplainAssistant.tsx`)
consumes. The cutover (Phase 5 / S5) must ship the additive discriminated-union type
**and** keep the flag-OFF shape byte-identical. Captured as a contract in Phase 5.

### R-7 — Duplicate evals skill in the bundle
Two identical copies of the `healthcentral-evals` skill were provided. Committed once
under `skills/healthcentral-evals/SKILL.md`. No content lost.

## Resolved / no action needed
- Success metrics: taken verbatim from AGILE_PLAN §1 and audience Report 0. Not redefined.
- Step budget (≤5), graph shape, tool registry: taken verbatim from the agent skill.
- Guard order (advice ×2 → groundedness → confidence → audit): verbatim from the
  guardrails skill.
