# Hermes Agent (Nous Research): self-improvement and its gates

**Last Updated:** 2026-10-31
**Owner:** repository owner
**Refresh Trigger:** a Hermes Agent release that changes the curator, `skills.write_approval`, `memory.write_approval` or `agent/background_review.py`; a `hermes-agent-self-evolution` phase marked built; an owner answer in [the harness improvements plan](../../plans/2026-10-31-harness-improvements-plan.md#drafted-owner-questions-not-asked).

> **Point-in-time research (2026-10-31).** Docs only. A Haiku research agent wrote the first notes; the Opus planner re-checked every claim kept below against the primary page on 2026-10-31. WebFetch returns a model summary of each page, so the quotes below are as that summary gave them. Markers: **[V]** confirmed on the primary page; **[C]** changed after the re-check (the change is stated); **[X]** not confirmed, so dropped from the recommendations. Summary and status table: [00-README.md](00-README.md).

## 1. What it is

Hermes Agent is Nous Research's open-source agent (https://github.com/NousResearch/hermes-agent). Its README says it creates skills from experience and improves them during use. A separate repo, `hermes-agent-self-evolution`, holds an offline optimisation plan (§4).

## 2. In-agent self-improvement

- **Skills are agent-authored files.** The system prompt asks the agent to record a non-trivial workflow with `skill_manage` "when it worked out a multi-step workflow worth repeating", "when it hit errors or dead ends and found the working path" and "when the user corrected its approach" [V] (https://hermes-agent.nousresearch.com/docs/user-guide/features/skills). The research note's claim that the docs require `skill_view` before a patch is **[C]**: the skills page does not say so; the summary of `background_review.py` says skill edits go through `skill_manage`, "which enforces read-before-write".
- **Background review.** After a turn a forked review agent may run [V] (https://raw.githubusercontent.com/NousResearch/hermes-agent/main/agent/background_review.py): `_REVIEW_MAX_ITERATIONS = 16`; single-flight per parent agent; dangerous-command approval resolves to `"deny"`; "Write tools stay denied — autonomous maintenance must go through skill_manage's validation"; the dispatch whitelist adds only `read_file` and `search_files`. **Its input is the conversation**: on the same model it gets the "full snapshot"; on a routed model older turns are collapsed into a digest and "Recent turns follow verbatim" [V].
- **Memory.** `MEMORY.md` is capped at 2,200 characters and `USER.md` at 1,375; the injected copy is frozen per session; sessions are stored in SQLite (`~/.hermes/state.db`) with FTS5 [V] (https://hermes-agent.nousresearch.com/docs/user-guide/features/memory).

## 3. Gates

- **Ungated by default.** `skills.write_approval` and `memory.write_approval` both default to `false` ("false = write freely (default)") [V] (https://hermes-agent.nousresearch.com/docs/user-guide/configuration). When enabled, skill writes are staged under `~/.hermes/pending/skills/` and reviewed with `/skills pending | diff | approve | reject` [V].
- **Staged patch bound to its target: [X].** The note said a staged patch records its target and is refused if the target changed. Neither the configuration page nor the skills page says so. Dropped; the idea is evaluated on its own merits in the plan (rejected there).
- **Curator** (https://hermes-agent.nousresearch.com/docs/user-guide/features/curator) [V]: runs when `interval_hours` (default 168) has passed and the agent has been idle `min_idle_hours` (default 2); skills unused for `stale_after_days` (14) go stale and for `archive_after_days` (30) are archived; the automatic transitions are "deterministic, no LLM" (an LLM consolidation pass is off by default); `hermes curator restore`, `rollback` and `ledger` exist; it "never auto-deletes" (`purge` is explicit, TTL default 0). The page contradicts itself: another section says "30d unused → stale → 90d unused → archived" [V].

## 4. Offline self-evolution plan

`hermes-agent-self-evolution/PLAN.md` (https://github.com/NousResearch/hermes-agent-self-evolution/blob/main/PLAN.md) [V]:
- "Benchmarks are GATES, not fitness functions." The fitness function is task-specific; benchmarks check that a change "didn't break something else".
- Phase 1 success: "≥1 skill shows measurable improvement on its eval dataset (≥10% score increase)" with "No benchmark regression (TBLite score holds within 2%)" **[C]**: the note said "no benchmark regression"; the plan allows a 2% band.
- Judge rubric, each 0-1: procedure followed, output correct/useful, concise (within token budget); a length penalty so "variants that approach the limit get scored lower".
- "all changes deploy via PR, never direct commit".
- It is a plan: no phase is marked built.

## 5. What transfers to Asclexis

| Idea | Verdict | Where |
|---|---|---|
| Lifecycle report for agent-authored artifacts (which rule fired, which never did) | **Keep, report only.** Archiving or deleting a guard is a weakening (`gateNumstat` is additions-only, `rsi-loop.js:68-81`), so never-fired rules are reported to the owner, not retired | Plan row RSI-METRICS-VERSIONED |
| Benchmarks as gates, not fitness | **Already ours**: the replay set is a pass/fail gate (`rsi-loop.js:332`), not a score | — |
| Deterministic, no-LLM automatic pass | **Already ours**: `gateDiff` / `gateNumstat` run before any model critic (`rsi-loop.js:312-330`) | — |
| Review agent with dispatch-level tool limits | **Already ours**, stronger: proposers may edit only ALLOW, checked twice on the diff (`:312`, `:327`) | — |
| Reviewer reads the full conversation | **Reject**: metadata only (mod README `:17`) | Plan, rejected ideas |
| Self-authored skills applied by default | **Reject**: RSI-4 human gate | Plan, rejected ideas |
| Target-bound staged patches | **[X]** unconfirmed; rejected on merit | Plan, rejected ideas |
