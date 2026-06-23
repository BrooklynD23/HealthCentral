# Reconciliation — exploration vs. inherited planning bundle

**Last Updated:** 2026-06-23
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
