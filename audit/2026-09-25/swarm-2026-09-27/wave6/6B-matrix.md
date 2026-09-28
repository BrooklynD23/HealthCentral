# 6B-matrix report (Wave 6, 2026-09-28)

Done: 4 owned files edited. The matrix now has 73 rows: 4 enforced · 18 tested · 4 implemented · 15 partial · 20 gap · 9 contradicted · 2 owner-gated · 1 unknown. `docs_lint` passes.

## Scorecard recount (task 2)

Script: `scratchpad/scorecard.py`. It covers §1–§10, takes one row per `| ID |`, reads the first `**bold**` word in the Status column, and splits on unescaped pipes outside code spans. It also asserts that no ID appears twice.

```
$ python3 scorecard.py <orig matrix copy>
62 rows: 4 enforced · 18 tested · 4 implemented · 16 partial · 13 gap · 3 contradicted · 2 owner-gated · 2 unknown | other: {}
$ python3 scorecard.py docs/capstone-report/specs-compliance-matrix.md
73 rows: 4 enforced · 18 tested · 4 implemented · 15 partial · 20 gap · 9 contradicted · 2 owner-gated · 1 unknown | other: {}
```

- The "before" count reproduces the old `:31` figure exactly (62).
- The "after" count differs from 3b's forecast (16 partial / 8 contradicted) by one row. TIME-03 is `contradicted`, not `partial` (see M-TIME below).
- Core of the script (Python):

```python
for l in text.split('\n'):              # track "## N." sections; keep 1..10
    cells = split_outside_backticks(l)  # "\|" = literal pipe
    if cells[0] == 'ID': col = cells.index('Status'); continue
    if re.match(r'^[A-Z]+-\d+$', cells[0]):
        c[re.match(r'\*\*([a-z-]+)\*\*', cells[col]).group(1)] += 1
```

## Findings → disposition

| Finding | Disposition |
|---|---|
| 3b §2.1: 27 rows | **applied.** A check script confirms exactly 27 rows changed: LOCAL-01..04, ISO-02, KEY-02, SAFE-02/04/08, PRIV-04/06/08, LLM-01..03, AUD-02..04, TIME-01, MIG-02, GATE-02/03/05/06/07/09, GATED-06. Every other row only gained `— |` for the new **Planned by** column. A legend was added under the status table. Owner-gate cells now use the 3a canonical IDs (SQL-ECHO, D4-EXPORTS, VERIFIED-FALLBACK, EXPORT-QUESTIONS, GOV-D11, BG-REACH/GOV-BG, EMB-REV, AUD-INTERP, P1-DRIFT) |
| 3b §3: 11 new rows | **applied**, in their own sections: LOCAL-06/07, KEY-08, PRIV-09/10, AUD-05/06, TIME-03, GATE-12/13/14. No ID collides with an existing row. Plan 01 already uses GATE-14 with the same meaning. The "inferred" mark stays on LOCAL-06 and the "UNMEASURED" marks stay on KEY-08 and GATE-14 |
| M3 counts: GATE-03 `:137`, GATE-06 `:140`, overview `:211`, claims `:42` | **applied.** Re-measured by static count @40f590e. Vitest: 165 tests / 28 files (A 174/30, B 170/29). Playwright chromium: 28 tests / 5 files (31 `test(` declarations minus 3 in-body `test.skip(true,…)`; the `ui-full-verification` spec is excluded at `playwright.config.ts:72`). "155/25" are pass counts at `docs/features/TASK_LIST.md:794-795` (3b wrote `TASK_LIST.md:794`; the path is corrected here) |
| M4 PRIV-08 → gap; overview `:84` | **applied.** Verified `api/export.py:44,47,50` and `api/pinboards.py:13,495` |
| M5 PRIV-06 → contradicted | **applied.** Verified `database.py:46`, `profile_database.py:308`, `config.py:28`, `.env.example:14`, `dev.ps1:573`, `notification_scheduler.py:517-520` and `profiles.py:328` (main = B). `hide_parameters` has 0 hits @main/A/B |
| M6 stale cites | **applied.** Matrix `:71` → `rag.py:323-331`; `:77` → `:123-140` (`:126,128,133,134`); `:98` → `:438` @main / `:456` @B. Contract `:169`, `:211`. Overview `:111`, `:130`. Claims `:27`, `:51` |
| M6 overview `:185` (3→5 imports), `:188` (P3→P4) | **applied.** The `git grep -nE '^\s*(from modules\|import modules)' 40f590e -- src/backend/core` command gives 5 hits. `implementation-program.md:50` shows P4 is the doc-drift phase |
| M9 contract `:137`/`:146` eval-gate Verify | **applied.** Both now say that the gate prints PASS and then hangs (`rc=124`, 420 s, Win Py 3.13.7) and point to GATE-14 as unfixed and unowned. No fix is claimed. Evidence: `wave3/evalgate.out` ends `rc=124 elapsed=409s` |
| M10 (9 findings without rows) | **applied** through the 11 new rows |
| 3b minor 1 / 6A handoff (TIME-01 aware sites) | **applied, corrected.** 3b's "7 in 6 files" is wrong: the plain `datetime.now(timezone.utc)` form has 7 sites in **5** files. `git grep -nE '(dt_)?timezone\.utc' 40f590e -- 'src/backend/*.py' ':!src/backend/tests' ':!src/backend/core/time.py'` gives **12 lines in 8 files**: 9 `now(…utc)` calls in 7 files (including the alias form at `gamification.py:148` and `badge_evaluator.py:84`) plus 3 aware conversions (`auth.py:207`, `medications.py:84`, `badge_evaluator.py:54`). The command is stated in the TIME-01 row and in C-TIME-1 |
| **M-TIME (new, by reading)** | **applied.** `modules/badge_evaluator.py:84` builds an aware `now`, which flows to `earned_at=now` (`:101`) and then to `EarnedBadge(earned_at=…)` (`:157-163`). That column is a naive `DateTime` (`models/gamification.py:64-68`), reached from the dose route at `api/medications.py:1000`. So an aware value **is** persisted, and 3b's "none persisted" is false. TIME-03 → `contradicted`; C-TIME-1 records it. Not tested (read only) |
| minor 11 (name the method) | **applied.** Claims H9 now reads "16 in 6 files by AST; `git grep` gives 18 lines in 7 files (string literal at `test_profile_recovery.py:344,350`)". TIME-01 names grep (101) vs AST (109). The scorecard line names its counting method |
| 3b §2.2 contract bullets | **applied** for C-LOCAL-1/2, C-REDACT-1/2/3, C-SAFE-2/5, C-VERIFY-2, C-LLM-1/2, C-AUDIT-1/2, C-TIME-1, C-KEY-1, C-ISO-2 and C-GATE-1. A **Planned by** field was added to the field table |
| 3b C-VERIFY-2 "fix `rag.py:322-328` → `:323-331`" | **not applied.** C-VERIFY-2 has no such citation (stale lead). The cite was fixed where it actually occurs (matrix, overview, claims) |
| 3b C-LLM-1 Verify "add `--include=*.py` + `import llama_cpp` form" | **not applied.** Contract `:209` already has both. W-7 F-2 concerns the plan's grep |
| 3b SAFE-02 / C-VERIFY-2 `api/export.py:128-150` | **not applied as written.** `_fetch_observations` starts at `:130` (`:128-129` are blank), so `:130-150` is kept |
| 3b LOCAL-07 `rag.py:1256` compose_prompt | **corrected to `:1257`.** `:1256` is the "Step 2b" comment. The `:1256-1268` range is kept where it is cited as a range |
| 3b LOCAL-01 "B adds `src/backend/scripts/download_models.py`" | **reworded.** The file exists at main; B adds the `huggingface_hub` import (`:53`). The count of 7 @main / 8 @B was re-run and is unchanged |
| 3b LOCAL-02 source cell (dropped `AGENT.md` Configuration) | **not applied.** No finding targets it, so the original source is kept |
| Ledger: `core/auth.py:73` `Session.is_expired` aware | **applied** as a note in C-TIME-1 (Owner: auth code, ask first) and in TIME-03 |
| Contract `:383` / matrix GATED-06 / GATE-09 after D1 | **applied.** D1 is confirmed at `owner-decisions-2026-09-27.md:17-18` ("A: build real agents"; D1-scope "All 5") |
| 3b §4 (false doc claims) | **not fixed** (task 6). Matrix/contract rows point to the owning phase: P04 N1/N4/N5/N6/N8, P08, S-1, W-2, W-4, W-8 and W-10 |

## Files changed (4)

1. `docs/capstone-report/specs-compliance-matrix.md`: 27 rows replaced, 11 rows added, Planned-by column and legend, scorecard `:31`, unrun-checks rows, evidence basis, Last Updated 2026-09-28.
2. `docs/capstone-report/architecture-engineering-contract.md`: §2.2 bullets, M9 Verify wording, C-TIME-1 aware sites and auth note, `:383` D1 row, Planned-by field, Last Updated.
3. `docs/capstone-report/architecture-overview.md`: `:84`, `:111`, `:130`, `:185`, `:188`, `:211`, Last Updated.
4. `docs/capstone-report/claims-ledger.md`: `:27` (C2), `:42` (H2), `:49` (H9), `:51` (H11), Last Updated.

Scratch only (not in repo): `matrix_rows.py`, `contract_edits.py`, `scorecard.py`, and `*.orig.md` backups in the session scratchpad.

## Handoffs

| Target | Owner | Item |
|---|---|---|
| `implementation-program.md` P5 row | 6A / orchestrator | Route TIME-03 (aware sites, including the `badge_evaluator.py` persistence) into the P5 / plan 05 scope note. `badge_evaluator.py` is not ask-first; `core/auth.py` and `core/security.py` are |
| ledger | orchestrator | Record M-TIME. Record the 3b minor-1 correction (5 files, not 6; 12 lines in 8 files including the alias) |
| PRIV-10 / GATE-12 / GATE-14 / AUD-06 / KEY-08 / LOCAL-06 | orchestrator | Still unowned; the matrix says "unowned → proposal" |

## Must fix now

None blocking. `docs_lint` passes.

## Later (in my files; not targeted by any finding, so left alone per rule 5)

1. Matrix GATE-04: the unescaped `|| true` inside backticks breaks the GFM table (10 cells vs 8). This is pre-existing. The fix is `\|\| true`.
2. The contract still says "owner-gated" after D3, D4, D10 and D12 in these places:
   - reconciled-table rows `:386-389` (export scope, verified-only, HIPAA, external runner);
   - the C-LOCAL-1 exceptions bullet;
   - the C-REDACT-2 "Known exceptions (OWNER-GATED, not approved here)" header;
   - the C-LOCAL-2 Owner line (stale after D8).
3. Matrix GATED-08: "Recorded owner position: none" is stale after D3/D4 (P0-D-MOOT).
4. Overview `:87` still calls `logs/asclexis.log` UNVERIFIED; AUD-05 and C-AUDIT-2 now say it is false.
5. Overview §13 `:203` (`.claude/agents` "owner-gated") and `:205` (export scope) are stale after D1/D3/D4.

## New owner gates surfaced

- **None with a canonical ID.** M-TIME (`badge_evaluator.py` persists an aware value) needs a home. The proposal is the P5 scope; the owner decides.
- RL-EXPORTS (3a §3.3 orphan ID) is referenced in PRIV-10. It is not in the SHARED-RULES canonical list, so it is flagged here.

## docs_lint (full output)

```
$ python3 scripts/docs_lint.py
Docs lint passed.
rc=0
```

Next action: orchestrator reviews `git diff -- docs/capstone-report/specs-compliance-matrix.md` TIME-03 and decides the P5 routing for M-TIME.
