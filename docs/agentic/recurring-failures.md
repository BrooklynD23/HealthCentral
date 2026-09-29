# Recurring Failure Modes

Mistakes this codebase has actually produced, with the evidence that exposed
each one. Not hypothetical risks — every entry below shipped, or nearly shipped,
and was caught late.

Read this before claiming work is done. Each entry ends with a **recheck**: the
specific thing to go look at, phrased so you can answer it with a command rather
than an opinion. If you catch a new instance of one of these, add the evidence
to that entry. If you find a failure mode that is not here, add it.

The common thread across all of them: **the check that was run was not the check
that mattered.** Every one of these coexisted with a passing signal.

---

## 1. A green suite that could not have failed

The most expensive pattern in this repo's history, twice over.

- A restore endpoint returned **400 for every request** — its `Depends(require_profile_access())`
  read `path_params["profile_id"]`, and that route only has `backup_id`. All 32
  backup tests passed, because they called the handler as a plain function and
  FastAPI's dependency graph never ran.
- A backup download shipped **every other profile's `display_name`, bcrypt hash,
  salt, and the whole audit trail**. The isolation test asserted on *filenames*,
  so it could not see data leaking inside a file.
- A frontend test used `waitFor(() => expect(...).not.toBeInTheDocument())`,
  which resolves on the first tick before the component has rendered anything.
  It passed against deliberately broken code.

A 2026-09-09 instance in the one place it hurts most — the security gate itself.
`scripts/security_gate.py:44-51` and `:71-78` catch `FileNotFoundError,
json.JSONDecodeError` on the bandit and pip-audit reports, print a WARNING, and
`return []`. The gate reads an empty list as *zero findings*, not as *the scan
did not happen*. `.github/workflows/ci.yml:92,95` compound it by running both
scanners with `|| true`, so a scanner that crashes leaves no exit code and no
usable report. Every step is green and nothing was scanned. A gate that cannot
distinguish "clean" from "did not run" is not a gate.

A 2026-09-29 instance in the agent answer cache (S-CACHE). `modules/agent/cache.py`
keyed `CacheKey` on `(normalized_question, profile_version)` — no profile id — and
`_cache` was a module-level dict shared by every profile in the process. The
existing tests in `tests/test_hc_a1_agent_verification.py` seeded the cache
directly with `_seed_cache(question, terminal)`, without a profile id, under
the fixed fingerprint a fresh empty profile computes (`"o:0:|d:0:"`); a request
from any other profile with the same empty fingerprint then hit that seeded
entry. The leak — a shared cache entry serving across profiles — *was the
tested behaviour*, so the suite stayed green while any two empty (or otherwise
evidence-identical) profiles could receive each other's cached answers.
`tests/test_agent_cache_isolation.py::test_hc_cache_iso_001_two_profiles_never_share_cached_answer`
drives two real profiles through `route_client` with a call-counting stub and
caught it: profile B's response carried profile A's cached text and the stub
ran only once instead of twice.

**Recheck:** ask what your test would *fail to notice*. Then break the code on
purpose and confirm the test goes red. For any gate that parses a report another
step produced, delete the report and confirm the gate goes RED, not green —
absent evidence must never read as absence of findings. A test that has never failed proves
nothing. Route tests asserting auth, path scoping, or status codes go through
HTTP — use `src/backend/tests/support/routes.py::route_client`. When a test seeds
shared state (a cache, a module-level dict) by hand, check whether the seed
itself omits the exact dimension (tenant/profile id) the test is meant to prove
is isolated — a hand-seeded test can pass by construction instead of by
correctness.

---

## 2. The fix that creates the next bug one layer over

Every individually-correct fix in the backup subsystem propagated a new false
statement or data-loss path somewhere adjacent:

- Scoping the backup at *create* time fixed the credential leak — and introduced
  a whole-install restore that **deleted every other profile**.
- Making restore report partial progress fixed one false "Nothing was changed" —
  a second pass found **three** more false statements across other return paths.
- The refusal added to block the data-loss path told users to re-run with
  `--profile-id`, which `main()` never forwarded. The remediation instruction
  was a dead end.

**Recheck:** after fixing anything in a multi-step flow, re-walk the *whole*
round trip — create → verify → download → restore → prune — not just the diff.
Ask what every other caller of the thing you changed now believes.

---

## 3. Figures asserted instead of measured

- `CLAUDE.md` and `AGENT.md` both claimed **"~620 backend tests"** for months.
  The real figure was roughly double.
- A cautionary note claimed **"1244 passing tests coexisted with"** two backup
  bugs. Collection at those commits was 1207 and 1208. The number came from
  HEAD, and the anecdote was about the past.
- An orchestrator instructed a subagent to use `~/venvs/healthcentral-backend/bin/python`.
  That venv does not exist. A less careful agent would have reported a failed
  run as a test result.

**Recheck:** any number in a doc, brief, or commit message is a claim and needs
the command that produced it. Overriding a plan's figure with a "correction" is
itself a claim — it does not get a pass because it came from the orchestrator.

---

## 4. Environment-dependent results written as absolutes

- `test_api_rag_index_002b` needs a real embedding model: **1245 pass in CI,
  1244 pass and 1 fails locally**, same commit. A baseline stating only one of
  those reads as a regression in the other environment — and a staleness rule
  keyed to it once instructed agents to delete the "do not lower the 0.7
  threshold" guard.
- Playwright only runs here with `HC_E2E_CHROMIUM_PATH=/opt/pw-browsers/chromium`.
  Without it, `npx playwright test` fails on a missing binary and executes zero
  tests. Two reports appeared to contradict each other until that surfaced.

**Recheck:** before writing a figure, ask which environment produced it and
whether another environment produces a different one. Prefer numbers that do not
vary — collected counts over pass counts.

---

## 5. Gates run in a contaminated tree

`generate_docs_index.py --check` reported **fresh** in the working tree while CI
reported **stale** on the same commit. A concurrent subagent held ~37 files
modified, so the working tree was not HEAD.

**Recheck:** when anything else is editing the tree, verify commit-level gates in
a throwaway `git worktree` detached at HEAD, not in place. Related: parallel
agents running `git add` sweep each other's staged work — commit with explicit
pathspecs (`git commit -m … -- <paths>`), and never `git reset` to clean up.

---

## 6. Documented commands nobody ran

`AGENT.md` listed `python scripts/download_models.py # GGUF / ollama pull
(Gemma 4 tiers)`. That script contains **zero** references to ollama and cannot
download any Gemma 4 tier. The correct script is
`src/backend/scripts/download_models.py`. The line predates the branch that
found it, so every "did my change break anything?" review passed over it.

A related class: a command that inherits the wrong working directory from the
bullet above it. The definition of done once listed `python -c "from main import app"`
directly after a `cd src/frontend` line.

**Recheck:** run every command a doc quotes, exactly as written, from the
directory the surrounding text implies. Inherited-from-`main` is not a reason to
skip it — it is a reason it survived this long.

---

## 7. SQL three-valued logic

Scoping a backup with `WHERE profile_id != ?` silently kept every row where
`profile_id` was `NULL`, because `NULL != 'x'` evaluates to `NULL`, not `TRUE`.
The audit trail leaked through a filter that looked correct.

**Recheck:** any `!=` or `NOT IN` on a nullable column needs an explicit
`IS NULL OR …`. Test with a NULL row present, not just the happy path.

---

## 8. Stale guidance that reads as authority

The 2026-07-07 rename audit recorded "keep DB filenames — renaming breaks
existing vaults." That rationale was inaccurate: vault filenames are per-profile
and never carried the product name. The decision stood unchallenged for weeks
because it was written down.

A security review likewise cited a `data-privacy.md` line to justify leaving
backups on disk after profile deletion. That line was written about a different,
older backup location. The same review asserted an FK cascade removed a row;
`PRAGMA foreign_keys` is set nowhere in the codebase, so it is inert on SQLite.

A 2026-09-08 near-miss in the same shape, caught at implementation: a research
track recommended routing `api/memory.py`'s `value` through
`sanitize_untrusted_field` before persisting, to neutralize prompt injection.
The *risk* was real; the *layer* was wrong twice over. `modules/rag.py::_retrieve_memory_context`
already filters injection-bearing memory items at compose time — and it fails
closed on the whole item, which is safer than scrubbing a string. Worse,
`sanitize_untrusted_field` applies **strict PHI redaction**, so writing through
it would have silently and irreversibly corrupted memory items a patient
deliberately saved into their own encrypted vault. The invariant is "redaction
before anything *leaves*"; a write into the per-profile vault is PHI arriving,
not leaving. Two of the eight tracks had flagged the memory route, which made
the recommendation look corroborated — convergence is evidence the *area*
matters, not that the *proposed fix* is right.

**Recheck:** a written decision is evidence about what someone believed, not
proof that it was true. When a doc gives a *reason*, check the reason. An
agent's report — including a reviewer's — is a lead, not a finding. Before
applying a defensive transform, check whether the defense already exists
somewhere better, and ask what the transform destroys when it fires.
