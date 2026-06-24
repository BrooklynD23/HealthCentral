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
