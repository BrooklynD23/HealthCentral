# Status — what has shipped since the tracks were written

**Read this before acting on any recommendation in this directory.**

The eight track documents were written on 2026-09-08 against the repo state in
[`00-brief.md`](00-brief.md). Work has shipped since. The tracks were **not**
rewritten — they are point-in-time research, and editing them after the fact
would destroy the record of what was known when. This file is the reconciliation
layer instead.

This exists because of [`recurring-failures.md`](../../agentic/recurring-failures.md)
#8: *stale guidance that reads as authority*. A track that still lists a shipped
change as a recommendation will get it implemented twice, and a track that lists
a **rejected** change as a recommendation will get a known-harmful change made.

## The consultation and the accepted roadmap (2026-09-10)

[`13-consultation.md`](13-consultation.md) is Claude Fable 5.1's verdict on the
~113 candidate rows the ten tracks produced. It kept **19**, dropped the rest
with reasons, and found the roadmap's ordering wrong in nine specific places.

[`docs/plans/2026-09-10-implementation-roadmap.md`](../../plans/2026-09-10-implementation-roadmap.md)
turns that verdict into work and **supersedes [`09-roadmap.md`](09-roadmap.md)'s
wave ordering**. Eight of the consultation's load-bearing claims were
re-verified before acceptance; all eight held. One was escalated: the agent path
does not merely fabricate `faithfulness_score=1.0`
(`api/assistant.py:641-648`) — that value is **rendered to patients**
(`ExplainAssistant.tsx:607`, gated on an `enabled=True` the same code hardcodes),
so the fix moved from the consultation's Phase B to Phase A.

## Prompts for the next model

| Prompt | Purpose | Size |
|---|---|---|
| [`CONSULT-PROMPT.md`](CONSULT-PROMPT.md) | **Start here.** Which of the ~128 candidate changes should actually be integrated | 4,390 chars |
| [`GOAL-PROMPT.md`](GOAL-PROMPT.md) | Is `09-roadmap.md` right? (subsumed by the consultation) | 3,464 chars |
| [`INDUSTRY-PROMPT.md`](INDUSTRY-PROMPT.md) | What changed outside the repo since May 2026 | 4,227 chars |

The consultation subsumes the roadmap audit — it asks explicitly where
`09-roadmap.md` is wrong — so running both is largely redundant. The industry
prompt is genuinely separate: it looks outward, the other two look in. Full context pack and data boundary:
[`FRONTIER-AUDIT-PROMPT.md`](FRONTIER-AUDIT-PROMPT.md).

## Shipped

| Commit | Change | Tracks now stale |
|---|---|---|
| `2c98ae6` | Audit logging on all five `api/memory.py` routes | T3 §Recommendations row 8; T7 row 3 |
| `2c98ae6` | Answer-cache versioned on evidence, not a count (`_profile_version` now fingerprints verified observations **and** verified documents) | T7 row 2 |
| `2c98ae6` | Dead `default_embeddings_model` config removed | T5 |
| `3c77eec` → `3eb9e9d` | `llama-cpp-python` pinned, then raised to `==0.3.35` | T2 row 3 |
| `3eb9e9d` | Mid tier `Phi-3-mini-4k` → `Phi-4-mini-instruct`, context 4096 → 16384 | T1 tier table; T2 §5 quant table; T5 rows 3 and the tier table |
| `f8ca137` | `download_models.py verify` — checks every tier repo against HuggingFace, exit-coded | T5 row 2 (the `list_repo_files()` recommendation) |
| `13b1466` | Per-tier capability disclosure (`get_tier_capabilities`, `TierCapabilities` component) | New — no track proposed this; it came out of implementation |

## Rejected — do not implement

**T3's recommendation to route `MemoryItemCreate/Update.value` through
`sanitize_untrusted_field` before persisting** (`03-agentic-loops.md`
§Recommendations). The risk it names is real; the layer is wrong twice over:

1. `modules/rag.py::_retrieve_memory_context` already filters injection-bearing
   memory items at compose time, and fails closed on the **whole item** —
   strictly safer than scrubbing a string.
2. `sanitize_untrusted_field` applies **strict PHI redaction**. Memory items are
   things a patient deliberately saved into their own encrypted vault. Writing
   through it would corrupt them irreversibly, since the original is never
   stored. The invariant is *redaction before anything **leaves***; a write into
   the per-profile vault is PHI arriving at its designed home.

Two tracks independently flagged the memory route, which made this look
corroborated. Convergence is evidence the **area** matters, not that the
**proposed fix** is right.

## Still open, with new evidence

- **Gemma 4 is real and supported.** `LLM_ARCH_GEMMA4` exists in current
  llama.cpp; 0.3.35 vendors `llama.cpp@4df29be4f`, which declares it. The
  blocker was only ever the 22-month-old wheel. The **repo paths remain
  unverified** — run `python scripts/download_models.py verify`.
- **The low tier is untouched by design.** `Qwen2.5-0.5B` is two generations
  behind (llama.cpp now declares `qwen3`, `qwen35`, `qwen4exp`), but T5's
  finding holds at any generation: 0.5B-class models cannot drive a tool loop.
  Awaiting verified repo paths before a swap.
- **`function_calling` is under-declared in `TIER_MODEL_CONFIG`.** Only the
  Gemma 4 entries set it; Phi-4-mini and BioMistral support tool calling
  regardless. The capability UI therefore says "Tool support unconfirmed" rather
  than asserting absence. Filling these in properly is open work.

## Baseline drift

`CLAUDE.md`'s collected-test baseline moved **1245 → 1269** across these
commits. Any track quoting 1245 is quoting the number that was true when it was
written.

## Tracks added after the first eight (2026-09-09)

Two dimensions of the original request had no track. Both were dispatched on
2026-09-09. They are numbered by file, not dispatch order: files `01`-`08` are
tracks 1-8, `09-roadmap.md` is the synthesis, and these follow it.

| Track | Subject | File |
|---|---|---|
| 9 | The repo as an artifact demonstrating the SWE → agentic journey | [`10-demonstration-artifact.md`](10-demonstration-artifact.md) |
| 10 | Harness & loop engineering — building the dev tooling and environment | [`11-harness-engineering.md`](11-harness-engineering.md) |

Track 9's central finding is a set of **claim-vs-evidence gaps** — things the
CS4610 reports describe that the repo cannot evidence. Every one below was
verified independently before acceptance:

| Claim | Source | Repo reality |
|---|---|---|
| Subagent definitions live in `.claude/agents/` | `docs/agentic/harness.md:25` | Directory does not exist |
| A PreToolUse hook blocks PHI-bearing tool calls | Final Report §7.2 | No hooks, no `settings.json` anywhere |
| A Ralph-style RAG sweep tuned reranking | Final Report §7.3 | No artifact — and `grep -i rerank modules/rag.py` returns nothing, so the swept feature does not exist |
| OpenWiki provides repo navigation (present tense) | `CLAUDE.md` | `openwiki/README.md:15` — "still not generated (as of 2026-07-27)" |
| Daily standup / retro in `docs/agile/STANDUP.md`, `RETRO.md` | `AGILE_PLAN.md:50,53` | Both moved to `docs/archive/agile/`; refs are inline code so `docs_lint.py` cannot catch them |

Also verified: `docs/agentic/progress.md`'s last entry is 2026-07-30, with
**48 commits since** — the log went silent across the backup-restore security
fixes, the Asclexis rename, and this entire research pass, while
`feature_list.json` and git history stayed current. And `CS4610_Report_Demo/`
holds two tracked LibreOffice lock files (`.~lock…#`, `~$…docx`) that are not
gitignored; they carry a container session name, not personal identity — repo
litter rather than a leak.

Track 10 found two things that are **defects, not documentation gaps**, both
verified here before acceptance:

1. **The security gate can pass without scanning anything.**
   `scripts/security_gate.py:44-51` and `:71-78` catch
   `FileNotFoundError, json.JSONDecodeError` on the bandit and pip-audit
   reports, print a WARNING, and `return []` — which the gate reads as *zero
   findings*, not as *failure*. `.github/workflows/ci.yml:92,95` run both
   scanners with `|| true`, so a crashed scanner produces no exit code and a
   missing or truncated report. The chain ends with CI green and nothing
   scanned. This is `recurring-failures.md` #1 — a green signal that could not
   have failed — in the one gate whose whole job is to fail.
2. **`repo_hygiene_check.py` never runs against the live repo.** README.md:393
   and CONTRIBUTING.md:75 document it as part of the pre-merge proof bundle, but
   `ci.yml` never invokes it; only its unit tests against synthetic fixtures run.

Track 10 also **corrects the reports' PHI-hook claim rather than just marking it
unbuilt**: Claude Code hooks fire on the *coding agent's* tool calls and are
documented upstream as "a convenience feature for automation, not a security
boundary." They could not have enforced the product's runtime network
guarantee. That guarantee does exist, correctly, as code —
`core/llm/ollama_provider.py::_assert_localhost` and `modules/redaction.py` —
independent of any hook. The reports described the wrong mechanism for a
property the repo actually has.
