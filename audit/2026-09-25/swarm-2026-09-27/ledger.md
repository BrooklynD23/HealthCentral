# Orchestrator ledger

## Wave 0 (2026-09-27)
- fetch ok; main=origin/main=40f590e; A 5/0 692fdf3; B 19/0 7b2ff1f; merge-tree 5 conflicts (same). No drift.
- No 3.11 venv. Win Py 3.13.7: 1245 collected; 4 failed / 1241 passed (s4_2_offline_loop, bkup_039, bkup_039b, docs_index_check). 002b PASSED here.
- docs_lint pass; generate_docs_index --check stale (INDEX.md, _link_graph.json).
- DRIFT vs handoff: pass counts were unmeasured in handoff; now measured. 3 non-env failures (s4_2, bkup_039/039b) not in handoff baseline narrative.

## Owner decisions this session
- D8-delivery: "Script + offline load" (verbatim option: "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git.")
- Effort: all planning/adversarial agents + orchestrator on high.

## Open owner gates (collected)
W-6: Q1 break-glass reach (all envs vs prod-only); Q2 CLAUDE.md:60 names audited break-glass (routed to W-10); Q3 warning placement (settings only vs chat too); Q4 core/external_runner.py edits (holds API-key encryption helpers :27-92) ask-first; test_redaction.py existing test amended.

## Reviewer log
(see reviews/reviewer-log.tsv)
W-2: O-2 (BLOCKS Task 3) strict redaction turns %m/%d/%Y dates into [DATE-REDACTED] — switch to ISO (rec) or accept loss; O-1 summary has no patient identifier (new decision needed to add one); O-3 strict mode misses underscore-joined PHI (fix = redaction.py ask-first); O-4 ExportPage Copy joins unredacted /export/questions; S-5 P0-D brief moot?
W-2 facts: text summary built in api/export.py:551-604 (not only modules/export.py) -> matrix PRIV-04 / C-REDACT-1 citations incomplete; summary includes unverified obs (D4 doesn't cover).
Ownership decision: data-privacy.md D3/D4 wording + :200 break-glass -> W-10 (not P4). guardrails SKILL.md:63 -> P4 after W-6.
Order: P5 -> W-2 (modules/export.py); W-2 -> G-C1 (api/export.py); W-10 -> W-2.
W-7: OG-1 tier picks model weights (core/llm change)?; OG-2 existing /interpret + LabInterpreter UI use tiered path? (spill-over: one interpretation row per observation); OG-3 audit rows for 6 unaudited api/interpretations.py routes (C-AUDIT-1 gap, not in matrix AUD-01).
W-7 facts: model_selector import at B:456 (not 438); acceptance grep misses `import llama_cpp`; plan 05 Task 11 model_selector lines +18 after P1; 2 latent bugs (unique observation_id IntegrityError; template stored as model tier).
Order: P5 -> W-7 (model_selector.py, api/interpretations.py).
W-4: OQ-1 (BLOCKS Task 2) which existing template: T1 ABSTAIN_TEMPLATE (rec) / T2 knowledge fallback / T3 rag insufficient-context; OQ-2 ack: is_valid=False has 5 triggers (not only <0.6) -> abstention rate UNMEASURED; OQ-3 interpret-grounded also serves invalid answers (not licensed); OQ-4/5 escalate vs abstain, green "claims verified" footer (not licensed); Seed PR permission (throwaway draft PR to run CI on seed).
W-4 facts: C-SAFE-2/SAFE-04 describe trigger as faithfulness only — code (rag.py:825-865) also citations/advice/failed_claims; B CLAUDE.md:30 says 1288 vs AGENT.md:76 says 1269 (P1 reconcile); _fetch_latest_obs no user_verified filter (sent to W-3); agent_eval_gate.py:6-8 "future" stale; asclexis-evals SKILL.md:41 ≥95% vs gate 1.0.
Order: api/assistant.py P1 -> W-4 -> W-3; ci.yml P1 -> P5 -> W-4 -> G-B3/G-B4 (W-11a).
W-5: C-1 CLAUDE.md:62 D11 wording -> W-10 absorb w/ owner confirmation; prompt clause "where N is the number in that source's context label" not licensed (own sign-off); live model [cite:N] emission UNMEASURED.
W-5 facts: prompt at rag.py:123-140 (contradictory :128,:133,:134), not :120-132 (handoff/matrix SAFE-08); HC-CIT substring matches HC-CITE (my Wave-0 note wrong about substring); F-3 bug: answer [N] uses chunk index but chips numbered by position ExplainAssistant.tsx:558 (out of scope, new finding); program "ask-first-adjacent" overstated.
Order: rag.py W-5 before W-4 recommended (W-4 doesn't edit rag.py) and serial with W-3. P4 gets pipelines.md:111, 00_features_index.md:38, 04_self_improvement_loop.md:113.
W01: 4 broken harness.md links (DOC-007) — fix in review.
W-8: Q-FC (BLOCKS merge) patient-visible fail-closed surfaces; Q-HASH stop searching legacy hash-fallback vectors (docs vanish until reprocess; row counts UNMEASURED); Q-OFFLINE per-call offline (not process-wide HF_HUB_OFFLINE).
W-8 facts: CI has no model install step (CLAUDE.md:30-31/AGENT.md:57,64 claim wrong) — 002b passes via implicit download; C-LOCAL-1 allow-list 7 -> 8 after P1 (download_models.py huggingface_hub); reprocess deletes chunks before embed (documents.py:867-871 @A) data-loss bug; MIT vs Apache-2.0 wrong in 2026-06-30 survey:152; HF cache refs/main rewritten 2026-09-27 17:05 -0700 — likely my Wave-0 full-suite run (002b PASSED = implicit HF fetch = LOCAL-03 gap demonstrated) — UNVERIFIED hypothesis; socket-block tests fragile; models/ dir needs .gitignore.
Order: W-8 after P1, P4, P5, W-1(.gitignore), W-3/W-4/W-5 (rag.py), W-6 (config.py), W-10, W-4/W-11a (ci.yml).
LOCAL-03 LIVE EVIDENCE: Win HF cache refs/main rewritten 17:05:28 -0700; my Wave-0 suite run output file written 17:05:46 -> the suite run (test_api_rag_index_002b) implicitly fetched from HF. Disclose; add to recurring-failures #4 candidate (env-dependent pass hides network fetch).
W-1: OG-1 write scope enforceable only via PreToolUse hook (hooks not licensed by D1) -> declarative + review; OG-2 verification-engineer read-only can't run tests; OG-3 HC-AGENTS-008 runs drift check in backend suite (CI coupling); OG-4 write scope beyond dev.ps1/dev.bat?; models haiku/opus choice not owner-specified.
W-1 facts: drift check exits 1 after P1 (A's recurring-failures.md:33 `GET /profiles/`) -> plan 01 lines 376/495 + P3 + handoff W-1 acceptance wrong; check-ignore on tracked file vacuous (need --no-index); drift check checks disk not git index; GATED-06 matrix:156, GATE-09 :143, contract :383 still "owner-gated/Not sure" after D1; plan 04 Task 15 roadmap.md lines :8,15 -> :10,17 post-P1.
W-3: O-5 (BLOCKS Task 3) chunk filter = parent Document.status=="verified" (agent rule retrieve_chunks.py:73); side effect: zero-observation docs can never be verified (VerificationWorkbench.tsx:523-527) -> vanish from legacy chat; O-1 veto on knowledge-fallback filter (Task 7, in scope under D4); O-2 InterpretedTrendChart green badge on unverified; O-3 interpretations.py:427-432 puts unverified value into model question (W-7 area); O-4 misleading "upload documents" message when only unverified data.
W-3 facts: HC-VER substring collides with HC-VERIFY-00x on B (my Wave-0 note wrong on substring); rag.py select :323-332; agent_eval_gate.py prints PASS then hangs >300s (timeout 124) on Win 3.13 — gate reliability issue; legacy tests use fake DB ignoring WHERE + _get_observation_chunks swallows exceptions (rag.py:450-451) -> recurring-failures #1 instance.
Order: rag.py W-5 -> W-4 -> W-3 (per W-3); api/assistant.py P1 -> W-4 -> W-3; api/observations.py P5 -> W-3; types.ts W-6 vs W-3.
INTEGRATION TODO (wave 3): P1 acceptance add "harness_drift_check exits 0 on merged tree" + resolve recurring-failures.md:33 `GET /profiles/` false positive in P1 conflict resolution (plan 01 lines 376/495 banner). W-1 owner option: .claude/settings.json deny data/** *.db (not licensed by D1).
SECURITY (new, verified): debug=True default (config.py:28 @B), .env.example:14 DEBUG=true, dev.ps1:573 DEBUG=true; echo=settings.debug on master (database.py:46) and VAULT (profile_database.py:308) engines -> SQL (probe: display name + audit insert) to stderr in default dev. security-reviewer scoping (read-only). Fix is ask-first (encryption-adjacent file) -> owner gate S-3.
P08: S-2 ordering: Brief 2 signed before P4 :169 task (run P8 right after P1, or P4 skips :169); D10 vs 2026-07-27 erase decision (purge audit rows on delete; data-privacy.md:150-153 @A) -> Q4b; S-3 debug SQL echo fix.
P08 facts: no logs/asclexis.log sink (measured); data-privacy.md:33 @A overstates "log file"; plan 08 archive-into-backup wrong (backups carry plaintext profile-scoped master copy w/ audit rows, scripts/backup.py:203-205,243-290); AUD-04 cite main :180-184 -> B :179-184; audit echo :257-264 @B; log_level/audit_log_enabled never read; plan 08 Task 4 "fail-open" stale; /export/questions unredacted; HIPAA-compliance claims in code comments core/audit.py:4,215 models/audit.py:4,24 + 2 migrations.
SECURITY scoped HIGH (security-reviewer): vault+master echo bound VALUES (lab values, chat, doc text, display name, bcrypt hash) to stderr on every dev.ps1 launch; no disk sink by default; no test catches; violates C-REDACT-3, PRIV-06; contradicts hipaa-controls.md:71, data-privacy.md:47. Fix options A (sql_echo flag default False) + B (hide_parameters=True) — ask-first profile_database.py. Tests HC-SQLECHO-001/002 (no caplog: fileConfig removes root handlers). -> new plan S-1.
W-2 rev: O-3 pre-merge gate + strict xfail; real audit rows; decision: CLAUDE.md "all N pass" wording false after xfail/skip — confirm replacement wording.
W-1 rev: checker edit removed; fresh-worktree boundary; OG-5 deny rules option.
W-10: Q1 D11 hunk C-3 in governance commit (rec yes); Q2 break-glass clause (rec yes); Q3 name runner under Local-first (default skip); Q4 order after P4 before W-2/3/6 (rec); Q5 "like backups" phrase. F-2 data-privacy.md:196-197 main false: whole prompt goes to external runner (rag.py:1257-1268) -> P4 addendum; F-3 api/backup.py:10-15 docstring false -> W-2 PR. CI also runs generate_docs_index --check (acceptance gap). W10 plan has broken link "-> target".
OWNERSHIP RULING: if W-10 Q1 unsigned, CLAUDE.md:62 stays unchanged and becomes an owner item; P4 never owns it. Fix W-10 plan :52.
P04: 30 tasks; OG-1 .serena/.gitignore /memories (not covered by D2); OG-2 exports include unverified rows (D4 doesn't cover); OG-3 ollama_base_url never passed to OllamaProvider (factory.py:51); overview :185 lists 3 core->modules imports, actually 5; overview :188 "P3" should be P4; ci-and-quality-gates.md:44 "~1160 passing"; pipelines.md:44-45 overclaims; README.md:94-97 "only outbound" false.
W-11a: OG-1 audit calls in api/profiles.py; Q-AUD-LIST; OG-2 ciphertext test confirm; Q-RUFF (a) hard-error rules only (0 findings) rec; Q-COV report-only; OG-3 seed draft PR. Facts: "25 e2e" was pass count (28 listed main, 30 A+B); vitest 165 main /179 A+B (Linux listing); Win 3.13 has no sqlcipher3 -> Wave-0 1241 passed ran UNENCRYPTED vaults; no Windows sqlcipher3 wheel -> native dev vaults unencrypted (dev.ps1:471-500)!; WSL has no python3.11 -> D9 blocked, ask owner; ruff 555 main/561 B findings.
FINDING: core/auth.py:73 Session.is_expired uses datetime.now(timezone.utc) (aware) — in-memory session model diverges from naive-UTC invariant (C-TIME); not covered by P5 (utcnow-only). W-11a r1 BLOCKER#1 resolved by reusing route_client Session (no timestamp built) — orchestrator accepts: using core.time.utcnow there would TypeError. Record as contract/matrix note, auth = ask-first.
WAVE5 facts (schedule skill, 2026-09-27): routine = isolated cloud session (CCR), own git checkout of https://github.com/BrooklynD23/HealthCentral (default repo), env "Default" env_012CLTzohPPrf26mKXAjBtJL (anthropic_cloud); allowed_tools list configurable; cron 5-field UTC, min interval 1h; 00:00 America/Los_Angeles = 07:00 UTC (PDT) / 08:00 UTC (PST) -> UTC cron can't follow DST; default model claude-sonnet-5; connectors: only claude.ai ones (Claude-Docs available); no local files; run logs via list_runs/get_run_log; cannot delete via API (claude.ai/code/routines). Cloud checkout = origin/main -> audit/ + capstone-report/ + new plans absent until P0-B merges; harness_drift_check.py absent until P1.
OWNER: round 4 approved for W-4 and W-8 (2026-09-27 chat). No round 5.
P04: OG-4 config/.env.example edit; OG-5 docstrings api/__init__.py, modules/agent/__init__.py; OG-6 delete scripts/download_models.py (root).
W-11b gates: S-C1-1 G-C1 go-ahead (exports stored in vault until profile delete); S-C1-2 profiles.py:799-803 docstring; S-C2-1 OpenWiki run + source to LLM API; S-C2-2 tool edits to CLAUDE/AGENT(S).md default reject; S-C3-1..3; S-C4-1..4.
W-11b facts: PRIV-08 CONFIRMED gap (404 after restart; pinboards.py:13,495 third store user); G-C1 needs P5->W-2->P6->P7; F-1 SECURITY rl_exports/ not gitignored, not swept by DELETE /profiles (profiles.py:799-800 docstring false); F-2 alembic.ini logging config drops INFO (SECURITY_AUDIT lines lost; HC-M07 Filter approach + AUD-04 premise fail); F-4 plan 06 breaks tests/test_care_tasks.py:809,825 (hard-coded head); F-5 D8-delivery missing from owner-decisions (fix in W3); F-3 extractor drops lines w/ unknown units; F-6 HC-PKT-014/015, HC-FHIR-103/104 direct handler calls (recurring #1).
OWNER: round 4 approved for W-1, W-2, P08 too.
S-1: gates S1-A (option A incl. 1 line in ask-first profile_database.py), S1-B (hide_parameters). Order P1 -> S-1 -> P2, before P6. Facts: tests touching master engine write into developer's REAL master DB (engine built at import, absolute path) — test-isolation finding (did my Wave-0 run write to data/asclexis.db? UNMEASURED); api/profiles.py:328 @B logs display name at INFO (hidden only by WARN root); llama_cpp_provider.py:136 verbose=settings.debug (prompt leak UNMEASURED); handoff §5 needs S-1 row.
OWNER: round 4 approved for W-3, P04, W-10, W-11a, W-11b. Round-4 final: W-1, W-2, P08 BLOCKERs fixed after last round -> open for owner acceptance; W-8 MAJOR same.
CORRECTED: Office lock files are tracked on MAIN; branch B 7b2ff1f deletes them -> P1 resolves (no action).

## RESUME POINT (usage limit hit, 2026-09-27 ~21:05 PDT)
Done: 16 plan files in docs/plans/2026-09-27-*; Wave 2 reviews (see reviews/reviewer-log.tsv, all Codex, no Opus fallback triggered); Wave 3b deliverable wave3/3b-evidence.md; owner-decisions D8-delivery row added; routine spec written.
Pending on resume:
1. Collect: Wave 3a (wave3/3a-integration.md), Wave 4 report plan, W-5/W-7 post-PASS edits, Codex W-10 r4, W-11a r4, S-1 r3, RTN r1.
2. Apply integration edits myself: implementation-program.md (graph from 3a, W-plan table, fix :69/:195 data-privacy routing, P0-B2 plan-set commit gate), specs-compliance-matrix.md (3b §2.1 + 11 new rows §3, recount by script), contract (3b §2.2), overview :185/:188, owner-decisions :46 size, handoff §5 S-1 row, capstone README + link all new plans (DOC-011).
3. Run: python3 scripts/docs_lint.py; generate_docs_index.py --check (stale due to owner INDEX.md edits — don't regenerate without consent); relative-link check.
4. Unowned: PRIV-10 rl_exports erase (needs new plan, ask-first), GATE-14 eval hang, TIME-03, KEY-08, AUD-06 (W-7 OG-3).

## Wave 6 — integration pass (2026-09-28)
- Snapshot: branch docs/p0b-plan-set, commit 5d56557 (plans + capstone + audit; wave3 repo-copy dirs excluded, untracked). Not pushed. P0-B / P0-B2 NOT signed by owner.
- Dispatched 6 file-disjoint opus agents; rules in wave6/SHARED-RULES.md; reports land in wave6/<id>.md:
  6A program+owner-decisions · 6B matrix+contract+overview+claims · 6C W01-W05 · 6D W06-W10 (+W10 r4 response) · 6E W11a/b,P04,P08,S01,RTN (+W11a r4, S01 r3, RTN r1 responses) · 6F audit plans 01/05/06/07 + handoff §5 + capstone README.
- RESUME POINT if cut off: read wave6/*.md; any agent without a report file = rerun it; then docs_lint + link check + verifier pass + commit.
- Wave 6 DONE (all 6 reports in wave6/). docs_lint rc=0; relative-link check 37 docs → 1 broken (pre-existing plans/04 → openwiki/README.md, untouched); generate_docs_index --check rc=1 (stale, owner consent needed).
- Codex final rounds closed: W10 r4, W11a r4, S01 r3 (PASS), RTN r1. New owner Q: RTN Q6 (routine push capability; default do-not-enable).
- Matrix recount: 73 rows = 4 enforced · 18 tested · 4 implemented · 15 partial · 20 gap · 9 contradicted · 2 owner-gated · 1 unknown.
- NEW FINDING (6B, by reading): aware now at modules/badge_evaluator.py:84 → earned_at (:101) → EarnedBadge naive DateTime column (models/gamification.py:64-68), reached via api/medications.py:1000. TIME-03 → contradicted. 3b minor-1 corrected: 12 lines / 8 files (both `timezone.utc` + `dt_timezone.utc` forms).
- PRIV-10 settled: default path src/backend/rl_exports NOT ignored (check-ignore rc=1); only data/rl_exports + src/backend/data/rl_exports match .gitignore:74.
- Owner items raised: P0-B2 scope incl. 16th file (senior-report-showcase-plan); api/profiles.py:328 display_name at INFO (S01 excludes; auth-adjacent).
- Next: Wave 7 verifier (cross-file consistency + queued fixes), then commit.

## Wave 7 — verifier (2026-09-28)
- 7 queued: 5 fixed, HC-VER no-op (selectors anchored, 0 collisions), openwiki link left (quoted AGENT.md text; target exists). Sweep: 14 inconsistencies fixed (config.py/ci.yml orders in W06/W07/W08/W11a, "62 rows" → 73, stale owner-gated text after D2/D4/D5/D6/D8, 5 broken GFM rows). New program owner items: LOCAL-07 (W-10 addendum proposed), PRIV-06 display-name log.
- docs_lint rc=0; links 283 checked / 1 broken (openwiki, intentional); GFM cell check clean.
- STATE: plan set integrated and consistent. Execution NOT started. Blocked on owner gates — see wave7-verifier.md §4.

## Owner sign-offs + PR (2026-09-28)
- OWNER (chat, 2026-09-28): P0-B2 "All 16, push + open PR"; D9-SRC yes (uv 3.11.16); P1-DRIFT, SLOT-RULE, P7-ROUTE signed; SQL-ECHO S1-A + S1-B. Recorded in owner-decisions (commit b115357).
- PR #19 opened: docs/p0b-plan-set → main. Before merge: regenerate INDEX.md + _link_graph.json (generate_docs_index --check rc=1).
- Stakeholder artifact: https://claude.ai/artifact/DzJ89t8zJo4tPf7NjzctxV (private; execution waves 0–8 derived as earliest-start levels of the program graph).
- NEXT: merge PR #19 (Wave 0) → build D9 venv → P1 (merge B then A) in a worktree.

## Dependency fix + execution handoff (2026-09-28)
- CI on PR #19 failed: SQLAlchemy 2.1.1 (PyPI 2026-09-25) moved greenlet behind [asyncio]; unbounded pin → every backend import failed. Fix PR #20 `sqlalchemy[asyncio]>=2.0.25,<2.1` merged by owner → main 5289cca. PR #20 CI: Backend 1245 passed; Agent Eval Gate pass; E2E Smoke fails (runner disk full, Errno 28) — also failed on main 2026-09-07 → new owner item CI-DISK.
- PR #19 rebased onto 5289cca (force-with-lease).
- Owner direction: execution via 3-tier orchestration — L0 program (Opus) → L1 per-wave orchestrator (Opus subagent) → L2 implementers (sonnet) + reviewers (Opus); Codex for architectural plan/diff reviews. Nesting depth 2 measured (general-purpose subagent has Agent; no Workflow tool in subagents).
- Written: docs/agentic/orchestration.md (process), audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md (prompt, state, waves+gates, briefs), program ground rule 9, plan 01 banner item 5 (keep the pin).
- RESUME POINT: owner merges PR #19 (Wave 0) → next session pastes handoff §1 → build D9 venv → Wave 1 (P1).
