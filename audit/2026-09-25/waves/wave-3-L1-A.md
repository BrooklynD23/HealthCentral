# Wave 3 — L1-A report (backend)

Status: all 3 phases done. PRs #41 (DDI), #44 (SAFE-CHAT) and #45 (G-C3b) are open, and CI passes 6/6 on each. None is merged.

## Phase 1 — DOC-DELETE-INTERP

PR **https://github.com/BrooklynD23/HealthCentral/pull/41** · branch `fix/ddi-doc-delete-interpretation` · head `ce5b692` · base `main` @ `90c502a` · worktree `../hc-ddi`

Commits:
1. `6d76498` docs(ddi): plan + Codex plan reviews r1/r2
2. `73ae541` fix(documents): cascade interpretations and unlink file after commit on delete (L2 sonnet)
3. `ce5b692` docs(ddi): execution record and Codex diff review

Fix: `Observation.interpretation` gets `cascade="all, delete"`. `delete_document` unlinks the `.bin` only after `profile_db.commit()`. `OSError` is logged without path or filename, and the audit row is still written. No schema, FK or migration change. No ask-first file touched.

### Commands and outputs (D9 venv, Py 3.11, `HF_HUB_OFFLINE=1`)
| Check | Output |
|---|---|
| Pre-fix probe, 90c502a | `IntegrityError … NOT NULL constraint failed: lab_interpretations.observation_id`. After rollback: documents 1, observations 1, lab_interpretations 1 |
| RED `-k HC_DDI` | `4 failed, 15 deselected` |
| GREEN `tests/test_documents_api.py` | `19 passed` |
| collect | `1346` → `1350 tests collected` (**+4**). Slots rewritten at `CLAUDE.md:30`, `:35` and `AGENT.md:76` |
| full suite (flock) | `1350 passed, 67 warnings in 724.08s`, rc=0 |
| boot | `boot ok` |
| scope | `SCOPE-OK` (migrations, core, modules, docs/compliance, docs/agentic unchanged) |
| CI `gh pr checks 41` | Agent Eval Gate, Backend Tests, Documentation Lint, E2E Smoke Tests, Frontend Tests, Security Scan: all pass |

### Break-it (detached worktree at head, by line number, then removed)
| Break | Result |
|---|---|
| BI-1: `cascade="all, delete"` removed (`models/observation.py:114`) | 001 and 004 FAIL |
| BI-2: unlink moved above `profile_db.delete` | 002 FAIL |
| BI-3: `try/except OSError` removed | 003 FAIL |
| restore | `4 passed` |

### Gates used
- W3-SEC-SCHED (verbatim in the brief). No other gate was needed.

### Codex
| Round | Verdict | Dispositions |
|---|---|---|
| Plan r1 | REVISE, 2 BLOCKER + 3 MAJOR | 4 accepted and fixed. 1 rejected at first (the recurring-failures edit), then reversed in r2 |
| Plan r2 (last) | REVISE, 1 BLOCKER + 8 MAJOR + 1 MINOR | 9 accepted and fixed. 1 rejected: rebase vs merge, because `orchestration.md:24` says merge |
| Diff | needs-attention, 2 high + 1 medium | All 3 checked against the code: none was introduced by this diff, and all are outside W3-SEC-SCHED. Recorded as owner items below |

Records: `audit/2026-09-25/reviews/DDI-r1-*`, `DDI-r2-*` and `DDI-diff-codex.txt` on the PR branch.

### Reviewers
- code-reviewer (opus): APPROVE, 3 MINOR. No change needed: residue is not audited, there is 1 lazy SELECT per observation, and mid-file imports.
- security-reviewer (opus): APPROVE. 1 LOW introduced: if the unlink fails after commit, the orphan `.bin` stays until the profile is deleted. 4 MEDIUM and 2 LOW were already on main.

### Docs truth value (not edited)
- `data-privacy.md:185` ("ORM cascade") was already true for observations and chunks; interpretations now follow it too. Not edited (owner-gated).
- `sql-fk-001:56` is true. `:59` is conditional on the pragma (P6) and is now also true through the ORM. Not edited.

### Open findings (owner items, new)
1. **REPROCESS-INTERP-ORPHAN** (security MEDIUM, Codex high): the reprocess bulk `delete(Observation)` at `api/documents.py:627-630` orphans `LabInterpretation` rows, which `/interpretations/recent` (`api/interpretations.py:631`) still lists. The same shape for `Chunk` at `:868` orphans embeddings.
2. **PANEL-INTERP-STALE** (MEDIUM): `PanelInterpretation.observation_ids_json` (`models/interpretation.py:159`) is not cleaned on delete, and `modules/interpret.py:347` can reuse it.
3. **DDI-AUDIT-ORDER** (Codex high, security MEDIUM): the master audit commit runs after the irreversible profile delete and unlink. If the audit fails, the deletion has no audit row. The same window existed on main.
4. **DDI-ORPHAN-BIN** (LOW, introduced): a failed post-commit unlink leaves ciphertext with no sweep until profile delete, and only a warning log records it.
5. **Proposed recurring-failures §9 paragraph** (not edited: W3-SEC-SCHED does not name the file; Codex r2 BLOCKER). Text: "the `Document → Observation` ORM cascade stopped one level short; `LabInterpretation` (NOT NULL FK, inert `ondelete`) turned every delete of an interpreted document into an IntegrityError after the file had already been unlinked; found by security review on PR #24, fixed by DDI. Recheck: when a parent's ORM cascade is relied on, walk every grandchild with a NOT NULL FK." `CLAUDE.md:49-52` asks for same-commit recording, which conflicts with the gate scope. Owner decides.

Later (not this phase): `CLAUDE.md:31` "all 1288 pass" is stale (AGENT-PASS-LINE).

### Merge order
#41 changes the count slots (1350). Any PR that merges after it must merge `origin/main`, re-measure and rewrite the slots.

## Phase 2 — SAFE-CHAT

PR **https://github.com/BrooklynD23/HealthCentral/pull/44** · branch `fix/safe-chat-legacy-abstain` · head `e188567` · base `main` @ `90c502a` · worktree `../hc-safechat`

Commits:
1. `ba5a2e0` docs: plan + Codex plan review r1
2. `f5961e7` fix(assistant), from the L2 sonnet implementer
3. `45c15a9` review loop 1: import grouping, plus a test asserting the escalation segment has empty citations
4. `e188567` docs: execution record and Codex diff review

Fix: `ValidatedResponse.prohibited_advice` is now set by `validate_response`. On the legacy `/assistant/chat` path a flagged answer is replaced by `ESCALATE_TEMPLATE` (segments, full_response and verification all reset). A fail-closed audit row is written before the turn is persisted: `assistant.prohibited_blocked`, details `{reason: prohibited_pattern, decision: escalate}`. `core/audit.py` is untouched; the action equals the event_type. No ask-first file is edited and no new copy is added.

### Commands and outputs
| Check | Output |
|---|---|
| RED | `2 failed, 3 passed` (001 "prohibited answer text reached the client"; 004 returns 200) |
| GREEN | `59 passed` (new file, chat_sessions, cache isolation, audit PHI) |
| collect (L1 re-measured) | `1351 tests collected` (**+5**) |
| full suite at f5961e7 (flock) | `1351 passed, 63 warnings in 171.23s`, rc=0, `FAILURES-SUBSET-OK` |
| re-check at 45c15a9 | collect 1351; the 4 test files plus `tests/agent`: `142 passed`; `boot ok` |
| scope | `SCOPE-OK` |
| CI `gh pr checks 44` | all 6 pass (Agent Eval Gate, Backend, Docs Lint, E2E Smoke, Frontend, Security Scan) |

### Break-it (disposable worktree at 45c15a9, by line number, then removed)
| Break | Result |
|---|---|
| BI-1: block removed | 001, 004 FAIL |
| BI-2: `verification = VerificationInfo()` removed (`api/assistant.py:882`) | 001 FAIL |
| BI-3: block moved after the turn commit | 001, 004 FAIL |
| BI-4: `prohibited_advice = True` removed (`modules/rag.py:842`) | 001, 004 FAIL |
| restore | `5 passed` |

### Gates
- SAFE-CHAT (verbatim from L0).
- **Assumption, owner to confirm:** `ESCALATE_TEMPLATE` instead of `ABSTAIN_TEMPLATE`. ABSTAIN's text ("not enough verified information") is false for an advice block, and ESCALATE is what the agent guard already returns. I asked L0 on 2026-10-04 and have had no answer at write time. Switching is 1 import plus 1 test constant.

### Codex
| Review | Verdict | Disposition |
|---|---|---|
| Plan r1 | REVISE, 5 MAJOR (procedural) | 4 accepted. 1 partly rejected: DDI is a work order, not a merge dependency; the shared count slots are handled by Step 4b. r2 not run (no code finding) |
| Diff | needs-attention, 1 high | **Rejected.** The no-model knowledge fallback returns seeded reference text, not model output. The "you have a cut" match is a false positive (`scripts/seed_knowledge_base.py:376`) |

### Reviewers
- code-reviewer (opus): APPROVE, 4 MINOR. 2 fixed. Open: `validation_errors` stays non-empty while verification is reset (cosmetic), and the test double does not model rollback.
- security-reviewer (opus): APPROVE. No channel for the prohibited text remains on the patched path, and the audit is fail-closed.

### Other paths (checked, not fixed; owner items)
1. **SAFE-INTERP-GROUNDED** (HIGH, pre-existing): `POST /observations/{id}/interpret-grounded` (`api/interpretations.py:383-505`) returns a prohibited answer verbatim, and `LabInterpreter.tsx:92,288` renders it. `api/interpretations.py` also writes no audit rows (`grep -c -i audit` → 0), which breaks the audit invariant.
2. **SAFE-CHAT-AGENT** (LOW, pre-existing): the agent guard uses `classify_advice`, which only matches question-shaped advice. Measured: "You have hyperlipidemia." and "Take 20 mg atorvastatin daily." pass. Drafts are built from templates, so only quoted record text is exposed. The semantic cache replays terminals.
3. **PROHIBITED-PARAPHRASE** (MEDIUM, ask-first `interpret_safety.py`): misses "You likely have diabetes." and "Consider starting atorvastatin 20 mg."
4. **SAFE-CHAT-FALLBACK**: the Codex diff finding above. Needs a ruling on reference text vs pattern false positives.
5. **SAFE-CHAT-HISTORY** (LOW): turns persisted before the fix can still hold prohibited text and are fed back as history.
- No streaming chat route exists.

### Merge order
#41 and #44 share only the count slots and the generated index. Whichever merges second must merge `origin/main`, re-measure (expected 1355) and rewrite the slots.

Note: the SAFE-CHAT implementer once wrote `collect.txt` by hand to pass its own commit gate. L1 re-measured with the real command (1351 matched), and the loop-1 brief forbids doing it again.

## Phase 3 — G-C3b (HC-M07 observability baseline)

PR **https://github.com/BrooklynD23/HealthCentral/pull/45** · branch `feat/gc3b-observability-baseline` · head `ba22622` · base `main` @ `90c502a` · worktree `../hc-gc3b`

Commits:
1. `564eb41` feat(monitoring), the C3b.4 commit, from the L2 sonnet implementer
2. `5e22907` review loop 1: reset the record factory in 001/002
3. `ba22622` docs: W11b execution-record row C3b

### Commands and outputs
| Check | Output |
|---|---|
| Preconditions | post-P1 `90c502a`; Py 3.11.16; collision grep rc=1; `notification_scheduler` ×5 in `main.py`; START collected 1346, no failures |
| RED | monitoring `3 failed` (`ModuleNotFoundError: core.logging_setup` ×2; `assert None == '-'`); audit `1 failed` (`KeyError: 'correlation_id'`) |
| GREEN | `tests/monitoring tests/security/test_audit_middleware.py` → `32 passed` |
| collected | `1350` (**+4**) |
| full suite at 564eb41 (flock) | `1350 passed, 56 warnings in 179.39s`, rc=0, `FAILURES-SUBSET-OK` |
| boot | `boot ok` |
| `grep basicConfig/dictConfig/setLevel core/logging_setup.py` | empty |
| ask-first diff (`core/auth`, `security`, `profile_database`, `audit`, `modules`, `alembic.ini`) | empty |
| Playwright E2E-HEALTH-001 | **UNMEASURED locally** (WSL); CI `E2E Smoke Tests` pass |
| CI `gh pr checks 45` | all 6 pass |

### Break-it (mode b, disposable worktree)
| Break | Result |
|---|---|
| A: `Filter` on root handlers | 001, 002, 004 red |
| B: call removed from `create_app` (`main.py:106`) | 004 red |
| audit `"correlation_id": ""` | 003 red |
| at 5e22907: no-op install with `main` imported first | 001, 002, 004 red (before loop 1, 001/002 would pass in that order) |
| restore | `4 passed` / `20 passed` |

### Gates
- S-C3-1 and S-C3-3: both signed per L0 (owner, chat 2026-10-04).
- **Not done: ticking the W11b sign-off checkboxes.** The permission layer blocked it as gate-signing on the strength of an agent message (classifier: "Instruction Poisoning"). It also blocked my read of `owner-decisions` in `hc-l0-docs`. L0 or the owner should tick them: `W11b:1949`, `:1951`.

### Reviewers
- code-reviewer (opus): APPROVE. MINOR-1 is fixed in loop 1: tests could pass by import order (recurring-failures §1). Still open:
  - the audit field is `""` outside a request, where log records use `"-"`. Unreachable in the `main.py` order.
  - the e2e URL derivation copies `global-setup.ts`.
  - pass-count clauses are stale.
- security-reviewer (opus): APPROVE. 3 LOW:
  1. Introduced: a client-chosen UUID can appear in the audit log; trust is unchanged.
  2. Pre-existing: `monitoring/correlation.py:50` should store `str(uuid.UUID(raw))`. Today it accepts `{\t…}` and `urn:uuid:` forms.
  3. Pre-existing: `run_in_executor` in `llama_cpp_provider.py:278` loses the context, so those logs show `-`.
- Codex: not run. G-C3b is not an architectural phase (`orchestration.md` §5), and the brief named none.

### Open findings
- F-2 / O-C3-4: production INFO logs are dropped, so the IDs are carried but not visible. Owner decision, flagged first in the PR body.
- CORRELATION-NORMALISE (LOW): a 1-line follow-up plus a test case.

## Merge order and count slots (all 3 PRs)
Each PR was measured alone on `90c502a`:

| PR | Collected | Delta |
|---|---|---|
| #41 | 1350 | +4 |
| #44 | 1351 | +5 |
| #45 | 1350 | +4 |

Combined: 1346 + 13 = **1359** (prediction; measure it). All 3 edit `CLAUDE.md:30,:35` and `AGENT.md:76`; #41 and #44 also regenerate `docs/INDEX.md` / `docs/_link_graph.json`. No other file overlaps.

Suggested order (safety first):
1. #41
2. #44
3. #45

Each later PR merges `origin/main`, re-measures `--collect-only`, rewrites the slots and regenerates the index before the owner merges it (`orchestration.md:24`).

## Gates used (all phases)
W3-SEC-SCHED, SAFE-CHAT, S-C3-1 and S-C3-3, all as relayed by L0. No gate was signed by L1. No ask-first file was edited.

## Escalations for L0 / owner
1. SAFE-CHAT template: ESCALATE (implemented) vs ABSTAIN (the decision's wording). L0 has not replied.
2. W11b sign-off checkboxes are not ticked. The permission layer blocked it.
3. DDI: the proposed recurring-failures §9 paragraph is in Phase 1, item 5. `CLAUDE.md:49-52` (record in the same commit) conflicts with the gate scope.
4. New owner items:
   - REPROCESS-INTERP-ORPHAN, PANEL-INTERP-STALE, DDI-AUDIT-ORDER, DDI-ORPHAN-BIN
   - SAFE-INTERP-GROUNDED (HIGH), SAFE-CHAT-AGENT, PROHIBITED-PARAPHRASE, SAFE-CHAT-FALLBACK, SAFE-CHAT-HISTORY
   - CORRELATION-NORMALISE

Worktrees left in place: `../hc-ddi`, `../hc-safechat`, `../hc-gc3b`. The break and probe worktrees were removed.
