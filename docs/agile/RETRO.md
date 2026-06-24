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
