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

*Superseded 2026-11-06 (BATCH-1106C; the instance above is a dated record and is not rewritten):* fixed on `main`. `scripts/security_gate.py:45-85` now raises `ReportError` on a missing or unparsable report and `main()` returns exit code 2 (`:156-158`); `ci.yml:191-220` is exit-code-aware (bandit exit 2 or more fails the build); the two `|| true` lines at `ci.yml:92,95` are gone (the one remaining `|| true`, at `ci.yml:425`, is inside a `trap` that stops the preview server).

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

A 2026-10-31 instance in RAPIDOCR-BUNDLE (cross-ref §9, §3). The local-first
test patched Python's `socket.connect` and saw nothing, while onnxruntime 1.31.0's
native OneCollector telemetry client (static libcurl, mobile.events.data.microsoft.com)
opened its own socket from a native thread about 9 s after the first session. A
Python socket guard cannot see a native library. The plan's claim that an
`LD_PRELOAD` probe had shown no traffic was never measured (§3). Opt-out is
`ORT_DISABLE_TELEMETRY=1` before the first onnxruntime import. HC-OCR-001 and
HC-OCR-015 now poll the process's real sockets in `/proc` and assert an empty-HOME
tree; HC-OCR-017 keeps any other module from importing onnxruntime first.
Recheck for a "no network" claim: a `/proc/net` socket poll after a wait longer
than the library's first-upload delay, plus an empty-HOME file assert.

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

A 2026-11-09 instance, a test that never reached the route (VERIFY-NONFINITE; sub-orchestrator review of `build/verify-nonfinite`). httpx 0.28 refuses `NaN` and `Infinity` in `json=` on the client ("Out of range float values are not JSON compliant") before any request is made, so a test that posted `json={"value": float("nan")}` could not fail whatever the route did: the exception came from the test client, not from the handler. The plan's HC-VNF cases were written that way. Recheck: for a test whose input the client library may refuse (NaN, Infinity, an oversized body), send the body as raw text (`content='{"value": NaN}'` with a JSON content type), keep one finite `json=` case as the control, and show the case RED against `main` with a status code from the route, not a client exception. The plan text is corrected in BATCH-1110A. It is recorded as an instance of this mode, not a new mode.

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

A 2026-11-03 instance in UI-PG-REVIEW (#452): the Source Trace sheet's "It
matches, mark as checked" verified through the sheet's own mutation, so the
page's `markChecked` (the hold and the ink) never ran, and the refetch dropped
the row and unmounted the open sheet. Nothing in the diff touched that path; it
was found only because the implementer listed it as a known unknown and
measured it on the default `/verify`, where it failed. Recheck: when a page
adds behaviour to one way of doing an action, list every other component that
performs the same action and run each.

A 2026-11-04 instance in KB-CANONICAL-NAMES (#486): renaming the seeded
`glucose_fasting` entry to `glucose` fixed the mismatch for "Glucose" and
"Fasting Glucose", but `normalize.py:153` maps "fasting glucose" and not
"glucose fasting", so a "Glucose Fasting" row is still stored as
`glucose_fasting`, which no seeded entry matched any more. The unrenamed seed
had matched it, so the rename lost that row's critical flag. A reviewer caught
it as the round 1 BLOCKER; the tests had not covered that label. Recheck: when a
rename moves the key a lookup uses, run every spelling the normalizer can
produce for the old key, not only the new one.

A 2026-11-05 instance in KB-UNIT-BADGE (#486), and this one was L0's own. L0's
first licence (D1, ruling 6673478599) said "anything `convert_to_canonical`
returns None for, or a missing unit: no critical", and compared a converted
value only when the KB unit normalised to the table's canonical unit. That
rule was too narrow. The Opus safety review at `2d406d48` (2 BLOCKER, 1 MAJOR)
found it would have dropped correct criticals that main shows today: TSH
(the KB unit `mIU/L` is a listed variant of the table entry, not its
canonical unit), WBC and platelets (the extractor writes `x10E3/uL`, `K/uL`,
`cells/uL`, which the table omits on purpose), and the D3 rebuild would then
have rewritten saved correct criticals into non-critical cards (ruling
6675742258, "L0's own D1 licence was too narrow"). The fix to one wrong alarm
had created the missing-alarm bug one layer over. Recheck: before licensing a
"no critical when it cannot convert" rule, list the analytes whose correct
alarms main shows today, with the unit spellings the extractor writes for each
(`extract.py`), and run each through the new rule; every one that fires on
main must still fire, or the loss is named as a known limit and the owner is
told.

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

A 2026-11-09 instance, a provenance claim in a model-written data file (MED-NAME-LIST). The header of `rxnorm_names.txt` said the 461 names were "selected by hand from the public-domain NLM RxNorm vocabulary". A model had written the list; nothing was extracted from RxNorm. The plan had said "RxNorm-derived" first, and the file repeated it. The sub-orchestrator reworded the header (`0da251fb`), and the owner answered "Hold for RxNorm" (2026-11-10): the row stays unmerged until a real extract exists. Recheck: a source, date or "derived from" statement in a data file or its plan is a claim and needs the command or the extract that produced it; when a model wrote the content, the header says so. A probe of the list against the classifier (vitamin D questions moving from none to medication) is the kind of measurement the header did not have.

A 2026-11-10 instance, a cause named to the owner without a measurement (OCR-COPY-ENGINE, #542; gate OCR-HEIGHT-SHORTEN). L0 attributed the 18 px HC-UISET-005 overflow (Settings > Advanced expanded 1814 px against the 1800 px bound; `main` 1796 px) to the longer `tesseract_missing` sentence wrapping to a second line, and put that to the owner without measuring the height with and without the sentence. The owner approved shortening it (OCR-HEIGHT-SHORTEN, "Shorten the sentence (Recommended)"); CI on `7ea39dde` still measured 1814 px. Recheck: before naming the cause of a height or timing overflow to the owner, measure it by bisecting reverts (revert one candidate change at a time on a clean copy and paste each height); a cause that has not moved the number is a hypothesis, and the question says so. It is recorded as an instance of this mode, not a new mode.

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

A 2026-11-09 instance, an environment assumption that passes alone and fails in the full suite (CRIT-LOG-ROUNDED and DOC-EXC-LOGGING; SUBORCH-2026-11-09). A test that read a process-wide value, the log record's `correlation_id` set from a static environment, passed on its own and failed after other tests had set it first. Recheck: run a new test file alone and again inside the full suite; a test that depends on module or environment state sets that state itself (`monkeypatch`) and never reads the default.

A second 2026-11-09 instance, wall-clock and load flakes on `main`. `test_hc_vrc_030` failed once in the full run of the ANALYTE-NAME-SWEEP branch at load about 9 and passed alone three times, though the branch does not touch it. `test_hc_edf_004` flaked the same way (KV-LEFTOVERS already carries it as item 22), and on #537 the three HC-ENL-001 cases failed at load 20 on `/mnt/e` and gave `38 passed in 22.05s` from a `git archive` copy in `/dev/shm`. Recheck: for a failure in a file the branch does not touch, re-run it alone and from a `/dev/shm` copy, paste the load average (`uptime`) with each result, and never move a limit or a threshold to make it pass. Report it as a flake with the evidence, not as a pass.

A 2026-11-10 instance, the same test failing on GitHub CI rather than under local load. `test_hc_edf_004` (the date regex must parse a 50,000-space header in under 1.0 s) failed on #541 three times (1.09 s, 1.04 s, 1.01 s) and on `main`'s own CI, and blocked every backend PR though none of them touch date extraction. The owner chose best of 3 (EDF-004-BEST-OF-3): the same input, the same 1.0 s bound, the fastest of three timed runs asserted, so a truly quadratic regex is still caught. The bound did not move. Recheck: a wall-clock test that fails on CI at a margin of 1 to 9 percent over its bound is a noisy bound, not a slow product; take the fastest of several runs and keep the limit, and never raise it.

A 2026-11-11 instance, a wall-clock perf pin that flakes under parallel pytest slots (KV-LEFTOVERS; reported by another builder). `test_date_extraction.py::test_hc_edf_004_dob_inputs_stay_linear_with_new_tail_regex` pins each DOB input to under 1.0 s. It flaked when run beside other pytest slots and passed in isolation, so a red result there can be machine load, not a regex regression. (Evidence is the builder's report; the pin's 1.0 s bound is verified in the test file, the flake is not re-reproduced here.) Recheck: on a failure of a wall-clock pin, re-run that test alone on a quiet box (`scripts/pyslot.sh` with no other slots busy) before changing code, and report both timings. Do not raise the bound to make it pass (CLAUDE.md section 3); if a pin must survive load, make it measure work (call counts, input-size scaling ratio) instead of seconds, as its own row. Same mode, not a new one.

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

**Box instance (2026-10-29, #410; queue bullet FOREIGN-CHROMIUM-ON-BOX).** The contaminant was the box, not the tree.
- A stillness timing run's quiet-box precheck was `pgrep -fa "playwright|vitest|pytest"`.
- Another repo's session was driving its own Chromium (`shoot.mjs`) on the same box at the time. The pattern could not see it.
- The check also could never print nothing. Run from an agent's Bash tool, `pgrep -f` matches the agent's own `bash -c` command line, which contains the pattern (planner check, 2026-10-30). So every agent was already judging by eye which lines were its own.
- The precheck now lives once, in [RUNBOOK](../plans/2026-10-15-build-program/RUNBOOK.md) §10.1, in bracket form (`[p]laywright|…`, which does not match itself), with Chromium, Rust and port checks added.

**Recheck:** when anything else is editing the tree, verify commit-level gates in
a throwaway `git worktree` detached at HEAD, not in place. Related: parallel
agents running `git add` sweep each other's staged work — commit with explicit
pathspecs (`git commit -m … -- <paths>`), and never `git reset` to clean up.
And for **any** docs change, `scripts/docs_lint.py` passing is not sufficient —
run `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py
--link-graph`. CI no longer runs Backend Tests on a docs-only PR (path-scoped CI,
#442), so see what it will do:
`git diff --name-only origin/main...HEAD | python3 scripts/change_scope.py --repo-root .`
(the Change Scope job's output). `docs_only=false` means a code path mentions one
of your docs, a docs↔test coupling, and the full suite runs; run it locally too.

A 2026-11-06 instance, a leaked preview server (#514 quiet-box batch; queue candidate PREVIEW-KILL-CHILD). The environment the next run started in was not the one the script thought it had left. The RED batch left a `vite preview` on :4173 (pid 1716032, an orphan whose cwd was the #514 worktree); `quiet_run` then refused to start the GREEN batch for 20 minutes and more, and the agent's own attempt to kill it was denied by the permission classifier, so L0 verified the pid and killed it. The second leak was the script's own: `batch514.sh:28` stopped the preview with `kill $P`, where the preview had been started as `bash -c "cd ... && vite preview &"`. `$P` was the `bash -c` wrapper, so the kill ended the wrapper and left the node child on :4173 (pid 1738555), which stalled the llama-bench prechecks for 1061 s with the pytest slots held. L0 patched the script to `pkill -P $P` first. Nothing in either run's output said a process was still alive: the batch exited, its results printed, and the next run was the one that stalled. An earlier case of the same shape held a pyslot lock for 4 hours (a leaked vite; the model-host notes name it). Recheck: after any batch that starts a server, before reading its results or starting the next run, list what still listens (`ss -ltnp | grep -E ':(4173|5173|3000|8000)\b'`, `pgrep -af 'vite|node'`) and expect nothing from your worktree. Stop a server by its process group or its children (`pkill -P "$P"` first, or `setsid` and `kill -- -"$PGID"`), never by the `$!` of a wrapper, and put the stop in a `trap ... EXIT` so every exit path runs it. It is recorded as an instance of this mode, not a nineteenth mode: the shape is the same (a gate run in an environment other work left dirty) and CLAUDE.md names the count of modes.

A 2026-11-06 instance, a worktree that measured taller than the same code (#523, SETTINGS-EXTAPI-PENDING; queue label WORKTREE-ENV-HEIGHT). The `hc-settings-extapi-pending` worktree measured every Settings section taller than a clean copy of the same code: Advanced 1874 px against 1796, Security 1296 against 1276, Assistant & privacy 1650 against 1573. `src`, `node_modules`, fonts and the lockfile were identical; moving `node_modules/.vite` aside changed nothing. The cause is unknown. The first reading was that the code had grown the page (the row's 1800 px bound), and the build was resumed to shrink it. Recheck: measure acceptance (heights, G10) from a clean copy of the head (for example `/dev/shm/hc523`), and A/B the worktree against that copy before blaming the code; paste both. It is recorded as an instance of this mode, not a nineteenth mode: the shape is the same (a gate run in a tree that is not the one the claim is about) and CLAUDE.md names the count of modes.

A 2026-11-07 instance of the leaked preview, again (#535, UI-PG-SECURITY; RUNBOOK §10.1 preflight item 7). The build agent's frontend build left a `vite preview` on :4173 (PID 2198476). Quiet batch 17 exited 75 PORT-LEAK three times, nothing ran, and the permission classifier refused L0's kill; the owner killed it. The 11-06 fix (the script's own `pkill -P`) covered L0's batches, not a build agent's. Recheck: after any frontend build, before a quiet batch, list the listeners (`ss -ltn | grep -E ':(3000|4173|5173|8000)\b'`) and expect nothing. Same mode, not a nineteenth.

A 2026-11-07 instance, a worktree that rendered a different font (#538, SAFETY-MODE-VERIFIED-FE; queue label WORKTREE-ENV, fonts; L0 ruling 6718736151). `node_modules` in the build worktree was a symlink into another worktree. Vite dev refused the `.woff2` files (403, outside `fs.allow`), so the fallback face rendered, the Safety Mode note measured 5 lines and 80 px, and L0's first ruling (6718543811) sized the box for that. With the loaded Source Sans 3, which patients get and CI measures, the note is 4 lines and overflows 64 px by about 1 px; the ruling was replaced by `lg:h-[66px]` (6718736151). Recheck: before measuring layout in a worktree, `ls -ld node_modules` must not show a symlink (`npm ci` for a real install), and a `.woff2` request to the dev server must return 200; paste both. It is recorded as an instance of this mode, not a new mode.

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

A 2026-11-09 instance, quiet-box helpers that lived only in `/tmp`. The box rebooted at about 22:06 on 2026-11-09 and wiped `/tmp/claude-1000`, where `quiet_run.sh`, `hold_slots.sh` and the CR-stripped `pyslot` copy lived. RUNBOOK §10.1 quotes those paths, so every documented quiet-box command would have failed until they were recreated (L0's notes record it). Copies are now kept in `~/hc-quiet-logs/tools/` (copy them back to `/tmp/claude-1000` after a reboot). Recheck: before a quiet run, `for f in quiet_run.sh hold_slots.sh; do test -x /tmp/claude-1000/$f || echo missing $f; done`, and after any reboot (`uptime`) assume they are gone. RUNBOOK §10.1 preflight item 2 now names the copy.

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

*Drifted cite, 2026-11-06 (BATCH-1106C; the instance above is a dated record and is not rewritten):* the `first_val` / `last_val` comparison it cites as `api/observations.py:660-671` is at `api/observations.py:755-760` on `origin/main` `d944b38b`.

A 2026-11-02 instance in VERIFY-KEEPS-FLAG (#463): the comment in
`modules/fhir_export.py` called `flag` a "short coded flag" while the flag was
stored as printed, free text of up to 2000 characters from import. The comment
read as authority and the line went out unredacted; it was exposed only once
Verify stopped erasing free-text flags. Recheck: when a comment states the
shape of a field, find where the field is written before relying on it.

A 2026-11-05 instance in KB-CANONICAL-NAMES (#486): the row's "`:392` is dead"
and "never loaded" were false for `glucose_fasting`, and hid the `Glucose
Fasting` regression that ruling 6651067212 fixed. Recheck: run the old key
through the lookup before calling a line dead or a row never loaded.

**Recheck:** a written decision is evidence about what someone believed, not
proof that it was true. When a doc gives a *reason*, check the reason. When a
ticket asserts an *absence* ("no X exists", "zero Y today"), grep for X before
planning against it — absence claims age faster than anything else in a tracker.
An agent's report — including a reviewer's — is a lead, not a finding. Before
applying a defensive transform, check whether the defense already exists
somewhere better, and ask what the transform destroys when it fires.

A 2026-11-07 instance, a build agent's "all checks pass" (#533, AUDIT-CHAT-LEGACY). The agent reported every check passing and the PR looked ready, but CI Backend Lint was red: I001 (import order) at line 19 of #533's new audit test file, job 128338185595. The report was a statement about what the agent ran, not about what CI ran. A narrow Sonnet agent fixed the imports only (head `9826f92c`). Recheck: before asking the owner to ready a PR, read its CI yourself (`gh pr checks <n>`), and run the CI's own lint command, not a nearby one. It is recorded as an instance of this mode, not a nineteenth mode.

A 2026-11-09 instance, a scan lead that read a status without the later ruling (RULES-RANGE-VALUE; SUBORCH-2026-11-09). A Haiku scan flagged the row as an unanswered owner gate because its plan and queue status said "gated, unanswered". The gate RULES-VERIFIER-ASKFIRST had been answered the same day in the L0 rulings (batch 5, "narrow to measured values"), so the row was licensed. The scan's report was a lead, not a finding (CLAUDE.md §1), and the sub-orchestrator caught it by reading the rulings file. Recheck: before reporting a gate unanswered or a row blocked, grep the owner-decisions record, the L0 rulings and the PR comments for the gate's name, and cite the newest hit; a status cell is a claim that may predate the answer. BATCH-1110A rewrites the stale status.

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
The dynamic-call rule had the same gap: it flagged a def passed as a bare name or `self.<def>` but not a bound method of any other object (`asyncio.to_thread(selector.detect_hardware_tier)`), so that edge left the guard without a named key until AUDIT-GUARD-ATTR-DYNAMIC widened the rule.


A 2026-10-31 instance in RAPIDOCR-BUNDLE (cross-ref §2). PDFium accepts one
thread at a time (pypdfium2 METADATA). The rule was enforced at one site,
`_ocr_pdf_pages` (`_PDFIUM_LOCK`), and not at the other caller in the same class,
`api/documents.py::get_page_image`, which renders with pdfplumber `to_image` on the
event-loop thread. Importing a scan while the viewer fetched a page image segfaulted
the process in 4 of 8 probe runs (PR #421 comment 6547136926). The first fix, a lock
held across the OCR call as well, fixed one site and nested two locks. HC-OCR-016
now runs the real `get_page_image` against four OCR workers (exit -11 before the
lock, 6 of 6 clean after). Recheck: `grep -rn "to_image(\|pypdfium2\|PdfDocument"
src/backend` and confirm every hit is inside `_PDFIUM_LOCK`.

**Recheck:** when a comment or doc justifies a deletion with a reason that names
a *category* ("verbatim document text", "credential material", "anything
exportable"), find every table in that category and confirm each has a delete
path — `grep -rn "quote\|verbatim" src/backend/models/` — rather than trusting
that the rule spread on its own. New features inherit schemas, not invariants.
And where cleanup depends on ORM cascade, `grep -n "delete(" src/backend/api/*.py`
finds the core statements that silently skip it. When a parent's ORM cascade is
relied on, walk every grandchild with a NOT NULL FK.

A 2026-11-05 instance, "clinical check unit-blind on main", found while
planning KB-UNIT-BADGE (#486, ruling 6673478599). Observations are stored as the
lab printed them with their unit (`models/observation.py:61-63`), but both
critical checks compare the bare number with a limit in one fixed unit: the
badge in `_classify_severity` (`modules/interpret.py:894-897`) and the review
banner, which passes the raw value to `check_critical_value`
(`modules/interpret.py:246-255`; defaults at `modules/interpret_safety.py:82-90`,
glucose 50 and 400). A glucose of **7.0 mmol/L**, a normal result, got a
`critical_low` badge and the banner "Critical low value: 7.0 is below critical
threshold of 50.0". The rule "critical limits are in this unit" held at the
tests' own values (same unit) and nowhere else. A first fix covered the badge
and the banner for rows with a knowledge-base entry; the path with none
(potassium, sodium) still compares raw values against the default table
(queue bullet CRIT-DEFAULT-TABLE-UNITS). Recheck: for any threshold check on a
lab value, list every call site that compares a number with a limit, name the
unit each number is in and the unit each limit is in, and run one value in a
different unit through each site, not only the site you edited.

A 2026-11-06 instance, "the unversioned-vault matcher assumes every revision
changes the schema", found while planning OCR-OPT-IN-MIGRATION (L0 ruling R2,
`docs/plans/2026-11-06-owner-answers-rows-plan.md`), before any code was
written. `_match_unversioned_vault` (`core/migrations.py:631-657`) identifies an
unversioned vault by a fingerprint of tables, columns and foreign-key actions
(`_schema_fingerprint`, `:568`) and returns the newest match; HC-FKB-001
(`test_fk_migration_017.py:2495-2506`) asserts "one fingerprint per revision".
That rule held for all 17 existing revisions because each one changes the
schema, and nowhere else. A planner probe added a throwaway data-only `018`
(one `UPDATE`) to a scratch copy and ran `migrations._reference_fingerprints()`:
18 revisions, 17 distinct fingerprints, tie `018` / `017`. So HC-FKB-001 would go
RED, and an unversioned vault with the 017 schema would be stamped `018` and
skip the `UPDATE` that makes OCR opt-in. Neither the matcher nor its test could
have noticed: both pass until the first revision that does not touch the
schema. Recheck: before adding a revision that changes no schema, run
`_reference_fingerprints()` with it in place and list every tied pair; name each
data-only revision in the guard test instead of loosening it, and make the
matcher take the oldest tied revision so later data steps still run.

*Superseded 2026-11-06 (BATCH-1106C; the instance above is a dated record and is not rewritten):* it was fixed by #512. `_match_unversioned_vault` now takes the oldest tied revision (`core/migrations.py:651`, "oldest first"), so "returns the newest match" no longer holds; the chain has 18 revisions, not 17 (head `018_ocr_opt_in`, `ls src/backend/migrations/profile/versions/`); and `tests/test_migration_heads.py` (HC-MIGHEAD-001…003) enforces one head per chain.

A 2026-11-06 instance, "a guard that only looks at handlers that commit", found by DOCS-AUDIT-1106 and closed by AUDIT-READ-ROUTES. CLAUDE.md requires an audit row on every route that touches documents, observations or profile data. HC-AUD-ORD-030 (`tests/test_audit_order_guard.py`) enforces the order of audit and commit, but it only scans handlers from which a `.commit()` is reachable. A read handler that never commits is outside that set, so it was invisible to the guard, and eight vault reads shipped with no audit row: the chat session list and history, the assistant memory setting, the feedback stats, and the medication list, detail, schedules and doses. Every one had a green test, because no test asked whether a GET writes a row. HC-ARR-011 (`tests/test_audit_read_routes.py`) now guards the class: every handler in `api/` reaches an audit sink or is named in `UNAUDITED_ROUTES` with a reason, and a stale entry fails. Its blind spot is written in the test docstring (the graph links calls by name; it sees handlers, not paths, so a handler that audits on one branch passes). Recheck: when a guard is scoped to a subset of handlers (the ones that commit), list the handlers outside the subset and say what covers them; run one new handler outside the subset through the guard and confirm it is reported.

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

**Frontend instance (2026-10-29, #407 review; queue bullet SOURCE-TRACE-UNWIRED).**
- The Source Trace sheet (`src/frontend/src/components/results/SourceTrace.tsx`, UI-PROVENANCE) has unit tests.
- `CitationTooltip` renders the "Open source" button and the sheet only when it gets a `source` prop.
- Neither call site passes one: `InterpretedResultCard.tsx:122` and `PanelInterpretationDashboard.tsx:110`.
- The `/interpret` e2e mock has only a `knowledge_base` citation.
- So the sheet cannot be reached in the browser, and a plan (#407's first draft) chose it as a test host.

**Recheck for components:** for an optional prop that gates a feature, grep every call site of the component for that prop. Confirm that some e2e path renders the gated branch before you treat the component as shipped, or use it as a test host.

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

UI-SHELL (PR #370) failed CI's E2E job on twelve routes with stillness sampling gaps of 44-155 ms against the 40 ms G10 bound, and the 2026-10-25 handoff read it as load flake. On one production build, L0 timed the same navigations with a bare 20 ms `setInterval`: 20-30 ms on main and on the branch, apart from `/settings` on the branch (47-48 ms). `stillnessProbe` stamped each sample with `performance.now()` after reading every `[data-t0]` node's style and rect (`src/frontend/e2e/support/gates.ts`, `snapshot()`), so each gap included the probe's own forced layout. Moving the stamp to the start of `snapshot()` kept every HC-UIG-006 self-test result, and most route gaps fell under 40 ms. The same pass turned up a real defect that both readings had hidden behind the flake label: the Safety Mode note's rect changes on every navigation (376.8 → 307 px wide, about 40 ms in).

**Recheck:** before ruling a timing failure "flake" or "load", time the same action with a bare instrument (a plain timer, a `PerformanceObserver` for `longtask`) on main and on the branch, using the same build. When a probe's result is a duration, find where it reads the clock relative to its own work. Read the probe's other failure lines too: a timing failure can hide a real one in the same run.

A 2026-11-05 instance in UI-PG-SETTINGS (PR #488, G10 on `Show advanced settings`, L0 comment 6665469225): CI failed three attempts at 59, 67 and 61 ms with no colour, rect or opacity lines. A CDP trace of the production build showed no single long task, but four to five short tasks after the click (skeleton layout, then panel layout) holding the sampler back, the largest gap 48.5 ms. A bare 20 ms `setInterval` with no probe also exceeded 40 ms in 3 of 15 runs (47, 55 and 73 ms), so it was app work and not the probe alone; the gap was real, and the fix went into the app. Recheck, widened: when a bare timer is clean on main and not clean on the branch, trace what runs between the click and the next sample before choosing between the probe and the app.

A second finding in the same PR (#488, 2026-11-05, rounds 1 and 2 of the fix for the instance above): round 1 moved the settings and tiers reads to section mount, so the loading state was gone, and a click then mounted the whole panel synchronously inside the click handler. G10 on dev went from 4 misses in 10 to 10 misses in 10, because a render started by a discrete event (a click) cannot yield to the sampler. Round 2 gave the panel a `useDeferredValue` and then rendered the cards in three idle-gated commits, and G10 `Show advanced settings` passed 30 of 30 on production (19 of 30 before; L0 comment 6669591593, `a3878571`). The recheck lesson: after a change removes a loading state (a skeleton, a spinner, a wait), trace where the work moved. Work that used to wait for data now runs at the moment of the event. Re-measure the gap the change was meant to close before calling it closed, on the same build and the same line.

---

## 15. A test runner returns while its command is still queued or running, and the result reads as a test failure

On 2026-11-02 PRs #398, #454 (C-P6), #457 and #399 each stopped with "tests failing" while no test had failed. The Haiku runner backgrounded the full suite, reported `exit_code -1` or NOT RUN, and `all_passed: false` sent the row to a stop. Slots can be held for over an hour by a quiet-box run, so a runner that does not wait for its command reports the queue as the result.

Related trap, same day: a named workflow loads from the session's main checkout, so a session on an old branch runs an old `build-item.js`. That session ran a 366-line copy against main's 481 lines, without HARNESS-SPEEDUP's scope gating, so frontend-only rows ran the full backend suite. Ask whether a harness change you are relying on is in the copy this session actually runs.

Second cause, same day: #399 (twice) and #454 stopped as "incomplete" with no failing test. In the #454 implementer's transcript (workflow run wf_33290fe3-3f3) the agent started commands with `run_in_background`, then sent the text-only message "Waiting for the background events." The harness replied `[structured-output-enforce] You MUST call the StructuredOutput tool`, so the run ended, and the background-command notice says such a command "is terminated when you give your final answer". The WAIT FOR EVERY COMMAND sentence reached only the runner prompts and said to keep checking, not how. `build-item.js` STYLE, which is appended to every agent prompt, now carries a HOW TO WAIT rule: a foreground `timeout 580 bash -c 'until grep -q "^EXIT=" <file>; do sleep 5; done'` loop (exit 124 only means not yet).

**Recheck:** the runner prompt says to wait for every command, and a result with `exit_code -1` is never a finding. Before relying on a merged harness change, `diff` the session's `.claude/workflows/<name>.js` against origin/main, and use `scriptPath` with a copy of main's file if they differ. A stop that says a command had not finished is read in the agent's transcript, not in the stop text: a `[structured-output-enforce]` line right after a text-only message means the agent ended its own turn.

---

## 16. A deliberate break that never reached the code the test loaded

UI-PG-DOCUMENTS (PR #464, 2026-11-03): to show HC-UIPAL-005 can still fail after the route-fade wait, the implementer added a slide to a palette option in `CommandPalette.tsx` and ran the cold test. It passed. The worktree is on `/mnt/e` (WSL drvfs), where `vite` gets no file-change events, so the dev server went on serving the module it had cached before the edit; `curl http://127.0.0.1:3101/src/components/layout/CommandPalette.tsx | grep -c translateX` printed 0. Restarted with `CHOKIDAR_USEPOLLING=1 CHOKIDAR_INTERVAL=300`, the same break failed the test with six lines naming the moved rects. A RED-by-break that is green is the same failure as mode 1, with a different cause: the break was real, and the test never saw it.

**Recheck:** after a deliberate break, before running the test, fetch the served module and grep it for a string only the break contains (`curl -s <dev server>/<path> | grep -c <string>`). A break that passes is evidence about the server until the grep says the server has it. On `/mnt/e`, start `vite` with `CHOKIDAR_USEPOLLING=1`, or use `vite build` and `vite preview`.

---

## 17. A fixture that answers every call the same way hides the second event

UI-PG-DOCUMENTS (PR #464, review round 1, 2026-11-03): the HC-UIDOC-006 jump tests for an import ran one import, against a mock (`mockDocuments`, `e2e/ui-documents.spec.ts`) that answered every `POST /documents/import` with the same document id. The import card committed with its row, the tests were green, and a second import in one visit still moved the rows three times (1091.5 -> 959.1 -> 1214.7 px on a production build): the old card left when the import resolved, and the new card and row arrived with the list. A retry after a failed import did the same with the alert (944.3 -> 835.8 -> 1091.5). The first event has no previous card or alert to leave, so no test of it could see the split. Same class, one cause: the fixture could only produce the first event, so the test could only fail on the first event.

**Recheck:** for every UI state that a new event replaces (a card, an alert, a warning, a selection), the test runs the event twice in one visit, and the fixture gives the second answer its own id and name. A jump or flicker test that runs a state's first event alone is not a test of the state's replacement. Ask what the second and the retry would do, then make the mock able to ask it.

Round 2 (same PR, 2026-11-03) found the same class one event later. The round-1 fix made an import "ready" only while its row was in the list or the list was not fetching. After a Remove, the removed import's row never comes back, so on the next refresh it was not ready again: the card of an older import, or the "Import failed" alert of a file the retry had already imported, returned for the length of the fetch. Rows held three positions in four sequences: import A, import B, Remove B, Remove an old row (735.1 -> 867.5 -> 734.8 px); the same, then import C (959.1 -> 1091.5 -> 1214.7); fail, retry, Remove, Remove an old row (835.8 -> 944.3 -> 712.6); fail, retry, Remove, import C (835.8 -> 944.3 -> 1091.5). Every one of these passed the tests that ran the event, then Remove, and stopped. The fix is in `importReady` (`removedIds`); the tests are HC-UIDOC-006 (q) to (t).

**Recheck, widened:** after the replacement test passes, run the chain event, Remove of what the event made, then a refresh of the list (another Remove, another import). A state that depends on "is its row in the list" changes meaning when the row has been removed.

Round 3 (same PR, 2026-11-03) found the class again, with two events that overlap in time. Round 2's chain ran Remove once, alone. A second Remove sent while the first DELETE was still in flight lost the first's record of the removed document: `confirmDelete` passed `onSuccess` to `mutate`, and a per-call `onSuccess` fires only for the observer's latest call (query-core `mutationObserver.ts`). The card and the "3 values ready to review" link stayed for a deleted document: `{"card":"Document imported: private-fresh.pdf","link":"3 values ready to review","rows":[]}`. The fix records the removal from `mutateAsync(id).then(...)`; the tests are HC-UIDOC-018 (vitest, and e2e with `holdDelete()` on the mock, RED at fb6e7ef2: the card count stayed 1). The same round added a 3 s timer that marks an import ready when the list refresh never settles. A timer is an event too: it fires after the Remove, and a fix that put it before the `removedIds` check brought the removed card and the retry alert back (HC-UIDOC-017 fails with that break: 2 failed of 2).

**Recheck, widened again:** the chain also runs the events overlapping, not only in sequence: two Removes with the first held, a second import while the first is still in flight. Hold the first request, send the second, release both, and read the settled page for the state the first event owned. And any callback passed per call to a React Query `mutate` is read as "fires only for the latest call": state that must survive overlap goes in `mutateAsync(...).then`, or in the hook's own options. A timer or any deferred effect joins the chain: fire it after the Remove, not before.

---

## 18. A batch that reports done while most of its lines never ran

L0's quiet-box batch on 2026-11-05 printed ALL-DONE and exited 0 with only 5 of 18 lines run. A `run()` helper assigned the global `L` that the script also used as the log directory, so every later redirect failed before its command started. Those 13 failed to start and left no log, so nothing in the output said they had not run: the exit status and the final line both read as success.

**Recheck:** before reading results, count the logs against the lines the batch was meant to run (`ls <logdir> | wc -l` against the number of lines), and read each log's own exit line. Make a batch exit non-zero when a line could not start (`set -u`, no helper that reuses a global the script also uses, and a check that every line left a log). A batch that prints "done" is evidence about the script, not about the lines.


---

## 19. Acceptance scoped to the row's own spec misses the spec that shares the component

UI-PG-SECURITY (#535, 2026-11-07): the quiet batch ran only the row's own spec. CI's run of another spec — one that renders the same settings components — failed on a regression the batch never exercised. The owner's same-day analysis counted the class four ways: status cells that lag merges (UISET-013-TEST already done inside #523, STILLNESS-NAV-LATE Task 3 already merged, each wrong start a burned run), plans older than the code (C-GC1's 2026-10-06 plan never learned #334's 2026-10-24 expiry and logout purges), file lists that name no test that breaks (a migration guard compares every table at the newest migration), and the narrow acceptance above.

**Recheck:** the planner greps `e2e/` for every spec that renders a changed component (selectors and testids, not only file names) and lists them all in the row's acceptance; the gate re-runs the grep on the final head. Before a build, `git log --since=<plan date> --oneline origin/main -- <files>`: any commit means re-plan. Before starting a row, check `gh pr view` and `git log origin/main` for the merge itself, not the status cell. The four fixes are RUNBOOK §10.1 planner checklist items 4-7.

Three 2026-11-09 instances found by the sub-orchestrator's diff review (SUBORCH-2026-11-09), all of the "file lists that name no test that breaks" and "plans older than the code" kinds.
- **A plan that omits an assertion an owner answer forces.** SAFETY-MODE-DUPROW's plan said the existing assertions in `test_safety_mode_setting.py` stay unedited and listed only new HC-SMS-008 cases. The owner's any-ON answer forces HC-SMS-004's shared-vault tail (profile B's GET reads True, not False), and HC-SMS-008c asserts the same thing. The build had to edit it, and L0 licensed that after the fact (ruling R1, 2026-11-10). RUNBOOK §10.1 planner checklist item 1 exists for this (grep the tests for each file the row touches); it was not run against the assertion the owner answer changes. Recheck: when an owner answer changes a behaviour, grep the tests for assertions of the old behaviour and list each one that must flip in the row's file list, with the answer's name beside it.
- **A stale plan fact.** ANALYTE-NAME-SWEEP's step 2 said `plan.py` mapped "cholesterol" to a name that is never stored. `query_observations.py:69` already canonicalizes "Cholesterol" to `total_cholesterol` (CHAT-FACT-ROUTING), so the planned test (HC-ANS-003) could not fail. The Phase A build replaced it with a DB-backed planner-to-tool test whose mutation turns RED. Recheck: for each planner step that claims a defect, run the cheap RED on `main` before the row is ready (checklist item 3) and paste it.
- **A plan that contradicts an owner answer, and a ruling that contradicts its own pinned tests.** The f-3 plan for RECOVER-ORDER said `issue_recovery_code` was out of scope and that no owner gate applied; the owner then answered RECOVER-ORDER-COMMIT with the same reorder for `issue_recovery_code`. Separately, L0's ruling 6732000906 item 5 (prune every row in the vault on save) contradicted HC-EXPA-028 and HC-EXPA-032, which the same ruling kept unedited, and L0 withdrew that half (6734556486). Four rows (FIT-REPORT-SECTION, RECOVER-ORDER, FALLBACK-COUNT-50, TEST-RESET-ROUTE) were each planned twice, which meant two sets of test ids. Recheck: before publishing a plan or a ruling, compare it with every owner answer on the row and with the tests it declares unedited; keep one plan section per row (BATCH-1110A reconciled the four).
All three are recorded as instances of this mode, not new modes.
---

## 20. A hold-everything wrapper that enumerates fewer locks than the pool it excludes

KV evidence (#298): the model-host `hold_slots.sh` quiet-run wrapper flocks a hard-coded list of `hc-pytest` slot locks (`for i in 1 2 3 4 5 6 7 8`, lock files `/tmp/claude-1000/hc-pytest.$i.lock`) while `scripts/pyslot.sh` hands out slots `1..PYSLOTS` (`n="${PYSLOTS:-3}"`, line 5). When the wrapper's list stopped at 3 (later 8), a `PYSLOTS` above it let a pytest take an unheld slot and run beside the run the wrapper exists to isolate: the exclusion silently covered only part of the pool.

**Recheck:** any "hold every X" wrapper must derive its count from the thing it excludes (`PYSLOTS` itself, or `ls` over the lock prefix), not keep a copy of it. Before trusting an exclusive run, run one probe job at a `PYSLOTS` above the wrapper's top lock and prove it still blocks. The wrapper lives outside the repo today (the durable copy is `~/hc-quiet-logs/tools/hold_slots.sh`); if HOLD-SLOTS-IN-REPO lands first it moves into the repo's scripts directory.

**Owner action (KV evidence item 4, not a failure mode):** the Ollama fallback tag `gemma4:12b` (`core/llm/factory.py:49`, `model = llm_model or "gemma4:12b"`) already matches the documented recommendation (`config/.env.example`), so no repo change is needed. It is not pulled on the model host, so a `LLM_PROVIDER=ollama` install without `LLM_MODEL` asks for a missing model. The owner runs `python scripts/download_models.py ollama --tag gemma4:12b` (or `ollama pull gemma4:12b`) on the model host.

---

## 21. A captured subprocess whose background grandchild keeps the pipe open

The inverse of the leaked-orphan instance under mode 5: there the orphan outlived the batch and held a port or lock; here the orphan makes the caller wait. Reported by another builder: `subprocess.run(..., capture_output=True)` on a command that leaves a background grandchild blocks on pipe EOF until the orphan exits, because the grandchild inherited the stdout/stderr pipe write ends. The test hung with the command already at rc=0; nothing in the output showed a wait on a pipe. (Evidence is the builder's report; not re-reproduced here.)

**Recheck:** a test that runs a command which may background anything redirects the child's stdout/stderr to a file (or `DEVNULL`) instead of pipes, or sets a `timeout=` and kills the process group (`start_new_session=True`, `os.killpg`). When a test hangs at rc=0, list the process's descendants (`pgrep -P`, `ps --forest`) before blaming the code under test.
