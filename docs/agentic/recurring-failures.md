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
- 2026-09-08, `SEC-RECOV-002`: a unit test mocked `has_recovery_code` onto the
  response of `GET /profiles/{id}`. The backend returns that field on
  `ProfileListResponse` (the list route, `GET /profiles`) and **never** on `ProfileResponse`
  (`api/profiles.py:132-152`). Six green tests therefore certified a component
  that could never reach its "replace" state, because the flag it branched on
  was always undefined in production. The mock was not a simplification of the
  API — it was a different API. Caught only by an e2e run against the real
  backend, which rendered the wrong half of the component.

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

A 2026-10-08 instance in a launcher (DEV-PS1-INSTALL, PR #55). The first
version of the branch called `& npm ci` in `dev.ps1` STEP 5, and ten green
cases of `scripts/check_dev_ps1_install.ps1` passed, because the check puts a
stub `npm.cmd` first on PATH. The real call was broken: under Windows
PowerShell 5.1 with npm 11.6.2, `npm` resolves to the `npm.ps1` shim, which
cuts `InvocationName.Length` characters off the statement; through `&` that
is one character, so npm receives `pm ci` and exits 1 (`Unknown command:
"pm"`). `main`'s own `& npm install` (`dev.ps1:635` before #55) had the same
bug, so a first-time launch could not install. The first real `npm` run found
it; the merged fix calls the npm application found by
`Get-Command npm -CommandType Application` (`dev.ps1:646-650`), not the shim
(`wave-4-L1-B.md`, "Finding on `main`"). The stub replaced exactly the layer
that failed.

Two 2026-10-09 instances in the React Router 7 tests (PR #57). The plan's
empty-page check for lazy navigation recorded "any moment with no element
children and no text" in `<main>`. `AppLayout` keeps a keyed `PageTransition`
element inside `<main>` (`src/frontend/src/components/layout/AppLayout.tsx:18-25`), so `<main>`
always has an element child and that check could not fail. The spec as
written (`src/frontend/e2e/routing.spec.ts`, E2E-ROUTE-002) tests text content instead, and
the break-it (`lazyRoute` fallback → `null`) turned it red at `:59`; the plan
text was corrected in `512218b`. Separately, the "no Future Flag warning" half
of HC-ROUTE-001 could not fail once v7 was installed, because v7 prints no
such warning; code review caught it and it was removed in `e754b5d`
(`wave-4-L1-D.md`). An assertion that stays true after an upgrade checks
nothing after that upgrade.

A 2026-10-11 instance in the medication routes. The create route (POST /medications/)
committed the row and its audit entry, then returned 500: `MedicationResponse.from_model`
reads `med.schedules`, a default lazy-load relationship, and an async session
cannot lazy-load (`sqlalchemy.exc.MissingGreenlet`). The update, list and get
routes failed the same way. No medication test went through HTTP
with a real session. `tests/test_medications_dose_logging.py` uses a
`_FakeProfileDb` whose `refresh` is a no-op, so the fake replaced exactly the
layer that failed. It was found by the E2E seeding step of PR #74 (CI run
38197253929). `tests/test_medications_routes_http.py` drives all four routes
through `route_client` with an in-memory aiosqlite session, and all four went
red with MissingGreenlet before the fix.

A 2026-10-12 instance in agent chat (AUDIT-ORDER row 28). The agent's audit
rows were only `add`-ed; they reached the master DB through `get_db`'s
commit-on-exit, which FastAPI runs *after* the response is sent. No test could
see that: `route_client`'s `get_db` override returns the session directly, so
the exit commit never runs under test, and a failed exit commit could never turn
into a 500. `tests/test_audit_order.py` HC-AUD-ORD-060 went red on both cases
(200 instead of 5xx; `assert 0 == 1` rows) until `chat` committed explicitly.

**Recheck:** ask what your test would *fail to notice*. Then break the code on
purpose and confirm the test goes red. For any gate that parses a report another
step produced, delete the report and confirm the gate goes RED, not green —
absent evidence must never read as absence of findings. A test that has never failed proves
nothing. Route tests asserting auth, path scoping, or status codes go through
HTTP — use `src/backend/tests/support/routes.py::route_client`. When a test seeds
shared state (a cache, a module-level dict) by hand, check whether the seed
itself omits the exact dimension (tenant/profile id) the test is meant to prove
is isolated — a hand-seeded test can pass by construction instead of by
correctness. And for any hand-written mock of a backend response, open the
response model and confirm the field is on *that* endpoint: a mock is an
assertion about the API, and an unchecked one turns the suite green against a
contract that does not exist. When a check stubs an external tool (`npm`,
`git`, a scanner), run the real call at least once and paste its output; for
a DOM-shape assertion, confirm against the real layout that the shape it
looks for can occur at all.

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

Caught in advance once, 2026-09-08, which is the only reason it is not a fourth
bullet above. `CARE-QUOTE-001`'s own written plan said to clear
`care_plan_task.source_quote` on document delete **and to mirror that into the
reprocess path**. Mirroring it would have broken duplicate detection:
`get_care_task_candidates` keys "already accepted" on
`(source_document_id, source_quote)` (`api/care_tasks.py:182-199`), so a cleared
quote resurfaces every accepted task as a fresh candidate on each reprocess. The
plan was written from the delete path alone; the reprocess path had a second,
unrelated reason to need that column. Reading the consumer before editing the
producer is what caught it.

**Recheck:** after fixing anything in a multi-step flow, re-walk the *whole*
round trip — create → verify → download → restore → prune — not just the diff.
Ask what every other caller of the thing you changed now believes. Before
clearing or nulling a column, grep for every reader of it — a column that looks
like dead provenance to one path is often a key to another.

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
- The collected count varies too. `tests/test_embedding_no_network.py` calls
  `pytest.importorskip("sentence_transformers")` at module level, so its 2
  tests are collected only where that package is installed. Measured
  2026-10-20 on `b2b3f4e`, same box, same command: 2026 collected, then 2028
  after another session installed `sentence-transformers` into the shared venv.

**Recheck:** before writing a figure, ask which environment produced it and
whether another environment produces a different one. Prefer numbers that do not
vary — collected counts over pass counts — and when quoting a collected count,
say whether `sentence-transformers` was installed.

---

## 5. Gates run in a contaminated tree

`generate_docs_index.py --check` reported **fresh** in the working tree while CI
reported **stale** on the same commit. A concurrent subagent held ~37 files
modified, so the working tree was not HEAD.

A second instance, 2026-09-08, with a different cause: a docs-only commit added
two plan docs, ran `python3 scripts/docs_lint.py` — the command `CLAUDE.md` and
`AGENT.md` both name — and got "Docs lint passed." The commit shipped stale
`docs/INDEX.md` and `docs/_link_graph.json` anyway, and
`tests/test_docs_lint.py::test_docs_index_check_passes_on_real_repo` failed on the
next full run. `docs_lint.py` does not check whether the generated index is
current; only the pytest suite does. The documented command and the actual gate
were two different things, and the passing one was the one that got run.

**Recheck:** when anything else is editing the tree, verify commit-level gates in
a throwaway `git worktree` detached at HEAD, not in place. Related: parallel
agents running `git add` sweep each other's staged work — commit with explicit
pathspecs (`git commit -m … -- <paths>`), and never `git reset` to clean up.
And for **any** docs change, `scripts/docs_lint.py` passing is not sufficient —
run `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py
--link-graph`, or run the backend suite, which is the only place the freshness of
those two generated files is actually asserted. A docs-only diff is not a reason
to skip the suite; it is the case where the relevant check is least obvious.

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

Plans are docs too. LLM-PATH-LOG's plan (2026-10-19) told the implementer to
re-run `test_llm_import_boundary.py` from `tests/`; that file exists only as a "to
create" entry in the W07 plan, so the acceptance command failed (#208). And the
pytest slot script every runbook command calls directly, `scripts/pyslot.sh`,
was mode `100644` in git: on a checkout with `core.fileMode=true` the documented
call exited 126, `Permission denied` (measured 2026-10-20; fixed by #220).

**Recheck:** run every command a doc quotes, exactly as written, from the
directory the surrounding text implies. A planner checks every path it cites
with `git ls-files <path>` on the base it plans from. Inherited-from-`main` is not a reason to
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

A third instance, 2026-09-08: the `INGEST-FHIR-001` tracker row opened with
"zero structured ingest exists today; everything goes PDF/image → OCR → regex."
HC-M23 shipped `modules/import_structured.py` — FHIR R4 Bundle and lab CSV
parsing — on 2026-07-30. The row's premise had been false for weeks, and an
audit built on it re-reported the ticket at full scope. A row is written once
and read many times; nothing re-checks its opening clause when adjacent work
lands.

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

A fifth instance, 2026-10-20: the RRSI research said the Trends page uses
"latest-vs-prior with a 5% band" and cited `modules/analytics.py:96-112`. That
module has no caller; the Trends page shows `GET /observations/trends/{analyte}`,
which compares the **first and last** result (`api/observations.py:660-671`).
The owner answered RRSI-OQ-21 on that premise ("Adopt the Trends page's
latest-vs-prior comparison"), so the answer names two different rules, and the
CHAT-TREND-DEF plan had to ask again (gate CTD-DEF). A cited line proves the
code exists, not that the feature runs it.

**Recheck:** a written decision is evidence about what someone believed, not
proof that it was true. When a doc gives a *reason*, check the reason. When a
ticket asserts an *absence* ("no X exists", "zero Y today"), grep for X before
planning against it — absence claims age faster than anything else in a tracker.
An agent's report — including a reviewer's — is a lead, not a finding. Before
applying a defensive transform, check whether the defense already exists
somewhere better, and ask what the transform destroys when it fires.

---

## 9. An invariant enforced at one site, not across its class

`delete_document` deletes `DocumentEntity` rows and states the rule in a comment:
entity quotes are "verbatim document text" and must not "outlive the document
into exports or pins" (`api/documents.py:1846-1851`). That is a rule about a
*class* of data, enforced at exactly one table.

`CarePlanTask.source_quote` — "Verbatim clinician wording the task was derived
from" (`models/care_plan_task.py:45`) — is the same class, added later by HC-M15,
and nothing deletes it. There is no `delete(CarePlanTask)` anywhere in `api/`. A
patient who deletes a visit note still has its verbatim text in the tasks table.
Found 2026-09-08, and only because `SQL-FK-001`'s audit forced a read of every
parent/child delete path; no test failed, and nothing in the tracker pointed at
it.

The same shape appears in cleanup that rides on ORM cascade: `Chunk.embedding`
declares `cascade="all, delete-orphan"`, so deleting a document through the ORM
reaches embeddings — but the re-embed path uses a core `delete(Chunk)` statement
(`api/documents.py:867`), which bypasses ORM cascade, and no `delete(Embedding)`
exists to cover it. One path honours the rule, the adjacent one does not.

It also appears when the cascade stops one level short. The `Document →
Observation` ORM cascade did not reach `LabInterpretation` (NOT NULL FK, inert
`ondelete`), which turned every delete of an interpreted document into an
IntegrityError after the file had already been unlinked; found by security
review on PR #24, fixed by DDI (PR #41). The reprocess path's core
`delete(Observation)` (`api/documents.py:629`) still bypasses that cascade
(owner item REPROCESS-INTERP-ORPHAN).

It appears for time too. `taken_at` is stored naive UTC, and `streak_engine`
buckets it on the profile's wall clock, but `modules/adherence_patterns.py`
bucketed the same column by UTC hour, weekday and date, so a Los Angeles
patient's 08:00 dose was learned as 15:00/16:00 (ADHERE-TZ, 2026-10-14). The
streak helpers and `calculate_streak` callers (STREAK-TZ, D-1 PR #104), the
gamification streak (D-3 PR #109) and the scheduler clock with learned windows
(SCHED-TZ, D-2 PR #115, profile migration `013_adaptive_windows_local`) now use
the profile's local date and time (2026-10-16). One hit remains:
`modules/export.py:454` uses the UTC `today` (queue row EXPORT-TODAY-TZ; what it
dates is corrected below). Recheck: `grep -rnE
"taken_at\.(hour|date\(\)|weekday)|utcnow\(\)\.(date|time)\(\)" src/backend`.
Planning EXPORT-TODAY-TZ (2026-10-17) found that `:454` sets the care-task
questions window, not the doctor summary's date. The summary is dated by its
HTML footer, `utcnow().strftime(...)` (`modules/export.py:401`), which the
grep above does not match. Recheck the class with `grep -rn
"utcnow()\.strftime\|utcnow()\.date()" src/backend --include=*.py`. On
`b54f105` it prints `export.py:401`, `:454` and `scripts/backup.py:390`; the
last is a backup filename stamp, UTC by design.

That grep went stale after #155 reshaped the UTC fallback at `modules/export.py`:
the fallback is now `today or now.date()` (`:460`) and `today or
generated_at.date()` (`:703`), which neither pattern above matches. On
`d6a2964` the old grep prints only `scripts/backup.py:413`, the same backup
filename stamp. Replacement: `grep -rnE "or (now|generated_at|utcnow\(\))\.date\(\)"
src/backend --include=*.py`; it prints `export.py:460` and `:703`, the two
fallbacks that apply only when a caller omits `today=`.

It appears for audit too. The audit-order guard (`tests/test_audit_order_guard.py`,
HC-AUD-ORD-030) checks that every committing handler is *classified*, not that
the class is *true*. It lists `api/notifications.py::update_notification_settings`
and `::record_reminder_interaction` as `"C"` (audit after change), but
`api/notifications.py` had no audit call at all; its `log_document_event`
import was unused (found planning AUDIT-MISSING-MED, 2026-10-17; row
AUDIT-NOTIF-ALL). Fixed by AUDIT-NOTIF-ALL: both `"C"` handlers now audit
after the vault commit, and the settings and history reads use
`audit_and_commit` (HC-AUDNTF-001..008). Recheck: for each `"C"` or `"A2"`
row, `grep -n
"audit_and_commit\|audit_intent\|log_.*_event(" <file>` must hit inside that
handler.
Applied to every `"C"` and `"A2"` row on `046d12c` (planning AUDIT-NOTIF-ALL,
2026-10-18), that recheck finds 17 more `"C"` handlers with no audit call in
the body and none reached through a helper: 3 in `api/assistant.py`, 6 in
`api/medications.py`, 8 in `api/model_settings.py` (list in the lane D
AUDIT-NOTIF-ALL plan; queue row AUDIT-C-CLASS). A per-file grep misses
them, because the same file audits in a sibling handler; walk each handler body
instead.
The class is now a test
(`test_hc_aud_ord_030_c_and_a2_handlers_reach_an_audit_call`), so a new
unaudited `"C"` or `"A2"` row fails CI.


**Recheck:** when a comment or doc justifies a deletion with a reason that names
a *category* ("verbatim document text", "credential material", "anything
exportable"), find every table in that category and confirm each has a delete
path — `grep -rn "quote\|verbatim" src/backend/models/` — rather than trusting
that the rule spread on its own. New features inherit schemas, not invariants.
And where cleanup depends on ORM cascade, `grep -n "delete(" src/backend/api/*.py`
finds the core statements that silently skip it. When a parent's ORM cascade is
relied on, walk every grandchild with a NOT NULL FK.

---

## 10. A fully unit-tested feature that was never started

`modules/notification_scheduler.py` had complete unit coverage for schedule
evaluation, message generation, and delivery — every function green — but
nothing called `start_notification_scheduler()` from `main.py`, and nothing
registered a profile's session with it from `core/auth.py`. The feature was
dead on every boot for months (audit 2026-09-25 §11.2). A 100% green suite at
the function level is silent about whether the function is ever reached in
production; "tested" and "wired" are different claims, and only the second
one matters to a user. The backup scheduler had already made the identical
start/stop/register/unregister wiring shape once (`modules/backup_scheduler.py`),
which is exactly why it was missed here — a sibling module's wiring being
correct creates no evidence about this one's.

**Recheck:** for any background task or scheduler, grep for its start/stop
functions outside its own test file (`grep -rn "start_<name>\|stop_<name>" src/backend/main.py`)
before trusting its unit tests as a completeness signal. A module that is
fully testable in isolation is not evidence it is reachable from `main.py` or
any other entry point — check the call site, not just the callee.

---

## 11. Harness rule text broader than the plan it summarises

The queue row for E-3a, written by the orchestrator, told implementers to run `ruff format` as part of the cleanup. The approved plan allowed only safe `ruff check --fix` changes and excluded the ask-first files (`modules/redaction.py`, `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`) and merged migrations. `ruff format` rewrites whole files, so following the row would have edited ask-first files. The E-3a implementer did not follow it: it skipped the step, flagged the conflict between queue row `:71` and plan section 2.3a in its PR #142 report, and waited for a ruling; the ruling and the row correction ("never `ruff format`") landed in #147. The row text was the orchestrator's own paraphrase, broader than the plan, and nothing but the implementer's habit of re-reading the plan stood between it and an ask-first edit. A one-line instruction in a queue row reads as authority and was never checked against the plan it summarised.

**Recheck:** when writing or following a queue-row instruction that names a command, compare it with the plan section it cites: `grep -n "<command>" docs/plans/<plan>.md`. If the plan does not name the command, do not run it. For any bulk-edit command (`ruff format`, `--fix`, codemods), run it on a scratch branch and list `git diff --stat` against the ask-first file list before committing.

---

## 12. A gate merged beside PRs built before it

E-3-T7 (#160) added the Backend Lint gate to CI. #156 and #165 were built before it existed and merged in the same group without being run against it. Each passed the checks it had been given, but the gate was new, so neither had ever seen it. Main's lint went red on `d427868` with 5 `I001` (unsorted import) errors, and #171 fixed it afterwards. Every PR in the group was green on its own head; the failure existed only in the combination, and nothing in the merge step asked whether the new gate held on the merged tree.

**Recheck:** after merging a PR that adds a gate (a CI job, a lint rule, a guard test), run that gate on `origin/main` before merging the rest of the group, and rebase or fix the remaining PRs on it. Do not read "each PR was green" as "main will be green": `git log --oneline -- .github/workflows/ci.yml` shows which gates are new, and a PR whose base predates one has not been checked against it.

---

## 13. An agent returns while its own background RED/mutation run is still editing the worktree

Two rows returned while a background RED or mutation run was still in their worktree. UI-TOKENS (PR #356): three product files were left staged at origin/main's versions, and L0 restored them from HEAD. UI-PRIM-CONTROLS (PR #365): `src/frontend/src/components/ui/Button.tsx` was left mutated, and L0 restored it from the run's byte snapshot. A result read from a worktree that a background job is still writing to says nothing about the files as they stand.

**Recheck:** run RED and mutation evidence in a separate scratch worktree, or run the snapshot/restore script in the foreground to completion and compare every snapshot file before returning. Never return while a background job writes to the worktree.

---

## 14. A probe that charges its own work to the thing it measures

UI-SHELL (PR #370) failed CI's E2E job on twelve routes with stillness sampling gaps of 44-155 ms against the 40 ms G10 bound, and the 2026-10-25 handoff read it as load flake. On one production build, L0 timed the same navigations with a bare 20 ms `setInterval`: 20-30 ms on main and on the branch, apart from `/settings` on the branch (47-48 ms). `stillnessProbe` stamped each sample with `performance.now()` after reading every `[data-t0]` node's style and rect (`e2e/support/gates.ts`, `snapshot()`), so each gap included the probe's own forced layout. Moving the stamp to the start of `snapshot()` kept every HC-UIG-006 self-test result, and most route gaps fell under 40 ms. The same pass turned up a real defect that both readings had hidden behind the flake label: the Safety Mode note's rect changes on every navigation (376.8 → 307 px wide, about 40 ms in).

**Recheck:** before ruling a timing failure "flake" or "load", time the same action with a bare instrument (a plain timer, a `PerformanceObserver` for `longtask`) on main and on the branch, using the same build. When a probe's result is a duration, find where it reads the clock relative to its own work. Read the probe's other failure lines too: a timing failure can hide a real one in the same run.
