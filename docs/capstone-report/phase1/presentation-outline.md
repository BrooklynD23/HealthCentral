# Senior Report Phase 1 — Presentation Outline

**Last Updated:** 2026-11-11
**Owner:** repository owner
**Status:** DRAFT (Phase 1). 18 slides, about 20 minutes plus demo. Numbers are from [report-draft.md](report-draft.md) and are sourced in [evidence-index.md](evidence-index.md).
**Refresh Trigger:** any change to a number in the report draft; the Phase 2 merge of other-project material.

Each slide lists a title, 3-5 bullets, a suggested visual, and speaker notes. Figures marked "showcase" can be lifted from the ledger-gated page `docs/capstone-report/asclexis-showcase-2026-10-22.html`; re-check any number on them against the evidence index, because that page is dated 2026-10-22.

---

### Slide 1 — Asclexis: a private health-records companion, built with agents

- Senior project report (Phase 1 draft), following the May 2026 CS4610 report
- A local-first app for understanding your own lab results
- And a study of building software by directing coding agents
- Thesis: the harness is the deliverable; its failures are the findings

**Visual:** title card; product screenshot of the Results page on the right.
**Speaker notes:** Introduce both halves in one breath: a product and a method. Say early that the talk shows measured evidence and names what is missing.

### Slide 2 — Why: a mother's bloodwork

- Autoimmune labs every few months, little explanation
- Cloud tools trade privacy for convenience
- Goal: patient data stays on the device; answers cite her own records
- Education only, never medical advice

**Visual:** a redacted, synthetic lab report next to a trend chart.
**Speaker notes:** Report §1.1 and `00-original-goal.md`. Keep it short and human; this is the motivation the May report also opened with.

### Slide 3 — What changed since the May report

- May 2026: a report about tools and intent
- Sep 2026: an audit and a claims ledger re-checked every claim
- Four May claims were false (every byte encrypted, backups leak nothing, no cloud, desktop app); one was false when written (named subagents); seven were not evidenced (AgentShield hook, secret-scanning hook, synonym skill, RAG sweep, two bug anecdotes, three MCP servers)
- This report: current facts, each with a source

**Visual:** a three-step timeline (May report → Sep audit + ledger → Nov measured state) with a red/green claim tally.
**Speaker notes:** Report Appendix A. Own the corrections up front; the committee should hear them from you first.

### Slide 4 — Architecture at a glance

- FastAPI backend on 127.0.0.1, React frontend, started by a script
- Master DB (plain SQLite) + one SQLCipher vault per profile
- Dual Alembic chains: 3 master, 19 profile revisions
- 19 routers, 45 module files plus the agent package, 17 pages; 11 CI jobs

**Visual:** integration diagram (showcase §02, or `architecture-overview.md` §2 Mermaid), with the master DB marked "unencrypted".
**Speaker notes:** Report §1.2. Point at the master DB yourself; it is the main open privacy gap.

### Slide 5 — From PDF to verified trend

- Upload → encrypt (AES-GCM) → extract (pdfplumber, opt-in bundled OCR, FHIR/CSV)
- Observations start unverified; the patient verifies in a workbench
- Trends show unverified points, marked (owner decision D4)
- Extraction golden set: 28/0/0 on synthetic data

**Visual:** pipeline strip with a "human check" gate in the middle.
**Speaker notes:** Report §1.3. Mention that all test data is synthetic, by design.

### Slide 6 — The assistant: cite or abstain

- Default agent path: plan → act → reflect → draft → guard; no model call
- Fallback RAG path: `ModelRunner` → `[cite:N]` validation → abstain on failure
- 74 golden safety cases in CI: groundedness, citation and abstention must be 1.0
- Local models measured: abstained 75-100% rather than cite falsely (n=20 each)

**Visual:** two-lane diagram (showcase §04 safety lane) with the abstain exit highlighted.
**Speaker notes:** Report §1.4, §2. The surprise: the default assistant uses no LLM. The local-model table shows the guard working, not the models.

### Slide 7 — Privacy layers

- Redaction strict / standard / minimal; doctor summary strict since W-2
- Only the patient's own CSV/JSON export is exempt (D3)
- Opt-in cloud runner: off by default, strict on every call, audited break-glass (D12)
- Audit rows for profile, document, observation and export events

**Visual:** a "what leaves the device" table: path → redacted? → evidence.
**Speaker notes:** Report §1.5, §2. Say what is still open: unencrypted master DB, audit coverage not re-checked.

### Slide 8 — Model-agnostic, local-first

- One facade (`ModelRunner`), providers inside `core/llm/`
- llama.cpp in-process by default; Ollama pinned to localhost
- The cloud runner is the single named exception
- The agent path is model-free, so "agnostic" covers the fallback only

**Visual:** provider box diagram: facade → llama.cpp / Ollama (localhost) / external (dashed, opt-in).
**Speaker notes:** Report §2.

### Slide 9 — The development story in numbers

- 3836 commits; 593 merged PRs; 393 merged in October alone
- 2563 commits co-authored by Claude; Opus 1323, Sonnet 713, Haiku 267
- Backend tests: 621 (June) → 1245 (Sept) → 4984 (Nov)
- Counts show what is checked, not quality

**Visual:** test-count line chart over time (report §5.5 table) and a monthly merged-PR bar chart.
**Speaker notes:** Report summary table, §5.5, §6.3. Say that the counts come from different environments.

### Slide 10 — Four agent runtimes

- Claude Code: primary runtime; the harness is built around it
- Codex: read-only adversarial reviewer; 51 review rounds on 14 plans
- Devin: wired in for two days in October; one PR refresh delivered, then MCP disconnects
- Cursor: a 40-minute interim session merged 3 PRs under the same runbook

**Visual:** four columns, one per runtime: role, evidence, failure.
**Speaker notes:** Report §4. Note that the file named "Devin-Audit-report" contains no Devin content. Lesson: integration with the shared machine mattered more than model capability.

### Slide 11 — A green suite is not proof

- Restore returned 400 for every request; 32 backup tests passed
- The backup download shipped other profiles' password hashes; the test checked file names
- Fix: route tests through real HTTP (`route_client`)
- Every plan now states what its test would not notice

**Visual:** a green test bar next to a red HTTP 400 response; then the file-name assertion versus the leaked row.
**Speaker notes:** Report §5.2; commits `842bc494`, `565f7085`. This is the single most important slide in the methodology half.

### Slide 12 — 21 ways a check can lie

- "The check that was run was not the check that mattered"
- Modes 1-10: product and test design (mocks, one-site invariants, unstarted features)
- Modes 11-21: mostly harness-level, appeared once many agents shared one machine
- New instance → added in the same commit

**Visual:** 21-tile grid, coloured product vs harness.
**Speaker notes:** Report §5.1. The shift from product failures to harness failures is a finding in itself.

### Slide 13 — The quiet box and a flake that was ICU data

- Timing checks need a quiet machine: one lock, all test slots held, load below 1.5
- UIDOC-006A: a 42-50 ms gap against a 40 ms bound
- Cause: the first `toLocaleDateString()` loads ICU data; idle warm-up → 0/20 misses
- The bound did not move; MEDS-G-FLAKE came next: harness timing, not ICU (warm-up A/B: no change)

**Visual:** before/after bar (9/20 → 0/20 at normal CPU; 11/20 at 2× throttle, a known limit).
**Speaker notes:** Report §5.4. Emphasise that `gh run view` returned the wrong attempt's log, and the real count was 3, not 5.

### Slide 14 — Orchestration: L0, planners, builders

- L0 (Opus) plans, reviews, merges; never writes product code
- build-item: Haiku explore → Opus Task 0 → Sonnet implement → Haiku test → Opus review → PR
- Task 0: spec exists, deps merged, gates answered, no shared files, count matches
- Docs batch merges before the code it licenses

**Visual:** swimlane of one build item across the five models.
**Speaker notes:** Report §6.1-§6.2. Each rule maps to a failure from slides 11-13.

### Slide 15 — Routing changed by owner decision

- Sep 28: Sonnet implements, Opus reviews
- Oct 24: "never use Sonnet"; Haiku implements (267 Haiku commits, Oct 24-28)
- Oct 29: reverted; Haiku only runs tests
- Not an experiment: no conclusion about which model is better

**Visual:** timeline with the trailer counts per model.
**Speaker notes:** Report §6.3. Be explicit that this is a case study.

### Slide 16 — Context, skills and cost

- `CLAUDE.md` (rules) + `AGENT.md` (facts) + file-based state the scripts check
- 36 skills: 14 Superpowers, 18 Pocock, 4 domain; vendored so cloud sessions see them
- 18 build items: 12.7 agent-hours, 10.8M tokens; a 1-line fix cost 382k tokens
- Fixes: fast lane, scope-gated suites, narrow agents

**Visual:** bar chart of the in-repo figures: 18 items, 12.7 agent-hours, 10.8M tokens, 8 ready vs 10 stopped; and the two tiny rows at ~400k tokens each.
**Speaker notes:** Report §7.5. Mention the off-repo call breakdown only as a lead; it is not in git.

### Slide 17 — Self-improvement, with the gate in charge

- RSI loop: mine failures → reflect → propose ≤3 edits → replay 36 cases → owner merges
- 4 archived runs: one rule merged (#341), then two runs with nothing worth proposing; one more rule (#230) from an unarchived cloud run
- No causal improvement shown
- Data donation stays off: PHI detector recall 71% on names vs a 95% bar

**Visual:** loop diagram with the gate and the human merge drawn larger than the proposer.
**Speaker notes:** Report §8. The donation story is the clearest case of a gate stopping the owner's own feature.

### Slide 18 — What it shows, what it doesn't, what's next

- Shows: one developer directing agents through 593 merged PRs, with every rule tied to a failure it answers
- Doesn't show: speed or quality versus another method; no user study; no cost in dollars
- Next: constrained decoding for citations, encrypted master DB decision, installer, MEDS-G fix (option A, awaiting owner gate MEDS-G-X1)
- [PHASE 2 PLACEHOLDER: other projects]

**Visual:** three columns: shows / does not show / next.
**Speaker notes:** Report §10-§12. End on the thesis.

---

### Demo (after slide 8 or at the end, about 5 minutes)

Script: `docs/plans/2026-09-27-senior-report-showcase-plan.md` §6. Start with `dev.sh`, create a synthetic profile, import a synthetic lab PDF, verify two values, open the trend, ask the assistant a question it can cite and one it must abstain on, export the doctor summary and show the redaction.

[PHASE 2 PLACEHOLDER: slides for other projects, inserted between slides 17 and 18.]
