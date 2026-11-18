# CS4610 Report Demo — scope note

These two documents (Final Report, Technical Companion) were written for a
CS4610 course deliverable. They describe the harness and the product's
development process, and some of what they describe is aspirational rather
than shipped. Read them as a snapshot of intent at the time of writing, not
as a changelog of this repo.

Claims checked against the repo and found **not evidenced**:

- **A `PreToolUse` hook ("AgentShield") that scans tool calls for PHI and
  blocks network-bound calls** — Final Report §7.2, Technical Companion §4.6.
  No `PreToolUse` hook exists in this repo. The only committed hook (since
  2026-10-10, owner HOOKS-COMMIT) is a metadata-only `PostToolUse`/`SessionEnd`
  session logger (`.claude/hooks/session_log.py`) that scans nothing and blocks nothing.
  "AgentShield" appears nowhere in the code — only in these documents and in
  the research notes that recorded the gap. The real, evidenced mechanism for
  the invariant this claim describes is
  `core/llm/ollama_provider.py` (localhost-only by construction) and
  `modules/redaction.py` (redaction before anything exportable leaves) —
  see `docs/agentic/harness.md`.
- **Named subagent definitions under `.claude/agents/`** (`docs-consistency-scanner`,
  `dependency-policy-auditor`, etc.) — implied throughout both documents.
  When the reports were written that directory did not exist, and subagent
  dispatch was ad hoc. On 2026-10-01 the five named definitions were written new
  and committed by owner decision (D1, 2026-09-27). They were not recovered
  from anywhere, and they do not make the reports' description true
  retroactively: four are read-only scanners, and the one implementer's write
  scope is declared, not enforced by Claude Code. See `docs/agentic/harness.md`.
- **An overnight "Ralph-style" RAG parameter sweep** (chunk size, embedding
  model, reranker on/off) producing a Pareto frontier — Final Report §7.3;
  the same campaign is described as a GSD v2 run in Technical Companion §5.6.
  There is no reranker in `modules/rag.py` to have been swept, and no sweep
  artifact or eval-card output exists in the repo.
- **A specific cross-vendor review catching a JWT log-leak bug** — Final
  Report §7.1. No matching commit, design doc, or plan entry exists; the
  cross-vendor review workflow itself is real and in progress
  (`docs/research/2026-09-08/FRONTIER-AUDIT-PROMPT.md`), but this particular
  anecdote is not evidenced as something that already happened.
- **A specific unique-IV entropy bug caught by two-stage review on the
  SQLCipher/JWT modules** — Technical Companion §6.5. The superpowers-based
  review workflow is real and documented; this specific bug anecdote has no
  matching commit or design-doc entry.
- **Hook-based secret scanning in this project's harness** — Final Report
  §5.1, §6 (timeline phase 8). Same finding as the AgentShield bullet above:
  no `PreToolUse` secret-scanning hook exists in the repo. The only committed
  hook is the metadata-only `PostToolUse`/`SessionEnd` session logger
  (`.claude/hooks/session_log.py`, F-10 #68), which scans nothing. The
  user-level PreToolUse hooks are continuous-learning and GSD only
  (`docs/capstone-report/claims-ledger.md` H6, whose last sentence about
  `.claude/settings.json` predates #68). The repo's scanner is the CI security
  gate, which failed open on main until branch B's fix was merged (ledger H4).
- **A project Skill holding the analyte-synonym map and unit-conversion rules,
  updated by a Stop hook from earlier corrections** — Final Report §7.2,
  Technical Companion §4.6. No such skill exists on main or either branch
  (`git grep -il analyte -- '*SKILL.md'` returns nothing). The synonym map is
  ordinary code in `src/backend/modules/normalize.py` and `glossary.py`
  (ledger H16).

Claims checked against the repo on 2026-09-27 (main @ `40f590e`) and found
**false**:

- **"Every byte of patient data is stored in an AES-256-encrypted SQLCipher
  database with per-document keys and initialization vectors"** — Final
  Report §1; repeated in §3.2. The master database is plain SQLite and holds
  profile display names, password hashes and audit rows
  (`src/backend/core/config.py:180-184`, `models/profile.py:47,53`).
  Documents are AES-GCM files encrypted with the profile's key and a fresh IV
  per document, not per-document keys (`core/security.py:443-466`,
  `core/document_crypto.py:19-36`). On Windows the dev launcher falls back to
  unencrypted vaults when SQLCipher will not install (`dev.ps1:473-487`,
  `:583-591`). Ledger C16, C18, C21.
- **"Even a compromised backup file leaks nothing without the master key"** —
  Final Report §3.2. Each backup archive includes a plain-SQLite copy of the
  master database reduced to that profile: display name, password hash and
  audit rows (`src/backend/scripts/backup.py:199-205,243-251`). Ledger C17.
- **"HealthCentral never uploads patient data … a compromise of the cloud is
  architecturally impossible because there is no cloud"** — Final Report
  §3.3. True by default only. An opt-in, off-by-default assistant path sends
  redacted prompts to OpenAI or Anthropic (`src/backend/core/external_runner.py:261-300`),
  and outside production a setting can switch that redaction off (`:201`);
  owner decision D12 (2026-09-27) approved removing that bypass. Ledger C10.
- **"A local-first desktop application"** — Final Report §3.1. There is no
  desktop shell or installer; the app runs as a local web app started by
  `dev.ps1` (backend on 127.0.0.1:8000, frontend on :3000). Ledger C8, C30.

Changed since submission (accurate or unverified when written; different on
main @ `40f590e`):

- The reports describe the assistant as a local LLM grounded by RAG (Final
  Report §1, §3.2). Since the June–July 2026 agent work, the default assistant
  path composes answers from templates over the patient's verified data and
  makes no LLM call. The LLM path still exists as the fallback when the agent
  is switched off or fails (`src/backend/modules/agent/settings.py:19`,
  `api/assistant.py:745-751`). Ledger C14.
- The Final Report's cover gives the submission date as May 15th, 2026; its §6
  timeline (row 14) gives Apr 22, 2026. The two disagree; the repo does not
  record which is right.

This list was produced by re-checking each claim against the repo (`grep`,
`find`, `ls`) rather than taking the documents at their word — see
`docs/research/2026-09-08/10-demonstration-artifact.md` §2 for the full
gap table and verification commands. The 2026-09-27 additions cite rows in
`docs/capstone-report/claims-ledger.md`.
