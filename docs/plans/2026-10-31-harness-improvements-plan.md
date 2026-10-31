# Harness improvements 2026-10-31 — plans for RSI-REPLAY-STRICT, RSI-GATE-ADVERSARIAL, RSI-ARCHIVE-LINEAGE and RSI-METRICS-VERSIONED

**Last Updated:** 2026-10-31 (L0: owner rows RSI-HARNESS-GO-EH, OQ-HI-DOC-ADDONLY, OQ-HI-STRICT, OQ-HI-FIXTURE and OQ-HI-PRIOR answered 2026-10-31, recorded in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md), so rows E-H are ready; Opus planner on `4ffcd45f`: four further RSI-loop improvements (rows E-H) from the [harness landscape research](../research/2026-10-31-harness-landscape/00-README.md), per the owner instruction of 2026-10-31 (part of RSI-HARNESS-GO). Each row is **planned, awaiting owner approval**, not ready)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner); **owner answers recorded 2026-10-31 (L0 note):** RSI-HARNESS-GO-EH (all four of E-H), OQ-HI-DOC-ADDONLY (a), OQ-HI-STRICT (a), OQ-HI-FIXTURE (a) and OQ-HI-PRIOR (a) are answered in owner-decisions `owner-decisions-2026-09-27.md:446-449`; rows E-H are **ready** in the queue. The sentence that follows is the planner's original text, kept for the record. Docs only. **No owner approval is recorded here.** Every row needs its own owner yes (gate **RSI-HARNESS-GO**, one answer per row) before build-item may claim it, and rows F and G also need the owner questions named in them. Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md). The drafted owner questions at the end are not asked; L0 has them reviewed before AskUserQuestion.
**Base measured:** `origin/main` @ `4ffcd45f` (2026-10-31, #423 merged). Every `file:line` below was re-read by the planner on that commit. Rows A-D ([2026-10-31-rsi-harness-plan.md](2026-10-31-rsi-harness-plan.md)) are planned but not built on this commit, and they move lines in `logic.ts`, `rsi.test.ts`, `rsi-loop.js` and `build-program.js`; each row here re-anchors in Task 0 on the commit it starts from. `claude plugin test .claude/mods/asclexis-rsi` → `29 pass`, `0 fail` (planner, this machine).
**Refresh Trigger:** a merge of any row A-H; any edit to `.claude/mods/asclexis-rsi/` or `.claude/workflows/rsi-loop.js`; an owner answer to RSI-HARNESS-GO or a question below; a change to the rsi-runs `summary.json` format.

Queue rows: [queue.md, "Planned 2026-10-31, harness improvements"](2026-10-15-build-program/queue.md#planned-2026-10-31-harness-improvements). Research and the full transfer matrix: [harness landscape](../research/2026-10-31-harness-landscape/05-transfer-matrix.md). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d.

**Rules that hold for every row here** (the same as rows A-D, restated where they bind).
- **Privacy (mod README `:17`):** metadata only. No row, summary, archive row or fixture output holds command text, tool output, prompts or user paths. Every new field is a fixed literal, an enum value, a count, a run id matching `^[A-Za-z0-9._-]{1,40}$`, a git object id matching `^[0-9a-f]{40}$`, or a cluster key `tool/error_class` built from logged literals. Gate `reason` strings stay where they are today (`rsi-loop.js:351`) and are never copied into a new field.
- **RSI-4's human gate is unchanged** (`owner-decisions-2026-09-27.md:203`): no row is agent-merged; the owner merges. Every row edits files outside rsi-loop's ALLOW list (`rsi-loop.js:34-38`), so rsi-loop can never promote any of them; they are normal build-item rows.
- **ALLOW and DENY are unchanged by every row.** Row F is the only row that changes a gate function (`gateNumstat`), and only if the owner answers OQ-HI-DOC-ADDONLY (a); that is an explicit owner question, not a planner decision. Row E makes the replay test stricter, which narrows what rsi-loop can promote; that is also put to the owner (OQ-HI-STRICT).
- **Test running:** Sonnet 5.5 implements; Haiku 5.5 (medium) runs `claude plugin validate` / `claude plugin test` and node fixtures (MODEL-ROUTING-SONNET-IMPL). No pytest in any row (collected delta 0), no pyslot, no code slot.

**Order.** E needs RSI-RULE-TOOLFIELD (B) merged (same `rsi.test.ts` and `logic.ts` check functions). F, G and H all edit `rsi-loop.js`, which rows C and D also edit, so they run strictly after D, one at a time: **D → F → G → H**. F goes first because its fixture pins the gate functions before G and H touch the file. E is file-disjoint from F, G and H, so after B and D: **E ‖ F**, then G, then H.

---

## RSI-REPLAY-STRICT (row E) — each rule is necessary for its positive cases; rule text is linted

**Source:** DeepSeek V3.2's environment filter (F2P ≥ 1, P2F = 0; [04-deepseek-harness.md §3](../research/2026-10-31-harness-landscape/04-deepseek-harness.md#3-verifiable-tasks-in-the-model-reports)), adapted; OpenClaw incidents and Trojan's Whisper (scanners and LLM critics are evaded; [02-openclaw.md §4](../research/2026-10-31-harness-landscape/02-openclaw.md#4-skill-market-incidents-why-scanners-are-not-the-boundary)). Kind: **HARNESS, RSI** (mod test; no slot).

**Facts (re-read on `4ffcd45f`).**
1. The replay test (`rsi.test.ts:24-43`) runs each case through `$.tool.call` and asserts `deny` / `hint` / `pass` for that case's own rule id; `:44-50` requires a positive and a negative case per rule. Nothing asserts that a rule is *needed*: if rule Y already hints a case, a new rule R placed before Y gets its positive case green while duplicating Y's coverage; placed after Y, the case fails today, but only because the hint id differs.
2. P2F is already enforced: the whole replay set must pass in the rsi-loop Gate (`rsi-loop.js:318`, `:332`) and in CI (`ci.yml:337-338`).
3. **F2P in the literal sense is tautological here.** A new rule's positive case always fails on the old table, because the old table cannot emit the new rule id. Planner probe: mod copied to a scratch dir with `no-such-file-path` removed from `rules.ts` → `(fail) replay set > no-such-file-path-pos-1`, `-pos-2`, `27 pass, 2 fail`. The meaningful check is **necessity**: with the rule removed, no other rule fires on its positive cases. Planner probe on `4ffcd45f` (`checkBefore` / `checkAfter` over `RULES` minus the case's rule): `positive cases 10, covered by another rule 0`. So the new test is GREEN on today's table.
4. A hint's `message` is appended to what the model reads after the tool result (`register.ts:91`): it is the persistence channel the OpenClaw incidents describe. The only check on its text is the Codex critic's phrase list (`rsi-loop.js:284-289`), which runs only on the rsi-loop path, and an unavailable critic admits the candidate (`:334`, `:341`). A hand-written rule PR gets no text check at all.
5. All 7 seed messages are 102-185 characters, printable ASCII, contain no `http`, and none of the critic's phrases (planner probe). `checkBefore` / `checkAfter` take a `rules` parameter (`logic.ts:36`, `:47`).

**Design (test-only; no change to `logic.ts`, `rules.ts`, `register.ts` or `cases.ts`).** New `describe('rule table strictness')` in `rsi.test.ts`:
- `every rule is necessary for its positive cases`: for each case with `expect` `deny` or `hint`, the same check function over `RULES.filter(r => r.id !== c.rule)` returns `undefined` (deny cases via `checkBefore`, hint cases via `checkAfter` with `failed` as in `:29`). Uses whatever per-tool field matching RSI-RULE-TOOLFIELD merged.
- `rule text is plain and bounded`: for every rule, `message` 1-300 characters and `source` 1-200, both `^[\x20-\x7e]+$`; neither matches `/https?:\/\//i`; neither matches the critic's phrase list (copied as one regex from `rsi-loop.js:286`, with a comment naming the source line so a future edit updates both); `match`, `command` and `absent` compile with `new RegExp` (deny already fails closed if they do not, `register.ts:94-96`; this makes it a test failure instead of a held call).
- The helpers are local to the test file. The RED for each test is a planted bad table, asserted inside the test: a test-local copy of `RULES` plus a duplicate of `no-such-file-path` under another id must report one overlap; a planted message with `https://x`, one with `ignore previous`, one of 301 characters and one with a non-ASCII character must each be reported. So each test fails if its helper is a no-op.

**Tasks (test-first).**
0. **Task 0 (read-only).** Re-run Facts 3 and 5 on the start commit (rows A and B may have added rules and cases) and paste the counts. If any merged rule already fails necessity or the lint, stop and tell L0: that is an owner question about that rule, not something this row fixes.
1. **RED.** The two tests with their helpers stubbed to return no findings: the planted-table assertions fail. Paste the `(fail)` lines.
2. **GREEN.** Real helpers. Paste `claude plugin test` (N pass, 0 fail).
3. **Mutation check (pasted, scratch only).** In a scratch copy of the mod (`git archive HEAD .claude/mods/asclexis-rsi | tar -x -C <scratch>`), add a rule that duplicates `no-such-file-path` and a case pair for it; `claude plugin test <scratch>/.claude/mods/asclexis-rsi` must show `(fail) rule table strictness > every rule is necessary …`. Nothing from the scratch copy is committed.
4. README `:34-35`: one sentence that a rule must be necessary for its positive cases and its message is linted.

**Acceptance:** `Validation passed`; `claude plugin test` → `N pass, 0 fail` with N = the count on the start commit + 2, RED pasted; mutation check pasted; CI `rsi-replay` green; `git diff origin/main --stat` lists only `rsi.test.ts` and `README.md`. Est 1.5 h.

**Files:** `.claude/mods/asclexis-rsi/rsi.test.ts` (new describe only), `.claude/mods/asclexis-rsi/README.md` (`:34-35`).

**depends_on:** RSI-RULE-TOOLFIELD merged. **Never beside:** RSI-ERRCLASS-NONBASH, RSI-RULE-TOOLFIELD, any open rsi-loop RSI PR (`gh pr list --search "rsi: in:title" --state open`; such a PR's new rule must pass this test, so it merges first or is re-gated after). **Owner gates:** RSI-HARNESS-GO (row E); OQ-HI-STRICT; owner merges (RSI-4). **Stops:** a merged rule that fails the test; any need to edit `rules.ts` or `cases.ts`.

---

## RSI-GATE-ADVERSARIAL (row F) — an adversarial fixture for the gate functions, and the recurring-failures deletion gap

**Source:** AlphaEvolve's leaky verifier (Georgiev, Gómez-Serrano, Tao, Wagner: "it always eventually figured out a way to cheat") and DGM's faked test log ([03-deepmind-evaluator-loops.md §1-2](../research/2026-10-31-harness-landscape/03-deepmind-evaluator-loops.md#1-alphaevolve-and-the-leaky-verifier)): a loop finds the gap in its verifier, so the verifier needs its own tests. Kind: **HARNESS, RSI** (workflow script + fixture; no slot).

**Facts (re-read on `4ffcd45f`).**
1. The deterministic gate is `gateDiff` (`rsi-loop.js:55-67`, over ALLOW `:34-38` and DENY `:39-54`), `gateNumstat` (`:70-81`) and `parseCodexVerdict` (`:122-128`). No committed test exercises them (row A-D Fact: `grep -rln "gateNumstat"` finds only `rsi-loop.js` and plan docs); the repo pattern is a scratch `sed` + node fixture (lane E §2.25a), and committing one is drafted as OQ-RSI-FIXTURE.
2. **Gap found by the planner's probe.** `gateNumstat` checks additions-only for `rules.ts` and `cases.ts` only; every other path is skipped (`:77`). `gateNumstat("0\t12\tdocs/agentic/recurring-failures.md")` → `ok: true`. The Codex critic gets only the `rules.ts` / `cases.ts` diff (`:319`) and Publish says so (`:343-344`). So a candidate that deletes recurring-failures rows passes every deterministic gate; only the owner's review stops it. Deleting a recorded failure mode removes a recheck that CLAUDE.md §4 tells every agent to read.
3. Other probe results (all as intended today): `gateDiff` rejects `<mod>/hooks/../hooks/rules.ts`, `Scripts/x.sh`, `.\scripts\x.sh`, `<mod>/rsi.test.ts`, `.claude/workflows/rsi-loop.js`, an empty list, and any list containing a non-ALLOW path; accepts `./<mod>/hooks/rules.ts`. `gateNumstat` rejects a deletion in `rules.ts`, a binary row and empty input; accepts a rename row `1\t0\t<mod>/hooks/{rules.ts => r.ts}` (the rename is caught by `gateDiff` on the new name, so only the pair is safe). `parseCodexVerdict` accepts BOM + `VERDICT: PASS` and `VERDICT: PASS\r`, and returns `UNAVAILABLE` for ` VERDICT: PASS`, `verdict: pass`, `VERDICT: PASS and REVISE` and `null`.

**Design.**
- **Fixture.** A node script that extracts `const ALLOW … ` through the end of `gateNumstat` (`sed -n '/^const ALLOW = \[/,/^const namesOf/p'`, prefixed with the `MOD` constant from `:18`) and `parseCodexVerdict` (`sed -n '/^function parseCodexVerdict/,/^}/p'`), and asserts a table: every Fact 3 row; every DENY reason (one path each: `src/backend/tests/x.py`, `__tests__/x`, `e2e/x`, `a.test.ts`, `test_x.py`, `scripts/x`, `.github/x`, `docs/threshold.md`, each ask-first file, `core/auth.py`, `security/encryption/x`); absolute and `..` paths; the rename pair asserted as a pair (`gateDiff` on its name list fails, so the candidate fails). If the owner answers OQ-HI-FIXTURE (a), the fixture is committed as `.claude/workflows/tests/rsi-gate.fixture.mjs` and run by one new step in the `rsi-replay` CI job (`ci.yml:317-338`); if (b), it stays the scratch pattern and its output is pasted in the PR.
- **Gap fix (only if OQ-HI-DOC-ADDONLY (a)).** `gateNumstat`'s additions-only list (`:77`) gains `docs/agentic/recurring-failures.md`. Nothing else in the gate changes. If (b), the fixture asserts today's behaviour (`ok: true` for a doc deletion) with a comment naming the owner answer, so the decision is pinned either way.
- ALLOW, DENY, `gateDiff`, `parseCodexVerdict`, `mergeReflections` and the prompts are unchanged.

**Tasks (test-first).**
0. **Task 0.** Re-anchor on the start commit (after D); confirm the two `sed` ranges extract runnable code; read the owner answers to OQ-HI-FIXTURE and OQ-HI-DOC-ADDONLY from owner-decisions and quote them.
1. **RED.** With OQ-HI-DOC-ADDONLY (a): the fixture row `0\t12\tdocs/agentic/recurring-failures.md` → `ok: false` fails on the start commit. With (b): RED is the `sed` extraction printing nothing for a misspelt range, shown once, then the fixture green on the unchanged gate.
2. **GREEN.** The one-line `:77` change (if (a)); the fixture; the CI step (if (a) on OQ-HI-FIXTURE).
3. **Dry run.** `rsi-loop` with `{dry_run: true, run_id: '<date>-gatefix-dry'}`; paste the result's `candidates` and `rejected` (expected unchanged behaviour on real candidates).

**Acceptance:** fixture output `gate ok (N)` with RED pasted; `git diff origin/main -- .claude/workflows/rsi-loop.js` shows at most the `:77` list change; `claude plugin test` unchanged; CI green including the new step if added. Est 2 h.

**Files:** `.claude/workflows/rsi-loop.js` (`gateNumstat` `:77` only, conditional), `.claude/workflows/tests/rsi-gate.fixture.mjs` (new, conditional), `.github/workflows/ci.yml` (`rsi-replay` job, one step, conditional), `docs/agentic/rsi-runs/README.md` (one line: the gate fixture and how to run it).

**depends_on:** RSI-OWNER-NOTES merged (same file). **Never beside:** RSI-MINE-OUTCOMES, RSI-OWNER-NOTES, RSI-ARCHIVE-LINEAGE, RSI-METRICS-VERSIONED; any other PR on `rsi-loop.js` or `.github/workflows/ci.yml` (contracts §b). **Owner gates:** RSI-HARNESS-GO (row F); **OQ-HI-DOC-ADDONLY** (changes a gate function: explicit owner question); **OQ-HI-FIXTURE**; owner merges (RSI-4). **Stops:** any change to ALLOW or DENY; a fixture row that shows a gate admitting a path outside ALLOW (stop and tell L0: that is a security finding, not this row's fix).

---

## RSI-ARCHIVE-LINEAGE (row G) — every candidate archived as fixed fields, with lineage, repeats and a saturation signal

**Source:** DGM's archive ("a transparent, traceable lineage of every change", which is how the faked log was found) and ShinkaEvolve's novelty filter ([03-deepmind-evaluator-loops.md §2-3](../research/2026-10-31-harness-landscape/03-deepmind-evaluator-loops.md#2-darwin-gödel-machine-gaming-caught-by-lineage)). Kind: **HARNESS, RSI** (workflow script; no slot).

**Facts (re-read on `4ffcd45f`).**
1. Only gate-rejected candidates are archived, as `{id, reason, diff_stat, run_id}` lines in the local, git-ignored `.claude/logs/rsi/archive.jsonl`, by the Publish agent (`rsi-loop.js:366`). Publish runs only when there are candidates; the common "nothing worth proposing" path returns at `:278` with `reflections` and `codex_reflections` in the result, and L0 archives that result as `summary.json` (rsi-runs README `:21`).
2. Accepted candidates appear only as ids in `summary.accepted` (`:359`) and as PRs; declined reflections are not linked to earlier runs; no field says "this cluster was declined last time too". Five run folders exist (rsi-runs README `:36-42`); the README's Runs table and the capstone §6 count "consecutive runs with zero promotions" by hand.
3. Every rejection `reason` starts with a fixed prefix written by code: `propose:` (`:311`), `gate(diff):` (`:313`), `gate: validator agent failed` (`:326`), `gate(diff, recheck):` (`:328`), `gate(numstat):` (`:330`), `claude plugin validate exit` (`:331`), `claude plugin test (replay) exit` (`:332`), `codex-critic:` (`:339`). The tails hold paths and critic text, so they are never copied into a new field.
4. Reflect already avoids duplicates of *existing rules* (`already_covered_by`, `:163`, `:244`); nothing checks against *earlier candidates*.

**Design.**
- New self-contained `function archiveRows(runId, reflections, codexReflections, proposed, results, max)`: one row per reflection from either source, `{run_id, cand, cluster, target_file, source, stage}`. `stage` enum: `declined` (`worth_proposing` false), `capped` (worth proposing but cut by `max`, `:115-118`), `propose-stopped`, `gate-diff`, `validator-failed`, `gate-numstat`, `validate`, `replay`, `codex-revise`, `accepted`, mapped from the Fact 3 prefixes in memory (anything unmatched → `unknown`). `cluster` must match `^[A-Za-z0-9_.*-]{1,80}/[a-z0-9-]{1,40}$`, `target_file` the existing enum (`:161`), `source` `claude | codex`, `cand` the `rsi-<run>-<n>` id or `null`; rows failing any check are dropped with a count note.
- New self-contained `function priorStats(rows, clusters)`: from validated prior rows, per top cluster `{declined, rejected, accepted, last_run}` counts, and `repeat_of` = the latest prior `run_id` with the same `cluster` + `target_file`.
- **Prior rows (Mine, one step).** Mine reads the committed `docs/agentic/rsi-runs/*/summary.json` in the main checkout and returns `prior_rows`: each summary's `archive_rows` if present, else its `reflections` / `codex_reflections` mapped to `declined` rows (the format of the archived runs). JS keeps only rows that pass the same checks as `archiveRows` output (OQ-HI-PRIOR).
- **Use.** The per-cluster counts go into the Reflect prompt as context, with one sentence: a cluster declined in two or more earlier runs, with no new rule since, needs new evidence to be worth proposing. They are **not** a filter: no JS drops a candidate for being a repeat (conservative: a better second try must stay possible; the owner sees `repeat_of`).
- **Saturation.** `summary.saturation = {runs_without_promotion, saturated}`: `runs_without_promotion` from prior summaries' `accepted` lengths, newest first; `saturated` is true when this run proposes 0 and every top cluster has `declined >= 2`. It is a report, not a stop.
- `archive_rows`, `prior` and `saturation` go into `summary` (`:356-362`), the `:278` return and the final return (`:373-380`). Publish's archive line (`:366`) and PR text (`:367`) are unchanged.

**Tasks (test-first).**
0. **Task 0.** Re-anchor after D (row D adds `owner_notes` to the same returns). Confirm the Fact 3 prefixes are unchanged; list which archived `summary.json` files carry `reflections` (expected: those written on the `:278` path) and paste the count.
1. **RED (fixture, scratch `sed` pattern).** `sed -n '/^function archiveRows/,/^}/p'` and the same for `priorStats`; a node script asserts: each Fact 3 prefix → its stage; a planted `codex-critic: SECRET-123 /home/x/patient.pdf Jane` → `codex-revise`, and the serialised rows contain none of the planted strings; a reflection with cluster `Bash/no such file` dropped; a target outside the enum dropped; 5 worth-proposing with `max` 3 → 2 `capped`; `priorStats` on 3 prior runs declining `Bash/other` → `declined: 3`, `repeat_of` the newest; `saturated` true only when candidates = 0 and every top cluster has `declined >= 2`; non-array inputs → `[]` with a note. RED: both `sed`s print nothing.
2. **GREEN.** The two functions, the Mine step, the Reflect sentence, the three return sites.
3. **Dry run.** `{dry_run: true, run_id: '<date>-archive-dry', since: <last run date>}`; paste `archive_rows`, `prior` and `saturation`; secrets grep as in rsi-runs README step 4.

**Acceptance:** fixture `archive ok (N)` with RED; dry-run result pasted with `prior` non-empty (the 2026-10-31 summary carries reflections); `git diff origin/main -- .claude/workflows/rsi-loop.js` leaves ALLOW, DENY, the gate functions, `mergeReflections`, the target enum, the Codex prompts and Publish's PR text unchanged. Est 3 h.

**Files:** `.claude/workflows/rsi-loop.js` (`MINE_SCHEMA` `:131-154` + `prior_rows`; Mine prompt `:217-224`, one step; Reflect prompt `:243-246`, one sentence; new `archiveRows`, `priorStats`; `summary` `:356-362`; returns `:278`, `:373-380`), `docs/agentic/rsi-runs/README.md` (one line: `summary.json` carries `archive_rows`, `prior`, `saturation`, fixed fields only).

**depends_on:** RSI-GATE-ADVERSARIAL merged (file order). **Never beside:** rows C, D, F, H; any other `rsi-loop.js` PR; a running build-program or rsi-loop during the dry run. **Owner gates:** RSI-HARNESS-GO (row G); **OQ-HI-PRIOR**; owner merges (RSI-4). **Stops:** any field that would need free text; any proposal to filter candidates on repeats (that is an owner question, not this row).

---

## RSI-METRICS-VERSIONED (row H) — rule hit counts, never-fired rules, a first-try-ready rate and the harness version

**Source:** Hermes's curator (usage counts drive the lifecycle; [01-hermes.md §3](../research/2026-10-31-harness-landscape/01-hermes.md#3-gates)), DeepSeek's pass@1-vs-cost reporting pinned to a named harness ([04-deepseek-harness.md §3](../research/2026-10-31-harness-landscape/04-deepseek-harness.md#3-verifiable-tasks-in-the-model-reports)). Kind: **HARNESS, RSI** (workflow script; no slot).

**Facts (re-read on `4ffcd45f`).**
1. `metrics` (`MINE_SCHEMA` `:142-149`) holds tool calls, failure rate by tool, retries, items, retries per item and `tokens_per_item`. In every archived `summary.json`, `items` is 0 and `tokens_per_item` is null or absent. No metric counts rule hits, though every row logs `guard` and `hint` ids (`register.ts:81-82`).
2. Rule hits in the archived rsi-logs (planner count): `no-such-file-path` 38, `pkill-self` 13, four rules 1 each, `llama-cpp-no-compiler` 0.
3. Nothing in a summary names the harness that produced it, so capstone §7 can only say windows differ.
4. Row C adds `outcomes` with `stop_class` per build-item result (`done-ready`, `done-draft`, `failed`, …).

**Design.**
- Mine step 5 (`:222`) also returns `rule_hits: {id: count}` from the `guard` and `hint` fields, and `harness: {workflows_tree, mod_tree}` from `git rev-parse origin/main:.claude/workflows origin/main:.claude/mods/asclexis-rsi` in the main checkout.
- New self-contained `function versionedMetrics(metrics, ruleIds, outcomes)`: keeps `rule_hits` entries whose id is in `existing_rule_ids` and whose count is a non-negative integer; `never_fired` = rule ids with no hit in the window; `harness` kept only if both ids match `^[0-9a-f]{40}$`; `first_try_ready = {ready, items, rate}` from C's validated outcomes (an item counts once, by its first entry; `rate` null when `items` is 0). No cost metric (no token source).
- Added to `summary.metrics`. `never_fired` is a **report**: no rule is retired, deleted or disabled by any code (that would be a weakening; `gateNumstat` is additions-only). The rsi-runs README Runs table gains a `harness` column (short tree ids) filled by L0 from the summary.

**Tasks (test-first).**
0. **Task 0.** Re-anchor after G; confirm row C's `outcomes` field name and enum on the start commit.
1. **RED (fixture, scratch `sed`).** `versionedMetrics`: hits for an unknown id dropped; a negative or non-integer count dropped; `never_fired` correct for a 3-rule table with one hit; a 39-character or non-hex tree id → `harness` null; outcomes `[{id:'A', stop_class:'done-ready'}, {id:'A', stop_class:'failed'}, {id:'B', stop_class:'escalated'}]` → `{ready: 1, items: 2, rate: 0.5}`; no outcomes → `rate: null`. RED: the `sed` prints nothing.
2. **GREEN.** The function, the Mine step addition, `summary.metrics`, README column.
3. **Dry run** with a pasted `metrics` block.

**Acceptance:** fixture `metrics ok (N)` with RED; dry run pasted with `rule_hits` and `harness` filled; `rsi-loop.js` diff limited to `MINE_SCHEMA` metrics, Mine step 5, the new function and the `summary` line. Est 2 h.

**Files:** `.claude/workflows/rsi-loop.js` (`MINE_SCHEMA` metrics `:142-149`; Mine prompt `:222`; new `versionedMetrics`; `summary` `:361`), `docs/agentic/rsi-runs/README.md` (Runs table column, `:36-42`).

**depends_on:** RSI-MINE-OUTCOMES merged (needs `outcomes`); RSI-ARCHIVE-LINEAGE merged (file order). **Never beside:** rows C, D, F, G; any other `rsi-loop.js` PR. **Owner gates:** RSI-HARNESS-GO (row H); owner merges (RSI-4). **Stops:** any code path that disables, deletes or reorders a rule.

---

## Rejected ideas (with reasons)

| Idea (source) | Why not here |
|---|---|
| Background reviewer that reads the conversation (Hermes `background_review.py`: full snapshot or digest + verbatim recent turns) | Violates metadata only (mod README `:17`): transcripts can hold PHI, secrets and paths. Our Mine sees rows of literals only. |
| Self-authored skills or rules applied without review (Hermes `write_approval: false` default; OpenClaw `auto` for new installs) | Violates the RSI-4 human gate: the owner merges every promotion. |
| Default-on upload of session logs; telemetry with no built-in redaction (DeepSeek Harness `session-log-deepseek` `enabled: true`; `session-telemetry`) | Violates redaction before anything leaves and local-first. Our logs are git-ignored and committed only by L0 after a secrets grep. |
| An LLM or signature scanner as the security boundary (ClawHub VirusTotal + Code Insight) | Evaded in practice (Trail of Bits; Trojan's Whisper: 94%). The Codex critic stays advisory, behind deterministic gates and the owner; row E adds a deterministic text check. |
| Identical-failure breaker on tool + input fingerprint + error class, all tools (OpenClaw loop detection) | No evidence of need: 0 `retry: true` among 14,270 archived tool rows, 1 retry in each mined window (8210 and 7499 calls). A new deny path can block legitimate waits and re-runs. Revisit if a run's `retries` rises well above that. |
| Proposal bound to the target file's hash, refused if it moved (Hermes, claim unconfirmed; OpenClaw revision binding) | The owner merges a specific PR head on GitHub; concurrent RSI PRs append to the same arrays and conflict there; CI runs on the PR. Low value for the added state. |
| Held-out replay cases kept out of proposer context | The Sonnet proposer has the whole worktree (`rsi-loop.js:295-296`), so an in-repo held-out set is readable and would give false assurance. The real version is the sealed set OW-3 / S5 already in the 2026-10-17 package, waiting on the owner. |
| Frozen task set and cost per completed item | A build item costs hours of agent time, so replaying a frozen set per harness version is not small; `tokens_per_item` has no source. Row H keeps a per-window rate tagged with the harness version instead. |
| Retire never-fired rules; restore ledger (Hermes curator) | Removing a guard is a weakening (`gateNumstat` additions-only); git history is already the ledger. Row H reports `never_fired` only. |
| Pin plugin / skill hashes and rescan (OpenClaw) | The repo installs no marketplace skills; vendored skills are in git (changes are reviewed diffs); CI pins the CLI (`ci.yml:332`); the Codex version is already logged (`rsi-loop.js:197`, `:360`). User-level plugins are the owner's machine config. |
| Evolutionary search, islands, Pareto over prompts; split judge rubric with length penalty (AlphaEvolve, ShinkaEvolve, GEPA, Hermes PLAN.md) | Out of scope per the applicability report (`docs/plans/2026-10-10-rsi-loop-applicability-report.md:20`, `:30`); our candidates are at most 3 data-only edits per run. Row E caps message length deterministically. |

---

## Drafted owner questions (not asked)

**L0 note 2026-10-31: all five questions below were asked by L0 AskUserQuestion and answered the same day.** RSI-HARNESS-GO rows E-H: **all four** (owner-decisions row RSI-HARNESS-GO-EH). OQ-HI-STRICT: **"Necessity + lint (Recommended)"** = (a). OQ-HI-DOC-ADDONLY: **"Yes, additions-only (Recommended)"** = (a). OQ-HI-FIXTURE: **"Commit gate fixture + CI step"** = (a). OQ-HI-PRIOR: **"Mine reads past run summaries"** = (a). The last two were one multi-select question, both chosen. Rows: `owner-decisions-2026-09-27.md:446-449`. The bullets below are the drafts as planned, kept for the record.

- **RSI-HARNESS-GO, rows E-H** (one per row). "Build row <id> as planned in `docs/plans/2026-10-31-harness-improvements-plan.md`?" Options: (a) yes, as planned (Recommended); (b) not now. No row is claimed before its yes is recorded on `origin/main`.
- **OQ-HI-STRICT** (row E). "Make the RSI replay test stricter: a new rule fails the test if another rule already handles its positive cases, and rule messages must be short plain ASCII with no links or injection phrases. This narrows what rsi-loop can promote; it does not change ALLOW, DENY or your merge gate." Options: (a) yes (Recommended: all 7 current rules pass; it stops duplicate rules and holds the text check when Codex is unavailable); (b) lint only, no necessity test; (c) no.
- **OQ-HI-DOC-ADDONLY** (row F; changes a gate function). "The RSI gate lets a candidate delete rows from `docs/agentic/recurring-failures.md` (the additions-only check covers only `rules.ts` and `cases.ts`, and Codex never sees the doc). Make the doc additions-only for rsi-loop candidates too?" Options: (a) yes (Recommended: conservative; a recorded failure mode is a recheck agents rely on, and a correction can still be made by a normal PR); (b) no, your review is enough.
- **OQ-HI-FIXTURE** (row F; a narrower form of OQ-RSI-FIXTURE). "Commit the gate fixture and run it in the `rsi-replay` CI job, so every change to `rsi-loop.js` re-tests the gate?" Options: (a) yes, for the gate fixture only (Recommended: a gate test that runs only once protects nothing afterwards); (b) keep the scratch pattern and paste output in the PR.
- **OQ-HI-PRIOR** (row G). "May rsi-loop's Mine read the committed run summaries in `docs/agentic/rsi-runs/` to see earlier candidates (fixed fields only: cluster, target file, stage, run id)?" Options: (a) yes (Recommended: those files are already committed and metadata only); (b) no, use only the local git-ignored archive on the machine that runs the loop.
