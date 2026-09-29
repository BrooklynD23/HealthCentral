# 3b fork — number audit, plans W01–W06

Verdict: 0 BLOCKER · 0 MAJOR · 4 MINOR. 111 checks, 107 match, 4 mismatch. Test-count arithmetic is internally consistent in all 6 plans.

Refs: main=40f590e · A=origin/claude/asclexis-repo-audit-349pjq@692fdf3 · B=origin/claude/healthcentral-agentic-research-r1n54x@7b2ff1f.
Helper used: `s(){ git show $1:$2 | awk -v a=$3 -v b=$4 'NR>=a&&NR<=b{print NR": "$0}'; }`

## MINOR findings

| # | Plan:line | Claim | Measured | Command |
|---|---|---|---|---|
| 1 | W01:743 | `B@7b2ff1f dev.bat:16` runs `powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1"` | `:16` is `REM -NoProfile skips…`; the powershell line is `:17` (same at main) | `git show $B:dev.bat \| grep -n powershell` → `17:` |
| 2 | W01:64 | program P3 acceptance "at `:180`" | acceptance line is `implementation-program.md:181`; `:180` is the `docs_lint.py` verification bullet | `sed -n 178,181p docs/capstone-report/implementation-program.md` |
| 3 | W05:848 (F-2) | "`git grep -n "HC-CIT"` returns 11 at main, A and B" | that command returns **2** at each ref (`TASK_LIST.md:63` `CITE-SRC-001`, `test_citation_source_links.py:9`). 11 = `git grep -ni "HC-CIT\|hc_cit"` (2 + 9 `test_hc_cite_00N` defs). Conclusion (usable, `-k hc_cit` ambiguous) still holds | `git grep -n "HC-CIT" <ref> \| wc -l` → 2; `git grep -ni "HC-CIT\|hc_cit" 40f590e \| wc -l` → 11 |
| 4 | W06 ↔ W11b (cross-plan) | W06 defines `HC-EXT-*`; W11b defines `HC-EXTR-*` | `HC-EXT` is a text prefix of `HC-EXTR`. Both plans' `-k` selectors carry a trailing `_` (`hc_ext_`, `hc_extr_`), so pytest selection is safe; a bare `grep HC-EXT` / `-k hc_ext` would cross-select | `grep -noE "\-k [\"']?hc_ext" docs/plans/2026-09-27-W06-*.md` (all `hc_ext_`) |

## 1. Test-count arithmetic (claims vs tests written in the plan's code)

| Plan | Claim (plan:line) | Tests actually written | Result |
|---|---|---|---|
| W01 | `START_COLLECTED + 7` (:862, :1177, :1341); `+ 8` only after Task 9/OG-3 (:1318, :1447) | 7 defs `test_hc_agents_001…007` (:338,:350,:465,:475,:496,:514,:527), no parametrize; Task 9 adds `test_hc_agents_008` (:1273) | MATCH |
| W02 | `N0+2` after Task 1 (:634), `N0+8` after Task 2 (:1052, :1292, :1353) | Task 1: `002` parametrized csv/json = 2. Task 2: `001` ×3 fmt (:778) + `001_real_pdf` (:815) + `001_known_gap` xfail (:835) + `003` (:881) = 6. Total 8 = :102 list. Result lines :1025 `6 passed, 1 skipped, 1 xfailed` / :1026 `7 passed, 1 xfailed` both sum to 8 | MATCH (3 IDs → 8 items is by design, stated at :102) |
| W03 | backend `start + 5` (−1 per skipped Task 3/7) (:1176, :1291); vitest `start + 8` (+6 if Task 6 vetoed) (:1246, :1296) | backend defs `hc_ver_001…005` (:544,:367,:657,:567,:1066); Task 3 = 003 only, Task 7 = 005 only. Vitest `it(` blocks: FE-002 ×3 (:738,:748,:757), FE-001 ×3 (:874,:881,:889), FE-003 ×2 (:1006,:1012) = 8; minus FE-003 = 6 | MATCH |
| W04 | `START_COLLECTED + 2` after Task 2 (:607); `+ 5` (:1086, :1300); "3 + 8 + 2 = 13 paths" (:1093) | Task 2: `001`, `004` (:496,:519). Task 3: `002`,`003`,`005` (:766,:783,:810). 8 golden JSON files listed in Task 3 (:680-730); staged = gate script + harness + test file (3) + 8 JSON + CLAUDE/AGENT (2) = 13 | MATCH |
| W05 | `START + 3` (:115-116, :565, :729, :804) | 3 defs `hc_cit_001…003` (:354,:366,:425), no parametrize | MATCH |
| W06 | backend `START_COLLECTED + 17` (:1062, :1119) = "001 ×4, 002 ×4, 002b, 002c ×2, 002d, 004 ×4, 004b"; vitest 3 (:1124) | 001 parametrize 4 tuples (:348-351); 002 = 2 env × 2 tuples = 4 (:499-503); 002b 1; 002c 2 tuples (:556-559); 002d 1; 004 4 tuples (:789-797); 004b 1 → 17. Sub-totals :423 "4 passed", :735 "12 passed" (4+4+1+2+1), :1122 "8 passed", :1123 "5 passed" all consistent. Vitest `it(` ×3 (:925,:933,:938) | MATCH |

Note for the program/handoff: handoff §5 lists W-6 as "3 tests" and W-2 as "3 new tests"; the plans add 17+3 and 8 collected items. Not a conflict (handoff lists minimum IDs), but "Measured acceptance: 3 tests" in handoff §5 rows W-2/W-6 is superseded by the plans' counts.

## 2. Line-number citations re-measured

### W01 (20 checks, 2 mismatch)
| Cite | Ref | Result |
|---|---|---|
| `docs/agentic/harness.md:27-28` names the 5 agents (:42) | main | MATCH (`:27` 4 scanners, `:28` windows-bootstrap-engineer) |
| `harness.md:25` "No subagent definitions are checked into this repo" (:255, :897) | B | MATCH |
| `harness.md:27` "Read-only scanners…", `:28-29` keep (:898, :902) | B | MATCH |
| `roadmap.md:10` "ad hoc scoped subagents", `:17` Agent orchestration row (:256, :899-900) | B | MATCH |
| plan 04's `roadmap.md:8,15` are main numbers; post-P1 `:10,:17` (:1245) | main/B | MATCH (main :8,:15 hold the `.claude/agents/` claims) |
| `scripts/harness_drift_check.py:63-74` `_is_checkable` skips extensionless tokens (:124) | B | MATCH |
| `harness_drift_check.py:12-14` docstring example (:903) | B | MATCH |
| `tests/test_harness_drift_check.py:44` fixture (:903) | B | MATCH |
| `A@692fdf3 docs/agentic/recurring-failures.md:33` `GET /profiles/` (:239) | A | MATCH |
| `.gitignore:44` `.claude/*` | main | MATCH |
| `core/config.py:37` `sqlite_database_path` | B | MATCH |
| `dev.bat:16` powershell wrapper (:743) | B | **MISMATCH → :17** |
| `dev.ps1` 855 lines; winget 3.11 at `:361-368` (:744) | B | MATCH (`wc -l` = 855) |
| 33 user-level agents (ledger H5, W01:1039) | host | MATCH (`ls ~/.claude/agents/*.md \| wc -l` = 33) |
| handoff `:138` W-1 row | pkg | MATCH |
| program `:169` P3 heading | pkg | MATCH |
| program acceptance `:180` | pkg | **MISMATCH → :181** |
| matrix `:143` GATE-09, `:156` GATED-06 | pkg | MATCH |
| contract `:340` C-GATE-1 | pkg | MATCH |
| ledger `:45-46` H5/H6 | pkg | MATCH |

### W02 (17 checks, 0 mismatch)
| Cite | Ref | Result |
|---|---|---|
| `modules/export.py:203` `%m/%d/%Y` in `_format_abnormal_values` | main | MATCH |
| `modules/export.py:211-221` `_format_trends` | main | MATCH |
| `modules/export.py:528-530,573` ISO dates in visit-prep | main | MATCH |
| `api/export.py:379-479` `generate_doctor_summary` | main | MATCH (`:379` decorator … `:479` close) |
| `api/export.py:446` `_summary_store[...] = summary_data` | main | MATCH |
| `api/export.py:455-459` audit details | main | MATCH |
| `api/export.py:476` `key_findings=summary.key_findings` | main | MATCH |
| `api/export.py:806-810` visit-prep `redaction_count` | main | MATCH |
| `core/audit.py` `ALLOWED_DETAIL_KEYS` has `redaction_count` | main | MATCH (`:86`, `:94`) |
| neither A nor B touches both export.py files | A,B | MATCH (`git diff --stat` empty) |
| `CLAUDE.md:30,31,35`, `AGENT.md:57` = 1245 | main | MATCH |
| B `CLAUDE.md:30` 1288 vs `AGENT.md:76` 1269 (:1462) | B | MATCH |
| HC-PKT-004 (dates ISO) exists | main | MATCH (`test_visit_prep_packet.py:176`) |
| HC-PKT-012/013/016 exist | main | MATCH (`:357,:385,:435`) |
| contract `:340` C-GATE-1, `:360` C-GATE-3 | pkg | MATCH |
| 8 items / result totals | plan | MATCH |
| `api/export.py:551-604` text summary build (ledger W-2 fact) | main | MATCH (boundaries `:551 else:` … `:604 )`) |

### W03 (25 checks, 0 mismatch)
All MATCH: `rag.py:322` `try:`, `:323-332` select, `:325-329` where (no `user_verified`); `:450-451` swallow; `:549-553` Chunk/Embedding/Document join (no status filter); `:607` `is_user_verified`; `:862` `< 0.6`; `:1236-1245` insufficient-context text; `:1174` `query(`; `:1277-1281` `ModelUnavailableError`; B `api/assistant.py:1329-1347` `_fetch_latest_obs` (no verified filter); B `:564-567` fingerprint docstring; `retrieve_chunks.py:70-74` (`:73` `Document.status == "verified"`); `query_observations.py:56`; `compute_trend.py:56`; `api/observations.py:529-535` (no filter), `:716-724` audit, `:476-489` auto-promotion; `api/interpretations.py:427-432` value in question; `InterpretedTrendChart.tsx:78-81` green `'verified'` badge; B `ci.yml:150-168` agent-evals; `models/document.py:57`, `models/observation.py:79` `nullable=False`; B HC-VERIFY-001…007 at `test_verify_model_repos.py:39-89` (B's own docstring at `:1` says 001..006 — stale in B, not in W03); C-VERIFY-1 grep = 2 hits at main and B; golden set = 74 JSON at main and B.
Consequence for matrix/handoff: SAFE-02 and handoff W-3 cite `rag.py:322-328`; W03:99 correctly moves it to `:323-332` (where `:325-329`).

### W04 (16 checks, 0 mismatch)
All MATCH: B `api/assistant.py:811-812` legacy branch, `:868` `is_valid = result.is_valid`, `:798` agent `is_valid = True`, `:1281` `_build_knowledge_fallback`, `:1464` `is_valid=True`; `templates.py:20-24` `ABSTAIN_TEMPLATE` (main); `rag.py:825-865` = 5 `errors.append` triggers (`:826,:833,:838,:858,:863`) and `:869 is_valid=len(errors)==0`; `rag.py:1290-1295` timeout text; `tests/support/routes.py:26-32` signature; `pages/ExplainAssistant.tsx:607-618` green "claims verified" footer; B `scripts/agent_eval_gate.py:6-8` "future CI workflow step" (stale); `faithfulness.py:362-403` `score_response`; matrix `:73` SAFE-04, `:76` SAFE-07; program `:286` G-B5; 8 golden files; 13 staged paths.
Not re-measured (needs a run): faithfulness 0.831 / 0.814 probe values (W04:87-101) — measured by the author on Win Py 3.13.7; UNVERIFIED here.

### W05 (15 checks, 1 mismatch)
MATCH: `rag.py:123-140` SYSTEM_PROMPT, contradictory `:128,:133,:134`, `:126` `[cite:N]`; `rag.py:819` pattern; `claim_extractor.py:92`; `services/assistant.ts:378,394`; `api/assistant.py:1346` main = `:1403` B; `rag.py:634-644` labels; `rag.py:672` history header; `rag.py:1268` `_generate_with_runner(prompt, runner)`; `ExplainAssistant.tsx:558` `[{i + 1}]` (F-3); `git grep "YOUR_RESULTS\|REFERENCE:" 40f590e -- src ':!src/backend/tests'` → only `rag.py:128,133,134,636`; doc grep (W05:617) = 8 hits exactly at `01_lab…:197,213,214`, `ai-safety.md:20`, `faq.md:109,110`, `workflows.md:115,116` (main; 8 at B too); B 1288/1269.
**MISMATCH:** W05:848 "`git grep -n "HC-CIT"` returns 11" → 2 (see MINOR #3).
Consequence: handoff W-5 row and matrix SAFE-08 / contract C-SAFE-5 cite `rag.py:120-132`; correct is `:123-140` (lines `:128,:133,:134`).

### W06 (18 checks, 0 mismatch)
All MATCH at B (and `core/external_runner.py`, `modules/rag.py` are byte-identical main↔B: `git diff --stat 40f590e $B -- src/backend/core/external_runner.py src/backend/modules/rag.py` empty; `core/config.py` differs by 1 deleted line, `api/model_settings.py` +11): `external_runner.py:168` policy from settings, `:172` prod-block condition, `:170-198` block, `:201` `if redaction_enabled:`, `:202-223` redaction block, `:236-237` SECURITY_AUDIT logger only, `:27-92` encryption helpers, `:95` class, `:126` availability gate, `:328-369` `get_runner_for_request`; `core/config.py:27` `app_env` default development, `:135-137` policy + break-glass, `:241` startup check; `tests/test_audit_phi_minimization.py:430` HC-AUD-010; `core/audit.py:201` `create_audit_log`; `core/database.py:51` `async_session_maker`; `api/model_settings.py:208-213`, `:690`, `:719-757`; `services/modelSettings.ts:214-219`; `SettingsPage.tsx:665`; B `data-privacy.md:200` "per `modules/redaction.py` policy" (also main `:200`).
Note: matrix LOCAL-04 / contract C-REDACT-2 cite `:201`/`:172` as main; valid at main and B (file unchanged).

## 3. Other numbers

| Plan:line | Number | Command given? | Agrees with pkg? |
|---|---|---|---|
| W02:1462, W05:256 | B `CLAUDE.md:30` 1288 vs `AGENT.md:76` 1269 | yes (`git show`) | Program/handoff say B collects 1288 (measured). AGENT.md:76 @B is stale (1269). Re-measured text: MATCH |
| W03:81 | C-VERIFY-1 grep exactly 2 hits | yes | MATCH contract :115 |
| W03:87, :125 | 74 golden cases | implicit | MATCH (74 JSON at main and B) |
| W04:73 | 5 `is_valid=False` triggers | cite only | MATCH (5 `errors.append` in `:793-872`); contradicts matrix SAFE-04 / contract C-SAFE-2 "faithfulness < 0.6 sets is_valid" as sole trigger (ledger W-4 fact) |
| W05:274 | "first 9 files gave `167 passed`" (Win 3.13.7) | author-run | not re-run (READ-ONLY); author-context only, labelled "not a target" |
| W01:1039 / ledger H5 | 33 user-level agents | yes | MATCH (33) |
| W01:744 | dev.ps1 855 lines @B | implicit | MATCH |

No plan in W01–W06 asserts vitest totals (155/165/179) or Playwright totals; W03 and W06 use `start + N` relative to a measured vitest start. Good.

## 4. Cross-plan IDs

| Plan | Defines | References (owner) | Collision status |
|---|---|---|---|
| W01 | HC-AGENTS-001…008 | — | none (`HC-AGENTS` 0 hits at main/A/B) |
| W02 | HC-EXPR-001…003 | HC-PKT-004/012/013/016 (existing, main) | none. W10 references HC-EXPR-001…003 (W02-owned) — reference only |
| W03 | HC-VER-001…005, HC-VER-FE-001…003 | HC-VERIFY-001…007 (B, existing) | `HC-VER` text-prefix of `HC-VERIFY` (B). Plan anchors greps (`HC-VER-[0-9]\|hc_ver_0\|HC-VER-FE`, :217) and uses `-k hc_ver_` — `hc_ver_` is not a substring of `hc_verify_`. Safe. W10 references HC-VER-001/002 |
| W04 | HC-LEG-001…005 | — | none |
| W05 | HC-CIT-001…003 | HC-CITE-001…009 (existing) | `HC-CIT` text-prefix of `HC-CITE`; plan says select by file/node ID (:242-244). `-k hc_cit` still appears at :242 and :848 only as the warning. Safe |
| W06 | HC-EXT-001, 002, 002b/c/d, 003, 003b/c, 004, 004b | HC-LLMB-001 (W07-owned, read-only allowlist ref at :173), HC-AUD-010 (existing) | `HC-EXT` text-prefix of W11b's `HC-EXTR` (MINOR #4). No ID defined by two plans. W10 references HC-EXT-001/004 |

No ID in W01–W06 is **defined** by two plans. HC-LLMB is defined by W07 only (W06 refers to it).
