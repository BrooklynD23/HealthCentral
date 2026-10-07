**Verdict: READY** — both hard dependencies are on `origin/main` and PARA-1 is signed. Two conditions before dispatch: PR #49 must merge (the PARA-1 row exists only on its branch), and owner question Q1 below should be asked first (the signed list stops catching "You have kidney disease.").

# PROHIBITED-PARAPHRASE execution — readiness pack

**Scaffolded:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e` (`docs/wave4plus-scaffold`), `origin/main` = `6b4dd84`.
**Plan:** `docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md` (412 lines).
**Nothing implemented.** No file under `src/`, `scripts/` or `docs/` was edited.

## 1. Readiness verdict

READY, with the two conditions in the first line. PARA-2 is unsigned and is not needed: the plan marks it optional and "Not part of PARA-1" (plan `:152`).

## 2. Task 0 evidence (measured 2026-10-07)

| Check | Command | Output |
|---|---|---|
| SAFE-CHAT (#44) merged | `git merge-base --is-ancestor 0bad019 origin/main; echo $?` | `0` |
| SAFE-INTERP-GROUNDED (#48) merged | `git merge-base --is-ancestor ee5721d origin/main; echo $?` | `0` |
| Plan PR (#47) merged | `git merge-base --is-ancestor 930c678 origin/main; echo $?` | `0` |
| Plan file tracked | `git ls-files docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md` | `docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md` |
| Plan Task 0 Step 2 refresh check | `git diff --quiet 90c502a origin/main -- src/backend/modules/interpret_safety.py src/backend/scripts/seed_knowledge_base.py src/backend/modules/agent/nodes/draft.py src/backend/modules/agent/guardrails/templates.py; echo $?` | `0` (all 4 files byte-identical to the plan's measurement ref) |
| D9 interpreter | `~/venvs/asclexis-311/bin/python --version` | `Python 3.11.16` |
| Collected baseline | `HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider --collect-only -q \| tail -3` (from `src/backend`) | `1370 tests collected in 10.00s` |
| Worktree product code = main | `git diff --quiet origin/main HEAD -- src/ scripts/ .github/; echo $?` | `0` |

| Gate | State | Evidence |
|---|---|---|
| PROHIBITED-PARAPHRASE ("Plan now, edit later") | signed 2026-10-04 | `docs/capstone-report/owner-decisions-2026-09-27.md:60` |
| **PARA-1** ("Sign, floor 85%") | signed 2026-10-07 | `docs/capstone-report/owner-decisions-2026-09-27.md:62` |
| PARA-1 row on `origin/main` | **not yet** | `git show origin/main:docs/capstone-report/owner-decisions-2026-09-27.md \| grep -c "PARA-1"` → `0`; PR #49 is `OPEN MERGEABLE 8d6f02e` (`gh pr view 49`) |
| PARA-2 (agent draft path) | UNSIGNED | plan `:152`; owner-decisions `:62` "PARA-2 … was not asked and stays unsigned" |

Plan Task 0 Step 1 ("PARA-1 signed verbatim in owner-decisions. Otherwise STOP.") fails in a worktree cut from `origin/main` until #49 merges.

## 3. Owner questions still to ask

**Ask-first edit inventory**

| File | Edit | Covered verbatim? |
|---|---|---|
| `src/backend/modules/interpret_safety.py` | replace the `PROHIBITED_PATTERNS` list body (`:49-68`) with the plan's `candidates.py` list (plan `:365-383`) | **Yes**, by PARA-1 (owner-decisions `:62`), for that exact list only. Any changed, added or removed pattern is not covered. |
| `interpret_safety.py` compile code (`:92-95`), `filter_prohibited_content` (`:213-246`) | none | Not licensed. Plan `:178` forbids it. |
| `redaction.py`, `faithfulness.py`, `verifier_agent.py`, auth, encryption | none | — |

**Q1 (top; ask before dispatch).** The list you signed as PARA-1 replaces "you have <any word>" with a form that needs a one-word condition ending in a fixed suffix. A scaffold probe (§7 R-1) found 13 of 13 plain diagnosis sentences that today's patterns catch and the signed list misses, for example "You have kidney disease.", "You have type 2 diabetes.", "You have hypertension.". The numbers you were shown (37 of 42, 0 false alarms) did not include this. How should execution proceed?
- A. **Measure first, then re-sign (recommended).** Execution builds the held-out corpus plus a "must not regress" set, measures the signed list in memory only, and returns the numbers. `interpret_safety.py` is not edited until you approve the final list.
- B. Run as signed. Accept that these sentences pass on the legacy path, and rely on the 85 % floor to catch it.
- C. Approve now a widened R1 (multi-word conditions, extra terms such as "hypertension") without new numbers.
- D. Pause the phase.

**Q2. Who writes the held-out corpus ("written independently")?** The plan says "owner or Codex" (`:170`).
- A. **Codex, read-only, given only the five category definitions and the product's must-allow sources, never the patterns or the author corpus; you spot-check the list (recommended).**
- B. You write it (at least 20 must-block and 20 must-allow).
- C. A separate Claude agent that has not seen the patterns.

**Q3. Which texts count for "0 false alarms on the must-allow set"?**
- A. **The plan's 77 texts plus the held-out must-allow sentences (recommended).**
- B. The plan's 77 texts only.

**Q4. PARA-2: also apply the patterns to the agent draft path?** Chat uses the agent path by default (`modules/agent/settings.py:19`), and that path does not read these patterns (§7 R-6).
- A. **Leave unsigned for this phase; decide after its numbers come back (recommended).**
- B. Sign now; needs its own plan section, because the plan has no PARA-2 tasks.
- C. Decline.

## 4. Plan drift check

Plan refs are `@90c502a`. Re-opened at `6b4dd84`.

| # | Plan cite | Now | Result |
|---|---|---|---|
| 1 | `interpret_safety.py:49-68` `PROHIBITED_PATTERNS` (plan `:16`) | `:49-68`, 11 patterns | MATCH |
| 2 | `interpret_safety.py:124-128` `validate_interpretation` loop (`:21`) | `:124-130` | MATCH |
| 3 | `interpret_safety.py:225-240` `filter_prohibited_content` (`:22`) | loop starts `:225`, ends `:244` | MATCH |
| 4 | `modules/rag.py:176-179` compile (`:20`) | `:178-181` | MOVED (+2; PR #44 `f5961e7` added the `prohibited_advice` field at `:112-113`) |
| 5 | `modules/rag.py:836-839` match loop (`:20`) | `:839-842` | CHANGED: `:842` now sets `prohibited_advice = True` (PR #44 `f5961e7`) |
| 6 | "After SAFE-CHAT and SAFE-INTERP-GROUNDED the whole answer is replaced" (`:20`) | `api/assistant.py:879-892`, `api/interpretations.py:542` | MATCH (both merged: #44, #48) |
| 7 | Task 0 Step 2 refresh diff (`:167`) | rc `0` | MATCH |
| 8 | `tests/test_interpret_safety_adversarial.py` (8 tests) (`:181`) | 8 `def test_` | MATCH |
| 9 | `tests/test_safe_chat_prohibited.py`, `tests/test_safe_interp_grounded.py` "if merged" (`:182`) | both exist | MATCH; fixture `:38` "This means you have hyperlipidemia and you should take 20 mg" still caught (probe: R1, K2) |
| 10 | Agent draft sentences "You have N …" (`:301-303`) | `modules/agent/nodes/draft.py:155`, `:193`, `:249` | MATCH |
| 11 | `ESCALATE_TEMPLATE`, `ABSTAIN_TEMPLATE` (`:221`) | `modules/agent/guardrails/templates.py:12`, `:20` | MATCH |
| 12 | Plan status "NOT APPROVED FOR EXECUTION" (`:5`); heading "Owner sign-off (unsigned)" (`:149`) | `:151` is ticked on the #49 branch (`98a452a`); `:5` and `:149` still say unapproved; `origin/main:151` is `- [ ]` | CHANGED |
| 13 | Spec "owner-decisions on `docs/wave3-close`" (`:12`) | rows at owner-decisions `:60`, `:62`, branch only | MOVED |
| 14 | Count slots (`:160`) | `CLAUDE.md:30`, `:34`; `AGENT.md:76` = 1370 = measured | MATCH |
| 15 | Baseline 13/42 and 13/77; candidates 37/42 and 0/77 (`:38`, `:68`, `:106`, `:112`) | not re-run here; inputs byte-identical (row 7) | UNMEASURED at `6b4dd84` |

**Count:** 10 MATCH · 2 MOVED · 2 CHANGED · 1 UNMEASURED.

**Plan amendments needed** (list only; the plan file is not edited here)

1. Status line `:5` and heading `:149`: state PARA-1 signed 2026-10-07 with the 85 % floor.
2. Line refs: `rag.py:176-179` → `:178-181`; `:836-839` → `:839-842`.
3. Add a step before Task 2: measure the candidate list **in memory** against HELD_OUT and the must-allow set; edit the ask-first file only after it passes (the signed row says "must first build … and reach …").
4. Green targets (`:179-182`): add `tests/test_rag_pipeline.py` and `tests/test_biomarker_assistant.py`; both assert on pattern matches (`test_rag_pipeline.py:599`, `:670`, `:687`, `:722`, `:1159`; `test_biomarker_assistant.py:513`, `:533`).
5. Task 1: name test IDs in the repo's `HC-XXX-NNN` form and fix the number of test functions; the plan names neither.
6. Task 3 Step 1: wrap the gate in `timeout` and record the exit code (GATE-14).
7. Task 3 Step 3: `filter_prohibited_content` has no product caller (§7 R-5); mark the step UNMEASURED or drop it.
8. Add a regression assertion: every sentence the current 11 patterns catch in MUST_BLOCK-class text stays caught (pending Q1).

## 5. File ownership

| File | Action | Overlap with undone phases |
|---|---|---|
| `src/backend/tests/test_prohibited_patterns_corpus.py` | create | none |
| `src/backend/modules/interpret_safety.py` | modify `PROHIBITED_PATTERNS` only | No undone plan edits it: read-only in W-3 (`:36`, `:154`), W-4 (`:135`), W-7 (`:39`, `:146`). W-2, W-8, W-11a, W-11b, W-10 mention it 1-4 times each; not opened (UNMEASURED) |
| `CLAUDE.md:30`, `:34`; `AGENT.md:76` | collected slots | every collection-changing phase: P5, W-4, W-2, W-3, P6, P7, W-7, W-8, W-11a PR-1, W-11a PR-3, G-C1, G-C3a, G-C5. Serial at merge (ground rule 8) |
| `docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md` | amendments (first commit) + execution record | PR #49 edits `:151`; merge #49 first |
| `docs/INDEX.md`, `docs/_link_graph.json` | regenerate if the docs gates ask | every docs-touching PR; generated files |
| `docs/features/TASK_LIST.md` | Session Note (definition of done) | serial, newest-first (program `:158`) |

Not edited by this phase; L0 updates after merge: matrix `SAFE-05` row (`specs-compliance-matrix.md:81`), program rows `:425` and `:490`.

**Behaviour overlap (no shared file):**
- W-7 calls `validate_interpretation` on model output (W-7 plan `:88`); its 23 new tests must be measured on the new list.
- W-4 golden case `abstain-prohibited-advice` ("You should take metformin…") stays caught by K5 (probe). W-4's two `answer-*` cases match nothing (probe).
- Owner items SAFE-INTERP-EMBEDDED and SAFE-CHAT-AGENT / -FALLBACK "resolve with PARA-1" (program `:493`, `:497`).

The program's shared-file list (`implementation-program.md:137-161`) has no `interpret_safety.py` line. Extension needed: `modules/interpret_safety.py`: PROHIBITED-PARAPHRASE only.

## 6. Briefs

**Classification**
- Architectural per `orchestration.md` §5: not listed. Codex plan + diff review still applies: ledger RESUME POINT `:192` ("security-reviewer + Codex") and owner direction `:193` (large plans; models "6.1 sol", then "6-luna high" — IDs unconfirmed, ledger says confirm before first use).
- Reviewers: `code-reviewer` (always) and `security-reviewer` (ledger `:192`; safety boundary).
- Fable adversarial brief review: owner direction (`ledger.md:194`) names large stages; L0's reading lists the frontend sequence. Not required by that reading. Recommended here because of R-1 and R-2; L0 decides.
- Tests this phase adds: **N = the number of test functions in `test_prohibited_patterns_corpus.py`.** The plan lists 3 assertions and no function count, so N is undetermined until amendment 5.

### L1 brief (handoff §4 template)

```
You are the L1 Wave Orchestrator for Wave 4 of the Asclexis execution
program. Follow docs/agentic/orchestration.md §3 exactly; you are L1.
Phases in this wave: PROHIBITED-PARAPHRASE: docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md
Base: origin/main @ <sha after PR #49 merges>. Confirmed merged dependencies:
SAFE-CHAT (#44, 0bad019), SAFE-INTERP-GROUNDED (#48, ee5721d), plan PR #47 (930c678).
Signed gates you may rely on (verbatim from owner-decisions): PARA-1 "Sign,
floor 85%": "Approve the candidate list. Execution must first build a
held-out corpus written independently and reach at least 85% recall on it
with 0 false alarms on the must-allow set, or stop and come back to you."
<plus the owner's answers to scaffold Q1-Q3, verbatim>
Unsigned gates: PARA-2 (agent draft path). A task that needs one STOPS; report it.
Architectural phases (Codex plan + diff review): PROHIBITED-PARAPHRASE
(owner direction 2026-10-07; confirm the Codex model ID before first use).
Per phase: worktree ../hc-para, branch fix/prohibited-paraphrase-patterns, one PR.
Spawn implementers with Agent(subagent_type="general-purpose",
model="sonnet") using the §5 brief; reviewers with
Agent(subagent_type="code-reviewer", model="opus") using the §6 brief (plus
security-reviewer when the diff touches redaction/auth/encryption/export/
logging/external runner). Implementers must not spawn agents.
This phase also gets security-reviewer (ledger RESUME POINT 2026-10-07).
Run each plan's measured acceptance yourself, in the worktree, with the D9
venv and HF_HUB_OFFLINE=1. Paste the commands and their outputs.
Order inside the phase: (1) plan Task 0; (2) commit plan amendments 1-8 from
audit/2026-09-25/waves/scaffold/PROHIBITED-PARAPHRASE.md §4 as the first
commit; (3) obtain the held-out corpus from the author the owner named;
(4) measure the signed list IN MEMORY against it; (5) if held-out recall
< 85% or any must-allow text matches, STOP and report: do not edit
interpret_safety.py; (6) only then the L2 implementer runs Tasks 1-3.
Acceptance commands (from ../hc-para/src/backend unless noted):
  HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_prohibited_patterns_corpus.py -p no:cacheprovider -q
  HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/test_interpret_safety_adversarial.py tests/test_safe_chat_prohibited.py tests/test_safe_interp_grounded.py tests/test_rag_pipeline.py tests/test_biomarker_assistant.py -p no:cacheprovider -q
  HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider --collect-only -q | tail -3
  flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q
  (repo root) HF_HUB_OFFLINE=1 timeout 600 ~/venvs/asclexis-311/bin/python scripts/agent_eval_gate.py; echo "rc=$?"
  (repo root) git diff origin/main...HEAD --name-only
  (repo root) git diff origin/main...HEAD -- src/backend/modules/interpret_safety.py   # hunks inside PROHIBITED_PATTERNS only
  (repo root) python3 scripts/docs_lint.py
Collected count: start 1370 (measured 2026-10-07 @ 6b4dd84; re-measure at
your base). Tests this phase adds: N = test functions in the new corpus
file. End = start + N; update CLAUDE.md:30,:34 and AGENT.md:76 in the commit
that changes collection (SLOT-RULE).
Break-it: revert R9 to r"\b(guaranteed|definite(ly)?|certain(ly)?)\b" and
show the must-allow assertion FAIL; restore; show PASS.
Write audit/2026-09-25/waves/wave-4.md and return it: per phase the PR
URL, commands and outputs, collected delta, gates used, open findings, and
the merge order.
Do not merge. Do not sign gates. Do not edit files outside the phase plans'
file lists.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### L2 implementer brief (handoff §5 template)

```
Implement docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md, tasks 1-3, in
worktree /mnt/c/Users/DangT/Documents/GitHub/hc-para on branch
fix/prohibited-paraphrase-patterns.
Python: ~/venvs/asclexis-311/bin/python. Always export HF_HUB_OFFLINE=1.
Follow the plan literally, task by task. Test first: run the new test and
paste the FAIL, then implement, then paste the PASS. Commit exactly as the
plan lists, with explicit pathspecs (never `git add -A`), `fix(scope):` /
`feat(scope):` / `docs:` prefixes, ending with the Co-Authored-By line.
Ask-first files: src/backend/modules/interpret_safety.py. PARA-1
(owner-decisions row PARA-1, signed 2026-10-07) covers exactly one edit:
replacing the PROHIBITED_PATTERNS list body with the plan's candidates.py
list (R1, K2-K7, R8, R9, K10, K11, A1, A2b, A3-A7), copied character for
character. Nothing else in that file. No other ask-first file.
The HELD_OUT lists are supplied to you by L1. Do not write, extend, reword
or drop any held-out sentence. Do not tune a pattern.
Full suite only under: flock /tmp/claude-1000/hc-pytest.lock env
HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ -p
no:cacheprovider -q
Stop and report, without working around it, if: a step fails in a way the
plan does not predict, a count differs from the plan, a gate is needed, or
an edit would fall outside the plan's file list. Also stop if: any
must-allow text matches; held-out recall is below 85%; MUST_BLOCK caught is
below 37; any existing safety test would need a changed assertion.
Do NOT spawn agents. Do NOT push.
Return: commits (sha + subject), each test command with its output, the
collected count before and after, and any deviation with its reason.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 7. Risks and open findings the plan does not cover

Probe method for R-1 to R-3: a standalone script using only Python `re`, with the 18 candidate patterns copied from plan `:360-383` and the 11 current patterns copied from `interpret_safety.py:51-67`, compiled with `re.IGNORECASE` as the product does. It imports no product code. It is not the plan's corpus, and its sentences were written by this scaffold agent, so they are leads, not a held-out set.

**R-1 (HIGH). The signed list stops catching plain diagnoses the current list catches.** Recurring-failures §2.
Probe, "current 11 patterns | candidate list":
```
You have kidney disease. | CAUGHT | MISS
You have heart disease. | CAUGHT | MISS
You have type 2 diabetes. | CAUGHT | MISS
You have high blood pressure. | CAUGHT | MISS
You have a vitamin D deficiency. | CAUGHT | MISS
You have an underactive thyroid. | CAUGHT | MISS
You have chronic kidney disease. | CAUGHT | MISS
You have iron-deficiency anemia. | CAUGHT | MISS
You have lupus. | CAUGHT | MISS
You have hypertension. | CAUGHT | MISS
You have a tumor. | CAUGHT | MISS
The diagnosis of diabetes is confirmed. | CAUGHT | MISS
You are diagnosed with lupus. | CAUGHT | MISS
It is certain that this is serious. | CAUGHT | MISS
This is a definite sign of kidney trouble. | CAUGHT | MISS
```
The first 13 rows are diagnoses. The last 2 are the bare "certain" / "definite" forms that R9 drops on purpose (plan `:139`); they are listed so the owner sees the cost.
Cause: R1 needs the condition as the single word right after "have (a/an)", ending in a listed suffix; it also drops the "you are diagnosed with" and "diagnosis of" forms. The plan's MUST_BLOCK has only one-word conditions after "you have", so 37/42 could not see this.

**R-2 (HIGH). False alarms on ordinary lab education.** Each one replaces the whole answer with the escalation template (`api/assistant.py:879-892`). Recurring-failures §2.
```
FALSE-POSITIVE R8 '100%'   | Your oxygen saturation was 100% on this reading.
FALSE-POSITIVE R8 '100 %'  | Neutrophils made up 100 % of the counted cells in this note.
FALSE-POSITIVE A4          | Some labs use a fasting cutoff of 100 mg/dL for this test.
FALSE-POSITIVE A4          | Doctors take a fasting level above 126 mg/dL on two tests as a threshold.
FALSE-POSITIVE A4          | Labs use different units; your result of 5.2 units is in range.
FALSE-POSITIVE A6          | You may need to stop eating 8 hours before a fasting test.
FALSE-POSITIVE A6          | Your clinician can tell you whether you should start any follow-up testing.
FALSE-POSITIVE A6          | Start by looking at the reference range printed on your report.
FALSE-POSITIVE A3          | The lab note says you got results from two draws.
FALSE-POSITIVE A6          | Your result is 120 mg/dL. Stop and compare it with the reference range.
```
10 of 12 probe sentences matched. A4 fires on "take / use / try" followed within 40 characters by a number and `mg` or `units`, and `mg/dL` is the unit of most lab values. If the independent must-allow set contains one such sentence, the signed "0 false alarms" condition fails and the phase stops.

**R-3 (MEDIUM). Multi-line model output is missed.** A6's sentence-start branch uses `^`; the product compiles with `re.IGNORECASE` only (`interpret_safety.py:92-95`, `rag.py:178-181`), so `^` matches only the start of the whole answer. Probe: 4 of 6 missed, including `'Next steps:\n- Begin iron supplements right away'`, `'Next steps:\nSwitch to a different statin'`, `'**Begin** iron supplements right away.'`, `'You should be taking 81mg aspirin.'`. The plan forbids changing the compile code (`:178`), so a fix means a changed pattern, which PARA-1 does not cover.

**R-4 (MEDIUM). Two test files outside the plan's green targets assert on these patterns.** `tests/test_rag_pipeline.py:599`, `:670`, `:687`, `:722`, `:1159`; `tests/test_biomarker_assistant.py:513`, `:533`. Probe: all 7 fixtures plus the SAFE-CHAT fixture stay caught, and the clean answer at `test_biomarker_assistant.py:546-557` matches nothing. Not run under pytest (the plan ran only the 8 adversarial tests with the list monkeypatched, plan `:127`).

**R-5 (MEDIUM). `filter_prohibited_content` is dead in product code.** `grep -rn filter_prohibited_content src/` → the definition (`interpret_safety.py:213`) and one test (`tests/test_interpret_safety_adversarial.py:89`). Same at `90c502a`. The plan lists it as one of three consumers (`:22`) and plans a hand review of its output (`:189`). Recurring-failures §10.

**R-6 (MEDIUM). The default chat path is not affected.** `AGENT_ENABLED_DEFAULT = True` (`modules/agent/settings.py:19`); `grep -rn "PROHIBITED_PATTERNS\|interpret_safety" src/backend/modules/agent` → 0 hits. The edit changes legacy chat (agent off), the grounded-interpretation route and template-interpretation validation (`modules/interpret.py:209`, `:959`). Recurring-failures §9. PARA-2 is the gate.

**R-7 (LOW). Records disagree on PARA-1.** On the #49 branch, owner-decisions `:62` and plan `:151` say signed; `implementation-program.md:425` ("PARA-1 (unsigned)") and `:490` ("not approved for execution") still say unsigned. Recurring-failures §8.

**R-8 (LOW). GATE-14.** `scripts/agent_eval_gate.py` printed PASS and then did not exit on Windows 3.13 (program `:464`); Linux 3.11 is UNMEASURED. Task 3 Step 1 needs `timeout` and the recorded exit code.

**R-9 (LOW). The measurement scripts exist only as text in the plan** (`:211-408`); `$D` is not in the repo. The pattern strings reach `interpret_safety.py` by transcription. Reviewer check: extract the list from the plan and compare string for string with the diff.

**R-10 (LOW). "0 false alarms" has two readings** (the plan's 77 texts, or those plus held-out must-allow). See Q3.

**Not measured by this pack:** the plan's own `measure.py` / `candidates.py` at `6b4dd84`; any real model output; the 60 KB fields under the candidate list (plan reports 0 of 60).

Next action: merge PR #49, then put Q1 to the owner.
