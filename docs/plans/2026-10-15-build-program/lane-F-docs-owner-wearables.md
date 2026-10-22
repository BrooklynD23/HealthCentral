# Lane F — Docs, Owner Queue, Wearables Consumer Map — Build Design

**Last Updated:** 2026-10-21 (§2.15 FEATURE-LIST-LICENCE planned on `b902e0f`; #261 round 1: lint interpreter stated); 2026-10-19 (F-4 and F-9 rechecked after owner rows P8-B2, SHOW-FREEZE; status cells fixed); 2026-10-15
**Owner:** repository owner
**Status:** DESIGN — nothing here is implemented. Owner answers are quoted from [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md); this file records no new approval. Every "default" or "recommended" is the lane designer's, not the owner's.
**Refresh Trigger:** any merge of #72, #74, #84, #94, #68 or a W-2 / W-3 / W-7 / W-8 / P6 / P7 PR; an owner answer to any gate in §5; P8 Brief 2 signed; any commit to `docs/architecture/pipelines.md`, `docs/architecture/README.md`, `docs/architecture/backend.md`, `docs/compliance/data-privacy.md`, `docs/features/TASK_LIST.md`, `skills/asclexis-guardrails/SKILL.md` or `CS4610_Report_Demo/README.md`.
**Base measured:** `origin/main` @ `3b2236c` (2026-10-15). Every `file:line` without a ref is at this base. Open PR branches read with `git diff origin/main...origin/<branch>` on 2026-10-15 and assumed to merge as-is.

> **For agentic workers:** one item = one PR on its own worktree. Docs items: the "test" is the grep; paste the Before match (exactly 1) and the After grep. Never tick an owner box and never write an owner answer that is not a row in owner-decisions. Merged plans stay authoritative; this file gives only their corrections on today's main.

**Baseline note:** `CLAUDE.md:30` and `AGENT.md:76` read **1574 collected** at `3b2236c`, not the 1501 the dispatching orchestrator quoted. Not re-measured (no pytest on this host). Every docs item below leaves the count unchanged; only F-10 (#68) moves it (+7).

**Prior art reused, not repeated:** readiness packs [P4-deferred](../../../audit/2026-09-25/waves/scaffold/P4-deferred.md), [W-10b](../../../audit/2026-09-25/waves/scaffold/W-10b.md), [G-C2](../../../audit/2026-09-25/waves/scaffold/G-C2.md), [RTN](../../../audit/2026-09-25/waves/scaffold/RTN.md), [SHOWCASE](../../../audit/2026-09-25/waves/scaffold/SHOWCASE.md) (all measured 2026-10-07 @ `6b4dd84`). Their L1/L2 briefs stay usable once the deltas below are applied.

---

## 1. Items

| ID | Item | Kind | Source | Plan on main? | Depends on | Readiness |
|---|---|---|---|---|---|---|
| F-1 | P4-deferred N8: D11 citation vocabulary (4 files) + two stale `pipelines.md` lines | DOCS | [P04](../2026-09-27-P04-doc-drift-sweep-amendment.md) `:911-941`; program `:431` | yes → delta §2.1 | W-5 (#34) merged | ready |
| F-2 | P4-deferred N10: guardrails skill names break-glass | DOCS | P04 `:956-987` | yes → delta §2.2 | W-6 (#32), W-10 (#53) merged | ready |
| F-3 | P4-deferred F6: D12 "not yet implemented" flip | DOCS | P04 `:998` | yes → delta §2.3 (Before texts changed) | W-6 + W-10 merged | ready |
| F-4 | P4-deferred N9: `hipaa-controls.md:169` key rotation | DOCS | P04 `:943-954` | yes → §2.4 | P8-B2 answered 2026-10-19: B + A (`owner-decisions-2026-09-27.md:297`) | in progress (#200, claimed 2026-10-20; blocked once on the embedding-bundle environment failures, resumed by L0) |
| F-5 | P4-deferred F1–F5 flips | DOCS | P04 `:993-997` | yes → trigger table §2.5 | W-3, W-2, W-7, W-4 (#72), W-8 | blocked-on-item |
| F-6 | W-10b privacy status flip | DOCS | [W10 plan](../2026-09-27-W10-governance-invariant-amendments.md) Task 6 `:1489-1499`; program `:434` | yes → delta §2.6 | W-2 (lane E E-1), W-3 (lane A) | blocked-on-item |
| F-7 | G-C2 OpenWiki generation (owner runs, session reviews) | OWNER → DOCS | [W11b](../2026-09-27-W11b-roadmap-items-gc1-gc4.md) G-C2; program `:447`; G-C2-DEFER (`owner-decisions:77`) | yes → delta §2.7 | owner run (OW-4) | blocked-on-owner |
| F-8 | RTN nightly doc-drift routine | OWNER (routine config) | [RTN spec](../2026-09-27-nightly-doc-drift-routine-spec.md); program `:451` | yes → delta §2.8 | spec §9 Q1–Q6 | blocked-on-owner |
| F-9 | SHOWCASE senior-report update + demo | DOCS + demo | [showcase plan](../2026-09-27-senior-report-showcase-plan.md); program `:452` | yes → delta §2.9 | SHOW-AUDIT (A) and SHOW-DATE answered; F-10 (#68) and W-8 (#168) merged; O-1…O-7 gate only their own tasks | ready (§2.9 "Executable 2026-10-19") |
| F-10 | #68 RSI-loop research + session-log hook landing | DOCS + harness | PR #68 @ `de5b700`; PR68-SYNC (`owner-decisions:158`) | PR → landing steps §2.10 | merges **last** (OW-5) | blocked-on-PR |
| F-11 | Close #61 | OWNER (gh) | PR #61 @ `9c8f297`; PR61-CLOSE (`owner-decisions:141`) | — → §2.11 | #72 merged | blocked-on-PR |
| F-12 | Wearables program (#94) as consumer: P6/013 and shared-file map | map (no code) | PR #94 @ `4ff5d43`, 14 plans + program 00 + tickets | PR → §2.12 | M0: OW-W0 + owner plan-set approval; #94 merge | blocked-on-owner |
| F-13 | Owner queue (OW-*, OM-*, MM-*, OW-W*) compiled; `TASK_LIST.md` queue refresh | DOCS | [TASK_LIST](../../features/TASK_LIST.md) `:76-104`; wearables program 00 §10 | — → §2.13 | #94 merged (so OW-W* links resolve) | blocked-on-PR |
| F-4-FOLLOWUPS | KEY-05 matrix wording, `ci.yml` SLOT-RULE-2a comment, `TASK_LIST.md:220` Q-COV note (takes TASK-LIST-COV) | DOCS | PR #200 and #207 review MINORs | yes → §2.14 | F-4 (#200), Q-COV-GATE (#207) merged | ready |

Graph: F-1, F-2, F-3 are independent docs PRs today (F-1 and F-3 share no file). `F-1 → F-5(F1, F2, F4)` on `pipelines.md`; `F-3 → F-5(F3, F5)` on `README.md`/`backend.md`; `E-1 + W-3 → F-6 → WEAR-14`; `#72 → F-11`; `F-10 → F-9` (`CS4610_Report_Demo/README.md`); `#94 → F-13`. No lane-F item is a code L1; none needs the 12 GB box's code slots.

---

## 2. Per-item design / delta

### 2.1 F-1 — N8 delta (plan @ P4-core → main `3b2236c`)

**Trigger re-run on main:** `grep -n "YOUR_RESULTS:N\]\|REFERENCE:N\]" src/backend/modules/rag.py` → `:130`, `:135`, `:136`, all "Context labeled …" label wording; `citation_pattern = r"\[cite:(\d+)\]"` at `:822`. Hit. `REPORT FACTS`/`GENERAL INFO` split still at `:130-131` → keep that clause (Step 1).

| Plan row | Now | Correction |
|---|---|---|
| `pipelines.md:111` | `:126`, text identical | anchor `:126` |
| `00_features_index.md:38`, `04_self_improvement_loop.md:113`, `TASK_LIST.md:63` | same lines, Before strings match | none. `services/assistant.ts:378` cited in the After text: re-check at dispatch |
| Step 3 sweep `grep -rn … . \| grep -vE "^\./…"` | filters nothing on this host (paths print without `./`) | use `git grep -n "YOUR_RESULTS:N\|REFERENCE:N" -- '*.md' ':!docs/archive' ':!docs/plans' ':!docs/research' ':!audit' ':!docs/capstone-report'`. Expected hits only: `AGENT.md:89`, `CLAUDE.md:61`, `docs/architecture/pipelines.md` (0 after the edit), `docs/brand/brand-guidelines.md:37-38`, `docs/compliance/ai-safety.md:20`, `docs/features/00_features_index.md`, `docs/features/01_lab_result_interpreter_architecture.md:199,205,217,218`, `docs/features/04_self_improvement_loop.md` |
| "`CLAUDE.md:62` not owned; stays unchanged while GOV-D11 unsigned" | GOV-D11 signed 2026-10-07; W-10 (#53) rewrote it (`CLAUDE.md:61` now names `[cite:N]` as the marker) | nothing to do; drop the caveat |

**Folded into the same PR (second commit, `pipelines.md` only), owner question P4D-PIPELINES-127:**

1. `pipelines.md:127` says a prohibited-advice match is "answer still served (W-4 pending)". False since SAFE-CHAT (#44): `api/assistant.py:886-888` replaces the answer with `ESCALATE_TEMPLATE`. After (two lines replace `:127`):
   `    SAFE -->|"prohibited-advice match"| ESC["escalation template (SAFE-CHAT)"]`
   `    SAFE -.->|"missing citations or faithfulness < 0.6:<br/>is_valid=false, answer still served (W-4 pending)"| OUT`
2. `pipelines.md:209-211` "to be named as deliberate exceptions in `CLAUDE.md` and `docs/compliance/data-privacy.md` (work item W-10)" — W-10 merged (`CLAUDE.md:59` names CSV/JSON). After: "named as deliberate exceptions in `CLAUDE.md` and `docs/compliance/data-privacy.md`". The W-2 half of that sentence stays for F2.

If the owner answers "wait" to P4D-PIPELINES-127, ship commit 1 alone; F4's Before text is then unchanged.

**Acceptance (run in the worktree, paste outputs):** `grep -c 'cite:N\] markers (context labels are not citations)' docs/architecture/pipelines.md` → 1; `grep -c "ground in two citation layers" docs/features/00_features_index.md` → 0; `grep -c "format preserved" docs/features/04_self_improvement_loop.md` → 0; amended sweep → only the expected list; with commit 2: `grep -c "W-4 pending" docs/architecture/pipelines.md` → 1 (the dashed edge), `grep -c "work item W-10" docs/architecture/pipelines.md` → 0; `python3 scripts/docs_lint.py`, `python3 scripts/generate_docs_index.py --check`, `python3 scripts/harness_drift_check.py`, `python3 scripts/repo_hygiene_check.py` → pass; `git diff --name-only origin/main...HEAD` → the 4 N8 files. Mermaid edits are parsed by no CI gate: render `pipelines.md` once on Windows or record "Mermaid UNCHECKED".

**Rollback:** `git revert` the PR; docs only.

### 2.2 F-2 — N10 delta

Trigger hits: `core/external_runner.py:95` (`redaction_bypass_active`), `:112` (`BREAK_GLASS_AUDIT_EVENT`); `pages/ExplainAssistant.tsx:475`, `pages/LabInterpreter.tsx:194` (`redaction_break_glass`). Before text `skills/asclexis-guardrails/SKILL.md:62-64` matches.

Changes: the closing note "W-6 Q1 and Q3 are open" is stale (BG-REACH `:40`, W6-Q3 `:44` signed); delete that note from the PR body. The scaffold's option C ("hold N10 until W-10") is satisfied: `CLAUDE.md:59` already names break-glass as the only bypass (GOV-BG). After text: the plan's, verbatim. Acceptance: `grep -c "bypass redaction for any reason" skills/asclexis-guardrails/SKILL.md` → 0; `grep -c "keep break-glass" skills/asclexis-guardrails/SKILL.md` → 1; relative-link check; 1 file in the diff. Reviewer: security-reviewer confirms the text grants nothing beyond D12 + GOV-BG.

### 2.3 F-3 — F6 delta (Before texts changed by P4-core N4/N5)

| File | Before (main) | After |
|---|---|---|
| `docs/architecture/README.md:111-112` | `Naming the exception in \`CLAUDE.md\` is` / `**approved, not yet implemented** (work item W-10).` | `\`CLAUDE.md\` names the exception (Hard invariants, D12).` |
| `docs/architecture/backend.md:107-108` | `and naming it in \`CLAUDE.md\` is work item` / `W-10, not yet implemented)` | `and \`CLAUDE.md\` names it)` |

Trigger: `grep -n "core/external_runner.py" CLAUDE.md` → `:25` and `:59` hit. Plan acceptance `grep -rc "W-6" docs/architecture → 0` cannot hold ("landed in W-6", "(work item W-6)" are correct text); use `grep -c "work item W-10" docs/architecture/README.md docs/architecture/backend.md` → `0` and `0`. Match on whitespace-collapsed text (both Befores wrap). Commit: `docs(architecture): W-10 landed — drop the pending note (F6)`.

### 2.4 F-4 — N9 (no change to the plan)

`hipaa-controls.md:169` still `| Key rotation | Medium | Manual via password change |`; packet ledger row `audit/2026-09-25/gated-items-decision-packet.md:421` still `☐ approve ☐ reject ☐ defer`, Brief 2 `Owner decision:` at `:117` blank. The overclaims at `:49`, `:52` were fixed by W-10 (W10-HIPAA) — drop scaffold question 4. Run the plan's N9 After row for the signed option only.

**Executable 2026-10-19 (rechecked on `origin/main` @ `d42dba9`).** The owner answered P8-B2 = **B + A** (`docs/capstone-report/owner-decisions-2026-09-27.md:297`: "Approve true DEK rotation as a future guarded maintenance op; fix `hipaa-controls.md` wording now; F-4 writes 'Owner-approved 2026-10-19, not yet implemented'."). Two corrections make N9 runnable as written:

1. **Trigger.** N9's trigger is the ticked packet ledger row (`gated-items-decision-packet.md:421`). That row is still unticked, and agents never tick owner boxes (RUNBOOK §9 item 2). The owner-decisions row is the gate record (RUNBOOK §4 step 3), so the trigger is met by `:297`. The packet tick, if wanted, is L0's.
2. **After row.** Use N9's "B or C approved" row with `<signed date>` = `2026-10-19`. No DEK-rotation implementation plan exists, so `<link>` points at the decision (packet Brief 2, or the owner-decisions row), never at a plan.

Before is still exactly one hit at `docs/compliance/hipaa-controls.md:169` (re-checked). The item is claimed as #200 (draft, 2026-10-20), and its diff follows both corrections. It posted "blocked: tell L0" once, only for the 5 known environment failures from the missing embedding bundle; L0 resumed it after the bundle fix (Task 0 re-run 2026-10-20).

### 2.5 F-5 — F1–F5 trigger table (who unblocks what)

| Task | Unblocked by (lane) | Trigger (must hit) | Before-text status on main |
|---|---|---|---|
| F1 | W-3 (lane A) | plan `:993`'s grep already hits today (`api/observations.py:115`, a different model). Use `grep -n -A12 "^class TrendPoint" src/backend/api/observations.py \| grep -c user_verified` → 1 **and** `grep -c "Observation.user_verified == True\|Observation.user_verified.is_(True)" src/backend/modules/rag.py` → ≥ 1 (both 0 today) | MATCH: `pipelines.md:46`, `:66-70` |
| F2 | W-2 (lane E E-1); W-10 half done | `grep -n "def redact_summary_data" src/backend/modules/export.py` → 1 hit (0 today). Plan `:994`'s `RedactionEngine` grep already hits today (`:533`, `:637`, visit-prep), so it cannot be the trigger | MATCH `:208-211`; after F-1 commit 2 the tail ends at "deliberate exceptions in …" |
| F3 | W-7 (lane B B-5) | plan `:995` | MATCH: `README.md:114-117`, `backend.md:103-105` |
| F4 | #72 merge (lane B B-7 / MM-1) | `grep -n "legacy-evals" .github/workflows/ci.yml` (0 today) | if F-1 commit 2 landed, Before = the dashed edge from §2.1; else `pipelines.md:127`. Template name: read #72's merged code. F4 also adds the `LEGACY` node + table row to `docs/architecture/ci-and-quality-gates.md` (P04 `:996`); #72 itself does not edit that file |
| F5 | W-8 (lane A) | plan `:997` | MATCH, wrapped across `README.md:103-104` |

Each is one `docs(architecture):` commit, its own PR, collected unchanged. F1, F2, F4 serialise on `pipelines.md`; F3, F5 on `README.md`. F4 also shares `ci-and-quality-gates.md` with lane E E-3 Task 9 and lane A W-8 (`:58`): any order, each adds only its own node/row, the second lander rebases (lane A: F4 usually precedes W-8). F3 trigger re-checked: `modules/model_selector.py:457` still imports `llama_cpp`, so it does not hit before W-7.

### 2.6 F-6 — W-10b delta (Task 6 on main `3b2236c`)

**Committed status lines W-10b flips (`docs/compliance/data-privacy.md`):**

| Block | Lines | Variant now | Becomes I when |
|---|---|---|---|
| DP-2 W-2 (Redaction scope) | `:80-85` | P | W-2 merged + 4 criteria |
| DP-2 W-2 (export list) | `:190-192` | P | same |
| DP-3 W-3 (Unverified Extracted Values) | `:219-226` | P | W-3 merged + 4 criteria; extras per W10B-D4-EXTRAS |
| DP-4 W-6 (external API) | `:262-266` | U (`2f0cb6f`; conformance unverified) | criterion 4 holds, see below |

**Still valid:** the four variant-I criteria (W10 plan `:502-528`), stop gate S6, the one-file rule, the commit message.

**Corrections:** (1) W-6's HTTP test `test_hc_ext_004_external_api_settings_reports_break_glass` (`tests/test_external_runner_hardening.py:263`) reaches `route_client` via the same-file helper `_get_external_api` (`:244-247`), which criterion 4 does not accept; `test_hc_ext_004b…` (`:271`) calls it directly (`:276`, `:285`). Owner question W10B-RC decides. (2) **Contract for W-2 and W-3 (lanes E and A):** their named HTTP tests (W-2 HC-EXPR-003, W-3 HC-VER-002) must call `tests.support.routes.route_client` inside their own function body, and their PR bodies must paste red-first output and one break-it run; otherwise W-10b must write U, not I. (3) W10B-SPLIT default: one PR after the last of W-2 / W-3; the DP-4 line may ride in it. (4) `$WT` path in Task 6 Step 1: use `../hc-w10b` (caller convention), not `HealthCentral-w10b`.

**Shared file order:** `data-privacy.md`: W-10 (done) → F-6 → WEAR-14 (wearables docs plan edits the same file). WEAR-14 must re-anchor after F-6.

**Acceptance:** plan Step 4 (`w10_assert.py`, lint, index, `git diff --cached --name-only` = 1 file). Rollback: revert.

### 2.7 F-7 — G-C2 delta

**State:** G-C2-DEFER (`owner-decisions:77`, 2026-10-07): "Not in Wave 4 … the run is still yours to schedule." S-C2-1/2/3 unsigned. `openwiki/` holds only `README.md`; status line `openwiki/README.md:15`. Queue item OW-4 exists, so the owner may still schedule it.

| Plan / pack citation | Now |
|---|---|
| referrer `AGENT.md:20` | `:20` (stub wording) — MATCH |
| referrer `docs/00_architecture_plans_index.md:58` | `:63` |
| `CLAUDE.md:65-67` OpenWiki paragraph | `:66` (one paragraph line) |
| `openwiki/README.md:28` "Requires an LLM API key" | `:27` |

Design unchanged: the owner runs Task C2.1 in `../hc-gc2` from `origin/main` and pushes `docs/gc2-openwiki-generation`; an L1 runs Tasks C2.2–C2.3 with the pack's briefs (§6 of the G-C2 pack). New collision: generated `openwiki/` pages will describe whatever lands by then; nothing depends on them (advisory). `CLAUDE.md:66` "generation has not run yet" goes stale on merge; fix in its own one-line governance commit (GC2-CLAUDE-66), never inside G-C2.

### 2.8 F-8 — RTN delta

**Still valid:** platform choice, checks C1–C9, report template, guardrails §6, read-only audit, kill switch. §9 unsigned (`spec:165-167`).

| # | Spec text | Now | Correction (one `docs:` commit, only after RTN-Q1 = yes) |
|---|---|---|---|
| 1 | `:7` "Until P0-B2 is signed and merged it is untracked on `main`" | merged (PR #19) | delete the sentence |
| 2 | `:171` "Until P0-B and P0-B2 merge … C3 reports `SKIPPED`" | all on main | delete |
| 3 | §2 "back on 2026-03-08" | past date | next PST→PDT switch is 2027-03-14 |
| 4 | §7 / Q4 model `claude-sonnet-5` | id unverified against today's lineup | read the schedule skill's routine default at creation; record the id used |
| 5 | Refresh trigger "a new docs gate script lands" fired: `scripts/time_source_lint.py` (`d4b70dd`, 2026-10-08) | CI `docs` job runs it and `feature_list_lint.py` on every push (`ci.yml:28,34`) | add neither to the routine; note it in §3 |
| 6 | §6.3 "No patient data" | after #68 merges, the committed `.claude/settings.json` hooks also fire inside the routine session; they write git-ignored `.claude/logs/session-log.jsonl` | C9 (`git status --porcelain --untracked-files=no`) is unaffected; add one line to §10 Known limits |

Collected baseline it compares (C5): `CLAUDE.md:30`, `AGENT.md:76` = 1574. #68's §5 #3 "weekly failure-miner" reuses this routine; it is not licensed (never asked) and is out of scope.

### 2.9 F-9 — SHOWCASE delta

**State:** plan unaudited, never reviewed; O-1…O-7 unsigned except O-4's location (SHOWCASE-O4 `:121`: "Yes, docs/reviews/"; plan `:810`, `:864`, `:880` already say `docs/reviews/`). No showcase date. Claims ledger has rows C1–C10 (`claims-ledger.md`, Last Updated 2026-09-28); the plan adds C11+.

**Fired refresh triggers since the pack:** W-10 (#53), P5 (#54), RCC ×3, SAFE-CHAT (#44), SAFE-INTERP (#48), DDI (#41), P2 notifications (#31), UTC sweep (#93). Corrections the refresh must carry:

1. §6.4 **F-NOTIFY** ("reminders built but not started … P2") is false since #31: replace with a demo step or drop it.
2. §6.2 5:45 "metformin dose" step: legacy path now escalates (SAFE-CHAT, `api/assistant.py:886`); the default agent path abstains. The presenter line must name which path the dry run showed.
3. §6.3 check 4 names `dev.ps1` only; `dev.sh` exists (#86) — Windows demo stays on `dev.ps1`; no change, note only.
4. Task 0 Step 2's `--grep=<plan file>` prints 0 for merged phases; use `git merge-base --is-ancestor <merge sha> HEAD` per phase.
5. Every `main@40f590e` line and figure: Task 1 re-measures them (that is its job); the collected figure is 1574, vitest/Playwright counts per W-11a PR-4 and later.

**Shared files:** `CS4610_Report_Demo/README.md` — #68 (F-10) edits `:10-13`; SHOWCASE Task 5 edits the same file → **F-10 first**. `docs/capstone-report/claims-ledger.md` — serial with W-8 (its plan edits it).

**Demo needs no model** (agent path, template answers; plan §6.2), but needs a warm embedding cache (check 7) and states F-ENC on Windows (KEY-08: no `sqlcipher3` wheel for Win Py 3.13). Not an MM item.

**Executable 2026-10-19 (rechecked on `origin/main` @ `d42dba9`).**

- **Gates.** SHOW-AUDIT answered 2026-10-17 (`owner-decisions-2026-09-27.md:232`): "**A: refresh + Codex plan review, then run**". SHOW-DATE (`:243`, freeze = showcase − 7 days) plus SHOW-FREEZE (`:277`): showcase **2026-10-31**, claim freeze **2026-10-24**, so `{FREEZE_DATE}` = `2026-10-24`. O-1…O-7 (plan §13, `:861-867`) are still unsigned, but each gates only its own task or commit: O-2 Task 5 / C4, O-1 Task 7 publish / C5, O-4 Task 8 / C6, O-3 the demo `.env` step, O-7 §8 Edit 5, O-6 Task 10 Step 2. Skip those and list them in the PR body (RUNBOOK §4 step 3). They do not block the item.
- **Dependencies.** F-10 merged (#68, `3536cc6`) and W-8 merged (#168, `26106ee`; it was the other `claims-ledger.md` writer). No open PR touches a F-9 file on `5750a97` (#185, #198 and #201 have merged; #200 edits only `hipaa-controls.md` and the index).
- **Order inside the item (SHOW-AUDIT A).** (1) Refresh the plan in place: Task 0's `/mnt/c/...` worktree commands become the RUNBOOK §3 claim; Task 0 Step 2 uses `git merge-base --is-ancestor` (correction 4); carry corrections 1-5 above; set `{FREEZE_DATE}` = 2026-10-24. Commit the refresh first. (2) Run a Codex adversarial plan review (RUNBOOK §10.2, read-only) on the refreshed plan and post its output on the PR. A BLOCKER stops the item (RUNBOOK §8). (3) Then run Tasks 1-4, 6 and 7 (the ledger check; committing the copy, C5, needs O-1) and Task 10 Step 1, plus each O-gated task whose gate the owner has signed by then.
- **Who.** Task 9 (demo dry runs on the Windows demo machine, Wi-Fi off) is the owner's. The rest is a claude docs item.
- **Deadline.** Task 10 runs on the freeze date, 2026-10-24, and needs O-6. If the PR is not ready by then, the item stops and L0 asks the owner whether to move the freeze.
- **Files** (plan §14, `:875-881`): `docs/plans/2026-09-27-senior-report-showcase-plan.md`, `docs/capstone-report/claims-ledger.md`, `docs/capstone-report/report-outline.md`, `docs/capstone-report/README.md`, `docs/capstone-report/architecture-overview.md`, `docs/capstone-report/asclexis-showcase-2026-10-24.html` (built in Task 6; committed only with O-1), `CS4610_Report_Demo/README.md` (O-2 only), the `docs/reviews/` files O-4 names (O-4 only), `docs/INDEX.md`, `docs/_link_graph.json`. The queue row's old list missed the outline, the capstone index, the architecture overview and the HTML copy.

### 2.10 F-10 — #68 landing steps

**State:** branch `docs/rsi-loop-research` @ `de5b700`, 141 commits behind main, 2 ahead; `gh pr view 68` → `CONFLICTING`. `git merge-tree --write-tree origin/main origin/docs/rsi-loop-research` → conflicts in exactly `AGENT.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/capstone-report/owner-decisions-2026-09-27.md`. PR68-SYNC (`:158`): "An agent merges origin/main into the branch (no history rewrite, no force-push), keeps every owner-decisions row from both sides, re-measures the count. #68 still merges last."

Content: 2 docs (`docs/plans/2026-10-10-rsi-loop-applicability-report.md`, `…-rsi-audit-handoff-prompt.md`), `.claude/hooks/session_log.py` (metadata only, always exit 0), `.claude/settings.json` (PostToolUse / PostToolUseFailure / SessionEnd, async), `.gitignore` un-ignores exactly those two, `tests/test_session_log_hook.py` (7 tests), HC-AGENTS-002 widened, `CS4610_Report_Demo/README.md:10-13`, owner row HOOKS-COMMIT (present only on the branch).

**Steps (one L1, after every other open PR has merged — OW-5):**

1. `git -C <wt> merge origin/main` (no rebase, no force-push).
2. `CLAUDE.md:30,34`, `AGENT.md:76`: take main's text, then write the **measured** count (expected main N + 7; never compute it).
3. `owner-decisions`: keep main's file; insert the branch's HOOKS-COMMIT row in date order; `**Last Updated:**` = main's line with "HOOKS-COMMIT (2026-10-10)" added.
4. `docs/INDEX.md`, `docs/_link_graph.json`: regenerate with `python3 scripts/generate_docs_index.py` on the merged tree; never hand-merge.
5. Re-check `docs/features/TASK_LIST.md` (auto-merged): the #68 session note must sit in date order and say "1388" only as history.
6. Run: `pytest tests/test_session_log_hook.py tests/test_claude_agent_definitions.py -q` (7 + 8 passed), collect-only count, the 4 docs gates, `git check-ignore --no-index -q .claude/settings.json; echo $?` → 1.

**Out of scope (later, unlicensed):** report §4 patient-facing loops, §5 #2–#5, §6 telemetry (RSI-Q3/Q4 answered for a future plan, not built here). The report's §8 RL-export bug is fixed by #82 (lane D sync); RL-EXPORTS PR-1 is merged (`6d9dbfd`). Minor: the 7 new tests carry no `HC-XXX-NNN` id (CLAUDE.md §4 naming); a docstring id per test is optional, never a logic change.

**Rollback:** revert the merge commit; nothing persistent beyond the git-ignored log file.

### 2.11 F-11 — Close #61

`9c8f297` is **not** an ancestor of #72 (`merge-base --is-ancestor` → 1). #72's first commit `80a302b` amends the plan file `docs/plans/2026-09-27-W04-legacy-abstain-and-eval-gate.md`; #61 instead edits `audit/2026-09-25/waves/scaffold/W-4.md` (+171) and adds `audit/2026-09-25/swarm-2026-09-27/reviews/W-4-amend-codex.txt` (verdict REVISE, 2 BLOCKERs) and `W-4-amend-prompt.md`, which exist nowhere else. The owner's answer stands ("Close after #72 (Recommended)"). Steps after #72 merges: `gh pr close 61 --comment "<superseded by #72 80a302b; review evidence kept on branch docs/w4-plan-amend @ 9c8f297>"`. **Do not pass `--delete-branch`**, so the Codex evidence stays reachable (open question Q-F4).

### 2.12 F-12 — Wearables consumer map (#94)

**State:** #94 `docs/wearables-plans` @ `4ff5d43`, 38 files, docs only. Plans 00–15 + tickets, base `8234990`. Since that base, of every product file the plans cite, only `api/export.py` (+1 line shift, e.g. `_fetch_observations` `:131` → `:132`) and `core/time.py` (adds `NaiveUtcDatetime`) changed. No code before M0 (OW-W0 notes + owner approves the plan set). `security/input_validator.py` and `core/audit.py` diffs are owner-signed **exactly as written** (WEAR-D4).

**Which plans need P6 / `013`:** none has a hard dependency on P6 (plan 02 §6: "The wearable tables do not depend on P6 (explicit deletes)"). Two plans add profile migrations and are numbered after P6 by lane C's C-PMIG contract:

| Plan | Migration | Effect if C-P6 merges first | Effect if C-P7 merges first |
|---|---|---|---|
| WEAR-02 | `0NN_wearables` (expected `016`) | `wearable_daily_metrics.import_id` CASCADE becomes **enforced**; declare `ondelete=` in model + DDL and add a `core.fk_audit.FkCheck` row to `PROFILE_CHECKS` (HC-FKA-004); its reset test must use `tests.support.db.fk_profile_engine`, not an FK-off in-memory DB; head literal = `tests.support.migrations.PROFILE_HEAD` (one line), not 4 literals | append 3 models to `api.profiles._SYNTHETIC_RESET_MODELS` (children first) instead of the inline tuple `api/profiles.py:498-514`; owner gate RESET-APPEND (lane C) |
| WEAR-15a | `0NN_symptom_journal` (expected `017`, after WEAR-02) | no FK; head constant only | append 1 model; RESET-APPEND |
| WEAR-07 | none | explicit delete order (reviews → metrics → import) stays correct under FK ON | — |

All three plans still list `015_audit_outbox`; that claim is **withdrawn** (AUDIT-ORDER design D, merged #78 with no migration; lane C §3.0). Lane D's D-2 adds `NNN_adaptive_windows_local` (data-only) under C-PMIG; numbers follow merge order, so `016`/`017` above are illustrative and shift by one if D-2 lands before WEAR-02. Cite WEAR migrations as slug + "head+1 at final rebase". Head literal: before C-P6 the 4 literals (WEAR-02 Task 3.4 already lists them), after C-P6 the one constant `PROFILE_HEAD`. Pre-merge check is C-PMIG §3.0 #6.

**Shared files with other lanes (merge serially; the second lander rebases):**

| Shared file | Wearables plans | Other claimant | Rule |
|---|---|---|---|
| `src/backend/migrations/profile/versions/` + head literal | 02, 15a | C-P6, C-GAM2B, C-GC1, D-2 | C-PMIG; OW-W13 |
| `src/backend/api/profiles.py` (reset tuple `:498-514`, `delete_profile` `:773`, reset route `:477`) | 02, 15a, 09a-journal (OW-W12) | C-P7, E-2 (W-11a PR-1, OG-1) | after C-P7 use `_SYNTHETIC_RESET_MODELS`; delete-path edit is owner-gated (OW-W12) |
| `src/backend/core/profile_database.py:409-417` (`create_all` imports) | 02, 15a | C-P6; SQLITE-MIX follow-ups | serial |
| `src/backend/core/audit.py` (`ALLOWED_ACTIONS` `:36`, `STRING_DETAIL_KEYS` `:69`) | 02, 15a (OW-W11), 06, 07 use it | E-2 (OG-1 rows); C-DUPAUD option b (`STRING_DETAIL_KEYS`, gate DUP-AUDIT-KEY) | any order; second lander re-anchors without changing its owner-signed content (lane C §1); security-reviewer on every diff; WEAR-D4 / OW-W11 exact text |
| `src/backend/api/export.py`, `src/backend/modules/export.py` | 09a-metrics, 13 | E-1 (W-2), C-GC1 | E-1 first (lane E); 09a-journal also waits on G-C1 refresh trigger |
| `src/backend/security/input_validator.py` | 06 | — | WEAR-D4 exact diff |
| `src/backend/core/config.py` | 01, 06, 07 | — | serial within WEAR |
| `src/backend/main.py` (startup sweep), `src/backend/api/__init__.py` | 06, 01 | — | serial within WEAR |
| `src/backend/core/time.py` (read only by WEAR) | 03 (refresh trigger "any edit to `core/time.py`"), 02, 07, 11, 12 cite it | D-1 appends helpers after `to_naive_utc` | WEAR-03 cites pre-UTC-SWEEP `:9,:14,:24`; main is `:12,:17,:27`. Refresh WEAR-03 citations once, after D-1 merges (D-1 is append-only, so the anchors hold) |
| `src/frontend/src/components/layout/Sidebar.tsx` | 10 | #74 Tailwind 4 (E-4) | #74 first, then WEAR-10 rebases |
| `src/frontend/src/services/index.ts`, `App.tsx` | 10 → 07b → 08b → 15b | #84 (services/index.ts) | #84 first |
| `src/backend/requirements.txt` | 11b (`garmin-fit-sdk==`) | E-5 npm only | OW-W7 first |
| `docs/compliance/data-privacy.md`, `docs/features/TASK_LIST.md`, `docs/architecture/*` | 14 | F-6, F-1, F-3, F-5 | lane F items first |
| `CLAUDE.md:30,34`, `AGENT.md:76` count slots | every code plan | every code PR | SLOT-RULE: measure, never compute |

**Wave map (program 00 §6):** WA = 01 ‖ 02 ‖ 03 · WB = 04a → 04b ‖ 05, then 06 · WC = 07 ‖ 10, then 07b, 08a, 08b · WD = 15a ‖ 09a-metrics, then 15b, 09b-metrics, 13, 14; 09a/09b-journal only after OW-W9 · WE = 11a, 12, then 11b if needed. WF was removed (WEAR-13 moved into WD by WEAR-D7). At most 2 code L1s at once.

### 2.13 F-13 — Owner queue (all OW-*, OM-*, MM-*, OW-W*)

Source: `TASK_LIST.md:80-104` and wearables program 00 §10 (on #94). "Unblocks" = the first item that cannot start or merge without it.

| ID | What | Unblocks | State |
|---|---|---|---|
| MM-1 | W-4 20-question real-model count (#72) | #72 merge → F-11, F4, W-3 → F1 + F-6, W-8 → F5, G-C3a, G-C5 | open; needs-model-machine |
| MM-2 | PARA-1-R3 judge measurement | owner sign-off on PARA-1-R3 numbers (lane B B-3/B-4) | blocked on OW-3 + B-3 PR |
| MM-3 | full suite with a real embedding model | evidence only (pass line in `CLAUDE.md` §4); blocks nothing | open |
| MM-4 | real-app smoke with a local model | confidence for B-3 / B-5 and #84 widget; not a SHOWCASE gate | open |
| OW-1 | commit owner-decisions rows | — | rows are on main (`a44ad1f` "owner rows 2026-10-12/13 + owner/model-machine queue"); box unticked — owner ticks |
| OW-2 | Tailwind 4 screenshot review (TW4-SHOTS) | #74 merge (E-4) → E-5, WEAR-10 rebase | open |
| OW-3 | sealed set S5 | MM-2 | open |
| OW-4 | G-C2 tool run | F-7 | open; G-C2-DEFER says owner schedules |
| OW-5 | merge queue: lane D order (#95 → #97 → #99 → #82 → #84), #74 after OW-2, #72 after MM-1, close #61, #68 last | F-10, F-11, every count-slot PR | open |
| OM-1 = OW-W0 | Apple export notes (+ sleep overlap, prolog, duplicates) | M0 → every WEAR code wave | open |
| OM-2 = OW-W3 | Garmin export notes | WE (11a, 12, 11b) | open |
| OM-3 | Samsung export | nothing: Samsung is a program non-goal (00 §2) | candidate to drop (Q-F6) |
| OM-4 / OM-5 | clinician + patient conversations | nothing until OW-W6 says they are required | open |
| OM-6 / OM-7 | OD answers; legal read (FDA wellness, FTC HBNR, FIT licence) | public distribution (OD-8); the FIT-licence half = OW-W7 | OD direction answered via WEAR-OD1/OD2, WEAR-D1…D8; legal read open |
| OM-8 | read FDA Jan 2026 general-wellness guidance | public distribution; WEAR-D8 copy "can still change after the legal read" | open |
| OW-W1 | M4 dogfood on the real export | M4 exit evidence | after M4 |
| OW-W2 | Windows 200 MB perf smoke | R11 evidence for WEAR-04 | after WB |
| OW-W4 | Windows vitest / Playwright for 07b, 08, 09b, 10, 13, 15b | M3, M4 exit | after each PR |
| OW-W5 | answer D1–D8 | — | **done** (WEAR-D1…D8, `c53ba44`) |
| OW-W6 | are OM-4/OM-5 still required? | M0 scope | open |
| OW-W7 | FIT licence read → row `WEAR-FIT-LIC` | WEAR-11b | open |
| OW-W8 | copy approval for 07b, 08, 15b, 09 journal strings | WEAR-07b, 08b, 15b, 09b-journal | open |
| OW-W9 | names in free text: accept residual, or open an ask-first `modules/redaction.py` change | WEAR-09a-journal, 09b-journal (Task 0 STOP) | open; **ask-first if option 2** |
| OW-W10 | journal entries in `GET /export/json`? | a follow-up plan only | open |
| OW-W11 | journal audit vocabulary in `core/audit.py` | WEAR-15a | open |
| OW-W12 | purge preview snapshots in reset/delete paths (`api/profiles.py`) | WEAR-09a-journal | open; delete path (RL-EXPORTS-DELETE-PATH precedent) |
| OW-W13 | profile-migration merge order | WEAR-02, 15a numbering; lane C Q on GAM2-2b vs G-C1 order | open |
| M0 approval | owner approves the wearables plan set (+ merges #94, WEAR-PR "you merge") | all WEAR code | open; not an OW id today |

**TASK_LIST refresh (DOCS, one commit, after #94 merges):** add an `OW-W*` subsection under "Owner and Model-Machine Queue" listing OW-W0…W4, W6…W13 one line each with a link to the merged program 00 §10; annotate OM-1 = OW-W0, OM-2 = OW-W3; mark OW-W5 done with `c53ba44`. Never tick OW-1 or any OM box: that is the owner's. F-13 edits only the new `OW-W*` subsection and the OM-1 / OM-2 / OW-W5 annotations; it never edits the MM-1…MM-4 rows, so lane B's B-9 (MM rows) does not need to wait for it. `TASK_LIST.md` rule (lane E P-3): every claimant (E-3, C-P6, C-DUPAUD, B-9, F-1, F-13, #84, #68) edits only its own row or section; the second lander rebases. Acceptance: `grep -c "OW-W1[0-3]\|OW-W[0-9]" docs/features/TASK_LIST.md` ≥ 13; docs gates pass.

### 2.14 F-4-FOLLOWUPS — three docs lines still contradict F-4 and SLOT-RULE-2a (takes TASK-LIST-COV)

**Source:** PR #200 (F-4) review MINORs (queue bullet F-4-FOLLOWUPS) and PR #207 (Q-COV-GATE) review MINOR (queue bullet TASK-LIST-COV, folded here: same kind of fix, docs only, no shared file with anything open). Planned 2026-10-20 on `origin/main` @ `b2b3f4e`.

**Facts (`b2b3f4e`):**
1. `docs/capstone-report/specs-compliance-matrix.md:67` (KEY-05) still quotes `hipaa-controls.md:169` as "Manual via password change" and says "**owner-gated** (plan 08 brief 2)". Since #200, `docs/compliance/hipaa-controls.md:169` reads "Owner-approved 2026-10-19, not yet implemented (plan: decision packet Brief 2). Until it ships, a password change re-seals the existing data key only." The owner answer is P8-B2 = B + A (`docs/capstone-report/owner-decisions-2026-09-27.md:297`). The gap itself is still real: no DEK rotation exists.
2. `.github/workflows/ci.yml:21-22` comment: "SLOT-RULE-2: PRs do not commit docs/INDEX.md or docs/_link_graph.json; regenerate both here (DOC-011 sees new docs). Freshness on main is the orchestrator's post-merge batch, not a PR gate." SLOT-RULE-2a (`owner-decisions-2026-09-27.md:182`, "PRs regenerate the index"; contracts §d step 1; `RUNBOOK.md` §7 item 1) says PRs do regenerate and commit both. The step under the comment is right; only the comment is wrong.
3. `docs/features/TASK_LIST.md:220` (E-3 row, 2026-10-17): "`backend-tests` publishes `coverage.xml` and fails if it is missing (report only, no threshold, Q-COV)". True when written; since Q-COV-GATE (#207, `33fa9e6`) CI also fails below 74% TOTAL. `git grep -n "Q-COV-GATE" -- docs/features/TASK_LIST.md` is empty.
4. The decision packet's Brief 2 `Owner decision:` line (`audit/2026-09-25/gated-items-decision-packet.md:117`) and ledger row 2 (`:421`) are unticked. Recording an owner answer is L0's, verbatim (RUNBOOK §9 item 2; §2.4 above: "The packet tick, if wanted, is L0's."). **Not in this row:** L0 copies P8-B2 from `:297` in its next owner-rows PR, or leaves the packet as the historical brief.

**Design (docs and a YAML comment; no behaviour change):**
1. KEY-05: the Source cell quotes the new `:169` wording; the status cell keeps **gap** and says "owner-approved 2026-10-19 (P8-B2 B + A, `owner-decisions-2026-09-27.md:297`), not yet implemented"; the "a password change is a re-seal, not a rotation" sentence stays.
2. `ci.yml:21-22`: "SLOT-RULE-2a: PRs regenerate and commit docs/INDEX.md and docs/_link_graph.json; CI regenerates them again here so DOC-011 sees new docs (the committed index is checked by test_docs_index_check_passes_on_real_repo)." Comment lines only; the `run:` lines are unchanged.
3. `TASK_LIST.md:220`: keep the text and append "Superseded 2026-10-20: CI fails below 74% TOTAL (Q-COV-GATE, #207)."

**Checks (no pytest id):**

| Check | Expected | RED today? |
|---|---|---|
| `grep -c "Manual via password change" docs/capstone-report/specs-compliance-matrix.md` | `0` | yes (`1`) |
| `grep -n "PRs do not commit docs/INDEX.md" .github/workflows/ci.yml` | no output | yes (`:21`) |
| `grep -c "Q-COV-GATE" docs/features/TASK_LIST.md` | `1` | yes (`0`) |
| `git diff origin/main -- .github/workflows/ci.yml \| grep '^[-+] ' \| grep -v '^[-+] *#'` | no output (only comment lines changed) | n/a |
| `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` and `python3 scripts/docs_lint.py` | exit 0 | n/a |

**Files:** `docs/capstone-report/specs-compliance-matrix.md` (KEY-05 row only), `.github/workflows/ci.yml` (`:21-22` comment only), `docs/features/TASK_LIST.md` (`:220` only), `docs/INDEX.md`, `docs/_link_graph.json`. No slots.
**Expected collected delta:** 0. **Est:** 0.25 h.
**Acceptance:** the checks above, pasted; CI green on the PR. **Rollback:** revert.
**Order:** ready now (no slot). Never beside another PR on `ci.yml`, `specs-compliance-matrix.md` or `TASK_LIST.md` (none open on `b2b3f4e`; #210 does not touch them).

### 2.15 FEATURE-LIST-LICENCE — `feature_list.json` HC-M11 still says the NLI model is MIT

**Source:** #249 surprise 3 (queue bullet FEATURE-LIST-LICENCE). Planned 2026-10-21 on `origin/main` @ `b902e0f`.

**Facts (`b902e0f`):**
1. `feature_list.json:142` (HC-M11 `description`): "candidate: cross-encoder/nli-deberta-v3-xsmall, MIT, ~22M params". `git grep -n "nli-deberta-v3-xsmall, MIT" -- feature_list.json` prints `:142` only.
2. The authoritative sources say Apache-2.0: the model card (`license: apache-2.0`, README line 11, measured in [#249](../../reviews/2026-10-20/gc5-real-model-evidence.md)), `config/model_manifest.json` (`nli-deberta-v3-xsmall` note: "Apache-2.0 per the model card"), and the owner's GC5-OL-1 (`docs/capstone-report/owner-decisions-2026-09-27.md:269`: "licence Apache-2.0 (not MIT, as feature_list.json says)").
3. Other MIT mentions are dated records and stay as they are: `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md:97-98` (a June survey), `docs/archive/plans/2026-07-02-*.md` (archived), `audit/2026-09-25/gated-items-decision-packet.md:403` (already says "MIT per feature_list.json … UNVERIFIED") and `audit/2026-09-25/plans/08-gated-items-review-packet.md:248`, `:255`. Rewriting them would change what those records say was believed at the time; GC5-OL-1 and the GC5 plan (`docs/plans/2026-10-18-GC5-hc-m11-nli-flag-off.md:141`) already carry the correction.
4. `scripts/feature_list_lint.py` checks structure only (FL-001…FL-007); CI runs it.

**Design (one data string):** `feature_list.json:142`: `MIT` → `Apache-2.0`. Nothing else in the entry changes (its "~22M params" is the backbone figure the survey uses, and its "Verified 2026-07-07 … stub" sentence is a dated note; neither is this row). **No lint rule:** one string, and a licence rule needs a map from free text to manifest entries, which nothing else would use (CLAUDE.md §2).

**Checks (no pytest id):**

| Check | Expected | RED today? |
|---|---|---|
| `git grep -c "nli-deberta-v3-xsmall, MIT" -- feature_list.json` | no output, exit 1 | yes (`feature_list.json:1`) |
| `git grep -c "nli-deberta-v3-xsmall, Apache-2.0, ~22M params" -- feature_list.json` | `feature_list.json:1` | yes (no match) |
| `python3 scripts/feature_list_lint.py` (stdlib only: `json`, `re`, `sys`, `pathlib`, `feature_list_lint.py:25-30`; CI runs the same command, `ci.yml:29-30`) | exit 0 | n/a |
| `git diff --stat origin/main...HEAD` | `feature_list.json` only, 1 line changed | n/a |

**Files:** `feature_list.json` (`:142` only). Not under `docs/`, so no index regeneration. No slots.
**Expected collected delta:** 0. **Est:** 0.1 h.
**Acceptance:** the checks above, pasted; CI green on the PR. **Rollback:** revert.
**Order:** ready now (no slot). No open PR touches `feature_list.json` (checked: #210, #230, #239, #246). No ask-first file.

---

## 3. Provides

1. **`pipelines.md` text after F-1** (for lanes A and B): `:126` = `SAFE --> OUT["cited answer<br/>[cite:N] markers (context labels are not citations)"]`. If P4D-PIPELINES-127 = A, the W-4 lane's F4 Before text is exactly `SAFE -.->|"missing citations or faithfulness < 0.6:<br/>is_valid=false, answer still served (W-4 pending)"| OUT`, and prohibited advice is drawn as `SAFE -->|"prohibited-advice match"| ESC["escalation template (SAFE-CHAT)"]`.
2. **Variant-I contract for W-2 and W-3** (lanes E, A): HTTP tests HC-EXPR-003 and HC-VER-002 call `tests.support.routes.route_client` inside their own function body (or a same-file fixture argument); the merged PR body pastes red-first output per new test id and ≥ 1 break-it run. Without all four, `data-privacy.md` stays U.
3. **F-trigger commands** (§2.5): any lane can run them after its merge to tell lane F which docs flip.
4. **Wearables consumer map** (§2.12): per-plan migration effects under C-P6 / C-P7 and the shared-file table; withdrawn `015_audit_outbox`.
5. **Owner queue with unblock edges** (§2.13), and the merge rule: #68 merges last with the measured count (main N + 7); #61 closes after #72 without deleting its branch.

## 4. Consumes

1. Lane E E-1 (W-2) merged: merge sha + PR body → F2, F-6.
2. Lane A W-3, W-8 merged → F1, F5, F-6.
3. Lane B B-5 (W-7) → F3; B-7 / MM-1 → #72 merge → F4, F-11.
4. Lane C C-PMIG (`tests.support.migrations.PROFILE_HEAD: str`), C-P6 (`core.fk_audit.FkCheck`, `PROFILE_CHECKS`, `tests.support.db.fk_profile_engine`), C-P7 (`api.profiles._SYNTHETIC_RESET_MODELS`, gate RESET-APPEND) → wearables WEAR-02, 15a.
5. Lane D D-0 merge order and measured counts (#95 → #97 → #99 → #82 → #84) before F-10; D-2's migration number. Lane E E-4 (#74) before WEAR-10.

## 5. Owner gates

| Gate | Item | State |
|---|---|---|
| P4D-PIPELINES-127 | F-1 commit 2 | **unasked**; recommended A (fix in the N8 PR) |
| P4D-N10-WORDING | F-2 | unasked; recommended "approve as written" (quotes D12, matches GOV-BG). Not an ask-first file, but it narrows a "never bypass redaction" rule |
| P8-B2-ORDER (packet Brief 2) | F-4 | **answered 2026-10-19: B + A** (`owner-decisions-2026-09-27.md:297`); the packet ledger `:421` stays unticked (agents never tick) |
| W10B-RC, W10B-SPLIT, W10B-D4-EXTRAS | F-6 | unasked (W-10b pack §3) |
| S-C2-1, S-C2-2, S-C2-3; GC2-CLAUDE-66 | F-7 | unsigned; G-C2-DEFER in force. `CLAUDE.md` edit = governance |
| RTN §9 Q1–Q6 | F-8 | **unsigned**; Q6 default "do not enable" |
| SHOW-DATE, SHOW-AUDIT, O-1…O-7 | F-9 | SHOW-AUDIT answered (A, `:232`); SHOW-DATE answered (`:243` rule, `:277` showcase 2026-10-31, freeze 2026-10-24); O-1…O-7 unsigned, each gates only its own task (SHOWCASE-O4 answered location only) |
| HOOKS-COMMIT | F-10 | answered 2026-10-10 per the #68 branch row; not on main until #68 merges |
| PR68-SYNC, PR61-CLOSE, WEAR-PR | F-10, F-11, F-12 | answered (`:158`, `:141`, `:150`) |
| M0, OW-W0, OW-W3, OW-W6…OW-W13 | F-12 | open (§2.13) |
| Ask-first files | all | **none edited by any lane-F item.** Flags: OW-W9 option 2 would open `modules/redaction.py` (ask-first); OW-W12 edits the profile delete path in `api/profiles.py` (auth-adjacent, RL-EXPORTS-DELETE-PATH precedent); WEAR-02/06 `core/audit.py`, `security/input_validator.py` are owner-signed exact diffs (WEAR-D4) |

## 6. Open questions

**Ask now (each unblocks a ready item):**

1. **Q-F1 (P4D-PIPELINES-127):** fix the false "prohibited advice still served" edge in the N8 PR? A. Yes, second commit (recommended) · B. own PR · C. wait for F4.
2. **Q-F2 (P4D-N10-WORDING):** approve N10's After text as written? A. Yes (recommended) · B. with edits.
3. **Q-F3 (SHOW-DATE + SHOW-AUDIT):** showcase date, and refresh + review the 963-line plan before running it? Recommended: refresh with §2.9 corrections, then one review round (owner direction: Codex on large plans; REVIEW-OPUS-SUB applied to one round only).

**Later:**

4. **Q-F4 (#61 evidence):** keep the REVISE review on branch `docs/w4-plan-amend` only (default), or copy `W-4-amend-codex.txt` + prompt into `docs/reviews/` before closing?
5. **Q-F5 (wearables + migration order):** OW-W13 puts G-C1 before GAM2-2b; lane C puts GAM2-2b first and lane D's D-2 also claims `013`. One owner answer should fix the order for all of C-P6, C-GAM2B, D-2, C-GC1, WEAR-02, WEAR-15a.
6. **Q-F6 (OM-3):** drop the Samsung export from the queue? Samsung is a program non-goal.
7. **Q-F7 (orchestrator):** program `:431`, `:434`, `:447`, `:451-452` Sign-off cells are stale since 2026-10-09; record F-1/F-2/F-3 readiness and W-10 merged there.

## 7. Peer review (2026-10-15)

Checked against lanes A–E (their peer-review sections included) and the repo at `3b2236c` plus the open PR branches. No owner approval recorded; every gate in §5 keeps its state.

**Changed in this doc:**

| # | Finding (verified) | Change |
|---|---|---|
| 1 | F2 trigger `grep -n "RedactionEngine" src/backend/modules/export.py` already hits (`:533`, `:637`, visit-prep) — lane E P-2 | §2.5 F2 trigger = `def redact_summary_data` (lane E's provided symbol) |
| 2 | F1 trigger `grep -n "user_verified" api/observations.py` already hits (`:115`, not `TrendPoint` `:157-165`) | §2.5 F1 trigger scoped to `class TrendPoint` + the `rag.py` filter lane A provides |
| 3 | F4 also edits `ci-and-quality-gates.md` (P04 `:996`), shared with E-3 Task 9 and W-8; §2.5 omitted it | §2.5 F4 row + serialisation line |
| 4 | D-2 no longer hard-codes `013` (lane D §8 #1); WEAR numbers are illustrative (lane C §3.0 #3) | §2.12 migration paragraph; surface migrations cite slug + head+1 |
| 5 | `core/audit.py` row omitted C-DUPAUD (lane C §7) | §2.12 shared-file row |
| 6 | WEAR-03 cites `core/time.py:9,14,24`; main `:12,:17,:27`; D-1 appends (lane D §8) | §2.12 new `core/time.py` row |
| 7 | B-9 waits on F-13 (lane B P-7), but F-13 is blocked on the owner's #94 merge and edits disjoint rows | §2.13: F-13 never edits MM rows; lane E P-3 `TASK_LIST.md` rule adopted |

**Confirmed, no change:** variant-I contract met by design — lane E §2.1 #9 moves HC-EXPR-003 onto `route_client` in its own body; W-3 HC-VER-002 already does (`W03:379`). Lane E E-6's HC-AGENTS fix waits for #68 (both edit `tests/test_claude_agent_definitions.py`). #72 edits neither `pipelines.md` nor `ci-and-quality-gates.md`. #74 owns `Sidebar.tsx`, #84 owns `services/index.ts`; no peer edits `pipelines.md`, `architecture/README.md`, `backend.md`, `data-privacy.md`, `hipaa-controls.md` or the guardrails skill. `claims-ledger.md`: W-8 and F-9 serial (lane A §W-8 2a).

**Raised to peers / L0 (not edited here):** lane B P-7 wait on F-13 (drop it); L0 to sequence the F-10 (#68) count re-measure after the D-0 chain; one owner answer to OW-W13 / Q-F5 for all profile migrations (lanes C, D, F).

Back to: [implementation program](../../capstone-report/implementation-program.md) · [owner decisions](../../capstone-report/owner-decisions-2026-09-27.md) · [recurring failures](../../agentic/recurring-failures.md)
