# DeepSeek Harness (`dsh`) and DeepSeek's verifiable agent tasks

**Last Updated:** 2026-10-31
**Owner:** repository owner
**Refresh Trigger:** a `dsh` release that changes `session-log-deepseek` defaults or session-telemetry redaction; a DeepSeek report that describes a harness-side improvement loop; an owner answer in [the harness improvements plan](../../plans/2026-10-31-harness-improvements-plan.md#drafted-owner-questions-not-asked).

> **Point-in-time research (2026-10-31).** Docs only. Haiku notes re-checked by the Opus planner on 2026-10-31. The `dsh` repo was read through the GitHub API as raw text (`gh api repos/deepseek-ai/deepseek-harness/...`, branch `master`); none of its code was run. Other pages via WebFetch summaries. Markers: **[V]** confirmed; **[C]** changed after the re-check; **[X]** not confirmed, dropped. Summary: [00-README.md](00-README.md).

## 1. What it is

- `deepseek-ai/deepseek-harness`, created 2026-08-13T11:56:32Z, MIT (GitHub API) [V]. The README calls it "an open-source agent harness developed by DeepSeek AI", plugin-based, "developer preview", with "COMPATIBILITY-BREAKING CHANGES" to come [V].
- `SAFETY.md:7`: "experimental developer-preview software. It has not undergone a security audit and must not be treated as secure or production-ready" [V].
- **No self-improvement loop in the harness.** The research agent found none in docs and READMEs; the planner did not read the source either. Trajectory-based improvement is in DeepSeek's model reports (§3), not in `dsh`.
- Release tag, Cordis paper and star-count claims: **[X]**, not re-read.

## 2. Logging and privacy

- **"Model-visible means logged."** "Every model request must be reconstructable from the log" (`docs/architecture.md:128`) [V]. `assistant/attempt` "retains settled failed, retried, cancelled, and stream-error attempts without adding model history" (`:124`) [V]: failed attempts are kept apart from what the model sees. Tool hooks run `tools/pre-execute -> tools/execute -> tools/post-execute` (`:99`) [V].
- **Session-log upload is on by default.** `packages/session/session-log-deepseek/README.md` [V]: "Incremental canonical session-log upload for official DeepSeek LLM API requests"; the `enabled` key defaults to `true` (`:31`); "Shipped profiles mount the plugin" (`:34`); a Web settings switch turns it off (`:36`). It applies to requests to the official DeepSeek API.
- **No built-in telemetry redaction.** `packages/session/session-telemetry/README.md` [V]: "This package ships no rules: with no listener mounted, records reach the backend exactly as captured" (`:54`), "including any credentials embedded in file contents or command output" (`:118`). A throwing redaction listener withholds that record (fail closed, `:54`).

## 3. Verifiable tasks in the model reports

- **DeepSeek-V3.2** (arXiv 2512.02556, https://arxiv.org/html/2512.02556) [V]: code-agent environments are kept only if "applying the gold patch results in a non-zero count of false-to-positive (F2P) test cases" and "a zero count of pass-to-fail (P2F) test cases" **[C]** (the paper writes "false-to-positive", not "fail-to-pass"; the filter is the same). The general-agent pipeline "synthesizes 1,827 task-oriented environments", "hard to solve but easy to verify". "For reasoning and agent tasks, we employ rule-based outcome reward, length penalty, and language consistency reward" **[C]** (this is for reasoning and agent tasks in general, not only these environments).
- **DeepSeek-V4.1-Flash-1017** (2026-10-17, https://api-docs.deepseek.com/news/news261017) [V]: reports "DeepSWE v1.1 Pass@1 vs. cost per task ... tested with the mini-swe-v2 harness"; the values are images, so no number is quoted here.
- V4-Pro and V4.1 model-card training details: **[X]**, not re-read.

## 4. What transfers to Asclexis

| Idea | Verdict | Where |
|---|---|---|
| F2P / P2F: a change must make something pass that failed without it, and break nothing | **Keep, adapted.** P2F is already ours (the whole replay set must pass, `rsi-loop.js:332`). F2P as a *new tool-call outcome* is tautological for our replay test (a new rule id can never be hinted by the old table). The meaningful form is **necessity**: each rule's positive cases must get no guard or hint from the table without that rule. The planner measured it on `4ffcd45f`: 10 positive cases, 0 covered by another rule; and with `no-such-file-path` removed, its two positive cases fail (`27 pass, 2 fail`) | Plan row RSI-REPLAY-STRICT |
| Attempts are not outcomes | **Covered by row C** (RSI-MINE-OUTCOMES) at the workflow level; at tool level our rows cannot tell a recovered failure without text | — |
| Pass@1 and cost per task, pinned to a harness | **Keep in part**: a first-try-ready rate per window tagged with the harness tree ids; cost per item is dropped (`tokens_per_item` is null or absent in every archived `summary.json`) | Plan row RSI-METRICS-VERSIONED |
| Typed tool error classes | **Covered by row A** (RSI-ERRCLASS-NONBASH) | — |
| Default-on log upload; telemetry without redaction | **Reject**: redaction before anything leaves, local-first | Plan, rejected ideas |
