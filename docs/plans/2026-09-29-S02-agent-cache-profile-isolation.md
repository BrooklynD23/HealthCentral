# S-CACHE — Agent Answer Cache Profile Isolation + Memory-Audit Category Drop

**Status:** owner-approved 2026-09-29 (gates S-CACHE, MEM-AUDIT-CAT in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). Wave 1, after P1 PR #1.
**Source:** Codex plan review of plan 01, round 1 ([`docs/reviews/2026-09-29/P01-r1-codex.txt`](../reviews/2026-09-29/P01-r1-codex.txt), BLOCKER 1 and 2), verified by L0 against the code ([`P01-r1-response.md`](../reviews/2026-09-29/P01-r1-response.md)).
**Architectural:** yes (per-profile isolation, PHI in the master DB). Codex diff review + `security-reviewer` required.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Every new test is observed FAILING before the fix.

## Goal

1. The agent answer cache can never serve one profile's answer to another profile.
2. The user-typed memory `category` never reaches an audit row in the unencrypted master DB.

## Owner approvals (verbatim; nothing wider is licensed)

- **S-CACHE:** "Own PR in Wave 1, opened after PR #1 merges (B rewrites cache.py): add profile_id to CacheKey and pass it at the call site; add a two-profile regression test through route_client that fails before the fix. security-reviewer + Codex diff review."
- **MEM-AUDIT-CAT:** "In S-CACHE's PR: remove `category` from the memory audit details (keep value_length); add a test that a PHI-like category ('HIV') never reaches the audit row. api/memory.py only; core/audit.py untouched."
- **SLOT-RULE** (2026-09-28) applies: the commit that changes the collected count updates the `CLAUDE.md` / `AGENT.md` collected slots.

## Defects (measured at branch B `7b2ff1f`, which PR #1 lands on main)

| # | Where | Defect |
|---|---|---|
| 1 | `src/backend/modules/agent/cache.py:31-35` | `CacheKey` = `(normalized_question, profile_version)`; no profile ID. `_cache` is a module-level dict shared by every profile in the process. |
| 1 | `src/backend/api/assistant.py:553-596, 693-700` | `profile_version` is `o:<count>:<max verified_at>|d:<count>:<max verified_at>`. Any two profiles with the same fingerprint (for example two empty profiles, `o:0:|d:0:`) share cache entries for the same question. On main before PR #1 the version is only the verified-observation count (`assistant.py:552-563 @36b2ff2`), so the collision is easier. The agent path is on by default (`assistant.py:726-731`). |
| 1 | `src/backend/tests/test_hc_a1_agent_verification.py:73-79` | The existing tests rely on the leak: they seed the cache without a profile ID, and a request from a fresh random profile hits that entry. |
| 2 | `src/backend/api/memory.py:135` (create), `:165` (list) | `details={"category": ...}` carries the user-typed category (`MemoryItemCreate.category`, free text ≤100 chars, `:55`) or the `?category=` query value. `"category"` is allowlisted in `core/audit.py:73` and a compact value such as `HIV` passes `_ENUM_VALUE_RE`, so it lands in the master DB. |

## Files (the complete list)

| File | Change |
|---|---|
| `src/backend/modules/agent/cache.py` | Add `profile_id: str` to `CacheKey` (required field, no default); update the module docstring and `get_cached` docstring to say the key is profile-scoped. |
| `src/backend/api/assistant.py` | Pass `profile_id=profile_id` in the `CacheKey(...)` call inside `_serve_via_agent` (`:694`). Nothing else. |
| `src/backend/api/memory.py` | Remove the `"category"` entry from the `details` dicts at `:135` and `:165`. Keep passing `value_length` and `count` (owner text). Note: `value_length` is not in `ALLOWED_DETAIL_KEYS`, so `_scrub_details` already drops it (L1 measured, 2026-09-29); do not add it to the allowlist. Do not change the request/response models or the update route's field-name list (`:251`, names only). |
| `src/backend/tests/test_agent_cache_isolation.py` (new) | HC-CACHE-ISO-001 (HTTP), HC-CACHE-ISO-002 (unit). |
| `src/backend/tests/test_memory_audit.py` | HC-MEM-AUDIT-007 (create), HC-MEM-AUDIT-008 (list). |
| `src/backend/tests/agent/test_s5_cutover_cache.py` | Add `profile_id=` to every `CacheKey(...)`; the missing-field test (`:16`) also asserts `profile_id` is required. |
| `src/backend/tests/test_hc_a1_agent_verification.py` | `_seed_cache` takes the request's `profile_id` and seeds under it. |
| `CLAUDE.md`, `AGENT.md` | Collected slots → measured count (SLOT-RULE), in the commit that adds the tests. |
| `docs/agentic/recurring-failures.md` | Record the new instance (a shared cache keyed without the tenant; the tests seeded the leak and so could not see it) with its recheck, in the same PR. |

`core/audit.py`, `modules/redaction.py`, and every other ask-first file stay untouched. If a step seems to need one, STOP.

## Tasks

### Task 0 — Preconditions (STOP on any failure)

Start directory: the canonical repo root. Every later block names its own start directory; `W=/mnt/c/Users/DangT/Documents/GitHub/hc-s-cache` below.

```bash
set -o pipefail
git fetch origin
git ls-files docs/plans/2026-09-29-S02-agent-cache-profile-isolation.md   # non-empty
git merge-base --is-ancestor origin/claude/healthcentral-agentic-research-r1n54x origin/main && echo "B on main"
git worktree add ../hc-s-cache -b fix/s-cache-profile-isolation origin/main
W=/mnt/c/Users/DangT/Documents/GitHub/hc-s-cache
cd "$W/src/backend"
export HF_HUB_OFFLINE=1
find . -name __pycache__ -type d -exec rm -rf {} +
~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > /tmp/s-cache-start-collect.out; echo "rc=$?"; tail -1 /tmp/s-cache-start-collect.out   # START collected
~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rf > /tmp/s-cache-start-run.out; echo "rc=$?"; tail -3 /tmp/s-cache-start-run.out; grep '^FAILED' /tmp/s-cache-start-run.out   # START failure set
```

Record with the output: interpreter (`~/venvs/asclexis-311/bin/python --version` → 3.11.16), OS (WSL2 Linux), the commands above, START collected, START pass line, and the START `FAILED` list (expected empty).

If B is not yet on main, the phase may be *prepared* on a branch cut from the PR #1 merge branch, but it must be rebased onto `origin/main` after PR #1 merges, and Task 0 re-run, before the PR opens.

### Task 1 — HC-CACHE-ISO-001: two profiles, one question, over HTTP (RED first)

`tests/test_agent_cache_isolation.py`, following the `route_client` + `get_profile_db_session` override pattern in `test_hc_a1_agent_verification.py:43-66`:

- Two profiles `A` and `B`, each with its own empty in-memory profile DB (same fingerprint `o:0:|d:0:`).
- Monkeypatch `api.assistant.run_agent` (the graph entry point `_serve_via_agent` awaits on a cache miss, `assistant.py:714 @B`) with a stub that counts its calls and returns an `answer` terminal whose text names the requesting profile (for example `"answer-for-<profile_id>"`). Use `clear_cache()` before and after.
- POST `/assistant/chat` `{"question": "what is my latest ldl?"}` as A, then the same as B.
- Assert: both 200; B's response text contains B's marker and does **not** contain A's; the stub ran **twice**.

Run it before the fix and paste the FAIL (expected: B receives A's text and the stub ran once).

### Task 2 — HC-CACHE-ISO-002: the key itself is profile-scoped (RED first)

Unit test: `CacheKey(normalized_question="q", profile_version="v", profile_id="a") != CacheKey(..., profile_id="b")`, and `put_cached` under `a` then `get_cached` under `b` returns `None`. Before the fix, pydantic's default `extra="ignore"` silently drops the unknown `profile_id` (B's `CacheKey` sets only `frozen=True`, `cache.py:31-36 @B`), so both keys compare equal and the `!=` / `get_cached(...) is None` assertions FAIL (an `AssertionError`, not a `ValidationError`); paste that failure.

### Task 3 — Fix the cache (GREEN)

Edit `cache.py` and `assistant.py` as in the file table. Update `test_s5_cutover_cache.py` and `test_hc_a1_agent_verification.py` to pass `profile_id`. Run from `$W/src/backend` with `HF_HUB_OFFLINE=1`:

```bash
set -o pipefail
~/venvs/asclexis-311/bin/python -m pytest tests/test_agent_cache_isolation.py tests/agent/test_s5_cutover_cache.py tests/test_hc_a1_agent_verification.py -p no:cacheprovider -q
```

All pass. Break it on purpose: remove `profile_id` from the `CacheKey(...)` call in `assistant.py`, confirm HC-CACHE-ISO-001 fails, restore.

### Task 4 — HC-MEM-AUDIT-007/008: PHI-like category never reaches audit (RED first)

In `test_memory_audit.py`, using the file's existing HTTP pattern (`route_client`) and its capturing master-DB double (`:32-49`, which collects the `AuditLog` rows handed to the master session):

- 007: create a memory item with `category="HIV"`; the resulting `AuditLog` row's `details` has no `category` key and the string `HIV` appears nowhere in the serialized row.
- 008: `GET` the list with `?category=HIV`; same assertion on the list audit row.

Paste the FAIL, remove `"category"` from the two `details` dicts in `api/memory.py`, paste the PASS. The existing HC-MEM-AUDIT-001..006 must stay green.

### Task 5 — Slots, recurring failures, commit

Commits, in this order, each measured before it is made (from `$W/src/backend`: `set -o pipefail; ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1`, checking rc=0):

1. `fix(agent): scope answer-cache key by profile` — `cache.py`, `assistant.py`, the two updated test files, the new `test_agent_cache_isolation.py`, and the `CLAUDE.md` + `AGENT.md` collected slots set to the measured START + 2.
2. `fix(memory): keep user-typed category out of memory audit details` — `api/memory.py`, `test_memory_audit.py`, and both slots set to the measured START + 4 (= END). Any other delta at either step: STOP.
3. `docs: record shared-cache-without-tenant in recurring failures` — `docs/agentic/recurring-failures.md` only.

Slots: numbers only; leave the pass sentences. Explicit pathspecs.

**Ordering with P1 PR #2:** merge order is PR #1 → S-CACHE → PR #2 (plan 01 banner item 6h). Both edit the collected slots. If `origin/main` moves before this PR merges, rebase onto it, re-run Task 0's collect and Task 6, and rewrite the slots to the new measured numbers.

### Task 6 — Verification (L1 runs it and pastes output)

```bash
set -o pipefail
W=/mnt/c/Users/DangT/Documents/GitHub/hc-s-cache
cd "$W/src/backend" && export HF_HUB_OFFLINE=1
find . -name __pycache__ -type d -exec rm -rf {} +
~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rf > /tmp/s-cache-end-run.out; echo "rc=$?"; tail -3 /tmp/s-cache-end-run.out; grep '^FAILED' /tmp/s-cache-end-run.out   # collected = END; FAILED set ⊆ START FAILED set
~/venvs/asclexis-311/bin/python -c "from main import app"; echo "boot rc=$?"
cd "$W" && git status --short                                                           # only this phase's files
find "$W" -name "*.db" -newer "$W/CLAUDE.md" -not -path "*/node_modules/*"              # expect no output
cd "$W" && python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check && python3 scripts/harness_drift_check.py; echo "docs rc=$?"
```

Then `security-reviewer` + `code-reviewer`, and the Codex diff review:
`node ~/.claude/plugins/cache/openai-codex/codex/1.0.4/scripts/codex-companion.mjs adversarial-review --wait --base origin/main "per-profile isolation of the agent answer cache; no user-typed text in master-DB audit details"`.

## Stop gates

- Any file outside the table, or any ask-first file.
- A new test that passes before the fix.
- A collected delta other than +4.
- Any change to `_scrub_details`, `ALLOWED_DETAIL_KEYS` or `STRING_DETAIL_KEYS` (MEM-AUDIT-CAT says `core/audit.py` untouched).

## Rollback

One PR; `git revert <merge sha>` restores the prior behaviour. The cache is in-process only, so there is no persisted state to migrate.

## Out of scope (owner items)

- Memory `category` values already written to master-DB audit rows by B's code between PR #1 and this PR: none on a fresh install; a dev DB that ran B's code may hold some. Report, do not purge.
- Evicting per-profile cache entries on profile delete or logout (the key now isolates; eviction is a separate retention question).
- Cache staleness from sources outside the fingerprint: 3 agent tools read unverified data (care tasks, timeline, medication changes) that `_profile_version` does not cover (security-reviewer on PR #21, 2026-09-29). Owner item CACHE-STALE; the profile key does not change it.
