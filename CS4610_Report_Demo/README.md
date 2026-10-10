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
  model, reranker on/off) producing a Pareto frontier — Final Report §7.3.
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

This list was produced by re-checking each claim against the repo (`grep`,
`find`, `ls`) rather than taking the documents at their word — see
`docs/research/2026-09-08/10-demonstration-artifact.md` §2 for the full
gap table and verification commands.
