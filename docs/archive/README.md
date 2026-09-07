# docs/archive/ — Archive Policy

**Last Updated:** 2026-07-27
**Owner:** Project Lead
**Refresh Trigger:** A doc is archived or restored

This directory holds documentation that is retained for history only. Nothing
here is an active tracker, and nothing here should be read as describing
current plans, current status, or open work.

## What lives here

- `plans/` — superseded planning documents, one-time handoff prompts, and
  point-in-time findings reports that formerly lived in `docs/plans/`.
- `prd-phases/` — completed phase specs from the agent-overhaul PRD, formerly
  `docs/prd/phases/`.
- `agile-sprints/` — completed sprint records, formerly `docs/agile/sprints/`.
- `agile/` — point-in-time agile snapshots (standups, retros, reconciliation
  notes, exploration summaries), formerly `docs/agile/`.

## Policy

- **Retained for history, never an active tracker.** Every file moved here
  carries a "Historical Reference" banner pointing back to the live backlog.
- **Active work lives in [`docs/features/TASK_LIST.md`](../features/TASK_LIST.md).**
  If you are looking for current status, open tickets, or what to work on
  next, that file is the source of truth — not anything under this directory.
- **Relocate, never rewrite.** Files land here via `git mv` with no content
  changes beyond adding the required historical banner. The history of a
  decision is not edited after the fact.
- **One-way by default.** Material moves here when it is superseded or a
  sprint/phase closes out. It only moves back out of the archive if the
  underlying work becomes active again, which should be rare.
