**GATED** — merged dependencies are met (P8 packet PR #30, P1), but packet Brief 5 is unsigned (Q5a, Q5b) and **no plan exists**. Q5b (how the NLI model reaches the machine) blocks any build. First step is a plan-writing phase.

# G-C5 — HC-M11 NLI cross-encoder, flag off (readiness pack)

**Measured:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84`.
**Plan:** none (`implementation-program.md:410`, `:449`: "none yet").
**Kind:** PRODUCT, ask-first files. Acceptance in the program: "flag off ⇒ eval output byte-identical to before".

## 1. Readiness verdict

| Item | State |
|---|---|
| P1 | merged |
| P8 packet (Brief 5 written) | merged, PR #30, `242f7a0` |
| Build approval, flag default off | in force: `owner-decisions-2026-09-27.md:74` (worktree; `:56` on main) "HC-M11 approved behind a default-off flag only"; source `docs/plans/2026-09-08-backlog-closure-plan.md:403` |
| Brief 5 Q5a (production-behaviour change) | UNSIGNED: `gated-items-decision-packet.md:393`; ledger row `:425` |
| Brief 5 Q5b (NLI-model distribution) | UNSIGNED: `:407`; ledger row `:426` |
| Plan file | **does not exist** |
| Exact ask-first hunks | not named anywhere yet |

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| P1 | `git merge-base --is-ancestor 7b2ff1f origin/main; echo $?` / `… 692fdf3 …` | 0 / 0 |
| P8 | `git merge-base --is-ancestor 242f7a0 origin/main; echo $?` | 0 |
| Packet on main | `git cat-file -e origin/main:audit/2026-09-25/gated-items-decision-packet.md` | exit 0 |
| `Owner decision:` lines | `grep -n "Owner decision:" audit/2026-09-25/gated-items-decision-packet.md` | 8 lines (`:64`, `:117`, `:196`, `:330`, `:333`, `:336`, `:393`, `:407`), every one `☐ approve ☐ reject ☐ defer — notes/date: ____` |
| Sign-off ledger | `sed -n 417,427p` same file | rows 1, 2, 3, 4a, 4b, 4c, 5a, 5b all unticked, no dates |
| Plan | `git ls-files docs/plans audit/2026-09-25/plans \| grep -i -c 'm11\|gc5\|g-c5\|nli'` | 0 |
| Ledger entry | `feature_list.json:140-150` | `"status": "pending"`; 3 verification steps (flag on: contradicted claim scores below threshold; flag off: existing tests unchanged; offline test: no network at inference) |
| Hook points in ask-first files | `grep -n "use_llm_entailment\|entailment_scores" modules/faithfulness.py modules/verifier_agent.py` | `verifier_agent.py:88` `use_llm_entailment: bool = False`, `:223` `if self.config.use_llm_entailment:`; `faithfulness.py:99` `entailment_scores: Optional[list[float]] = None`, `:117-118`, `:160`, `:178` |
| Collected | collect-only, D9 venv, `HF_HUB_OFFLINE=1` | `1370 tests collected in 19.88s` |

No 2026-10-04 or 2026-10-07 owner row concerns G-C5.

## 3. Owner questions still to ask

1. **Q5b (packet `:395-407`), required before a plan can fix its file list.** "How may the NLI model (`cross-encoder/nli-deberta-v3-xsmall`, candidate) reach the machine? D8 covered the embedding model only."
   - A. One-time fetch by `src/backend/scripts/download_models.py` into a local models dir; Hugging Face offline at runtime; fail closed if absent. **(packet's recommendation; it reuses W-8's mechanism, and W-8 is not merged, so this makes W-8 a dependency)**
   - B. Bundled with the installer when one exists (G-C4; no installer today).
   - C. Other: ____.
2. **Q5a (packet `:391-393`).** "The build behind a default-off flag is already approved. Separately: may the flag ever default on, or NLI scores change production faithfulness outcomes?"
   - A. Not now; keep default off; G-C5 brings back eval evidence. **(packet's recommendation)**
   - B. Approve enabling after G-C5 shows a criterion you write: ____.
   - C. Reject.
3. **GC5-ASKFIRST.** "G-C5 edits two ask-first files. The 2026-09-08 approval names them as a pair. Approve the exact hunks once the plan lists them?" The plan must list each hunk in `modules/faithfulness.py` and `modules/verifier_agent.py`; orchestration §4 needs a signed line naming the exact edit. A. Yes, review the hunk list in the plan **(recommended)** · B. Re-open the approval.
4. **GC5-MODEL.** "Confirm the model, its licence and a pinned revision before any download." The packet marks the MIT licence UNVERIFIED and the size UNMEASURED (`:399-403`). A. Plan measures both, you confirm **(recommended)** · B. You name a different model.
5. **GC5-PLAN.** "Write the G-C5 plan now (plan only, like PROHIBITED-PARAPHRASE), or wait for W-8?" A. Plan now, execute after Q5b and W-8 · B. Wait for W-8 **(recommended if Q5b = A: the plan's download and offline-load steps copy W-8's merged code)**.

Ask-first touches: `modules/faithfulness.py`, `modules/verifier_agent.py` (CLAUDE.md §1). Also Local-first: a new model download path; the product path must stay offline.

## 4. Plan drift check

No plan. Register and packet citations re-checked:

| Citation | Now | Result |
|---|---|---|
| Program `:389`: "the `Owner decision:` lines … are unfilled" | 8 of 8 unfilled | MATCH |
| Packet Brief 5 `:338-415`; Q5a `:391`, Q5b `:395` | present | MATCH |
| Backlog plan §12 `:359-…`, approval row `:403` | present | MATCH |
| Backlog plan `:55`: HC-M11 "still cannot start until its non-GGUF model-distribution d[ecision]" | Q5b unsigned | MATCH (the blocker is real) |
| `verifier_agent.py` `use_llm_entailment`, `_check_entailment_llm` (packet sketch `:413`) | `:88`, `:223`; call at `:224`, definition at `:304`. A second `use_llm_entailment: bool = False` sits at `core/config.py:157` | MATCH |
| "via the existing sentence-transformers dependency" (`feature_list.json:142`) | `src/backend/requirements.txt:73` `sentence-transformers>=2.2.0` (unbounded above) | MATCH |

## 5. File ownership and overlap (expected; the plan fixes the list)

**Likely owned:** `modules/faithfulness.py` (ask-first), `modules/verifier_agent.py` (ask-first), `core/config.py` (the flag already exists at `:157`; the plan decides whether it is touched), `src/backend/scripts/download_models.py`, `config/model_manifest.json`, new tests, `CLAUDE.md` / `AGENT.md` count slots.

| Other phase | Shared file | Order |
|---|---|---|
| W-8 | `src/backend/scripts/download_models.py`, `core/config.py`, `config/.env.example`, model-manifest neighbourhood, `ci.yml` | W-8 → G-C5 (if Q5b = A) |
| W-4 | reads the faithfulness score (threshold 0.6, never lowered); legacy eval gate | W-4 → G-C5, so the "byte-identical with the flag off" check has the W-4 gate to compare against |
| W-3 | `modules/rag.py` neighbourhood (calls the verifier) | no shared file expected; confirm in the plan |
| PROHIBITED-PARAPHRASE | `modules/interpret_safety.py` (a different ask-first file) | none |
| P5 | `grep -n "utcnow" modules/faithfulness.py modules/verifier_agent.py` → 0 hits | no shared file |
| W-10 | `CLAUDE.md` invariant lines vs G-C5's count slots | different lines; serial at merge (ground rule 8) |
| G-C4 | installer bundling (Q5b option B) | decision record only |
| AUDIT-ORDER plan, G-C2, P4-deferred, NPM-AUDIT-2, React Router 7, Tailwind 4, P6, P7, W-2, W-7, W-11a, G-C1, G-C3a, W-10b | none expected | — |

## 6. Briefs

Execution briefs cannot be filled: there is no plan, no task list and no acceptance commands. The only dispatchable step is plan-writing, and only after Q5b.

### Plan-author brief (filled; dispatch only after Q5b is signed)

```
Write docs/plans/2026-10-XX-GC5-hc-m11-nli-flag-off.md in worktree
/mnt/c/Users/DangT/Documents/GitHub/hc-gc5-plan (branch docs/gc5-plan). Use the
superpowers:writing-plans skill. Read-only on everything except that one new
file. Do not edit any file under src/. Do not download any model.
Read first: CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md,
audit/2026-09-25/gated-items-decision-packet.md Brief 5 (:338-415),
docs/plans/2026-09-08-backlog-closure-plan.md §12 and §14 row 2 (:359, :403),
feature_list.json HC-M11 (:140-150), audit/2026-09-25/waves/scaffold/G-C5.md,
and the W-8 plan (docs/plans/2026-09-27-W08-bundled-embedding-model.md) plus its
merged code if W-8 has landed.
Approved scope, verbatim (backlog plan :403): "Building the cross-encoder behind
a flag that defaults off, in two ask-before-touching files. **Not** changing
production scoring behaviour, thresholds, or anything else in those files".
Signed owner answers: <Q5b verbatim; Q5a verbatim if given>.
The plan must: list every hunk in modules/faithfulness.py and
modules/verifier_agent.py with Before/After text (those lines go to the owner as
GC5-ASKFIRST); keep the 0.6 threshold and every existing test unchanged; prove
"flag off ⇒ output byte-identical" with a named command run before and after
(agent eval gate + the faithfulness/verifier test files, exit codes recorded);
load the model from a local path with HF_HUB_OFFLINE=1 and fail closed if absent;
add a socket-blocked offline test; pin the model revision and a sha256; measure
licence and size and write UNMEASURED where not measured; state the
collected-count delta and the ground-rule-8 slot commit; give break-it steps for
each new test; order itself against W-8, W-4 and P5.
Status line: "PROPOSED — plan only, not approved for execution". No ticked boxes.
Do NOT spawn agents. Do NOT push. Do not commit; L1 commits the plan with the
regenerated docs/INDEX.md and docs/_link_graph.json.
Return: the plan path, the ask-first hunk list, the unsigned owner lines, and
everything you could not measure.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

Reviews for that plan: Codex plan review (it changes a safety-scoring path beside ask-first files; treat as architectural, same class as W-4 in orchestration §5), `code-reviewer` and `security-reviewer` (opus). Acceptance for the plan PR: the same docs gates as any plan PR (`docs_lint.py`, `generate_docs_index.py --check`, `harness_drift_check.py`, `repo_hygiene_check.py`; collect-only unchanged; `git diff --name-only origin/main...HEAD -- src | wc -l` → 0).

## 7. Risks and open findings

| # | Finding | Evidence | Recurring-failures mode |
|---|---|---|---|
| 1 | "Byte-identical with the flag off" is easy to assert and hard to prove; a test that only checks the flag's default cannot see a changed code path | acceptance text, program `:410` | #1 a green suite that could not have failed |
| 2 | A new model download is a new outbound path beside the Local-first invariant | `CLAUDE.md:59`; packet `:399-403` | #4 environment-dependent results (a cached model hides a missing one; same class as `test_api_rag_index_002b`) |
| 3 | Licence "MIT" and artifact size are unverified | packet `:401` | #3 figures asserted instead of measured |
| 4 | The 2026-09-08 approval names files, not hunks; orchestration §4 wants the exact edit signed | backlog plan `:403`; `orchestration.md:48` | ask-first rule |
| 5 | The dev agent-eval gate prints PASS and then does not exit on Windows (GATE-14); a before/after comparison must record exit codes | program `:464` | #6 documented commands nobody ran |
| 6 | Q5a answered "enable" later would change patient-visible faithfulness outcomes; that is outside G-C5 | packet `:391` | scope |

Next action: ask the owner Q5b (question 1); nothing else in G-C5 can start before it.
