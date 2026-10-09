You are a READ-ONLY adversarial reviewer for an architectural plan in the Asclexis repo (local-first medical-results app; FastAPI + per-profile SQLCipher vaults; local LLM via a ModelRunner facade in src/backend/core/). Working dir: /mnt/c/Users/DangT/Documents/GitHub/hc-para-r3 (git worktree at origin/main plus the plan). Reasoning effort: HIGH.

DO NOT edit, create, stage or commit any file. Do not run git write commands. Read code and docs; run read-only commands (grep, git show, git grep, cat, sed) only.

PLAN UNDER REVIEW: audit/2026-09-25/waves/scaffold/PARA-1-R3.md

Context: the owner decided "Stop using patterns": recall for prohibited paraphrase (diagnosis or dosing phrased indirectly in model output) must not come from adding regex patterns to src/backend/modules/interpret_safety.py. Today's 11 patterns stay as a floor. The plan must place recall in another layer, keep the app local-first (no network in product paths; all LLM calls through core/model_runner.py), say how recall/precision is measured without overfitting (the previous blind set is lost), choose fail-closed vs abstain, give a test plan, residual risks, and owner questions. Ask-first files (must not be edited by any option): modules/interpret_safety.py, redaction.py, faithfulness.py, verifier_agent.py. Rules: CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md.

Check, with file:line evidence from the code:
1. Section 2's flow table. Is it true that the agent path (modules/agent/) emits no model-written prose? Is modules/rag.py:1276 really the only seam every user-facing model-written answer passes through? Find any user-facing path that calls ModelRunner.generate/generate_async, model_selector.run_inference, or an external runner and returns its text, which the plan missed (include extraction, memory, summaries, feedback, export, any streaming).
2. Option C's design: does the proposed hook placement actually cover both /assistant/chat legacy and /observations/{id}/interpret-grounded? Does using get_model_runner() keep text off external runners? Concurrency/locking issues with a second llama.cpp call on the same model instance? Timeouts? Does anything in existing tests or callers break when rag.query makes a second model call?
3. Fail-closed rules: any path where a judge failure would fail open, or where blocking would persist the answer anyway?
4. Measurement design (§6): is the sealed-set protocol sound against overfitting and loss? Are the metrics and the floor/judge separation correct? Any privacy problem with capturing real outputs?
5. Options A, B, D: are their dismissals or trade-offs factually right? Is the recommendation justified, or is another option better?
6. Wrong or stale citations, contradictions with CLAUDE.md invariants, and anything an owner would need asked that is missing from §9.

Output: a verdict line (APPROVE / REVISE / REJECT), then numbered findings, each with severity (BLOCKER/MAJOR/MINOR), file:line evidence, and a concrete fix. Max 12 findings, most severe first. No praise.
