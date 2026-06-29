# Reconciliation — exploration vs. inherited planning bundle

**Last Updated:** 2026-06-24 (S6 close-out — CI eval gate added, a672b88; R-1 resolved)
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
- **Status:** **RESOLVED** (S6, commit a672b88). The eval-gate CI workflow is
  now added with the agreed branch filter: the `agent-evals` job in
  `.github/workflows/ci.yml` runs `scripts/agent_eval_gate.py` and triggers on
  `pull_request: branches: [main]` + `push: branches: [main, 'Security-Revamp-*']`,
  matching the rest of CI rather than the bundle's never-created
  `fix/agent-overhaul`. The feature branch
  (`claude/agent-overhaul-prd-sprints-2vgb5h`) merges to `main`, so gating on
  PRs to `main` is the resolution: the gate runs on the PR that merges this
  work, not on pushes to the feature branch itself. The branch-filter
  question this item raised is therefore answered — the gate filters on
  `main`, the agreed integration target — and the workflow has been placed.
  (Not yet observed executing in CI, since no PR has run it from the feature
  branch yet; that's a "ships on first green run" note in PHASE_6 /
  RELEASE_CHECKLIST, not an open reconciliation conflict.)
- **Date found:** 2026-06-24 (S0 inception); **resolved:** 2026-06-24 (S6, commit a672b88)
- **Bundle says:** develop on `fix/agent-overhaul`.
- **Environment says:** develop on `claude/agent-overhaul-prd-sprints-2vgb5h` (the
  only feature branch present; `fix/agent-overhaul` does not exist in this clone).
- **Action taken:** Worked on `claude/agent-overhaul-prd-sprints-2vgb5h`, treating it
  as the same logical workstream. `main` untouched.
- **S6 close-out update (2026-06-24, commit 1571927):** The gate-script HALF
  of the eval-CI gate is now ready and proven — `scripts/agent_eval_gate.py`
  is runnable, exits non-zero on a regression, and `test_s6_3_ci_gate_fails_on_regression`
  proves it locally. What is still unresolved is exactly this reconciliation
  item: the `.github/workflows` job that calls this script, and which branch
  filter it should trigger on, have NOT been added — that placement decision
  is the live approval item in front of the user right now. Today's actual
  `ci.yml` triggers are `push: branches: [main, 'Security-Revamp-*']` and
  `pull_request: branches: [main]` — neither names this feature branch
  (`claude/agent-overhaul-prd-sprints-2vgb5h`) today. Nothing under
  `.github/` was changed in commit 1571927; this remains untouched pending
  the approval decision.
- **Needs you to:** Nothing further for the CI gate — the workflow is added
  and gates PRs to `main` (commit a672b88). If you still intend to
  rename/merge via `fix/agent-overhaul` rather than `main`, add that branch to
  the `agent-evals` triggers; otherwise the `main`-targeted filter is the
  resolution and no action is needed.

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
- **Status:** **RESOLVED** (S5, commit 3765565). `agent_enabled` is now a real
  Boolean column on `UserModelSettings` — a **PROFILE-DB** table, not master
  — shipped via profile migration `009_agent_enabled.py` (linear
  `down_revision` off `008_response_feedback`, reversible). A new
  `PATCH /model-settings/agent` endpoint toggles it, and `api/assistant.py`'s
  `POST /chat` reads the persisted value through `is_agent_enabled(settings)`
  to decide whether to serve via the agent graph. The recommended resolution
  below (own the migration in S5-1, when there's an actual caller) is exactly
  what happened.
- **Owner:** [Owner] (closed)
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

### R-12 — Planner analyte-synonym gap blocks the `mixed-partial-grounding` golden case (IMPORTANT)
- **Status:** **RESOLVED** (S4, commit 43f7a4b). `nodes/plan.py` adds
  `_detect_topics()` — a keyword→topic-group mapping (lipid, kidney, glucose,
  thyroid, electrolyte, vitamin, blood_count) plus a `_TOPIC_SINGLE_ANALYTE_FALLBACK`
  (kidney → `"Creatinine"`) for the single-topic case. When a question's keywords
  span MULTIPLE topics, `_default_planner` now plans `query_observations` with NO
  narrow `analyte` filter at all — broadening the query rather than guessing one
  exact-match string — so any verified row the vault actually has comes back, and
  groundedness/guard (S3) decides what's actually backed. `mixed-partial-grounding`
  now resolves to `answer` with 1 citation (LDL grounded, kidney-function claim
  dropped, matching its `expect.drops_unmapped: true`); single-topic behavior
  (e.g. "How has my LDL changed") is unchanged since it still resolves to exactly
  one topic and keeps the narrow filter; no S1/S2/S3 regressions. Verified live via
  `test_s4_3_golden_set_categories_pass` (all 30 golden cases, including this one
  and four new sibling mixed-topic cases, resolve to their expected terminal).
- **Owner:** S4 (closed)
- **Date found:** 2026-06-24 (S3 close-out reconciliation pass, post commit f60e0c1)
- **Bundle says:** The guardrails skill's mixed-evidence case
  (`mixed-partial-grounding.json`) expects a question naming multiple analytes
  ("What do my recent labs show about my cholesterol and kidney function?") to
  resolve to `answer`, with the grounded LDL claim surviving and the
  ungrounded kidney-function claim dropped by the guard (S3-2).
- **Reality:** The fixture does **not** pass end-to-end through `run_agent` —
  and it is not a guard bug. `nodes/plan.py`'s `_detect_analyte` maps the
  word "cholesterol" to the canonical analyte `"Cholesterol"`, but the
  fixture's vault seeds an observation named `"LDL"`, not `"Cholesterol"`.
  `query_observations(analyte="Cholesterol")` therefore misses the seeded LDL
  row, `check_verification` reports the analyte as absent, and the planner
  drafts with zero evidence before the guard node ever runs. The guard would
  correctly drop an unmapped claim or abstain on zero survivors — it never
  gets the chance to prove it on this fixture because the planner starves it
  first.
- **Action taken:** None yet — flagged here rather than patching the planner
  outside a scoped story. `test_s3_guardrails.py`'s guard-level assertions
  (`test_s3_2_unmapped_claim_dropped`, the advice-bait and low-confidence
  cases) exercise the guard directly and pass; only the full
  plan→act→draft→guard path for this specific golden case is blocked.
- **Recommended resolution:** S4 fixes the planner's analyte detection —
  either broaden `"cholesterol"` to resolve to the LDL/HDL/triglyceride lipid
  panel rather than an exact-match `"Cholesterol"` synonym, or drop strict
  exact-match filtering in favor of a multi-analyte question querying
  observations without a narrow single-analyte filter — so the mixed golden
  case resolves to `answer` with the unmapped kidney-function claim dropped,
  per its own `expect` block.
- **Needs you to:** Confirm S4 (not S3 follow-up, not S6) is the right sprint
  to own the planner fix, since the guard itself is already correct and
  tested.

### R-13 — Confidence threshold (PRD §10 Q2) resolved by proposal, not by client confirmation
- **Status:** Open — needs a human nod (proposed resolution already adopted in code).
- **Owner:** [Owner]
- **Date found:** 2026-06-24 (S3 close-out reconciliation pass, post commit f60e0c1)
- **Bundle says:** PRD §10 Q2 lists the confidence-threshold numeric cutoff as
  an open question for the human, with a proposed default: "reuse the
  existing faithfulness threshold from `modules/faithfulness.py`."
- **Reality:** S3-4 adopted the proposal as-is: `CONFIDENCE_THRESHOLD` in
  `guardrails/guard.py` is set to the faithfulness module's
  `min_overall_score` (0.6), and confidence itself is computed as a binary
  1.0/0.0 — 1.0 when at least one grounded sentence survives groundedness
  mapping with a real (non-empty) `source_id`, else 0.0. This was the
  pragmatic choice to unblock S3-4 rather than waiting on a round-trip with
  the client, since the bundle already named it as the proposed default.
- **Action taken:** Implemented the proposed default; did not introduce a
  graded/continuous confidence score, since the bundle's proposal and S3-4's
  AC only required a threshold comparison, not a scored confidence model.
- **Recommended resolution:** Client confirms (a) 0.6 (faithfulness's
  `min_overall_score`) is the right threshold for the guard's abstain
  decision specifically, as distinct from faithfulness scoring's own use of
  that number, and (b) whether a binary 1.0/0.0 default confidence is
  acceptable long-term or whether a graded confidence signal (e.g. proportion
  of sentences with real citations, or a model self-assessment) is wanted
  before S6's CI eval gate locks in abstention-correctness scoring against
  this threshold.
- **Needs you to:** Confirm the 0.6 threshold and the binary confidence
  default, or redirect before S6 builds the eval gate on top of it.

### R-14 — Golden set's `drops_unmapped` cases never exercise groundedness actually dropping a composed sentence
- **Status:** **RESOLVED** (S6, commit 1571927). `scorer.score_composed_drop_case()`
  (`src/backend/modules/agent/eval/scorer.py`) drives a real `plan → act →
  draft` for a genuinely citation-grounded case, then appends ONE extra
  sentence with NO corresponding citation to the drafted terminal, and feeds
  that augmented terminal to the REAL `guard()`/`groundedness.map_sentences` —
  not a synthetic draft, not a mocked guard. The guard mechanically drops the
  citation-less sentence live; the terminal stays `answer` at
  `groundedness_after_drop == 1.0`, proving the case the unit test
  (`test_s3_2_unmapped_claim_dropped`) already covered in isolation now also
  has an end-to-end eval-level proof. `report.composed_drop_check` (a
  `ComposedDropCheck` with `dropped`, `terminal`, `groundedness_after_drop`,
  `passed` fields) is asserted in `test_s6_2_four_axis_scoring`
  (`dropped is True`, `terminal == "answer"`, `groundedness_after_drop == 1.0`,
  `passed is True`) and is part of the gate's pass/fail decision in
  `scripts/agent_eval_gate.py`. This closes the exact gap flagged at S4
  close-out: "compose first, drop second" is now exercised end-to-end by an
  eval case, not only by the S3 unit test.
- **Owner:** S6 (closed)
- **Date found:** 2026-06-24 (S4 close-out reconciliation pass, post commit 43f7a4b)
- **Bundle says:** The guardrails skill's mixed-evidence golden cases (e.g.
  `mixed-partial-grounding.json`, `expect.drops_unmapped: true`) exist to prove the
  guard node's S3-2 groundedness mapping mechanically drops an unmapped claim from a
  drafted answer — "a sentence survives iff it has a citation with a non-empty
  `source_id`; unmapped sentences dropped mechanically" (RELEASE_CHECKLIST row 3).
- **Reality:** With R-12 resolved, the planner now broadens multi-topic queries
  instead of guessing a narrow filter — which means for every mixed golden case,
  the draft node only ever composes a sentence for the topic it actually retrieved
  evidence for (e.g. LDL). It never drafts a sentence for the ungrounded topic
  (kidney function) in the first place, because no evidence for that topic came
  back from `query_observations` to draft a sentence from. So `drops_unmapped`
  passes for the right reason at the planner/draft layer (no speculative prose is
  generated) but for the WRONG reason at the guard layer: `groundedness.map_sentences`
  is never actually exercised dropping an already-composed, citation-less sentence
  by any golden case. That specific mechanism — compose first, drop second — is
  real and covered, but only by the S3 unit test
  (`test_s3_2_unmapped_claim_dropped` in `test_s3_guardrails.py`), which hands the
  guard a synthetic draft directly. The end-to-end plan→act→draft→guard path never
  produces that shape on its own with today's golden fixtures.
- **Action taken:** None yet — flagged here rather than hand-crafting a golden
  fixture outside a scoped story. All 30 current golden cases pass
  (`test_s4_3_golden_set_categories_pass`); this is a coverage gap, not a failing
  test.
- **Recommended resolution:** S6's golden-set growth (30 → 50–100, per
  PHASE_4/SPRINT_4 and the success-metric gates' eval-axis work) should include at
  least one case engineered so the draft node composes a sentence for a topic with
  NO retrievable evidence (rather than the topic simply never being queried) and
  the citation-less sentence reaches the guard, forcing `groundedness.map_sentences`
  to drop it live. This closes the gap between "the mechanism is unit-tested" and
  "the mechanism is exercised end-to-end by an eval case," matching the same
  standard R-12 itself was held to.
- **Needs you to:** Confirm S6 (not an S4 follow-up) is the right sprint to own
  this golden-fixture gap, since today's 30 cases all pass and nothing is broken —
  this is a coverage recommendation, not a defect.

### R-15 — Agent path drops legacy context features (multi-turn history, memory, context filters) (IMPORTANT)
- **Status:** Open — needs a product decision before R2 GA (proposed resolution below).
- **Owner:** product/client
- **Date found:** 2026-06-24 (S5 close-out reconciliation pass, post commit 3765565)
- **Bundle says:** `/assistant/chat`'s existing contract (ASSIST-HIST-001,
  ASSIST-MEM-003) honors multi-turn conversation history loaded from the DB
  (falling back to client-supplied `history[]`), dual-gated memory injection
  (`use_memory` request flag AND the per-profile/global
  `assistant_memory_enabled` setting), and context-selection filters
  (`selected_analytes`, `selected_panel`, `from_date`, `to_date`,
  `document_category`) — all consumed by the legacy `rag.query` call in
  `api/assistant.py`.
- **Reality:** S5-1's cutover calls `_serve_via_agent(question=..., profile_id=...,
  profile_db=..., db=...)` — it does not pass `db_history`, `inject_memory`, or any
  of the five context-selection filters. Since the agent path is now the
  **default** (flag ON), every chat request that doesn't hit the exception
  fallback silently loses multi-turn context, memory injection, and the
  ability to scope a question to selected analytes/panel/date-range/document
  category — all of which the legacy path one branch below still honors.
  This is not a crash or a test failure; it is a silent behavioral narrowing
  on the new default path, caught by reading the diff against the legacy
  branch at close-out, not by any S5 test (no S5 AC named these inputs).
- **Action taken:** None — flagged here rather than threading five additional
  parameters into `run_agent`/`RunContext` outside a scoped story, since
  doing so touches the agent graph's planner/tool-context contract, not just
  the API call site.
- **Recommended resolution:** A product decision before R2 GA (i.e., before
  removing the legacy fallback or treating R2 as feature-complete): either (a)
  thread conversation history, memory injection, and the context-selection
  filters into `run_agent`/`ToolContext` so the agent path reaches parity with
  legacy, or (b) explicitly document the cutover as a deliberate scope
  reduction for R2 (agent serves single-turn, unfiltered, memory-less
  questions only) and decide whether that's acceptable for GA traffic.
- **Needs you to:** Pick (a) or (b) — this determines whether S6+ scope grows
  to include context-parity work.

### R-16 — `insufficient_context` hardcoded `False` on the agent path, even for abstain terminals
- **Status:** Open — needs a human nod (proposed resolution below).
- **Owner:** [Owner]
- **Date found:** 2026-06-24 (S5 close-out reconciliation pass, post commit 3765565)
- **Bundle says:** `ChatResponse.insufficient_context` exists so the frontend
  can render an "insufficient evidence" state distinct from a normal answer;
  on the legacy path it's set from `result.insufficient_context`, computed by
  `rag.query` from the actual verification outcome.
- **Reality:** On the agent success branch in `api/assistant.py`'s `chat()`,
  `insufficient_context` is set to the literal `False` unconditionally —
  regardless of whether the agent's terminal was `answer`, `abstain`, or
  `escalate`. `abstain` is literally the terminal that means "not enough
  verified info to answer" (`AgentTerminal.terminal: Literal["answer",
  "abstain", "escalate"]`), so a user whose question abstains today sees
  `insufficient_context=False` in the response — the opposite of what the
  field is supposed to signal, and a UI-accuracy regression versus the legacy
  path's behavior on the same underlying condition.
- **Action taken:** None — flagged here rather than patching the mapping
  outside a scoped story, since it's a one-line fix but changes response
  content the frontend may render on.
- **Recommended resolution:** Map `terminal == "abstain"` (and arguably
  `"escalate"`, pending a product call on whether escalation also counts as
  "insufficient context" for UI purposes) to `insufficient_context=True` on
  the agent branch, mirroring what the legacy path's verification outcome
  already produces for the analogous condition.
- **Needs you to:** Confirm the abstain→`insufficient_context=True` mapping
  (and decide on escalate) before or alongside the fix.

### R-17 — Semantic cache has no eviction and narrow invalidation (count-only, not document-content-aware)
- **Status:** Open — needs a human nod on bounding before high-traffic use (proposed resolution below).
- **Owner:** [Owner]
- **Date found:** 2026-06-24 (S5 close-out reconciliation pass, post commit 3765565)
- **Bundle says:** Phase 5's data-shape contract: cache keyed
  `(normalized_question, profile_version)`, invalidating "when new verified
  data lands" — a stale cached explanation of changed data is a correctness
  bug.
- **Reality:** `modules/agent/cache.py` is a module-level Python dict with no
  TTL, no LRU, and no size bound — every distinct `(question, profile_version)`
  pair seen across the process's lifetime stays resident in memory forever
  (only `clear_cache()`, a test-only helper, ever empties it). Separately,
  `profile_version` is sourced as the **COUNT** of verified observations only
  — it does not change when a verified **document's** content is edited, even
  though `retrieve_chunks` reads from verified documents. So a cached answer
  that cites a document chunk can go stale (the document was corrected/
  re-verified with different text) without the cache key changing, because
  the observation count didn't move.
- **Action taken:** None — implemented exactly to S5-2's AC (repeat question
  served from cache; invalidates on new verified data via the count signal),
  which did not specify eviction or document-content invalidation.
- **Recommended resolution:** Before high-traffic use: (a) bound the cache —
  either an LRU with a max-entries cap or a TTL, since an in-process unbounded
  dict is a slow memory leak under real traffic; (b) broaden the
  `profile_version` signal to also change on verified-document edits (e.g.
  fold in a document-content version/hash alongside the observation count),
  closing the document-edit staleness gap.
- **Needs you to:** Confirm bounding + broadening the invalidation signal as
  S6+ scope, or whether the bundle considers the count-only signal acceptable
  for the documents in scope today.

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
