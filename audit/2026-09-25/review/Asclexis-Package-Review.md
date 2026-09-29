# Asclexis Package Review — 2026-09-26

**Verdict: NOT EXECUTION-READY.** Plans 04 and 06 have stop-level risks; plans 01, 02, 05, 07, and 08 need factual or sequencing corrections. Plan 03 is sound only as a decision-gated correction path. The package’s capstone thesis is plausible as a case study, but its present evidence does not support quantified multi-agent economics or causal claims.

## Scope and verification basis

Reviewed the audit report, both handoff prompts, all eight plans, all nine Markdown files under `docs/capstone-report/`, and the included `asclexis-showcase.html`.

- Checkout: `main` at `40f590eee32a98bcafc2c4db39509f921e1d9994`; `origin/main` matches. Existing user changes to `.serena/project.yml` and `docs/INDEX.md` were preserved. The package itself is untracked.
- Branch refs: `origin/claude/asclexis-repo-audit-349pjq` is 5 commits ahead; `origin/claude/healthcentral-agentic-research-r1n54x` is 19 commits ahead, tip `7b2ff1f` (`git rev-list --count origin/main..origin/claude/healthcentral-agentic-research-r1n54x` → `19`).
- Timestamp scan: Python AST found 125 `datetime.utcnow` attribute references in `src/backend` across 36 files: 109 outside tests in 30 files, plus 16 in 6 test files. The scan counts attribute references, including column defaults; it excludes comments and string literals.
- User-level agent inventory: `find /home/danny/.claude/agents -maxdepth 1 -type f -name '*.md' | wc -l` → `33`.
- Test environment: `python` is not on PATH. `python3 -m pytest tests/ --collect-only -q -p no:cacheprovider` collected 303 tests before 59 collection errors caused by missing SQLAlchemy. The claimed 1,245 baseline could not be independently confirmed here.
- Research source pass: opened the first listed URL for each of 78 source-bearing research headings. The cited page/PDF identities matched their headings; this checks link identity, not every numeric result or every secondary URL. High-impact claims below received additional content checks.
- Review was read-only apart from this report. No tests were modified or run beyond collection.

## Findings

### F-01 — BLOCKER: Plan 04 can stage unrelated work and the entire untracked package

**Evidence:** [plan 04, Task 16, line 676](../plans/04-doc-drift-sweep.md#L676) runs `git add -A`. The current worktree already contains edits to `.serena/project.yml` and `docs/INDEX.md`, plus untracked `audit/` and `docs/capstone-report/` content.

**Impact:** Following the plan in this checkout can commit changes outside its stated file list, including this review and the pre-existing user edits.

**Required correction:** Replace `git add -A` with explicit task-owned pathspecs. Require `git status --short` and `git diff --cached --name-only` review before commit. Do not execute Task 16 as written.

### F-02 — BLOCKER: Plan 06 presents engineering FK choices as owner-approved

**Evidence:** [plan 06, lines 24–31 and 232](../plans/06-sql-fk-audit.md#L232) says four foreign-key actions are owner-approved, then schedules migration and runtime enforcement. The cited branch document `docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md` labels itself **AUDIT ONLY — no code changes** (line 3), identifies Backend as owner (line 5), and records P14–P17 as engineering “Decision” rows (lines 69–72). Audit §21’s owner answers do not approve those cascade/`SET NULL` behaviors.

**Impact:** Changing delete behavior on patient-vault rows is a product-data decision. A reference audit and engineering recommendation do not establish owner approval.

**Required correction:** Keep report-only orphan discovery available, but stop before the migration or pragma flip until the owner explicitly approves each affected relationship and deletion effect. Replace “owner-approved” with the actual evidence status.

### F-03 — MAJOR: Plan 05’s migration inventory is short by eight product references

**Evidence:** [plan 05, line 11](../plans/05-utcnow-migration.md#L11) and the claims ledger [H9, line 32](../../../docs/capstone-report/claims-ledger.md#L32) say 101 product sites plus 16 test sites. An AST scan finds 109 product references plus the same 16 test references: 125 total across 36 files. The audit report’s earlier estimate of about 50 sites in 13 files is also materially low. A `rg` search for calls ending in `()` is insufficient because it misses `default=datetime.utcnow` references.

**Impact:** The workstream’s checklist, progress gate, and promised zero-hit result do not start from a reproducible inventory.

**Required correction:** Regenerate the site list from the current checkout using an AST-aware scan that includes callable defaults; reconcile all 125 references and identify intentional test literals separately. Preserve the plan’s correct semantic target: naive UTC.

**Reproduction:**

```python
import ast
from pathlib import Path

hits = []
for path in Path("src/backend").rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr == "utcnow"
                and isinstance(node.value, ast.Name) and node.value.id == "datetime"):
            hits.append((path, node.lineno))
print(len(hits), len({path for path, _ in hits}))
print(sum("tests" not in path.parts for path, _ in hits),
      sum("tests" in path.parts for path, _ in hits))
```

### F-04 — MAJOR: Plan 02 reverses the timestamp helper’s actual semantics

**Evidence:** [plan 02, line 14](../plans/02-notification-scheduler.md#L14) calls `core.time.utcnow` timezone-aware and cites `backup_scheduler.py:66–67`. The implementation [core/time.py:9–11](../../../src/backend/core/time.py#L9) returns `datetime.now(UTC).replace(tzinfo=None)`, explicitly naive UTC. Plan 05 correctly documents this contract.

**Impact:** The plan teaches the opposite of the repository invariant and risks adding aware values to naive SQLite timestamps—the precise comparison failure it says it is preventing.

**Required correction:** Correct the statement and re-check each scheduler comparison against stored naive timestamps. Do not add timezone normalization based on the mistaken premise.

### F-05 — MAJOR: The branch inventory and merge estimate are stale

**Evidence:** The audit report [§9, line 154](../Devin-Audit-report.md#L154) and plan 01 [lines 34 and 108](../plans/01-merge-branches.md#L34) say Branch B has 21 commits; `git rev-list --count origin/main..origin/claude/healthcentral-agentic-research-r1n54x` returns 19. Plan 01 and the audit also estimate a merged test baseline around 1,291 without a successful collection on the merged tree.

**Impact:** The inventory contradicts itself, and the merge plan’s conflict/test expectations can drift from the refs it intends to merge.

**Required correction:** Recompute both branch ranges, merge base, conflicts, and expected test inventory immediately before execution. Treat 1,291 as an estimate until the merged tree is collected and tested.

### F-06 — MAJOR: The 1,245-test baseline is labeled verified without reproducible evidence

**Evidence:** The claims ledger [H2, line 25](../../../docs/capstone-report/claims-ledger.md#L25) labels 1,245 backend tests, 155 Vitest tests, and 25 E2E tests `AUDIT-VERIFIED`. The report’s methodology [line 300](../Devin-Audit-report.md#L300) says no tests were executed. This review’s pytest collection stopped after 303 tests with 59 import errors because SQLAlchemy is absent. A rough source declaration scan is not a substitute for a runner count.

**Impact:** Plans 01, 02, 06, and 07 use fixed counts as acceptance criteria; handoffs repeat the same baseline. The current environment cannot reproduce it.

**Required correction:** Attach the actual CI or clean-environment collection output and tool versions, or downgrade the count to an unverified historical baseline. Point commands at the project interpreter (`python3` or the documented Windows launcher/venv) and state the required dependency setup; `python -m pytest` fails in this Bash environment because `python` is absent.

### F-07 — MAJOR: Plan 07’s expected count ignores earlier planned work

**Evidence:** [plan 07, line 537](../plans/07-test-reset-tables.md#L537) expects `1245 + 7 = 1252`. The documented execution order merges the branches first, then runs plans 02–06 before plan 07 ([audit §23, lines 441–447](../Devin-Audit-report.md#L441)). Branch A alone records a 1,248 test baseline; plan 01 estimates about 1,291 after both branches, and plan 06 adds tests. Plan 07’s delete-order comments [lines 293–295 and 411–415](../plans/07-test-reset-tables.md#L293) also say FK enforcement is off even though plan 06 precedes it and turns enforcement on.

**Impact:** The expected count and explanation are stale before plan 07 starts.

**Required correction:** Make the baseline measured and supplied by the completed prior steps. Update the FK comments and tests for the post-plan-06 state; retain child-first ordering only as an explicit safety property if still required.

### F-08 — MAJOR: Plan 08 states an unsupported HIPAA status as fact

**Evidence:** [plan 08, line 219](../plans/08-gated-items-review-packet.md#L219) instructs the author to state “Asclexis is not a HIPAA covered entity.” The repo contains no legal/entity/contract analysis establishing that status. HHS says the HIPAA Rules apply to covered entities and business associates and ties business-associate status to the work and relationship; it specifically includes an app developer contracted to serve a covered entity’s patients ([HHS covered entities](https://www.hhs.gov/hipaa/for-professionals/covered-entities/index.html), [HHS business associates](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html)). The cited six-year period applies to Security Rule documentation required by §164.316, not blanket retention of all audit rows ([45 CFR 164.316](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.316)).

**Impact:** The decision packet could anchor the owner on a legal conclusion not established by this repo and could incorrectly dismiss a retention obligation.

**Required correction:** Make status contingent on the actual operator, contracts, and data flow; request owner/legal review. Describe the six-year requirement narrowly as Security Rule documentation retention, not a general audit-log requirement.

### F-09 — MAJOR: Research 01 overstates Laya’s hardware and benchmark evidence

**Evidence:** [research 01, lines 120–145](../../../docs/capstone-report/research/01-agentic-swe-tools.md#L120) and the index [research/README.md, line 15](../../../docs/capstone-report/research/README.md#L15) say CPU/MPS/GPU support is verified for all target hardware and call the comparison “independent-flavored.” The linked Hugging Face card is published by ConvAI, not an independent evaluator; its text has no `MPS` match. The same card says the zero-shot base scored 0.362 on typed-decision tasks, below its 0.461 majority baseline; 0.766 belongs to a checkpoint fine-tuned on that benchmark’s training split ([ConvAI model card](https://huggingface.co/convaiinnovations/laya)). The card also says Jev figures were third-party published and not measured in the same run with matched samples/prompts. The `laya.studio` comparison URL returned no readable page in this check.

**Impact:** Owner preference and vendor benchmarks are blended with independent hardware and efficacy claims. This is especially material because the proposed role is safety-adjacent decision classification.

**Required correction:** Retain Laya as an owner-selected test candidate, not as a verified all-tier or zero-shot winner. Mark the source as vendor-reported; separate CPU/GPU evidence from unsupported MPS claims; measure latency and accuracy on Asclexis tasks and actual target hardware before adoption.

### F-10 — MAJOR: Research 02 reverses Plan 03’s branch labels and recommendation

**Evidence:** [research 02, lines 189–193](../../../docs/capstone-report/research/02-harness-techniques.md#L189) says “Branch-B” means creating five `.claude/agents/` and recommends adopting them; the research index repeats “real agents” as a top ADOPT ([research/README.md, line 16](../../../docs/capstone-report/research/README.md#L16)). Plan 03 defines Branch A as creating/unignoring agents and Branch B as correcting the false documentation claims ([plan 03, lines 32–36 and 127–139](../plans/03-phantom-layer.md#L32)); its recommendation is B with a STOP gate ([lines 173–189](../plans/03-phantom-layer.md#L173)). Audit Q2 records the owner as “Not sure” and asks for investigation before choosing ([audit §21, line 311](../Devin-Audit-report.md#L311)).

**Impact:** The capstone research index currently points toward a product/configuration change that Plan 03 explicitly defers and does not recommend. The two documents call opposite options “Branch B.”

**Required correction:** Correct Research 02 and its index to match Plan 03. Keep the STOP gate: verify the owner’s user-level configuration and resolve the decision before creating or deleting project agent definitions.

### F-11 — MAJOR: Multi-agent “economics” and error-capture claims lack denominators

**Evidence:** The original goal calls the audit/planning observations “quantified” ([00-original-goal.md, lines 23–27](../../../docs/capstone-report/00-original-goal.md#L23)); the outline promises “error-capture rates” ([report-outline.md, line 44](../../../docs/capstone-report/report-outline.md#L44)); the ledger says M1 is “VERIFIED — twice” and M2’s drift/gates pattern is audit-verified ([claims-ledger.md, lines 39–40](../../../docs/capstone-report/claims-ledger.md#L39)). The cited evidence is two case observations (3 sibling errors and 4 planning-pass corrections), with no number of seeded errors, single-agent comparison, task-level denominator, time/cost data, or selection protocol.

**Impact:** Those observations support “review found errors in these runs,” not capture rates, causal advantage, or a general claim that multi-agent review is economically superior. The M2 “exactly where” claim also lacks a systematic sample or denominator.

**Required correction:** Present these as case studies and hypotheses. Remove “quantified,” “error-capture rates,” and causal language unless raw traces, comparison conditions, denominators, time, and token/cost accounting are added.

### F-12 — MAJOR: The audit’s promised 40-row drift source is not in the package

**Evidence:** Audit §8 says a full 40-row table exists but shows 12 headline rows ([report, lines 122–139](../Devin-Audit-report.md#L122)); Plan 04 contains a 16-row verified ledger ([plan 04, lines 27–46](../plans/04-doc-drift-sweep.md#L27)). The orchestrator handoff asks the next agent to read a “40-item doc-drift table” ([handoff, lines 23–25](../handoff-prompt-claude-orchestrator.md#L23)). Audit line 298 names `audit/repository-audit-dashboard.html`, but that path is absent; the included HTML is `asclexis-showcase.html`, a CS4610 showcase with 20 `<tr>` elements, not that dashboard.

**Impact:** A downstream orchestrator is told to rely on an unavailable source artifact. It cannot audit or execute the promised complete drift work from the package as delivered.

**Required correction:** Include the actual 40-row reconciler artifact and link it, or correct the count and handoff to the available 16-row verified ledger plus the report’s 12 headlines. Correct the dashboard path claim.

### F-13 — MODERATE: Plan 04 chooses deletion of Serena memories before resolving intent

**Evidence:** Audit §16 says to “decide” whether to refresh or delete `.serena/memories/` ([report, line 271](../Devin-Audit-report.md#L271)). Plan 04 labels deletion “recommended” and supplies regeneration only as Option B ([lines 542–568](../plans/04-doc-drift-sweep.md#L542)). The capstone’s harness research recommends a freshness gate and says deletion depends on owner choice ([research 02, lines 135–140](../../../docs/capstone-report/research/02-harness-techniques.md#L135)).

**Impact:** The implementation plan turns an unresolved retention choice into a delete-by-default action on seven tracked context files.

**Required correction:** Keep both options and mark the task blocked pending owner choice, or select a freshness gate with explicit owner approval. Do not describe deletion as already authorized.

### F-14 — MODERATE: Research 04 is described as contract-bearing, but its entries are citation placements

**Evidence:** The capstone README says every research document has a proposed integration contract ([README.md, line 18](../../../docs/capstone-report/README.md#L18)); the research index says every entry ends with a proposed contract ([research/README.md, lines 5–9](../../../docs/capstone-report/research/README.md#L5)). Research 04 instead uses “Fit for Asclexis” and a `CITE`/`WATCH` verdict; it generally identifies report sections rather than an exact module/interface contract.

**Impact:** The index promises a level of implementation guidance that Research 04 does not provide. Citation recommendations can be mistaken for architecture decisions.

**Required correction:** Call Research 04 a literature/source map, or add concrete contracts only where adoption is intended. Keep `CITE` distinct from implementation `ADOPT`.

### F-15 — MODERATE: Plan 06 confuses new connections with pooled checkouts

**Evidence:** [plan 06, line 14](../plans/06-sql-fk-audit.md#L14) says a pragma must be re-issued “on every pooled checkout” and names a `connect` listener as the correct hook. SQLAlchemy documents `PoolEvents.connect` as firing when a DBAPI connection is first created, while `PoolEvents.checkout` fires each time a connection is retrieved from the pool ([SQLAlchemy Core Events](https://docs.sqlalchemy.org/en/20/core/events.html)).

**Impact:** The chosen connect hook can correctly initialize each physical connection, but the stated guarantee/test condition is wrong. It may lead to unnecessary checkout work or a test that never verifies more than one physical connection.

**Required correction:** Say “once per new physical DBAPI connection” and test the pragma on each engine’s distinct connections. Add a checkout hook only if code can change the connection-local pragma while it is pooled.

### F-16 — MODERATE: Audit verification provenance is not packaged for handoff

**Evidence:** The audit says load-bearing claims were confirmed by “two independent agents” or direct source checks ([report, line 300](../Devin-Audit-report.md#L300)); the package does not include the separate agent reports, raw reconciliation table, test-collection output, or per-claim verification artifacts. The owner Q&A is labeled as recorded answers ([report, lines 304–316](../Devin-Audit-report.md#L304)), but no source record is linked from the table.

**Impact:** Readers cannot distinguish independent reproduction from a report author’s summary. Plans reuse these labels as approval and baseline evidence.

**Required correction:** Attach or link the verification artifacts and owner-decision provenance, or downgrade the unsupported labels to “reported in audit; not independently reproducible from this package.”

### F-17 — MINOR: Owner-machine agent count is off by one

**Evidence:** Audit §12 and Plan 03 say 34 generic user-level agent files; `find /home/danny/.claude/agents -maxdepth 1 -type f -name '*.md' | wc -l` returns 33. The material result—none of the five Asclexis-specific names exist—still holds.

**Impact:** The count is a small credibility defect in a finding whose purpose is precise inventory.

**Required correction:** Correct 34 to 33 or attach the exact command/output and define whether non-Markdown files are included.

## Readiness by document

| Document | Verdict | Gate before use |
|---|---|---|
| `Devin-Audit-report.md` | **Needs revision** | Correct branch/site/test claims; provide the missing 40-row source or retract it; repair the artifact path and distinguish verified evidence from summary assertions. |
| `handoff-prompt-claude-orchestrator.md` | **Needs revision** | Remove the unavailable 40-item reference and make the test baseline/environment explicitly conditional. |
| `handoff-prompt-review-agent.md` | **Ready for review use** | Its read-only criteria and explicit challenge requirements are useful; retain the limitation that execution evidence may be unavailable. |
| `plans/01-merge-branches.md` | **Needs revision** | Refresh current refs/counts and measure the merged baseline; keep branch movement as a preflight stop. |
| `plans/02-notification-scheduler.md` | **Needs revision** | Correct naive-UTC semantics; make interpreter/dependency setup reproducible and remeasure tests. |
| `plans/03-phantom-layer.md` | **Ready only through its STOP gate** | Its Branch A/B definitions and recommendation are internally sound; no implementation past the owner decision. Align Research 02 first. |
| `plans/04-doc-drift-sweep.md` | **Not ready in this worktree** | Replace `git add -A`; make Serena memory handling owner-selected. |
| `plans/05-utcnow-migration.md` | **Needs revision** | Regenerate the inventory and task counts from AST evidence. |
| `plans/06-sql-fk-audit.md` | **Blocked before behavior changes** | Obtain explicit owner approval for relationship actions; correct connection-event language and baseline. |
| `plans/07-test-reset-tables.md` | **Needs revision** | Use a measured post-plan-06 baseline and update FK-state explanations. |
| `plans/08-gated-items-review-packet.md` | **Needs revision** | Remove the categorical HIPAA claim and narrow the six-year retention statement. |
| `00-original-goal.md`, `claims-ledger.md`, `report-outline.md` | **Needs revision** | Preserve the case-study thesis but downgrade multi-agent rates/causal language; reclassify baseline and migration counts. |
| `docs/capstone-report/README.md`, `research/README.md` | **Needs revision** | Do not nominate the audit as unqualified source of truth; correct the phantom-layer and Laya descriptions; qualify Research 04’s contract status. |
| `research/01-agentic-swe-tools.md` | **Needs revision** | Vendor disclosures, hardware scope, zero-shot benchmark baseline, and `UNVERIFIED flags: none` need correction. |
| `research/02-harness-techniques.md` | **Needs revision** | Correct the Branch B inversion and avoid promoting unresolved agent creation as ADOPT. |
| `research/03-rag-local-llm.md` | **Conditionally usable as scouting** | Its owner gates and explicit unverified flags are useful; keep product claims behind local eval, license review, and measured hardware checks. |
| `research/04-papers-evals.md` | **Conditionally usable as related-work map** | Preserve explicit preprint status and cite sources as context; do not present the audit’s M1/M2 observations as quantitative or causal results. |
| `asclexis-showcase.html` | **Not an audit source** | It is a project showcase, not the dashboard or 40-row drift artifact described by the audit. |

## Claims verified and worth retaining

- Main exposes 18 API routers; the report’s 18-router count matches the current router registrations.
- The notification scheduler has definitions but no production caller; the backup scheduler is wired. “Reminders cannot fire today” is supported by call-site inspection.
- The live `/profiles/test/reset` at `src/backend/api/profiles.py:477–532` deletes 16 models and omits `ChatSession`, `ChatTurn`, `ResponseFeedback`, `CarePlanTask`, `Pinboard`, and `PinboardItem`.
- The profile DB connection listener at `src/backend/core/profile_database.py:314` configures SQLCipher; it does not set `PRAGMA foreign_keys`. Existing comments are not enforcement.
- The Laya source exists and its model-card limitations are explicit; the unsupported step is treating vendor-reported hardware/benchmark data as independent or representative of Asclexis workloads.

## Dependency order and execution stops

The package’s stated sequence is branches → scheduler → phantom-layer decision → doc-drift → UTC migration → FK work → reset tests → gated-items packet. Preserve those dependencies, with these corrections:

1. Refresh and merge-plan the current 5-commit and 19-commit branch refs; establish a real test baseline after the merge.
2. Correct plan 02’s timestamp contract before wiring the scheduler.
3. Keep plan 03 at its owner STOP gate. Do not let Research 02 silently choose Branch A.
4. Do not run plan 04’s broad staging command. Resolve Serena memory intent before deletion.
5. Recount UTC sites, obtain FK-action approval before behavior changes, and pass the measured baseline forward into plan 07.
6. Prepare plan 08’s packet with conditional legal framing; keep all five decisions owner-gated.

## Source notes

- Laya model card and limitations: [ConvAI’s Hugging Face card](https://huggingface.co/convaiinnovations/laya).
- HIPAA entity/business-associate definitions: [HHS covered entities](https://www.hhs.gov/hipaa/for-professionals/covered-entities/index.html) and [HHS business associates](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/business-associates/index.html).
- Six-year documentation rule: [45 CFR 164.316](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.316).
- SQLAlchemy connection event semantics: [SQLAlchemy 2.0 Core Events](https://docs.sqlalchemy.org/en/20/core/events.html).
- September 2026 papers cited in Research 04 resolve to arXiv records: [Traverse](https://arxiv.org/abs/2609.17930) was submitted September 15 and has no accepted venue listed in the record checked; [ParaRecover](https://arxiv.org/abs/2609.12345) was submitted September 11 and its record says accepted to EMNLP 2026. Keep their maturity labels distinct.
