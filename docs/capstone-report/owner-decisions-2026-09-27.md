# Owner Decisions — 2026-09-27

**Last Updated:** 2026-09-27 (D8-delivery added)
**Recorded by:** Claude orchestrator. Each answer was selected by the repository owner in the Claude Code chat on 2026-09-27, in reply to multiple-choice questions. Each option carried the description quoted below.
**Scope rule:** each approval licenses exactly the option text shown. Anything wider is still owner-gated. This record answers D1–D13 in [implementation-program.md](implementation-program.md#owner-decision-intake-p0-c), P0-B, two follow-ups, and the D8-delivery follow-up (answered later on 2026-09-27).

## Decisions

| # | Question (short) | Owner's choice | Option text as presented (what it licenses) | Recommended? |
|---|---|---|---|---|
| P0-B | Uncommitted `docs/INDEX.md` / `.serena/project.yml` edits and the untracked package | **Commit on a docs branch** | "Create a docs/ branch, commit INDEX.md + the audit/ and capstone-report/ package with explicit pathspecs, regenerate the index there. .serena/project.yml handled separately. Clean main for P1." | yes |
| D9 | Phase-gate interpreter | **New 3.11 venv** | "Build a 3.11 venv from src/backend/requirements.txt so local results match CI." | yes |
| D6 | Plan 02 `core/auth.py` hooks | **Approve as planned** | "Two small hooks in open/close_profile_database_on_login/logout; session-scoped reminders only (fire only while a vault is unlocked); records skipped_locked. Quiet hours stay unenforced." | yes |
| D5 | FK delete semantics (plan 06) | **Approve all four** | "P14/P15 CASCADE, P16/P17 SET NULL, pragma ON for master + profile engines. … owner still reviews the orphan report before migration." | yes |
| D3 | Export redaction scope | **Redact doctor summary only** | "Doctor summary goes to a third party → redact it (strict). CSV/JSON are the patient's own data export → keep full-fidelity like backups, and amend CLAUDE.md/data-privacy.md to name them as deliberate exceptions." | yes |
| D4 | Unverified values on trends / legacy RAG | **Label, exclude from RAG** | "Trends may show unverified points but visibly marked 'unverified'; legacy RAG cites verified values only (matches the agent path). Docs updated to say so." | yes |
| D1 | Phantom agent layer (plan 03) | **A: build real agents** | "Author ~3 read-only agent definitions, unignore .claude/agents/ in .gitignore, commit them. More work; turns the claim true going forward." The scope was then widened by the D1-scope answer below. | **no** (B was recommended) |
| D1-scope | How many agents | **All 5 claimed agents** | "Author all five named in harness.md, including windows-bootstrap-engineer (bounded write) and agentic-roadmap-researcher." | **no** (3 read-only was recommended) |
| D2 | `.serena/memories/` | **Delete them** | "git rm the 7 stale memory files; Serena can regenerate on demand." | yes |
| D7 | Dormant `model_selector` `llama_cpp` path | **Route via ModelRunner** | "Keep the tiered-interpretation feature but rewrite it to call ModelRunner, then wire it to a route. New feature work." | **no** (delete was recommended) |
| D8 | Implicit embedding download | **Bundle the model** | "Ship the small embedding model with the app / installer so no download is ever needed." | **no** (offline + explicit download was recommended) |
| D12 | Opt-in cloud LLM path | **Keep, harden** | "Keep the opt-in feature as a documented ModelRunner exception, but make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning). Amend CLAUDE.md to name the exception." | yes |
| D13 | `utcnow` swap in `api/profiles.py` auth hunks | **Approve** | "Same value (naive UTC), one import + swap per site; tests must show identical serialization. Reviewer checks the auth hunks specifically." | yes |
| D10 | HIPAA applicability | **Treat as HIPAA-aligned** | "Design retention/controls as if HIPAA applied (6-year Security Rule documentation, etc.) regardless of legal status." | **no** (conditional + legal flag was recommended) |
| D11 | Citation-marker vocabulary | **Docs match code** | "Keep [cite:N] as the validated marker; document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels; remove the contradictory prompt line. … no validator edit." | yes |
| D8-delivery | How the D8 model reaches the machine before an installer exists (Consequence #4) | **Script + offline load** | "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git." Asked and answered later the same day, in the planning session. | n/a (no option was marked recommended) |
| G-B5 | Low-faithfulness legacy answers | **Abstain + add eval gate** | "If is_valid=False, return the abstention/knowledge-fallback template instead of the answer, and add a CI eval gate for the legacy path. Threshold stays 0.6 (never lowered)." | yes |

## Earlier owner records still in force

| Record | Source | Scope |
|---|---|---|
| Merge both branches as-is | audit §21 Q3 (agent-recorded 2026-09-25) | P1 |
| Wire the notification scheduler | audit §21 Q1 (agent-recorded) | P2; D6 adds the auth-hook approval |
| Blast radius: fix orphan writes, never relax a constraint | branch A `backlog-closure-plan.md` §14 d3 (`fe31e78`, 2026-09-08) | P6; D5 adds the delete semantics |
| HC-M11 approved behind a default-off flag only | branch A §14 d2 | G-C5; production scoring change still gated |
| Care-task quote: keep the task, null provenance, clear the quote | branch A §14 d1 | landed by P1 (`45ac889`) |
| OpenWiki: the owner generates it locally | branch A §14 d4 | G-C2 |
| MFA, key rotation, pen test, audit retention: prepare only | audit §21 Q6 | P8 briefs; D10 now frames brief 4 |

## Consequences the next agent must carry

1. **Governance edits are now approved:** amend `CLAUDE.md` (D3: CSV/JSON as named exceptions; D12: the external runner as a named ModelRunner exception) and `docs/compliance/data-privacy.md` (D3, D4). These change invariants. Make them in their own `docs:` commit, citing this record, with nothing else in the diff.
2. **The D1 choices differ from plan 03's recommendation.** Plan 03 Branch A scoped 3 agents and warned against authoring a roster just to match old text. The owner chose all 5, including a write-capable `windows-bootstrap-engineer`. A new plan is needed: bounded write scope in frontmatter, read-only tools for the other 4, and a harness drift check that passes.
3. **D7 creates feature work beside a safety module.** Rewriting tiered interpretation onto ModelRunner and wiring it to a route touches `modules/interpret.py`, which calls `modules/interpret_safety.py`. The safety module stays read-only unless the owner separately approves an edit to it.
4. **D8 conflicts with current state:** there is no installer (HC-M08 is a spike). "Bundle the model" needs a delivery mechanism before an installer exists. **Open design question for the owner:** interim delivery via `src/backend/scripts/download_models.py` into a local models dir plus HF offline, vs vendoring the model files (size not measured). Do not commit model weights to git without asking. **Answered 2026-09-27 (D8-delivery row): script + offline load.** The patient-visible fail-closed behaviour and the exact model revision are still owner-gated in the [W-8 plan](../plans/2026-09-27-W08-bundled-embedding-model.md) (Q-FC, revision pin).
5. **D10 is a design posture, not a legal conclusion.** Documents must say "designed as if HIPAA applied (owner choice, 2026-09-27)". They must never say "Asclexis is a covered entity" or "is HIPAA-compliant".
6. **G-B5 changes patient-visible behaviour on the fallback path.** The abstention template lives beside ask-first modules; use the existing fallback/abstain templates and do not edit `faithfulness.py` / `verifier_agent.py`.

Back to index: [README.md](README.md)
