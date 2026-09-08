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

**Recheck:** ask what your test would *fail to notice*. Then break the code on
purpose and confirm the test goes red. A test that has never failed proves
nothing. Route tests asserting auth, path scoping, or status codes go through
HTTP — use `src/backend/tests/support/routes.py::route_client`.

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

**Recheck:** before writing a figure, ask which environment produced it and
whether another environment produces a different one. Prefer numbers that do not
vary — collected counts over pass counts.

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

A third instance, 2026-09-08: the `INGEST-FHIR-001` tracker row opened with
"zero structured ingest exists today; everything goes PDF/image → OCR → regex."
HC-M23 shipped `modules/import_structured.py` — FHIR R4 Bundle and lab CSV
parsing — on 2026-07-30. The row's premise had been false for weeks, and an
audit built on it re-reported the ticket at full scope. A row is written once
and read many times; nothing re-checks its opening clause when adjacent work
lands.

**Recheck:** a written decision is evidence about what someone believed, not
proof that it was true. When a doc gives a *reason*, check the reason. When a
ticket asserts an *absence* ("no X exists", "zero Y today"), grep for X before
planning against it — absence claims age faster than anything else in a tracker.
An agent's report — including a reviewer's — is a lead, not a finding.

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

**Recheck:** when a comment or doc justifies a deletion with a reason that names
a *category* ("verbatim document text", "credential material", "anything
exportable"), find every table in that category and confirm each has a delete
path — `grep -rn "quote\|verbatim" src/backend/models/` — rather than trusting
that the rule spread on its own. New features inherit schemas, not invariants.
And where cleanup depends on ORM cascade, `grep -n "delete(" src/backend/api/*.py`
finds the core statements that silently skip it.
