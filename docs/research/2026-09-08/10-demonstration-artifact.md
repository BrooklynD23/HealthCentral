# Track 10 — The repo as a demonstration artifact

**Date:** 2026-09-09 · **Researcher:** Sonnet 5 · **Scope:** documentation and
repo-structure only — no product code touched, no real patient data anywhere.

This track answers the question `STATUS.md` names as uncovered: *what should
exist in this repo so that a reader — hiring manager, collaborator, future
maintainer, or the owner in six months — can see the process, not just the
product?* Tracks 1–8 audited what Asclexis **does**. This audits what the repo
**proves about how it was built**, and where that proof runs out.

---

## Summary

The repo already contains an unusually rich process record: a real sprint plan
with dated exit criteria (`docs/agile/AGILE_PLAN.md`), a release checklist that
gates on accepted stories rather than code-complete (`docs/agile/
RELEASE_CHECKLIST.md`), a documented catalogue of eight failure modes with the
evidence that exposed each (`docs/agentic/recurring-failures.md`), a structured
task inventory with machine-checkable verification steps
(`feature_list.json`), and — as of this week — an eight-track, evidence-gated
research pass that corrected its own premise twice before writing a
recommendation (`docs/research/2026-09-08/`). Read together with `git log`,
these documents let a careful reader reconstruct the actual arc: vibe-coded
sprints (Feb–Mar), a stall (Apr), a PRD-and-agile-planning pass for the agent
overhaul (Jun), a five-week harness-engineering peak (Jul, 186 commits), then a
shift to research-before-build discipline (Sep). That arc is real and it is in
the repo — nobody has to take the owner's word for it.

Three things undercut that record, and all three are demonstrable rather than
argued:

1. **The narrative logs stopped, and the structured ones didn't.**
   `docs/agentic/progress.md`, `docs/features/TASK_LIST.md`'s Session Notes,
   and the sprint `STANDUP.md`/`RETRO.md` pair all go silent between
   2026-07-28 and 2026-07-30 — precisely the window before the project's two
   worst-documented bugs (the backup-restore 400 and the credential-leaking
   download, both now the lead example in `recurring-failures.md` #1) were
   found and fixed. `feature_list.json` and `git log` both stayed current
   through that window and past it. The mechanically-checked artifact survived
   the abandonment the hand-written one did not — see §5.
2. **Two of the report's most specific, most checkable claims have no repo
   evidence, and one of the underlying features doesn't exist to have been
   exercised.** No `.claude/agents/`, no hooks, no `settings.json` anywhere in
   the repo — so the Technical Companion's PreToolUse PHI-blocking hook and
   the Final Report's Ralph-style RAG parameter-sweep campaign are unfalsifiable
   as written. See §2 and the gap table.
3. **A generated navigation layer the top-level docs point readers to doesn't
   exist yet.** `openwiki/README.md` says so itself ("Status: still not
   generated"), but `CLAUDE.md` §"OpenWiki usage" reads as if it does. Low
   stakes, same shape of problem as #1 and #2: a doc asserting a state nobody
   re-checked.

None of this is disqualifying — a research artifact with visible gaps and an
honest accounting of them is closer to what the project claims to be than a
research artifact that hides them. The recommendations in §4 are sized to that
reading: closing gaps that are cheap to close and dangerous to leave (the PDF
reports are invisible to anyone browsing the repo; there is no ADR log despite
a skill that assumes one), and explicitly declining to build anything whose
maintenance cost this project has already shown it will not pay.

---

## 1. Audit of what already evidences the journey

### `docs/agentic/progress.md` — session log with verification evidence, abandoned mid-project

`docs/agentic/progress.md:1` describes itself as "Session-by-session record of
agent work: what changed, what was verified, what failed, and the next
priority... Newest entries first." What it actually contains is three dated
entries (`progress.md:5`, `:34`, `:57`), the newest being **2026-07-30 — HC-M10
stage 3: the product is Asclexis**. Each entry that exists is genuinely strong
evidence — it names exact commands run (`python3 scripts/agent_eval_gate.py`),
exact results (`74 cases; groundedness/citation/abstention 1.0`), and exact
test counts (`726 passed, 0 failed`), which is precisely the "evidence, not
belief" standard `AGENT.md`'s Definition of Done demands.

But `git log --format="%ad" --date=short | awk '$1 > "2026-07-30"' | wc -l`
shows **36 commits dated 2026-07-31 through 2026-09-08** — the backup-restore
security fixes (`30d5272
fix(backup): a scoped backup restored as a whole install deletes every other
profile`, `c4ef941 fix(backup): scope the master DB when the backup is created,
not when it is downloaded`), the full Asclexis rename, the creation of
`recurring-failures.md` itself, the three later doc-correction commits
(`7897e47 docs: fix three false claims found in verification`), and the entire
2026-09-08 eight-track research pass — none of which produced a `progress.md`
entry. A reader who trusts the file's own "newest entries first" framing would
believe the project stopped 40 days before it actually did, and would miss the
single most citable episode in the whole repo (a green test suite coexisting
with a data leak, caught and fixed with full before/after commands) because it
is narrated in `recurring-failures.md` and in commit messages, but not here.

### `docs/features/TASK_LIST.md` — Session Notes, same pattern

`AGENT.md`'s Definition of Done tells every agent to log non-trivial work "in
`docs/features/TASK_LIST.md` Session Notes." `grep -n "^### " docs/features/
TASK_LIST.md` shows the latest dated entry is **`### 2026-07-28 — Citation
click-through, backup UX, and running the e2e suite`** (`TASK_LIST.md:753`).
Same 40-day-plus gap as `progress.md`, same cause: the file only updates when
a session remembers to hand-write an entry, and enough sessions since have not.

### `docs/agile/` — the strongest single artifact in the repo, with a live broken link

`docs/agile/AGILE_PLAN.md` is not aspirational process theater. It names a real
branch (`fix/agent-overhaul`, later reconciled in `GROUNDING.md` to the actual
working branch), defines DoR/DoD in one paragraph, lays out three releases
across eight sprints with story points, and — critically — its companion
`RELEASE_CHECKLIST.md` gates each Report-0 dimension `[x]`/`[~]`/`[ ]` **on an
accepted story and a named test**, not on "looks done." Row 7's own status is
the best evidence the checklist is not rubber-stamped: it stays `[~]` because
"today's test only asserts the metric is surfaced... not that it clears the
+50% bar against the legacy path under load" (`RELEASE_CHECKLIST.md`, row 7) —
the checklist author refused to mark a row done on partial evidence, in a
document nobody but the same author would ever audit. That is exactly the
discipline `CLAUDE.md` §4 asks for, demonstrated rather than claimed.

The gap: `AGILE_PLAN.md:50` and `:53` tell the reader the daily/weekly record
lives at `docs/agile/STANDUP.md` and `RETRO.md`. Those files no longer exist at
that path — they were moved to `docs/archive/agile/STANDUP.md` and `RETRO.md`,
each now headed "Historical Reference: this is a point-in-time snapshot
retained for history and is not an active tracker." `python3 scripts/
docs_lint.py` reports clean (`Docs lint passed.`) because the references in
`AGILE_PLAN.md` are inline code spans, not markdown links, so the link
checker has nothing to walk. This is a small, low-stakes instance of
`recurring-failures.md` #6 ("documented commands nobody ran") — a path quoted
in prose that a mechanical check cannot see is stale.

Content-wise the archived `STANDUP.md`/`RETRO.md` are excellent artifacts in
their own right: `docs/archive/agile/RETRO.md`'s final entry documents the S6
close-out with a specific "Keep" bullet about *why* the eval gate was written
as a standalone script rather than a pytest fixture (so it could be proven
green independent of whether the CI wrapper ever got approved) — a real
design rationale, not a status update.

### `feature_list.json` — the artifact that stayed current

`feature_list.json:1`'s own header states the rule that makes it different
from the narrative logs: `"Never mark completed without running the
verification_steps; record outcomes in docs/agentic/progress.md."` The
`status` field is checked by nothing external — it is manually set — but it
demonstrably kept moving after the narrative logs stopped: `HC-M12` through
`HC-M24` (record-intelligence, comprehension, workspace, interoperability, and
the agent work itself — 13 features) all show `"status": "completed"`, and the
commits implementing them (the `HC-M*` branch names visible throughout
`TASK_LIST.md` and `git log`) postdate `progress.md`'s last entry. Total: 27
features, 18 completed, 8 pending, 1 in-progress
(`python3 -c "import json,collections; ..."` on `feature_list.json`, run this
session). What it proves to a reader: task-level intent and completion state,
kept in sync with reality more reliably than the prose logs — but it proves
*that* work happened, not *how*; there is no verification-command evidence
attached to most `HC-M12`–`HC-M24` rows the way `progress.md`'s three entries
carry for `HC-M05`.

### `docs/agentic/recurring-failures.md` — the sharpest artifact in the repo

Eight entries, each following the same shape: what shipped, the evidence that
caught it, and a recheck phrased as a command rather than an opinion. This is
the one document in the repo that a skeptical reader cannot dismiss as
after-the-fact narrative, because entry #1 documents a **security
vulnerability that shipped** (a backup download exposing every other
profile's password hash) alongside 32 passing tests, and names exactly why the
tests were structurally blind to it ("called the handler as a plain function,
and FastAPI's dependency graph never ran"). Entry #8 turns the lens on the
document's own genre: a stale rename-audit rationale stood "unchallenged for
weeks because it was written down," and a 2026-09-08 near-miss (this
directory's own STATUS.md) shows the pattern recurring within days of being
named. This is the artifact this track is explicitly designed not to become —
see §5.

Where it falls short as a *demonstration* artifact specifically: it proves
rigor about **product** bugs almost exclusively. Only entry #8's last
paragraph turns the same lens on a **process** document (a stale research
recommendation). Nothing in the file yet documents a harness-engineering
mistake — a bad hook, a subagent given too much scope, an eval gate that
passed while measuring the wrong thing — because (per §2) the repo has not
actually shipped hooks or subagents to fail in that way.

### The CI eval gate — real, narrow, and honestly scoped

`.github/workflows/ci.yml` runs six jobs (`docs-lint`, `backend-tests`,
`frontend-tests`, `security-scan`, `agent-evals`, `e2e-tests`) —
`agent-evals` (`ci.yml:112`) invokes `python3 scripts/agent_eval_gate.py`
(`ci.yml:129`), which scores 74 golden cases across six axes including
`injection_resistance` and `phi_leakage` (`00-brief.md` §2; `modules/agent/
eval/scorer.py`, 488 lines). This is a genuine, mechanically-enforced
demonstration of AI-safety practice — a PR that regresses groundedness or
reintroduces advice leakage goes red without a human having to notice. Its
scope is exactly as narrow as `docs/agentic/evals.md` states and no narrower:
it gates the **agent's answer-composition behavior**, not extraction quality
(`HC-M06`, the "flagship Data Science artifact" per `roadmap.md`, is still
`"status": "pending"` in `feature_list.json`) and not the RAG retrieval
pipeline's own parameter space (see §2 — there is no sweep of that space to
gate in the first place).

### This research directory itself

`docs/research/2026-09-08/` is, as of this session, the newest and most
self-aware process artifact in the repo. `PLAN.md` §9 ("Execution record")
documents its own failure modes as they happened — five of eight researchers
hit an account rate limit mid-run, and the orchestrator verified each
document was complete before trusting it rather than re-running or
reconstructing from a summary (`PLAN.md:264-270`). `STATUS.md` is a
purpose-built reconciliation layer that exists specifically to prevent
`recurring-failures.md` #8 from recurring on this directory's own
recommendations — and, per its own text, catches a near-miss within the same
session (the `sanitize_untrusted_field` recommendation two tracks converged
on and the orchestrator rejected). This is the pattern a "workflow-iteration
record" (§4) should generalize, not something to build from scratch —
see the "make it self-maintaining" recommendation.

---

## 2. Gaps between claim and evidence

Verified this session, each independently:

**`.claude/agents/` does not exist.** `find .claude -maxdepth 3 -type d` lists
only `.claude/skills/` and its 32 top-level skill subdirectories; `ls .claude/agents` errors
`No such file or directory`. `docs/agentic/harness.md:25` states "Subagent
definitions live in `.claude/agents/`. Use them to keep exploration noise out
of the main context" and goes on to name four specific subagents by role
(`docs-consistency-scanner`, `dependency-policy-auditor`,
`agentic-roadmap-researcher`, `verification-engineer`, `windows-bootstrap-
engineer`) — none of which exist as files anywhere in the repo (`find . -iname
"*consistency-scanner*" -o -iname "*policy-auditor*"` etc. all return
nothing). The document describes a subagent architecture in the present tense
that the repo does not contain.

**No hooks, no `settings.json`, anywhere.** `find / -maxdepth 6 -iname
"settings.json"` (excluding `node_modules`) returns nothing; the only hits for
`hook` in the whole tree are `src/frontend/src/hooks` (an ordinary React
hooks directory) and prose mentions inside skill/doc files. `.mcp.json`
configures exactly one MCP server — `serena`, for code navigation — and
nothing else. There is no `PreToolUse`/`PostToolUse` configuration, no
`AgentShield`, no secret-scanner, no PHI-pattern scanner wired to a tool-call
lifecycle event anywhere in this repo.

**The Technical Companion's specific claim is checkable, and fails.** §4.6
("How HealthCentral used ECC"), verbatim: *"AgentShield was wired as a
PreToolUse hook scanning every edit for PHI patterns; any tool call that would
emit identifiable medical data onto a network interface is blocked before it
runs."* `grep -rli "agentshield" .` (excluding `node_modules`) returns zero
files. No hook exists to wire. This is not "unverifiable" — it is
demonstrably absent.

**The Final Report's §7.2 claim is the same claim from a different angle.**
Verbatim: *"A PreToolUse hook scans for patterns that look like PHI and
blocks any tool call that would send them to a network."* Same finding: no
hook, no settings.json declaring one, no PHI-pattern scanner outside the
product code's own `modules/redaction.py` (which is a Python module the
*backend* calls on export paths — a real and well-tested guarantee, see
`docs/agentic/evals.md` item 7 — but it is not a Claude-Code-harness hook, and
it does not gate tool calls).

**The Ralph-style RAG evaluation sweep has no artifact, and the swept
parameter doesn't exist as a feature.** Final Report §7.3, verbatim: *"RAG
quality is a multi-dimensional problem: chunk size, embedding model, retrieval
threshold, reranking, citation style. A Ralph-style autonomous loop ran
overnight across a matrix of configurations... and summarized the Pareto
frontier by morning."* Checked: `grep -rln -i "rerank" src/backend --include
*.py` returns nothing — there is no reranking stage in `modules/rag.py` to
have swept on/off. `grep -rn "chunk_size" modules/rag.py` returns nothing (the
chunking parameter the claim names as swept is not itself a named, tunable
config value in the retrieval module). No `docs/agentic/eval-cards/` directory
exists (confirmed: `find docs -iname "*eval-card*"` empty), and `HC-M06` — the
feature that would produce exactly this kind of measured artifact — is
`"status": "pending"` in `feature_list.json`. This is the strongest gap in
this section because it is checkable two ways at once: no result artifact,
and no underlying feature to have produced one.

**The superpowers claim is the counter-example — it *is* evidenced.**
Technical Companion §6.5 claims superpowers was used for "the SQLCipher
encryption layer and the JWT auth module," with a specific caught bug (a
unique-IV generator with a mis-imported entropy source). The workflow claim
generalizes and checks out: `.claude/skills/README.md` documents real,
attributed vendoring of `obra/superpowers` (14 skills, MIT license, unmodified)
and `mattpocock/skills` (18 skills, pinned to commit `3cca18b`), and
`docs/superpowers/specs/` and `docs/superpowers/plans/` contain real,
dated design docs in exactly the format §6.2 of the report describes (a
`YYYY-MM-DD-topic-design.md` written and approved before implementation, e.g.
`docs/superpowers/specs/2026-05-11-dynamic-port-selection-design.md`). The
specific bug anecdote, however, does not: no commit message, design doc, or
`docs/plans/` entry anywhere in the repo mentions IV reuse, a mis-imported
entropy source, or a rejected Spec Reviewer pass on the crypto layer (`grep
-rln -i "unique.iv\|entropy source"` finds one unrelated hit, about a
recovery-code feature's entropy source, in a different context). Read
generously, the anecdote may be a compressed or fictionalized illustration of
the *kind* of bug a two-stage review catches, layered onto a genuinely real
practice — but as written it reads as a specific, dated claim, and the repo
does not back the specifics.

**Cross-vendor adversarial review (Codex) is a described practice, not a
repo artifact.** Final Report §7.1 describes a Claude-plans/Codex-reviews
loop that caught "a JWT leak in a log line" among other bugs. `grep -rln -i
codex` across the repo (excluding `node_modules` and this research directory)
finds only generic tooling references inside vendored skill files (`.claude/
skills/using-superpowers/references/codex-tools.md` — a reference doc for
using the Codex CLI, not a record of it having reviewed this codebase). No PR,
commit, or doc records a specific Codex review pass on Asclexis. Consistent
with this: `docs/research/2026-09-08/FRONTIER-AUDIT-PROMPT.md` is a prompt
pack **for** handing this research to "Claude Fable 5.1 or GPT-6 Astra" —
i.e., the project is currently building the capability to do this, not
retroactively documenting having done it in the past. Fine to plan; not fine
to claim as history.

**OpenWiki is described as existing and does not, by its own admission.**
`CLAUDE.md` §"OpenWiki usage": *"Generated repo-navigation docs live in
`openwiki/`. Use them to locate code, trace dependencies..."* — present
tense. `openwiki/README.md` itself: *"Status: still not generated (as of
2026-07-27). Wiki content has not been produced; only this hand-written README
exists..."* `AGENT.md`'s own line about it (`AGENT.md`, "Generated repo map"
row) correctly hedges with "Advisory only," but doesn't flag that there is, in
fact, nothing generated yet. Lowest-stakes gap in this list, but same shape as
the others: a doc's present tense outran the repo's actual state, and nothing
re-checks it.

**No ADR log exists, despite a skill that assumes the convention.**
`.claude/skills/domain-modeling/SKILL.md:3` — "Use when discussing codebase
terminology, writing or editing a CONTEXT.md, or recording or editing an
ADR" — and lines 18/30/34/37 give a directory layout with `docs/adr/`. `find .
-iname "CONTEXT.md"` and `find . -iname "*ADR*"` (excluding the skill's own
files) return nothing. The skill is available and would create these lazily
per its own instructions (line 40: "Create files lazily... If no `docs/adr/`
exists, create it when the first ADR is needed") — no session has needed one
yet, or no session has reached for the skill at a decision point. Either way,
zero ADRs exist for a project that has made a large number of real,
reversible-in-principle architecture decisions (rename to Asclexis, dual
Alembic chains, agent read-only-by-design, `ModelRunner` facade) that are
currently recorded only as prose inside dated plan files, not as a
navigable, one-decision-per-file log.

**The two CS4610 PDF reports are invisible to a repo browser.**
`CS4610_Report_Demo/` contains both PDFs plus their source `.docx` files (and
two stray lock files — `.~lock.*.docx#` and `~$...docx` — left by an editor,
which are not reports and should not ship). No README in that directory, no
link from the top-level `README.md`, `AGENT.md`, or `docs/INDEX.md` (confirmed
by grep: the only in-repo references to "CS4610" or "Technical Companion" are
inside `docs/research/2026-09-08/00-brief.md` and `PLAN.md`, which assume the
reader already knows what they are). A reader who does not already know these
reports exist — the exact "hiring manager, collaborator, future maintainer"
this track is written for — has no way to discover them by browsing the repo.

### Gap table

| Claim | Source | Repo evidence checked | Verdict |
|---|---|---|---|
| Subagent definitions live in `.claude/agents/`, incl. named scanners (`docs-consistency-scanner` etc.) | `docs/agentic/harness.md:25` and surrounding text | `find .claude -maxdepth 3 -type d`; `find . -iname "*consistency-scanner*"` etc. | **No evidence.** Directory and named files do not exist anywhere in the repo. |
| AgentShield wired as a PreToolUse hook blocking PHI-bearing tool calls | Technical Companion §4.6 | `find` for `settings.json`/hooks (none); `grep -rli agentshield .` (zero hits) | **No evidence.** No hook mechanism exists in the repo at all. |
| A PreToolUse hook scans for PHI patterns and blocks network-bound tool calls | Final Report §7.2 | Same as above | **No evidence.** Same finding, second report. |
| Ralph-style overnight RAG parameter sweep (chunk size, embedding model, reranker on/off) summarizing a Pareto frontier | Final Report §7.3 | `grep -rln -i rerank src/backend`; `grep -rn chunk_size modules/rag.py`; `find docs -iname "*eval-card*"`; `feature_list.json` HC-M06 status | **No evidence, and the swept feature (reranking) doesn't exist to have been swept.** |
| Superpowers used for SQLCipher/JWT modules; specific unique-IV entropy bug caught by two-stage review | Technical Companion §6.5 | `.claude/skills/README.md`, `docs/superpowers/{specs,plans}/`; `grep -rln -i "unique.iv\|entropy source"` | **Workflow claim evidenced** (real vendored skills, real dated design docs in the described format). **Specific bug anecdote not evidenced** — no matching commit, design doc, or plan entry anywhere. |
| Cross-vendor adversarial review (Claude plans, Codex reviews) caught specific bugs incl. a JWT log leak | Final Report §7.1 | `grep -rln -i codex .` (only generic tooling refs in vendored skill docs); `FRONTIER-AUDIT-PROMPT.md` (forward-looking, not retrospective) | **No repo evidence of a completed pass.** The capability is being built now (`FRONTIER-AUDIT-PROMPT.md`), not documented as having happened. |
| Generated repo-navigation docs live in `openwiki/` | `CLAUDE.md` §"OpenWiki usage" | `openwiki/README.md` | **Contradicted by the file itself** — "Status: still not generated." |
| A `docs/agile/STANDUP.md` / `RETRO.md` pair is the active daily/weekly record | `docs/agile/AGILE_PLAN.md:50,53` | `ls docs/agile/STANDUP.md` (not found); files exist at `docs/archive/agile/` instead, headed "not an active tracker" | **Stale path.** Content exists and is good; the pointer in the plan that's supposed to still be live is wrong, and `docs_lint.py` cannot catch it (inline code span, not a markdown link). |

---

## 3. How comparable work demonstrates process (external research)

Findings below are from `WebSearch` this session (September 2026); `WebFetch`
against `arxiv.org` was blocked by this environment's egress proxy for the two
most relevant papers, so those two are cited from search-result summaries with
URLs rather than full-text quotes — flagged inline.

**Architecture Decision Records remain the standard unit for "why," not
"what."** The MADR (Markdown Any Decision Records) format is the
still-current reference implementation — one file per decision, a dated
filename (`YYYYMMDD-decision-title.md`), and an explicit "Considered Options"
section listing rejected alternatives with their pros/cons, not just the
chosen one ([adr.github.io](https://adr.github.io/); [MADR project via
GitHub topics](https://github.com/topics/architectural-decision-records)).
The dated-filename-plus-alternatives-considered shape is exactly what this
repo's `docs/superpowers/specs/` design docs already do informally (each
carries a date, a Problem/Goal/Approach structure) — the gap is only that
there is no single indexed *log* of decisions distinct from the design docs
that happen to record them.

**"Eval cards" and "rollout cards" are the 2026 answer to the same problem
`recurring-failures.md` names: a headline number without the conditions
behind it.** Two arXiv papers from May–June 2026 formalize this:

- *Evaluation Cards: An Interpretive Layer for AI Evaluation Reporting*
  (arXiv 2606.09809) proposes a reporting schema built around four
  interpretive signals — **reproducibility, documentation completeness,
  provenance and risk, and score comparability** — derived from a review of
  52 papers and stakeholder interviews, now implemented as a live layer under
  Hugging Face's EvalEval initiative
  ([huggingface.co/blog/evaleval/evaluation-cards-launch](https://huggingface.co/blog/evaleval/evaluation-cards-launch);
  [evaleval-general-eval-card.hf.space/about](https://evaleval-general-eval-card.hf.space/about)).
  [UNVERIFIED beyond search-result summary — WebFetch to arxiv.org blocked
  this session]
- *Rollout Cards: A Reproducibility Standard for Agent Research* (arXiv
  2605.12131) is sharper and more damning: an audit of 50 popular
  agent-training/eval repos found **none** report how many runs failed,
  errored, or were skipped alongside their headline score, and re-grading
  preserved outputs under different-but-defensible reporting rules moved
  scores by up to 20.9 percentage points and inverted model rankings in some
  cases ([arxiv.org/abs/2605.12131](https://arxiv.org/abs/2605.12131)).
  [UNVERIFIED beyond search-result summary — WebFetch blocked]

  This is directly relevant to this repo's own eval gate: `scripts/
  agent_eval_gate.py` reports pass/fail and per-axis scores on 74 cases, but
  (per `evals.md` and `RELEASE_CHECKLIST.md`) does not itself report a
  drops/skips manifest the way a Rollout Card would ask — a smaller-scale
  version of exactly the gap the paper's audit found industry-wide.

**Portfolio and hiring-manager conventions in 2026 have converged on
"show the reasoning, not just the code."** Across multiple sources found this
session: a `DECISIONS.md` documenting *why* a specific technology or
parameter was chosen over the alternatives (the ChromaDB-vs-Pinecone,
chunk-size-1000 example appears verbatim in one source); "hiring managers ...
want to see your reasoning, not just your code"; a "six-component standard"
of story-driven README, architecture diagram, metrics, live demo, **technical
decision log**, and **honest limitations**; and the framing that what's being
evaluated in 2026 is not whether AI was used but "whether you reviewed,
tested, and understood the output" — record what the model proposed, what was
rejected, what was fixed, and why
([dev.to — 5 AI Portfolio Projects That Actually Get You Hired in
2026](https://dev.to/klement_gunndu/5-ai-portfolio-projects-that-actually-get-you-hired-in-2026-5bpl)).
This maps closely onto what `recurring-failures.md` and `RELEASE_CHECKLIST.md`
already do inside this repo for *product* decisions — the gap this track
flags is that no equivalent decision log exists yet for *harness* decisions
(why superpowers over GSD for a given task, why a subagent was or wasn't used,
why an eval axis has the bar it has).

**Practitioner-published session transcripts and pattern catalogues are an
active, ongoing genre, not a one-off.** Simon Willison's "Agentic Engineering
Patterns" project (started February 2026, ongoing as a series of
chapter-shaped posts) documents specific coding-agent practices as they're
discovered, and separately he has published literal AI-tool session
transcripts (e.g., a Codex desktop session's Markdown export) as primary
evidence rather than paraphrasing them
([simonwillison.net/2026/Feb/23/agentic-engineering-patterns](https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/);
[simonw.substack.com/p/agentic-engineering-patterns](https://simonw.substack.com/p/agentic-engineering-patterns)).
The pattern worth borrowing is narrow and cheap: when a real session
transcript already exists (this research pass's own dispatch is one), keep
the primary artifact rather than only a summary of it — which is exactly what
`PLAN.md` §9 already does for this directory's own execution record.

---

## 4. Recommendations

Ordered roughly by effort. "Reader" names who the artifact is *for*, not who
writes it. "Rot risk" is the specific failure mode this artifact will hit if
unmaintained — see §5 for the general argument.

| Artifact | What it proves | Reader | Effort | Rot risk |
|---|---|---|---|---|
| **Move/re-anchor the two PDF reports into the repo's doc graph.** Add a `CS4610_Report_Demo/README.md` (what these are, when, by whom, and their relationship to the live repo — including "some §7 claims about hooks/eval sweeps describe intended or aspirational practice, not what shipped, see Track 10"), link it from the top-level `README.md` and `docs/INDEX.md`, and delete the two stray editor lock files (`.~lock.*.docx#`, `~$...docx`). | The founding "journey" documents exist and are discoverable without prior knowledge; their claims are labeled with the honesty this project asks of everything else. | Hiring manager / collaborator arriving cold. | Low (~30 min). One doc, one link, one delete. | Low — a static pointer to two frozen PDFs has nothing to go stale except the caveat text, and that only needs updating if a claim gets built later (good problem to have). |
| **Reconcile or retract the specific unevidenced claims** (§2): either build the PreToolUse PHI hook and the RAG parameter-sweep artifact for real, or add a short, explicit correction — in the new PDF README above, or a `docs/research/2026-09-08/`-style STATUS note — stating plainly which report claims are aspirational/compressed rather than shipped. | The gap between the two reports' narrative and the repo's actual state stops being something a careful reader has to discover for themselves (as this track just did). | Anyone who reads the reports before the repo, which is most readers. | Low for the correction; Medium–High if actually building the hook (real hooks + `.claude/agents/` + `settings.json` is new harness surface, needs its own design pass and test). | The correction rots if a *later* report or doc repeats the same claim without checking this one first — mitigate by linking forward from `harness.md` itself, not just from this track. |
| **A `docs/adr/` decision log, populated retroactively for the ~6 decisions that already exist in prose** (Asclexis rename rationale, dual Alembic chains, agent read-only-by-design, `ModelRunner` as the sole LLM entry point, redaction-before-egress as a hard invariant, superpowers-over-GSD-by-default for skill routing). Use the MADR shape §3 describes: dated filename, Context, Decision, **Considered Options** (the alternatives actually rejected — e.g. why not route the memory-write risk through `sanitize_untrusted_field`, per `recurring-failures.md` #8's near-miss), Consequences. The `domain-modeling` skill already knows this format and directory layout — this is populating a skill that's present but unused, not adding new tooling. | *Why* the architecture is what it is, in one navigable place, distinct from the plans that happened to record the decision inline. | Future maintainer or collaborator asking "why is it built this way" without reading every dated plan file. | Medium (one afternoon for the retroactive backfill; low incremental cost per new decision going forward since the skill already exists). | High if treated as a one-time backfill and never revisited — an ADR log needs a trigger, not a memory. Mitigation in §5. |
| **A workflow-iteration record: how the harness itself changed, as its own dated log** (new file, e.g. `docs/agentic/harness-history.md`, or a "Changelog" section appended to `harness.md`). Not a restatement of `progress.md` — a narrower log of harness-shape changes specifically: when subagents were added/removed from `harness.md`'s own description and why, when a skill set was vendored (`.claude/skills/README.md` already has the "vendored 2026-09-08, commit `3cca18b`" pattern — generalize it), when an eval axis was added to the gate and what golden case forced it. | The Track-9/10 thesis directly: that the *process of building the harness* iterated, not just the product. This is the one artifact on this list with no existing substitute anywhere in the repo. | Hiring manager evaluating "harness engineering" as a skill, per `roadmap.md`'s own portfolio-relevance table. | Medium to start (reconstruct the history that already happened from git log + existing docs — most of the raw material is already in this track's §1); low per-entry going forward if entries are required at the same commit that changes the harness. | High unless tied to a mechanical trigger — see the `.claude/skills/README.md` vendoring-date pattern as the model: record the fact *in the file the change touches*, at the moment of the change, not in a separate log someone has to remember to update. |
| **Make `progress.md` (or its replacement) self-maintaining rather than hand-written prose.** Concretely: stop asking free-form "narrate your session" and instead require each session to append a **fixed-shape** entry — feature ID(s) touched, verification commands run, their actual output, next-priority — generated at the same moment `feature_list.json`'s status field is flipped, ideally by the same commit. `AGENT.md`'s Definition of Done already requires the commands-and-output; the fix is making the log entry mechanically bundled with the status flip, not a separate remembered step. | That the process is still live and evidenced *today*, closing the exact 40-day gap found in §1. | Anyone checking "is this project still being worked the way it claims," including the owner in six months. | Low–Medium: this is a discipline/template change, not new tooling — a short addition to `harness.md`'s step 5 and `AGENT.md`'s Definition of Done, pointing at a fixed entry template. | This is the artifact most likely to rot exactly as it already has, twice (`progress.md`, `TASK_LIST.md` Session Notes) — because it depends on a session *remembering* a step disconnected from the commit itself. §5 explains why bundling beats reminding. |
| **A single `docs/agentic/eval-cards/` entry for the existing agent eval gate**, before building the (still-pending) `HC-M06` extraction eval card. Apply the two frameworks from §3 even in miniature: report not just the 74-case pass/fail but what's *not* covered (extraction quality, the RAG retrieval parameter space §2 shows was never swept), and a drops/skips count for the golden set the way a Rollout Card would ask. | That "74 golden cases, 6 axes, all green" is read with the same "green suite is evidence, not proof" skepticism `recurring-failures.md` #1 demands of everything else in the repo. | A technically literate reader (collaborator, eval-literate hiring manager) deciding how much to trust the CI gate. | Low–Medium: the scoring code (`modules/agent/eval/scorer.py`) already computes everything needed; this is presentation and an honest "not covered" section, not new measurement. | Medium — an eval card rots the way any dashboard does, by silently going stale after the axes or golden-set size change. Mitigate by generating the numbers section from `agent_eval_gate.py`'s own output (a script appends to the card; a human writes only the qualitative "what this doesn't cover" prose), so the numbers can't drift from the gate. |
| **A short, explicitly-dated "how this was built" narrative doc** synthesizing the arc: vibe coding → PRD/agile planning (`docs/agile/`) → harness engineering (`docs/superpowers/`, this repo's July peak) → research-before-build discipline (`docs/research/2026-09-08/`) — with the two CS4610 PDFs as its primary citations and this track's gap table as its correction layer. | The single legible narrative a hiring manager or collaborator wants in five minutes, that today requires reading `AGENT.md`, `docs/agile/`, `docs/superpowers/`, and this directory to reconstruct. | Hiring manager / collaborator, first five minutes. | Medium: mostly synthesis of what already exists in this track and `PLAN.md`, but needs care to avoid becoming a second copy of the reports' claims without the same correction discipline. | Highest risk on this list — a narrative doc is the most tempting thing to write once and never revisit, and precisely the "stale guidance that reads as authority" shape `recurring-failures.md` #8 names. Only build this *after* the eval-card and workflow-iteration-record above exist, and make it explicitly point at those as its live sources rather than restating their numbers inline. |

**Deliberately not itemized as a separate recommendation:** `.claude/agents/`,
hooks, and `settings.json` themselves. Building the actual PreToolUse hook the
reports describe is real harness work — new attack surface on a repo whose
own `CLAUDE.md` requires asking before touching anything auth/encryption- or
safety-adjacent — not a documentation task, and it is out of this track's
read-only, docs-only scope. If the owner wants to close that specific gap by
building rather than correcting the claim, it should go through
`writing-plans`/`brainstorming` like any other feature, not get scaffolded
into existence to satisfy a report.

---

## 5. What NOT to build, and what makes an artifact self-maintaining

**Do not build a second narrative log parallel to `feature_list.json`.** This
repo has already run that experiment twice (`progress.md`, `TASK_LIST.md`
Session Notes) and both went silent at the same point for the same reason:
free-form prose that lives in a file separate from the change it describes
depends on a session remembering an extra step with no mechanical consequence
for skipping it. `feature_list.json` didn't survive because it's more
important — it survived because flipping its `status` field is *part of*
finishing the task (per `AGENT.md`'s Definition of Done and `harness.md`
step 5), not a follow-up chore. Any new artifact in §4 that repeats the
free-standing-log shape (a workflow-history file, a self-maintaining
`progress.md`) will rot the same way unless it is bundled into the same
commit/PR as the change it records, not appended after.

**Do not write the "how this was built" narrative doc first.** It is the
single most rot-prone item in §4 by its own entry, and this project has
first-hand evidence of exactly this failure mode: `recurring-failures.md` #8
documents a rename-audit rationale that stood "unchallenged for weeks because
it was written down," and a research-recommendation near-miss in the same
document that happened *within days* of the pattern being named. A synthesis
narrative written before the eval card and workflow-iteration record exist
would have nothing live to cite and would ossify into exactly that kind of
unchecked authority. Sequence it last, and make it point at the other
artifacts as sources rather than duplicating their content.

**Do not treat the ADR log as a one-time backfill.** A domain-modeling skill
that already knows the ADR format and directory convention exists in this
repo and has apparently never been invoked for that purpose in eight months of
active development — that is itself evidence that "available but not
mandatory" does not produce the artifact. If the owner wants a live ADR log
rather than a decorative one, the trigger needs to be structural: e.g., the
`writing-plans` or `brainstorming` skill's own template gets a line asking
"does this decision need an ADR" the way `RELEASE_CHECKLIST.md` already asks
"does this row have a backing story," not a hope that a future session
remembers the skill exists.

**Do not add process documentation as a gate that blocks merges.** Everything
in §4 is additive narrative or retrospective structure; none of it should
become a CI check the way `agent_eval_gate.py` or `docs_lint.py` are, because
the moment "did you update the ADR log" becomes a merge gate, it becomes
exactly the kind of check `recurring-failures.md` #1 warns about — one that
can be satisfied mechanically (an empty or copy-pasted entry) without being
true. The self-maintaining trick that works elsewhere in this repo
(`docs_lint.py` checking link integrity, `generate_docs_index.py --check`
catching drift) works because it verifies a *mechanical* property (does this
link resolve, is this file listed) — it would not work for verifying that a
decision record's *reasoning* is honest, which is the entire value of an ADR.

**The general rule, stated once:** every hand-written process artifact in
this repo that survived is one where the record-keeping step is the same
motion as the work (`feature_list.json`'s status flip, a `RELEASE_CHECKLIST.md`
row that literally cannot flip to `[x]` without naming the test that proves
it, `.claude/skills/README.md`'s one-line vendoring-date note added at the
moment of vendoring). Every one that didn't survive (`progress.md`,
`TASK_LIST.md` Session Notes, `STANDUP.md`/`RETRO.md`) was a *second* step,
temporally and physically separate from the commit it described, that
depended on being remembered. Any recommendation in §4 should be read against
that rule before being built.

---

## Sources

Repo (all verified this session, `path:line` or the command that found it —
commands quoted in §1/§2 bodies):

- `docs/research/2026-09-08/STATUS.md`, `00-brief.md`, `PLAN.md`, `09-roadmap.md`
- `docs/agentic/{roadmap,harness,progress,evals,mcp-tools,recurring-failures}.md`
- `README.md`, `AGENT.md`, `CLAUDE.md`, `.mcp.json`
- `feature_list.json`, `docs/features/TASK_LIST.md`
- `docs/agile/{AGILE_PLAN,GROUNDING,RELEASE_CHECKLIST}.md`, `docs/agile/sprints/SPRINT_7.md`
- `docs/archive/agile/{STANDUP,RETRO}.md`
- `docs/superpowers/{specs,plans}/*`
- `.claude/skills/README.md`, `.claude/skills/domain-modeling/SKILL.md`
- `skills/README.md`
- `openwiki/README.md`
- `.github/workflows/ci.yml`, `scripts/agent_eval_gate.py`, `modules/agent/eval/scorer.py`
- `CS4610_Report_Demo/HealthCentral_CS4610_Technical_Companion.{pdf,docx}` (§4.6,
  §6.5, §7)
- `CS4610_Report_Demo/HealthCentral_CS4610_Final_Report.{pdf,docx}` (§7.1–7.3)
- `git log` (300 commits total, 2026-02-23 to 2026-09-09; monthly distribution
  and the 2026-07-31–2026-09-08 commit list quoted in §1)

External (WebSearch, September 2026; two arXiv fetches blocked by this
session's egress proxy, marked inline):

- [Architectural Decision Records (adr.github.io)](https://adr.github.io/)
- [architectural-decision-records · GitHub Topics](https://github.com/topics/architectural-decision-records)
- [Evaluation Cards: An Interpretive Layer for AI Evaluation Reporting (arXiv 2606.09809)](https://arxiv.org/abs/2606.09809) [UNVERIFIED — full text not fetchable this session]
- [Introducing Evaluation Cards (Hugging Face / EvalEval)](https://huggingface.co/blog/evaleval/evaluation-cards-launch)
- [Evaluation Cards — a reporting layer for AI evaluations](https://evaleval-general-eval-card.hf.space/about)
- [Rollout Cards: A Reproducibility Standard for Agent Research (arXiv 2605.12131)](https://arxiv.org/abs/2605.12131) [UNVERIFIED — full text not fetchable this session]
- [Simon Willison — Writing about Agentic Engineering Patterns](https://simonwillison.net/2026/Feb/23/agentic-engineering-patterns/)
- [Simon Willison — Agentic Engineering Patterns (Substack)](https://simonw.substack.com/p/agentic-engineering-patterns)
- [5 AI Portfolio Projects That Actually Get You Hired in 2026 (dev.to)](https://dev.to/klement_gunndu/5-ai-portfolio-projects-that-actually-get-you-hired-in-2026-5bpl)
