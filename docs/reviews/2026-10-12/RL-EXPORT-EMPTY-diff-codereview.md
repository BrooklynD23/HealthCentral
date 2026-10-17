# RL-EXPORT-EMPTY diff code review (2026-10-12)

Reviewer: code-reviewer subagent (Opus 5.5), read-only, on commit `b80d032` (branch `fix/rl-export-prompt-snapshot`, PR #82). Pytest was not run by the reviewer; test evidence came from the author.

## Files reviewed
| File | Change |
|---|---|
| `src/backend/api/feedback.py` | new `_preceding_user_prompt` (lines 179-205); upsert uses the derived snapshot (lines 234-262) |
| `src/backend/tests/test_rl_export_prompt_snapshot.py` | new, 2 tests over HTTP (`route_client`), both read the exported JSONL |
| `CLAUDE.md`, `AGENT.md` | test count raised from 1466 to 1468, which matches the parent's 1468 collected |

## Must fix now

**[HIGH] The NULL-row backfill branch has no test, and a mutation in it survives (recurring-failures #1)**
- Location: `src/backend/api/feedback.py:236`, the clause `(existing is None or existing.prompt_snapshot is None)`.
- Cause: both new tests only create new rows. `test_rl_feedback.py::test_updates_existing_feedback` builds `existing` with `_make_fb`, whose default is `prompt_snapshot="What is glucose?"`. That test never reaches the derivation. If line 236 is changed to `if prompt_snapshot is None and existing is None:`, every test still passes, and old rows with NULL prompts stay out of the export forever.
- Fix: add `test_hc_rlexp_003`. Seed a user/assistant pair. Insert a `ResponseFeedback` row for the assistant turn with `prompt_snapshot=None`. Re-rate it through `_rate_and_export`. Assert `grpo_rewards_count == 1` and that the prompt matches the user turn.

## Later (warnings)

**[MEDIUM] Duplicate `turn_index` returns a 500 on feedback POST**
- Location: `feedback.py:197-204`, user-turn lookup with `scalar_one_or_none()`.
- Cause: `api/assistant.py:288-291` sets `turn_index` from `count(*)`. There is no unique constraint on `(session_id, turn_index)` (`migrations/profile/versions/007_chat_sessions.py:43`). Two concurrent asks in one session can write duplicate indexes. The lookup then raises `MultipleResultsFound`, and rating that answer, which used to work, now fails.
- Fix: keep returning None when there is more than one match (conservative: no snapshot, row skipped on export). For example, run `.scalars().all()` and return `rows[0].content if len(rows) == 1 else None`.

**[LOW] Two surviving mutants in the assistant-turn lookup**
- Location: `feedback.py:190-195`.
- Removing `ChatTurn.role == "assistant"`: no test rates a user turn, so the mutant survives. With that filter gone, rating user turn N would store user turn N-1 as its prompt.
- Removing the assistant-side `ChatTurn.profile_id == profile_id`: the test-002 decoy only puts the foreign profile on the user turn.
- Impact is low because each profile has its own SQLCipher DB. Fix: in test 002, add rating a user-turn id as one orphan case, and add a case where the assistant turn belongs to `OTHER_PROFILE`.

**[LOW] A client-supplied `prompt_snapshot` still beats the server-derived one**
- Location: `feedback.py:234`. This is pre-existing behaviour and fits the spec ("skipped when body supplies"). The server-derived prompt is the more trustworthy of the two. Consider deriving first and using the body value only as a fallback. Not required for this PR.

## Questions checked
| Check | Result |
|---|---|
| Correctness | OK. Rated turn matched by id, profile and role=assistant; prompt from the user turn at the same session, same profile, `turn_index-1`, role=user. Matches `_append_turns` (`assistant.py:299,309`). |
| Cross-profile isolation | OK. Profile filter on both queries; profile DB via `ProfileDbSession`; master `get_db()` not used. |
| Cross-session isolation | OK. Session comes from the stored assistant turn, not `body.session_id`. |
| `turn_id` is a user turn | Handled (None, row skipped on export). Untested (see LOW). |
| Client-generated `turnId` fallback (`ExplainAssistant.tsx:397`) | Handled: no matching ChatTurn, row skipped. Rare: both answer paths persist turns (`assistant.py:902,942`). |
| Re-rating old rows with NULL prompt | Implemented, **untested** (see HIGH). |
| `test_updates_existing_feedback` sidestepped? | No. Unmodified; its fixture has a snapshot, so it tests the "keep existing snapshot" branch honestly. |
| Redaction | Unchanged and enforced at export (`modules/rl_dataset.py`, strict). Test 001 checks the real file. `modules/redaction.py` untouched. |
| Audit logging | `_emit_audit("feedback.submit")` still called after commit. |
| Python 3.11 | No newer syntax. |
| Local-first / ModelRunner | No network or LLM calls added. |
| Safety-gated files | Not touched. |
| Test quality | Good: HTTP, reads the exported file, decoys in separate sessions. In-memory sqlite, acceptable for this logic. |

VERDICT: needs-attention
