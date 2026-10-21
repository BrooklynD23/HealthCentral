# B-3 plan review (R-22, Codex)

**Last Updated:** 2026-10-21
**Owner:** repository owner
**Refresh Trigger:** the B-3 L1 extracts the revised plan as the first commit on its branch (R-22).

Codex CLI 0.163.0 (`gpt-5.6-sol`), read-only, on main `b902e0f`, run by L0 on the GPU WSL box. Contracts R-22: if Codex returns REVISE with task-level gaps, the B-3 L1 fixes them as the first commit on its branch. Output verbatim:

VERDICT: REVISE

1. **BLOCKER** — Owner gates are answered but neither recorded nor implemented. `docs/capstone-report/owner-decisions-2026-09-27.md:214-215` signs PR3-TIER and PR3-S5N, while `lane-B-interpretation-eval.md:92-93,352-357` and `queue.md:220` still call them open. The design lacks the chosen runtime low-tier block. **Fix:** mark both answered; specify low-tier detection and fail-closed outcome, enforce measurement on mid-or-higher tiers, require S5 counts of 180 block/200 allow, and add RED tests for both rules. B-4 remains the merge gate.

2. **BLOCKER** — Task 4 has no RED-first automated test or complete CLI contract. `lane-B-interpretation-eval.md:85` adds `--judge`, but T1–T6 at `:87` cover only judge/parser/routes; T7 is an already-green agent regression. Today `measure_prohibited_patterns.py:204-214` has no `--judge`. Input flag/schema, two-pass behavior, minimum counts, tier selection, and failure exits are unspecified, and ModelRunner-only use is not pinned. **Fix:** add a queued `test_measure_prohibited_patterns.py` first, proving current-main RED via rejected `--judge`; define the JSON schema and exact CLI, validate 180/200 counts, test two passes/metrics/hashes/tier, and require inference through `ModelRunner`/`advice_judge`.

3. **MAJOR** — The post-merge anchors and test inventory were not refreshed. The stated seam `rag.py:1276` is now `rag.py:1347`; `ValidatedResponse` is `:119-129`; `_generate_with_runner` is `:1427`; audit reasons are `assistant.py:1015` and `interpretations.py:606`; `get_model_runner` is `model_runner.py:242`; `wait_for` is `llama_cpp_provider.py:282-285`. Only the measurement-script flag lines remain exact. Contracts R-2 explicitly names `test_verified_only_consumers.py` (`contracts.md:151`), but `queue.md:220` omits it; its real query at `test_verified_only_consumers.py:169-172` lacks `judge_runner`. Merged citation tests also reach real query at `test_rag_structured_cite.py:229` and `test_rag_citation_prompt.py:104`. **Fix:** refresh against `b902e0f`, anchor by symbol, add the contract-required file, and record the complete observed RED list after running all real-query tests.

4. **MAJOR** — Acceptance is not runnable as written. The exact command at `lane-B-interpretation-eval.md:97` fails here with `python: command not found` (exit 127); successful zero-match `grep` exits 1; “full suite under flock” is not a command; and CI now has eight jobs (`ci.yml:10,38,76,94,127,199,221,243`), not “6/6.” **Fix:** paste the RUNBOOK command from `RUNBOOK.md:137-142`, use `! rg -n 'llama_cpp'` for both judge and measurement script, run T7 explicitly from repository root, and require all eight current CI jobs.

5. **MINOR** — The count delta is only predicted as “≈ +12” (`lane-B-interpretation-eval.md:87`) against today’s documented 2118 baseline (`CLAUDE.md:30-40`), contrary to measure-not-predict (`contracts.md:134-138`). **Fix:** enumerate the exact parametrized collection delta, then paste the measured head count and delta from the prescribed project venv. I could not independently measure it here because the available environment lacks required test dependencies.

No B-3 file currently proposes editing the four ask-first modules. The core design otherwise preserves local-first behavior by using the local `get_model_runner()` rather than the request/external runner.