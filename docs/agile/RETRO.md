# Retro Log — Agent Overhaul

> **Format (keep it):** one block per sprint, three bullets — *Keep / Drop /
> Try*. Append at the **top** (newest first). The retro is the "revisit &
> iterate" engine (AGILE_PLAN §3, §8): every Sunday re-ask the three iteration
> questions and re-groom the backlog.
>
> The three iteration questions (AGILE_PLAN §8):
> 1. Did the eval set catch what mattered? If a real failure slipped through,
>    the first new story next sprint is a golden case that reproduces it.
> 2. Is the read-only rule still holding? Pressure to let the agent write = a
>    new epic, never a bent E1.
> 3. Is governance still structural? A guardrail that drifted into "ask the
>    model nicely" gets pulled back into the guard node.

---

## S6 — Golden set + 4-axis scorer + eval gate (implemented, commit 1571927) — **R3 release retro (final sprint)**
> This is the **final-sprint retro** for the Agent Overhaul plan: S6 is R3's
> last sprint (AGILE_PLAN §5), and R3 is the last release. The eval *logic*
> backing row 5 (golden set, 4-axis scoring, gate-fails-on-regression) is now
> live and green — but R3 itself is **not shipped**: the actual
> `.github/workflows` PR-gating job that wraps `scripts/agent_eval_gate.py` is
> PENDING USER APPROVAL and has not been added. RELEASE_CHECKLIST row 5 stays
> `[~]` and the R3 exit-criteria note is explicit: **R3 PENDING — CI workflow
> awaiting approval (2026-06-24).**
- **Keep:** Writing the gate script (`scripts/agent_eval_gate.py`) as a
  standalone, directly-runnable program — not a pytest fixture, not something
  that only exists inside CI — meant the gate's behavior (exit 0/1/2,
  regression detection) could be proven locally today, independent of
  whether or when the `.github/workflows` wrapper gets approved. Same
  defense-in-depth posture as S4's redaction gate and S2's hard step budget:
  the safety mechanism is real and testable on its own, not contingent on
  the infrastructure around it. Resolving R-14 by driving a REAL
  plan→act→draft and appending a synthetic citation-less sentence
  (`score_composed_drop_case`) — rather than handing the guard a synthetic
  draft directly, as the S3 unit test does — closes the exact gap RETRO
  flagged at S4 close-out: the end-to-end compose-then-drop path is now
  exercised by an eval case, not just a unit test.
- **Drop:** The golden-set growth (30→58) and the 4-axis scorer are both
  code-complete and green, but the release-level deliverable named in
  AGILE_PLAN §5 for R3 is "evals gate CI" — a CI job, not a script sitting in
  `scripts/`. Treating S6-3 as "logic done, ship it" risked declaring R3
  shipped on the strength of a script nobody's PR is actually gated by yet.
  Caught at close-out by re-reading PHASE_6's exit criteria literally
  ("`.github/workflows` job turns a planted regression PR red") rather than
  by a failing test — same shape of gap RETRO has flagged most sprints this
  release: a story's AC/logic being green doesn't mean the release-level
  claim is true. R3 is being held at PENDING specifically so this doesn't
  repeat what R-1 already flagged (workflow placement + branch filter is
  still an open human decision).
- **Try:** Re-asking the three iteration questions (AGILE_PLAN §8), at both
  sprint and **R3 release** scope, for the last time this plan:
  1. *Did the eval set catch what mattered?* Yes, decisively — growing to 58
     cases across all four categories and scoring every axis numerically
     means a real regression (advice leakage, dropped groundedness, a wrong
     abstain) now has somewhere concrete to show up, and
     `test_s6_3_ci_gate_fails_on_regression` proves the gate actually goes
     red on a planted one rather than just asserting green forever. At
     release scope: the eval set and scorer are release-ready; what's
     missing is purely the CI wrapper, not more eval coverage.
  2. *Is the read-only rule still holding?* Yes — the scorer and gate script
     only read golden fixtures and run the existing read-only agent graph;
     `score_composed_drop_case` drives a real plan→act→draft but mutates
     nothing persisted. No new write path introduced by S6.
  3. *Is governance still structural?* Yes, and this is the sprint where the
     answer becomes "yes, and provably so end-to-end": the gate's thresholds
     (groundedness==1.0, citation==1.0, abstention==1.0, advice_leakage==0)
     are numeric constants compared in code, not eyeballed; the regression
     test proves the gate isn't a gate that's always green by construction.
     The one piece of governance that is NOT yet structural is the release
     process itself — nothing currently stops a PR from merging without
     running this gate, because the `.github/workflows` wrapper doesn't
     exist yet. **This is the headline close of the whole plan:** R1 proved
     the loop, R2 proved the guard enforces in production, R3's logic proves
     the eval gate works — the only remaining step before this is a
     genuinely CI-enforced release is a human approving the workflow change.

## S5 — Cutover + cache (implemented, commit 3765565) — **R2 release retro**
> This is also the **R2 release retro point**: S5 is R2's last sprint
> (AGILE_PLAN §5), and the RELEASE_CHECKLIST rows backing R2 (3, 4, 6, 7, 9)
> are now `[x]`/`[~]` at this close-out (row 7 stays `[~]`: cache + per-node
> timing are live, but the p95 ≤ legacy+50% numeric gate is not yet measured).
> The three iteration questions below are answered both at sprint scope and,
> where noted, at release scope.
- **Keep:** Making the cutover's fallback a `try/except` around the ENTIRE
  agent call (`_serve_via_agent`) rather than around individual sub-steps
  means "any agent exception → legacy path" is a property of the call site,
  not a hope that every internal failure mode was anticipated — the same
  defense-in-depth posture S2 took with the hard `MAX_STEPS` budget and S4
  took with the redaction gate's signature-enforced no-bypass guarantee.
  Keying the semantic cache on `profile_version` (a COUNT, recomputed fresh
  every call) instead of a push-based invalidation event means there is no
  separate "remember to invalidate" code path to forget — staleness is
  structurally impossible by construction, not policed by convention.
- **Drop:** The cutover wires `_serve_via_agent` with only `question` and
  `profile_id` — it does not thread through `db_history`, the dual-gated
  `inject_memory` flag (ASSIST-MEM-003), or any of the context-selection
  filters (`selected_analytes`, `selected_panel`, `from_date`, `to_date`,
  `document_category`) that the legacy `rag.query` call two lines below it
  still receives. This was caught at close-out by reading the diff side by
  side with the legacy branch, not by a failing test — none of S5-1's AC
  named these inputs, so nothing asserts they're honored. Same shape of gap
  RETRO has flagged every sprint so far (S0–S4): a story's AC matching the
  happy path doesn't guarantee parity with the path it's replacing. Also
  caught: the agent branch hardcodes `insufficient_context=False`
  unconditionally, even when the terminal is `abstain` (literally "not
  enough verified info"), which is a UI-accuracy regression no test caught
  because no S5 test asserts on `insufficient_context` for an abstain
  terminal served via the agent path. Opened R-15 and R-16, recommended for a
  product decision / quick fix before R2 GA.
- **Try:** Re-asking the three iteration questions (AGILE_PLAN §8), at both
  sprint and **R2 release** scope:
  1. *Did the eval set catch what mattered?* At sprint scope: the cache-key
     and per-node-timing assertions in `test_s5_cutover_cache.py` pass live
     and exercise exactly the mechanisms they name. But the eval set has no
     case that drives a multi-turn or memory-dependent question through the
     now-default agent path, so it could not have caught R-15 (context
     features dropped) — that gap was found by code reading, not by a red
     test. At release scope: R2 ships with this gap open; next sprint's
     first new story should be a golden/integration case that asserts
     multi-turn context actually reaches the agent path, per AGILE_PLAN §8
     Q1's own rule of starting from the reproduction of the gap just found.
  2. *Is the read-only rule still holding?* Yes — the cache reads/writes an
     in-process dict (no DB write), and `record_node_timing` only reads node
     durations into the existing metrics collector. No new write path to
     profile/master data was introduced by S5.
  3. *Is governance still structural?* Yes for the cutover mechanism itself —
     the fallback is a `try/except` at the call site (structural), not a
     convention to remember; the flag is now persisted via a real column +
     migration, not just an in-memory default. But R-16
     (`insufficient_context` hardcoded `False`) is exactly the kind of drift
     RETRO's Q3 exists to catch: a UI-facing signal that was correct on the
     legacy path quietly became wrong on the new default path, not through a
     prompt or a model choice, but through a literal that should have been
     computed from the terminal type. **At release scope this is the
     headline R1→R2 boundary close:** R1 proved the loop, R2 proves the
     guard enforces and the agent serves live traffic with a safety-net
     fallback — R3 (S6) is where the eval gate gets CI teeth and where R-15
     (context parity) should be resolved before any GA push beyond R2.

## S4 — PHI gate + offline + golden set to 30 (implemented, commit 43f7a4b)
- **Keep:** Writing the redaction gate (`gate_external_payload`) as a
  mandatory chokepoint *before* any agent tool actually needs it, rather than
  waiting for the first external-egress tool to motivate the design, means
  the no-bypass guarantee is locked in by signature (no `bypass` param
  exists to add pressure to later) rather than retrofitted under deadline
  pressure once a real feature depends on it — the same defense-in-depth
  posture S1 took with `Literal[True]` and S3 took with the mechanical
  groundedness check. Fixing R-12 by broadening the planner's query
  (`_detect_topics()` + no-narrow-filter multi-topic path) instead of trying
  to enumerate every analyte synonym into `_ANALYTE_KEYWORDS` kept the fix
  small and pushed the actual "what's grounded" decision to groundedness/
  guard (S3), where it already belongs — the planner's job is to fetch
  candidate evidence, not to decide what survives.
- **Drop:** Growing the golden set to 30 mixed/grounded/abstain/advice-bait
  cases and watching all 30 pass green surfaced that the *kind* of "mixed"
  coverage we have is narrower than it looks: every mixed case currently
  achieves `drops_unmapped` by the planner never drafting a sentence for the
  ungrounded topic in the first place (no evidence retrieved → no sentence
  composed), not by `groundedness.map_sentences` actually stripping an
  already-composed, citation-less sentence out of a draft. That second path
  — compose first, drop second — is real, mechanically tested
  (`test_s3_2_unmapped_claim_dropped`), and presumably what will happen if a
  future drafter ever composes speculative prose. But no *golden* case
  exercises it end-to-end today. Same shape of gap RETRO has flagged every
  sprint so far (S0–S3): a story's AC matching the unit-level mechanism
  doesn't guarantee the eval suite exercises that mechanism's hardest path.
  Opened R-14, recommended for S6 scope (golden-set growth to 50-100 already
  on the books there).
- **Try:** Re-asking the three iteration questions (AGILE_PLAN §8):
  1. *Did the eval set catch what mattered?* Partially — growing to 30 cases
     and running them all green confirmed the planner fix (R-12) generalizes
     across topic combinations (lipid+kidney, glucose+kidney,
     electrolyte+kidney, lipid+glucose), which is real signal. But the set's
     blind spot (R-14: no case forces a compose-then-drop) was found by
     *reading* the fixtures at close-out, not by a failing test — the set
     told us our code works, not that our coverage was complete. Next
     sprint's eval work (S6) should add at least one golden case purpose-built
     to force a composed-then-dropped sentence, per AGILE_PLAN §8 Q1's own
     rule of starting from a reproduction of the gap just found.
  2. *Is the read-only rule still holding?* Yes — the redaction gate reads
     and transforms a payload string, writes nothing, and has no live caller
     in the agent graph at all yet (by design, S4-1's docstring is explicit
     about this). The offline test only asserts absence of network calls;
     it adds no new write path.
  3. *Is governance still structural?* Yes, and S4 extends the pattern one
     step further than S3: the redaction gate's "no bypass" guarantee is
     enforced by the **function signature itself** (no `bypass` parameter
     exists to pass `True` to), not by a convention or a code-review rule —
     the strongest form of "structural" seen yet in this project. The
     offline test makes "local-first" a property the CI suite can prove
     (network calls fail loudly) rather than a claim in a docstring.

## S3 — Guardrails as a node (implemented, commit f60e0c1)
- **Keep:** Making the advice classifier ONE shared instance called from two
  call sites (pre-model on the question, and inside the guard on the draft)
  rather than two independently-tuned classifiers means there's no drift
  between "what we refuse before thinking" and "what we refuse after
  thinking" — the same defense-in-depth posture S1 took with the
  `Literal[True]` pin and S2 took with the hard `MAX_STEPS` budget. Making
  groundedness mapping purely mechanical (citation with a non-empty
  `source_id`, nothing fuzzier) instead of model-judged means "no unmapped
  claim survives" is a property of the guard node, not a hope about model
  self-restraint — directly answering RETRO's S1/S2 carried-forward iteration
  Q3 ("is governance still structural?") with the headline R1→R2 boundary
  call: the guard node is no longer `_passthrough_guard`.
- **Drop:** The mixed-partial-grounding golden case surfaced a planner gap
  (analyte-synonym detection) at S3 close-out rather than during S3-2's own
  AC — same shape of gap RETRO has now flagged three sprints running (S0-2,
  S1-3, S2-1's AC deviations): "does this story's AC say what happens when an
  upstream node hands the guard zero evidence instead of partial evidence?"
  The guard behaved correctly (drop unmapped, would abstain on zero survivors)
  but never got the chance to prove it on this fixture because the planner's
  exact-match analyte filter starved it before guard ran. Opened R-12, owned
  by S4. Also carried forward without a sprint-level decision: PRD §10 Q2's
  confidence threshold was *resolved by proposal* (reuse
  `modules/faithfulness.py`'s `min_overall_score`, 0.6) rather than by an
  explicit client confirmation — same "open question answered by assumption"
  shape. Opened R-13.
- **Try:** Re-asking the three iteration questions (AGILE_PLAN §8):
  1. *Did the eval set catch what mattered?* Yes, sharply — the
     advice-bait pair (`advice-stop-statin`, `advice-is-this-dangerous`) and
     the unmapped-drop fixtures all pass live and exercise exactly the
     behavior they name. But `mixed-partial-grounding` (the case meant to
     prove "grounded answer + dropped unmapped claim" together) caught a real
     failure *upstream* of the guard — proof the four-axis golden set finds
     bugs anywhere in the pipeline, not just in the node under test this
     sprint. Next sprint's first new story should be the planner fix that
     makes this case resolve to `answer` with one dropped sentence, per
     AGILE_PLAN §8 Q1's own rule.
  2. *Is the read-only rule still holding?* Yes — the guard node only reads
     drafted sentences and citations already produced upstream; it writes
     nothing and calls no tool. The advice classifier and groundedness
     mapper are both pure functions over text already in hand.
  3. *Is governance still structural?* Yes, and this is the sprint where the
     answer changes from "partially" (S1, S2) to "yes" for the guard
     specifically: the four-step order (advice → groundedness → confidence →
     audit) is code in `guard.py`, not a prompt instruction; both fixed
     templates are module constants covered by a copy test, not
     model-generated strings; the confidence threshold is a numeric constant
     compared in code, not a model self-assessment. The remaining
     "governance" gap is no longer the guard node — it's S4's PHI redaction
     gate and S5's flag cutover, tracked separately.

## S2 — The loop closes (implemented, commit fbb4fe7) — **R1 release retro**
> This is also the **R1 release retro point**: S2 is R1's last sprint
> (AGILE_PLAN §5), and the RELEASE_CHECKLIST rows backing R1 (1, 2, 8) all
> flipped `[x]` at this close-out. The three iteration questions below are
> answered both at sprint scope and, where noted, at release scope.
- **Keep:** Letting the deterministic planner grow incrementally (trend
  questions → `compute_trend`; analyte "why" questions with no verified rows
  → `check_verification` → abstain) rather than reaching for a live LLM
  planner kept S2 provable the same way S1 was — no prompt-engineering risk
  taken on to close the loop. Making the reflect node's budget check
  structural (`MAX_STEPS=5`, hard stop → graceful `ABSTAIN_TEMPLATE`) instead
  of advisory means "the loop never spins" is a property of the graph, not a
  hope about model behavior — the same defense-in-depth posture as S1's
  `Literal[True]` pin on verified observations. Building `graph.replay` to
  reconstruct a terminal from `RunLog.steps` *without* re-calling any tool
  (proven by a test that makes `registry.get` raise during replay) means a
  failed run's story is trustworthy even if the live tools have since changed
  or are unreachable.
- **Drop:** Two AC deviations were absorbed mid-sprint rather than being
  flagged in S2-1's acceptance criteria up front — same shape of gap RETRO
  called out for S0-2 and S1-3: "does this story's AC say what happens when
  the ideal data path isn't available?" `retrieve_chunks` falling back to
  deterministic text-match (the real RAG vector retriever needs `Embedding`
  rows the golden fixtures don't generate) and `lookup_reference` reading the
  master DB directly instead of through `ctx.db_session` (which is
  profile-scoped, and `BiomarkerKnowledge` isn't) were both reasonable calls,
  but neither was anticipated in SPRINT_2's AC — caught at close-out via
  RECONCILIATION rather than stated going in. Opened R-10 and R-11.
- **Try:** Re-asking the three iteration questions (AGILE_PLAN §8), at both
  sprint and **R1 release** scope:
  1. *Did the eval set catch what mattered?* At sprint scope: yes for the two
     seed cases (`grounded-ldl-trend`, `abstain-unverified-ldl`), both pass
     live via the new harness. At release scope: the harness is real but it
     is **not yet CI-gated** (that's S6/R3) and only covers 2 golden cases —
     R1 shipping does not mean the eval set is comprehensive, only that the
     skeleton works end-to-end. Next sprint (S3) should add a golden case for
     the guard node's advice-bait rejection, since that's the next thing a
     real failure would slip through.
  2. *Is the read-only rule still holding?* Yes — all four new S2-1 tools are
     pure reads (`compute_trend` aggregates existing verified observations,
     `retrieve_chunks` reads verified-document chunks, `lookup_reference`
     reads master-DB reference data, `check_verification` reads status/counts
     only and never the unverified value itself). No write path introduced.
     At release scope: R1's entire surface area is read-only end-to-end —
     this held for the whole release, not just one sprint.
  3. *Is governance still structural?* Partially, same as S1's flag: audit
     emission is now structural across every node including the two new S2
     event types (`agent.reflect`, `agent.terminal`), and the step budget is
     structural (hard stop, not a suggestion) — but the guard node itself
     remains `_passthrough_guard`, so "governance enforced per step" is still
     not true end-to-end. **At release scope this is the headline R1→R2
     boundary**: R1 proves the loop and the audit trail; R2 (starting S3) is
     where the guard node stops being a passthrough. Don't let S3 treat the
     passthrough as load-bearing — RELEASE_CHECKLIST rows 3/4 stay `[ ]` until
     it's real.

## S1 — First tool, end-to-end (implemented, commit 0f09cd3)
- **Keep:** Making the planner a seam (`planner` param, deterministic
  keyword-based implementation for now) instead of either hard-coding the
  routing logic or reaching for a live LLM call meant S1 could prove the
  plan→act→draft wiring end-to-end without taking on prompt-engineering risk
  this sprint — the same pattern as `_passthrough_guard` for S3. Pinning
  `ObservationRow.verified: Literal[True]` at the output-model layer (on top
  of the DB-level `user_verified == True` filter) keeps "no unverified value
  can reach an answer" true even if a future query regresses — defense in
  depth, not just a single filter to trust.
- **Drop:** The reflect/budget loop (S2-2) and the real guard node (S3) were
  both known deferrals going in, but S1's own acceptance criteria didn't
  explicitly say so — same shape of gap RETRO flagged for S0-2 last sprint
  ("does this story require a schema/migration companion?"). Here it's "does
  this story leave a passthrough seam another sprint must fill?" Caught at
  close-out via the RELEASE_CHECKLIST rows rather than being stated up front
  in S1-3's AC.
- **Try:** Re-asking the three iteration questions (AGILE_PLAN §8):
  1. *Did the eval set catch what mattered?* S1 only exercises one grounded
     path and one audit-emission path live; the golden-case advice-bait and
     abstain cases referenced in SPRINT_1's test-coverage plan are not yet
     wired into this sprint's live suite (15 skips remain). Next sprint should
     confirm at least one abstain golden case runs live, not just collects.
  2. *Is the read-only rule still holding?* Yes — `query_observations` is a
     pure `SELECT`, no write path was added, and the registry only ever
     registers read-only tools this sprint. No pressure observed to bend E1.
  3. *Is governance still structural?* Partially — audit emission is
     structural (each node emits its own event, not a logged afterthought),
     but the guard node is still a no-op passthrough, so "governance enforced
     per step" is not yet true end-to-end. Don't let S2's loop close before
     S3 actually wires the guard; track via RELEASE_CHECKLIST rows 3/4 staying
     `[ ]` until then.

## S0 — Inception (implemented, commit 3e63df2)
- **Keep:** Defensive, shape-agnostic settings access (`is_agent_enabled` handles
  `None` / dict / ORM-attribute access uniformly) made the helper safe to call
  from any caller shape without guessing what it'll be handed. Defaulting OFF
  (`AGENT_ENABLED_DEFAULT = False`) was the right conservative call — no live
  behavior can change until something explicitly opts in. `emit_audit_event`
  no-op-ing when `db is None` simplified unit testing — callers exercise the
  mapping logic without a live session.
- **Drop:** The gap where `UserModelSettings` has no `agent_enabled` column (no
  migration exists) was caught late, by reconciliation after the fact, rather
  than being called out in S0-2's acceptance criteria up front. The story's AC
  ("flag defaults off; `/assistant/` path unchanged when off") is satisfied by
  the helper alone, so it shipped clean — but it left a silent assumption (a
  persisted field exists somewhere) unstated.
- **Try:** Future stories should explicitly answer "does this story require a
  schema/migration companion?" in their AC, even when the answer is "not yet."
  Re-asking iteration question 3 (AGILE_PLAN §8): governance held structural
  here — no flag logic crept into a prompt or a UI toggle — so no guard-node
  pull-back needed this sprint.

## S0 — Inception (planning, not yet run)
- **Keep:** Scaffolding-first approach — every sprint's stubs land import-clean
  and collectible before any feature logic, so DoR is provable from day one.
- **Drop:** Nothing yet.
- **Try:** Hold the Sunday review honestly even solo — demo the flag-OFF
  no-change guarantee to yourself before accepting S0 stories.

<!-- New entries go ABOVE this line. Template:
## S# — <sprint name>
- **Keep:**
- **Drop:**
- **Try:**
-->
