# Handoff Prompt — Critical Review of Asclexis Planning & Research Package

Paste into a fresh high-reasoning agent session (Opus-class or equivalent —
this task rewards skepticism and verification rigor over speed).

---

<role>
You are an adversarial reviewer, not an executor. A previous orchestrator
produced an audit, eight implementation plans, four research scouting docs,
and a capstone knowledge base for the Asclexis repository. Your job is to
determine whether that package is trustworthy enough to execute against —
and to say precisely where it is not. You fix nothing, change nothing,
commit nothing.
</role>

<objective>
Produce a single review report that answers, with evidence:

1. Which documents are sound enough to act on as written?
2. Which contain errors, stale data, overclaims, or internal contradictions
   — and exactly where (file + line + quoted text)?
3. Which verdicts and plans lack the evidence they claim to rest on?
4. What is missing entirely (unasked questions, unchecked assumptions,
   unhandled dependencies between plans)?
</objective>

<context>
Repo: /mnt/c/Users/DangT/Documents/GitHub/HealthCentral (branch main).
The package under review lives in `audit/2026-09-25/` (untracked) and
`docs/capstone-report/` (untracked). The owner intends to execute the
plans and cite the research in a CS4610 capstone report — errors that
survive review become published claims.
</context>

<goal>
If your environment supports a `/goal` command, run it with this exact text;
otherwise treat this block as your task charter:

/goal Critically review the complete planning-and-research package produced
for Asclexis on 2026-09-25/26 — the audit report, both handoff prompts, all
eight implementation plans, and the entire docs/capstone-report/ knowledge
base (index, original goal, claims ledger, report outline, four research
scouting docs). Verify every load-bearing claim against the live repository
and its cited sources; challenge each verdict against its evidence; map plan
ordering and dependencies; and deliver a severity-graded findings report at
audit/2026-09-25/review/ that states which documents are execution-ready
as written and which require revision. Read-only: fix nothing.
</goal>

<scope_inventory>
All markdown created in the authoring session — review every one:

**Audit bundle (`audit/2026-09-25/`, untracked):**
1. `Devin-Audit-report.md` — 23-section audit + owner Q&A (§21) +
   orchestrator handoff (§22) + plans index (§23)
2. `handoff-prompt-claude-orchestrator.md` — the /goal planning prompt
3. `handoff-prompt-review-agent.md` — this prompt (self-review optional)
4. `plans/01-merge-branches.md`
5. `plans/02-notification-scheduler.md`
6. `plans/03-phantom-layer.md`
7. `plans/04-doc-drift-sweep.md`
8. `plans/05-utcnow-migration.md`
9. `plans/06-sql-fk-audit.md`
10. `plans/07-test-reset-tables.md`
11. `plans/08-gated-items-review-packet.md`

**Capstone knowledge base (`docs/capstone-report/`, untracked):**
12. `README.md` — KB index + open threads
13. `00-original-goal.md` — product + research thesis
14. `claims-ledger.md` — 20 claims ↔ evidence ↔ verdict
15. `report-outline.md` — 10-section report skeleton
16. `research/README.md` — research index
17. `research/01-agentic-swe-tools.md` — 11 entries (Jev/Laya resolution)
18. `research/02-harness-techniques.md` — 17 entries
19. `research/03-rag-local-llm.md` — 16 entries (3 UNVERIFIED)
20. `research/04-papers-evals.md` — 39 entries

**Reference context (pre-existing, read but not under review):**
`CLAUDE.md`, `AGENT.md`, `docs/agentic/recurring-failures.md`,
`audit/2026-09-25/asclexis-showcase.html` (claims in it vs. reality — check
its status assertions, e.g. "8 plans written", against the actual files).
</scope_inventory>

<read_first>
In this order — do not skip:

1. `CLAUDE.md`, `AGENT.md` — the invariants every document must respect
2. `audit/2026-09-25/Devin-Audit-report.md` — the source audit (note §21
   owner answers, §23 plans index)
3. All eight `audit/2026-09-25/plans/0N-*.md`
4. `docs/capstone-report/README.md`, `00-original-goal.md`,
   `claims-ledger.md`, `report-outline.md`
5. All four `docs/capstone-report/research/0N-*.md`
6. `docs/agentic/recurring-failures.md` — the repo's own failure-mode list;
   check whether the package repeats any
</read_first>

<review_criteria>
Apply each criterion to every document; cite instances.

**C1 — Evidence reality.** Plans assert file paths, symbols, line numbers,
and counts. Spot-check a sample per plan (≥5 anchors per document): does
the named file exist? Does the symbol exist at the stated location? Is the
count correct *today* (e.g., re-run a `grep -c`)? A plan citing phantom
locations is a failure.

**C2 — Internal consistency.** Do documents contradict each other? Known
candidates to verify, plus find your own: audit's test baseline vs plans'
re-measured counts; audit §17 file lists vs merge plan's conflict set;
research doc verdicts vs claims-ledger rows.

**C3 — Ordering and dependencies.** The plan index defines an execution
order. Check it: does plan N depend on an artifact or decision from plan
M<N? Are there circular or unstated dependencies? Does any plan mutate
files another plan reads as stable?

**C4 — Verdict soundness.** Each research doc assigns ADOPT/ADAPT/WATCH/
REJECT/CITE. For each verdict, ask: is the cited source sufficient to
support it? Is the reasoning traceable, or does the verdict leap past the
evidence? Pay special attention to `WATCH→candidate` Laya — the owner
selected it, but the doc must not let owner preference inflate the
evidence.

**C5 — Recency risk.** Jev/Laya ecosystem claims are ≤2 weeks old and
vendor-sourced. September-2026 papers may be preprints. Flag every claim
that will need re-verification at report-freeze and assess whether the
doc already flags it.

**C6 — Invariant preservation.** Every plan must respect: local-first (no
network in product code), `core.time.utcnow`, ProfileDbSession isolation,
redaction-before-export, ModelRunner-only LLM access, dual Alembic chains.
Flag any plan step that would violate one.

**C7 — Missing scope.** Compare audit §17–§19 action items against the
eight plans. Anything dropped, merged, or silently descoped? Also: what
did the *audit itself* miss that an executor would hit on day one?

**C8 — UNVERIFIED honesty.** The claims ledger marks 6 contradicted and 2
not-evidenced claims. Verify those markings are accurate — including
whether any "verified" claim actually rests on the cited evidence.
</review_criteria>

<method>
- Verify before asserting: every finding carries the command run or the
  file:line read that produced it. "I believe" is not admissible.
- Sample, don't skim: for anchor checks use C1's ≥5-per-document minimum,
  chosen adversarially (check the *least plausible* claims first).
- Route-level claims (e.g., "endpoint exists", "scheduler starts") must be
  checked against actual registered routes in `main.py`, not doc text.
- Distinguish severity honestly: a wrong line number is MINOR; a plan that
  would corrupt a vault or violate an invariant is CRITICAL.
</method>

<output_format>
Write your review to `audit/2026-09-25/review/` as
`YYYY-MM-DD_review-findings.md` (create the directory; use real date):

1. **Verdict per document** — SOUND / NEEDS-REVISION / FLAWED, one line each.
2. **Findings table** — ID, severity (CRITICAL/MAJOR/MINOR), file:line,
   quoted claim, why wrong, evidence command, suggested correction.
3. **Coverage map** — audit action items ↔ plans ↔ gaps.
4. **Execution-readiness** — which plans could start today unchanged,
   which need revision first, blocked-by list.
5. **Your own uncertainty** — what you could not check and why.
</output_format>

<hard_rules>
- READ-ONLY. No file modifications, no commits, no test-runs that mutate
  state (pytest collection/grep/read are fine).
- Do not implement anything a plan describes — evaluate the plan.
- Do not soften findings. A package that survives adversarial review is
  worth more than one everyone praised.
- Report real outputs. Every command cited must have been run.
- `Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)`
</hard_rules>

<stop_conditions>
Stop and report rather than proceeding if:

- A plan's premise is measurably false (e.g., merge target branch gone,
  claimed defect already fixed on main) — record it, review the rest.
- The filesystem mount (`/mnt/c`) drops again — save partial findings to
  `/tmp/` and say so.
- You find evidence the audit package was generated without reading the
  repo (systemic phantom anchors) — that is itself the headline finding.
</stop_conditions>
