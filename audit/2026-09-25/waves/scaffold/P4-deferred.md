**READY: N8, N10 · GATED: N9 (P8-B2-ORDER unsigned) · BLOCKED: F1 (W-3), F2 (W-2 + W-10), F3 (W-7), F4 (W-4), F5 (W-8), F6 (W-10).**

# P4-deferred — N8, N9, N10, F1-F6 (readiness pack)

**Measured:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84`. Every file named below is byte-identical to `origin/main` except `docs/capstone-report/**` and `audit/**`.
**Plan:** `docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md`, "Deferred tasks" `:901-1000`, gates §11 `:1098-1131`, stop gates §12, commit plan §13.
**Kind:** DOCS. One branch, one commit, one PR per task. Not architectural (orchestration §5: no Codex for P4).

## 1. Readiness verdict per task

| Task | Verdict | Trigger | Blocker / gate |
|---|---|---|---|
| N8 D11 vocabulary (4 files) | **READY** | HIT: W-5 merged (PR #34, `d21c59d`) | none; 2 plan amendments (§4) |
| N10 guardrails SKILL (1 file) | **READY** | HIT: W-6 merged (PR #32, `2f0cb6f`) | none; owner wording check recommended (§3) |
| N9 `hipaa-controls.md:169` | **GATED** | not hit | P8-B2-ORDER: packet Brief 2 `Owner decision:` `:117` and ledger row `:421` unfilled |
| F1 D4 flip | **BLOCKED** | not hit | W-3 not merged |
| F2 D3 flip | **BLOCKED** | not hit | W-2 and W-10 not merged |
| F3 ModelRunner flip | **BLOCKED** | not hit | W-7 not merged |
| F4 legacy-abstain flip | **BLOCKED** | not hit | W-4 not merged. DOC-PIPELINES-PROHIBITED (`pipelines.md:127`) is fixable now on the owner's word (§3) |
| F5 outbound flip | **BLOCKED** | not hit | W-8 not merged |
| F6 D12 wording flip | **BLOCKED** | half: W-6 merged | W-10 not merged; both Before texts CHANGED (§4) |

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| P4-core (PR #40) | `git merge-base --is-ancestor 6b4dd84 origin/main; echo $?` | 0 |
| W-5 (PR #34) | `git merge-base --is-ancestor d21c59d origin/main; echo $?` | 0 |
| W-6 (PR #32) | `git merge-base --is-ancestor 2f0cb6f origin/main; echo $?` | 0 |
| P8 (PR #30) | `git merge-base --is-ancestor 242f7a0 origin/main; echo $?` | 0 |
| Plan tracked | `git ls-files docs/plans/2026-09-27-P04-*.md` | 1 file; on `origin/main` |
| W-2, W-3, W-4, W-7, W-8, W-10 | `gh pr list --state merged --limit 40`; `--state open` | no PR for any (open: #49 only) |
| Start gates | `docs_lint.py`, `generate_docs_index.py --check`, `harness_drift_check.py`, `repo_hygiene_check.py` | all pass, exit 0 |
| Collected | collect-only, D9 venv, `HF_HUB_OFFLINE=1` | `1370 tests collected in 19.88s` |

Trigger commands:

| Task | Command | Output |
|---|---|---|
| N8 | `grep -n "YOUR_RESULTS:N\]\|REFERENCE:N\]" src/backend/modules/rag.py` | `:130`, `:135`, `:136`, all label wording ("Context labeled …"); the cite instruction at `:128` says `[cite:N]` |
| N8 | `grep -n 'citation_pattern = r"\\\[cite:' src/backend/modules/rag.py` | `:822` (validator unchanged) |
| N10 | `grep -n "redaction_bypass_active\|BREAK_GLASS_AUDIT_EVENT" src/backend/core/external_runner.py` | `:95`, `:112`, `:134` |
| N10 | `grep -rn "redaction_break_glass" src/frontend/src \| head -1` | `pages/ExplainAssistant.tsx:475` |
| N9 | `grep -n "Key rotation" audit/2026-09-25/gated-items-decision-packet.md` | `:421` `☐ approve ☐ reject ☐ defer`, no date |
| F1 | `user_verified` inside `TrendPoint` | 0 hits |
| F4 | `grep -n "legacy-evals" .github/workflows/ci.yml` | 0 hits |
| F2, F6 | `grep -n "external runner" CLAUDE.md`; D3 exception | 0 hits (W-10 not merged) |

Gates: OG-4/5/6 are signed and used by P4-core. P8-B2-ORDER: UNSIGNED (P04 plan `:1180`). "Each deferred PR merged by owner": UNSIGNED (`:1181`). No 2026-10-07 owner row is needed by N8 or N10.

## 3. Owner questions still to ask

1. **P4D-PIPELINES-127.** "`docs/architecture/pipelines.md:127` still says a prohibited-advice match is 'still served (W-4 pending)'. SAFE-CHAT (PR #44) made that false: such an answer now returns the escalation template (`api/assistant.py:880-881`). Fix it now?"
   - A. Yes, as a second commit in the N8 PR. N8 already edits the line above (`:126`). **(recommended)**
   - B. Yes, as its own one-line docs PR.
   - C. Wait for F4 (after W-4).
2. **P4D-N10-WORDING.** "N10 changes the guardrails skill's Never-list from 'bypass redaction for any reason' to 'bypass redaction, except through the external runner's owner-approved break-glass (D12 …) · add any new bypass'. Approve this wording?"
   - A. Approve as written in the plan (`:972-976`). **(recommended; it quotes D12 and matches GOV-BG, signed 2026-10-07)**
   - B. Approve with your edit.
   - C. Hold N10 until W-10 merges, so the skill and `CLAUDE.md:60` change together.
3. **P8-B2-ORDER (for N9).** "Key rotation, Brief 2 of the gated-items packet: which option?" Options are the packet's own (`gated-items-decision-packet.md:100-117`): approve / reject / defer, with A (docs only), B or C (build), D (session-secret rotation). No recommendation is added here; the packet carries its own at `:109`.
4. **P4D-HIPAA-OVERCLAIM.** "`hipaa-controls.md:49` ('correlation IDs' in the audit log format) and `:52` ('append-only') overstate the code (DOC-OVERCLAIM). No P4 task owns them. Add them to the N9 PR when it runs?" A. Yes, same PR, separate commit **(recommended)** · B. Own docs PR now · C. Leave as an owner item.

Ask-first touches: none. `skills/asclexis-guardrails/SKILL.md` (N10) is not on the CLAUDE.md §1 list, but it states a privacy rule, so question 2 is asked before dispatch.

## 4. Plan drift check

### N8

| Plan anchor | Now | Result |
|---|---|---|
| `pipelines.md:111` `SAFE --> OUT["cited answer<br/>[REFERENCE:N] / [YOUR_RESULTS:N]"]` | `:126`, text identical, 1 match | **MOVED** (P4-core N2, PR #40) |
| `00_features_index.md:38` "ground in two citation layers. …" | `:38`, full Before string `grep -cF` → 1 | MATCH |
| `04_self_improvement_loop.md:113` | `:113` | MATCH |
| `TASK_LIST.md:63` "`[YOUR_RESULTS:N]` chips in ExplainAssistant become deep links" | `:63` | MATCH |
| `services/assistant.ts:378` (cited in the After text) | `:378` `text.match(/\[cite:(\d+)\]/g)` | MATCH |
| Step 1: `REPORT FACTS` / `GENERAL INFO` split | `rag.py:130-131`, `:135-136` still present | MATCH → keep the clause |
| Step 3 sweep expected list | extra hits in `docs/capstone-report/` (9 files: contract `:178,180`, matrix `:84`, `claims-ledger.md:28`, `00-original-goal.md:14`, `implementation-program.md:179`, `owner-decisions…:25,65`, `research/01…:379`, `research/04…:378`) | **CHANGED**: not in the expected list, not excluded by the filter → S5 would fire |
| Step 3 filter `grep -vE "^\./(docs/(archive\|plans\|research)\|audit)/"` | in this shell `grep -rn … .` printed paths without `./`, so the filter excluded nothing (41 files listed, `audit/` and `docs/plans/` among them). `type grep` → `grep is a function` (profile wrapper) | plan defect on this host. The `git grep` form in amendment 2 printed exactly: `AGENT.md`, `CLAUDE.md`, `pipelines.md`, `brand-guidelines.md` (2), `ai-safety.md`, `00_features_index.md`, `01_lab_result_interpreter_architecture.md` (4), `04_self_improvement_loop.md`, `TASK_LIST.md` |
| `docs/user/faq.md`, `docs/user/workflows.md` "confirm" | 0 hits in both | MATCH (nothing to confirm) |

### N9 and N10

| Plan anchor | Now | Result |
|---|---|---|
| N9 `hipaa-controls.md:169` `\| Key rotation \| Medium \| Manual via password change \|` | `:169` | MATCH |
| N10 `SKILL.md:62-64` Before (3 lines) | `:62-64` | MATCH |
| N10 note "W-6 Q1 and Q3 are both open" | both signed: BG-REACH (`owner-decisions:40`), W6-Q3 (`:44`) | CHANGED (note only; the After text needs no change) |

### F1-F6 (Before texts as P4-core wrote them)

| Task | Before text | Count now | Result |
|---|---|---|---|
| F1 | `**Included without a label:**` in `pipelines.md`; `W-3 pending` at `:46`, `work item W-3` at `:70` | 1 | MATCH |
| F2 | "the doctor summary is to be strictly redacted (**approved, not yet implemented**, work item W-2), and CSV / JSON … to be named as deliberate exceptions in" (wrapped across lines; matches after whitespace collapse) | 1; `work item W-2` at `:209` | MATCH (multi-line: anchor on collapsed text) |
| F3 | README "One dormant path bypasses it:"; `backend.md` "Known deviations: the dormant `llama_cpp` import …" | 1 and 1 | MATCH |
| F4 | `W-4 pending` in `pipelines.md` | 1 (`:127`) | MATCH, but half of that line is already false (DOC-PIPELINES-PROHIBITED) |
| F5 | README `**Embedding model, first use.**` | 1 | MATCH |
| F6 | README ": **approved, not yet implemented** (work items W-6, W-10)." | **0** | **CHANGED** (P4-core N4, PR #40: `README.md:105-111` now says "Strict redaction is now unconditional; break-glass … writes an audit record, and shows a warning in Settings and on the assistant chat page (work item W-6). Naming the exception in `CLAUDE.md` is …") |
| F6 | `backend.md` "work items W-6 and W-10, not yet implemented" | **0** | **CHANGED** (`backend.md:107-108`: "redaction hardening landed in W-6, and naming it in `CLAUDE.md` is work item W-10, not yet implemented)") |

**Plan amendments to make (not made here):**

1. N8 row 1: anchor `pipelines.md:126`.
2. N8 Step 3: replace the sweep with `git grep -n "YOUR_RESULTS:N\|REFERENCE:N" -- '*.md' ':!docs/archive' ':!docs/plans' ':!docs/research' ':!audit' ':!docs/capstone-report'`, and add `docs/capstone-report/**` (orchestrator-owned, point-in-time) to the expected list.
3. N8: add `**Last Updated:**` bumps for `00_features_index.md` and `TASK_LIST.md` to the commit pathspec check (already in Step 2).
4. F6: rewrite both Before texts to the `README.md:105-111` and `backend.md:107-108` wording; rewrite the acceptance grep (`grep -rc "W-6" docs/architecture → 0` cannot hold while "landed in W-6" is the desired text; use `grep -rc "work item W-10" docs/architecture` → 0).
5. F4: if question 1 is answered A or B, F4's Before for the dashed edge changes; F4 must re-anchor.
6. Deferred worktree names: `../hc-p4` still exists (branch `docs/p4-doc-drift`, `git worktree list`). Use `../hc-p4-n8`, `../hc-p4-n10`.
7. N10 closing note: Q1 and Q3 are no longer open.

## 5. File ownership and overlap

| Task | Owned files |
|---|---|
| N8 | `docs/architecture/pipelines.md`, `docs/features/00_features_index.md`, `docs/features/04_self_improvement_loop.md`, `docs/features/TASK_LIST.md` |
| N10 | `skills/asclexis-guardrails/SKILL.md` |
| N9 | `docs/compliance/hipaa-controls.md` |
| F1, F2, F4 | `docs/architecture/pipelines.md` (F4 also `ci-and-quality-gates.md`) |
| F3, F5, F6 | `docs/architecture/README.md` (F3, F6 also `backend.md`) |

Never touched: `CLAUDE.md`, `docs/compliance/data-privacy.md` (S3), `docs/capstone-report/**`, `docs/INDEX.md` unless a link changes (none does in N8/N10).

| Other phase | Shared file | Order |
|---|---|---|
| W-3 | `pipelines.md` (its plan names it 4 times) | N8 → W-3 → F1 |
| W-4, W-11a PR-3, W-8 | `ci-and-quality-gates.md` | P4 N6 → W-11a PR-3 → W-8 → F4 |
| P5 and every phase that adds a Session Note | `docs/features/TASK_LIST.md` | serial, newest-first; the second PR rebases |
| W-10 | none (F2 and F6 only read `CLAUDE.md`) | W-10 → F2, F6 |
| W-10, W-10b | `data-privacy.md` | not P4's |
| G-C3a | `docs/agentic/evals.md` | not touched by any deferred task |
| P6, P7, G-C1, G-C2, G-C5, W-2, W-7, W-11a PR-1, NPM-AUDIT-2, React Router 7, Tailwind 4, PROHIBITED-PARAPHRASE, AUDIT-ORDER plan | none | — |

Count slots (ground rule 8): no deferred task changes collection, so none edits `CLAUDE.md:30,34-35` or `AGENT.md:76`.

## 6. Briefs (N8 and N10 only)

### L1 brief (filled)

```
You are the L1 Wave Orchestrator for Wave 4 (docs lane) of the Asclexis execution
program. Follow docs/agentic/orchestration.md §3 exactly; you are L1.
Phases: P4-deferred N8 and N10:
docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md, "Deferred tasks" :901-987,
gates §11, stop gates §12, commit plan §13.
Base: origin/main @ <sha>. Confirmed merged dependencies: P4-core (#40, 6b4dd84),
W-5 (#34, d21c59d), W-6 (#32, 2f0cb6f).
Signed gates you may rely on: D11 (owner-decisions :25), D12 (:22). <P4D-N10-WORDING
and P4D-PIPELINES-127 answers, verbatim, once the owner gives them>.
Unsigned: P8-B2-ORDER (N9 does not run); every F-task trigger (do not run).
Not architectural: no Codex review.
N8: worktree ../hc-p4-n8, branch docs/p4-n8-citation-vocabulary, one PR.
N10: worktree ../hc-p4-n10, branch docs/p4-n10-guardrails-skill, one PR.
Apply the plan amendments in audit/2026-09-25/waves/scaffold/P4-deferred.md §4
(items 1-3, 6, 7) as the first commit on the N8 branch.
Implementer: Agent(general-purpose, model="sonnet"), L2 brief below, one per task.
Reviewer: Agent(code-reviewer, model="opus"), handoff §6. For N10 also
security-reviewer (opus): docs only, but the text narrows a "never bypass
redaction" rule, so check it grants nothing beyond D12 and GOV-BG.
Acceptance, run by you in each worktree, outputs pasted:
  python3 scripts/docs_lint.py                   -> Docs lint passed.
  python3 scripts/generate_docs_index.py --check -> exit 0
  python3 scripts/harness_drift_check.py         -> passed
  python3 scripts/repo_hygiene_check.py          -> passed
  the §11 relative-link resolver                 -> relative links OK   (N10)
  collect-only (D9 venv, HF_HUB_OFFLINE=1)       -> 1370, unchanged
  N8: grep -c 'cite:N\] markers (context labels are not citations)' docs/architecture/pipelines.md -> 1
      grep -c "ground in two citation layers" docs/features/00_features_index.md -> 0
      grep -c "format preserved" docs/features/04_self_improvement_loop.md       -> 0
      amended sweep (P4-deferred.md §4 item 2) -> only the expected list
      git diff --name-only origin/main...HEAD  -> the 4 N8 files (+ the plan file)
  N10: grep -c "bypass redaction for any reason" skills/asclexis-guardrails/SKILL.md -> 0
       grep -c "keep break-glass" skills/asclexis-guardrails/SKILL.md            -> 1
       git diff --name-only origin/main...HEAD -> that 1 file
Write audit/2026-09-25/waves/wave-4-L1-<X>.md and return it: per PR the URL,
commands and outputs, collected delta (0), gates used, open findings, merge order
(N8 and N10 share no file; either order).
Do not merge. Do not sign gates. Do not edit CLAUDE.md, data-privacy.md,
hipaa-controls.md, docs/capstone-report/** or any src/** file.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### L2 implementer brief (filled; N8 shown, N10 differs where marked)

```
Implement docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md, Task N8 only
(:911-941) [N10: Task N10 only, :956-987], in worktree
/mnt/c/Users/DangT/Documents/GitHub/hc-p4-n8 on branch docs/p4-n8-citation-vocabulary
[N10: hc-p4-n10, docs/p4-n10-guardrails-skill].
Python: ~/venvs/asclexis-311/bin/python. Always export HF_HUB_OFFLINE=1.
Docs task: the "test" is the grep. Before editing, run each row's Before grep and
paste the old line (expect exactly 1 match each); edit; paste the after-grep.
N8: the pipelines.md row is at :126, not :111. Keep the REPORT FACTS / GENERAL INFO
clause (rag.py:130-131 still has it). Bump **Last Updated:** in 00_features_index.md
and TASK_LIST.md. One commit, pathspecs exactly
docs/architecture/pipelines.md docs/features/00_features_index.md
docs/features/04_self_improvement_loop.md docs/features/TASK_LIST.md,
message "docs: describe [cite:N] as the citation marker and the context labels as
labels (D11)". [If L1 says P4D-PIPELINES-127 = A: a second commit, pipelines.md
only, with the After text L1 gives you.]
[N10: one commit, skills/asclexis-guardrails/SKILL.md only, plan After text
verbatim, message "docs(skills): name the owner-approved break-glass in the
guardrails never-list (D12)".]
End each message with Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>.
Explicit pathspecs; never `git add -A`.
Ask-first files: none. Do not touch CLAUDE.md, data-privacy.md, hipaa-controls.md.
Stop and report if: a Before text matches 0 or 2+ times; the sweep shows a hit
outside the expected list (S5); a gate in §11 fails; any file outside the list
would change.
Do NOT spawn agents. Do NOT push.
Return: commit sha + subject, each grep before and after, the §11 gate outputs,
collected before and after (collect-only), any deviation.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 7. Risks and open findings

| # | Finding | Evidence | Recurring-failures mode |
|---|---|---|---|
| 1 | `pipelines.md:127` states a safety behaviour that PR #44 removed | `api/assistant.py:880-881` `ESCALATE_TEMPLATE`; program item DOC-PIPELINES-PROHIBITED | #8 stale guidance; #2 (P4-core wrote it against `90c502a`, SAFE-CHAT merged after) |
| 2 | F6's Before texts no longer exist | counts 0 and 0 (§4) | #2; S1 would stop the executor |
| 3 | N8's sweep, as written, flags 9 capstone files | §4 | #6 documented command that does not give the documented result |
| 4 | N8 leaves `CLAUDE.md:62` with the old vocabulary until W-10 merges; SAFE-08 stays partial | `CLAUDE.md:62`; matrix `:84` | #8; expected, W-10 owns it |
| 5 | N10 before W-10: the skill names the break-glass exception while `CLAUDE.md:60` still says "must pass through `modules/redaction.py` first" with no exception | `CLAUDE.md:60` | #8; question 2 option C avoids it |
| 6 | `hipaa-controls.md:49`, `:52` overclaims have no owning task | program DOC-OVERCLAIM | #8 |
| 7 | `README.md:103-104` wraps "work item W-8" across a line break | wave-3-L1-C §5 later-4 | F5 must match on collapsed text |
| 8 | Mermaid edits in `pipelines.md` (N8 `:126`, question 1) are not parsed by any CI gate | wave-3-L1-C: Mermaid checked by hand on Windows | #1: run `npx @mermaid-js/mermaid-cli@11` on Windows, or record it as skipped |

Next action: ask the owner questions 1 and 2 in §3, then dispatch N8 and N10.
