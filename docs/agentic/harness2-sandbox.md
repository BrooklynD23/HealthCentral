# harness2 Sandbox Runbook

**Last Updated:** 2026-10-22 (superseded by H2-ALT); 2026-10-21
**Owner:** Project owner (sandbox build, both stage runs and teardown are owner actions)
**Status:** SUPERSEDED 2026-10-22 by owner H2-ALT (`docs/capstone-report/owner-decisions-2026-09-27.md`, row H2-ALT: Codex as second proposer in rsi-loop; harness2 dropped, H2-SETUP closed). Kept as a record; nothing here will be run. Before: PROPOSED. No owner approval of this runbook is recorded. The owner gates it relies on are answered (RRSI-OQ-2, H2-SOURCE (c)); H2-SETUP is an owner action not yet taken.
**Refresh Trigger:** a harness2 version bump (this runbook describes v0.1.0), a change to H2-SOURCE or H2-SETUP, a change to the egress allow-list or to an endpoint harness2 calls, or a change to the files under `.claude/mods/asclexis-rsi/`.

How to run google-research/harness2 as a dev-only tool inside an isolated sandbox. Plan: `docs/plans/2026-10-15-build-program/lane-E-privacy-gates-ci.md` section 2.26 (RRSI-H2-SANDBOX). Every harness2 fact below cites [01-harness2.md](../research/2026-10-20-rrsi-harness2/01-harness2.md) (section 3 "What it needs to run", section 4 "Safety posture"), which verified them against the harness2 source. Nothing here is invented beyond it.

**Nothing in this runbook has been executed.** Building the sandbox, stage 1 and stage 2 are owner work. An agent writes and revises this page; an agent does not run those steps.

## Scope and gates

- **RRSI-OQ-2** (`docs/capstone-report/owner-decisions-2026-09-27.md:323`): "(b) Run harness2 itself as a dev-only tool in an isolated sandbox with an egress firewall." Dev-only, never product code paths. The local-first invariant in CLAUDE.md applies to the product; harness2 is outside it and is never part of it.
- **H2-SOURCE** (answered 2026-10-20, option (c)): "the RSI replay cases and rule table only (`.claude/mods/asclexis-rsi/`), no other source". Only two files enter the sandbox (see [Source](#source)).
- **H2-SETUP** (owner action, not a question): host and container choice, Python 3.12, a Vertex project and an ADC credential the owner creates. No agent invents or stores credentials.

## Invariant

Nothing under `src/`, no CI job, no dependency. This runbook adds docs only. Check:

```bash
git diff origin/main -- src/ requirements*.txt src/backend/requirements*.txt
```

The output must be empty. harness2 is never added to `requirements*.txt`, never imported by repo code, and never wired into `.github/`.

## Sandbox

H2-SETUP is the owner's choice. Container or VM, owner picks.

Requirements (research section 3): Linux, Python 3.12 (harness2 needs `>=3.12,<3.14`), uv, Node 20+, gcloud CLI, and Vertex AI credentials via Application Default Credentials (ADC) with `GOOGLE_CLOUD_PROJECT` and `LOCATION` set.

- The sandbox has its **own** Python 3.12 and uv environment. Never use the repo venv, never touch `requirements*.txt`. (The repo targets Python 3.11+; harness2 does not fit it, research section 5.)
- Credentials appear only as placeholders in anything written down: `<PROJECT_ID>`, `<LOCATION>`, `<ADC_FILE>`. Never write a real value into this repo.
- The only credential that enters the sandbox is the Vertex ADC file. It is mounted read-only into the sandbox, and nothing else is.

### Egress allow-list

harness2's executor has unrestricted network access and its docs tell users to add their own egress firewall (research section 4). The firewall is therefore part of the sandbox, not optional.

Allowed:

- the Vertex AI endpoints for the owner's region (`<LOCATION>`)
- the package index, **during setup only**; remove the rule before any stage run

Everything else is denied by default. Other endpoints harness2 might need are **owner choices under H2-SETUP**, not decisions made here. Each one is allowed only if the owner chooses to, and each widens the exposure:

- OAuth token refresh for ADC (not verified in the research which host this uses; owner to determine)
- the endpoint of the `claude_cli` improver, if the owner selects that channel (research section 3 lists `opencode` or `claude_cli`)
- the GitHub and Hugging Face clones harness2 setup makes for pinned benchmark repos and data (research section 3). Stage 1 and stage 2 below do not need benchmarks; whether to allow these at all is the owner's choice

### Network and mounts

- Bind the LiteLLM bridge to `127.0.0.1` only. harness2 can bind it to `0.0.0.0` (research section 4, harness2 repo, docs/SETUP.md lines 131-133). Publish no ports from the container.
- No host mounts of any of: `src/backend/data`, any vault, `.env`, `~/.ssh`, `~/.claude`, or any credential other than the Vertex ADC file.
- No repo checkout in the sandbox.

### Bypass flags

harness2 runs agents with permission-bypass flags (research section 4):

- `--dangerously-bypass-approvals-and-sandbox` (Codex executor, harness2 repo, substrate/codex.py lines 166-167)
- `--dangerously-bypass-hook-trust` (same location)
- `--dangerously-skip-permissions` (`claude_cli` improver, harness2 repo, core/proposer.py lines 213-216)

These flags are allowed **only inside the container or VM, never on the host**. Do not run harness2 on the host to "try it". Research also reports a Codex rollout that downloaded its own task rubric unprompted (harness2 repo, docs/EXPERIMENTS.md lines 95-98), which is why the egress test in stage 1 matters.

## Source

H2-SOURCE (c): exactly two files, nothing else.

1. No repo checkout in the sandbox. No `git clone`, no worktree, no bind mount of the repo.
2. From `origin/main` on the host, record the SHA, then export each file to a staging directory and make it read-only:

```bash
git fetch origin main
SHA=$(git rev-parse origin/main)          # record this value in the stage 2 report
mkdir -p <STAGE>/.claude/mods/asclexis-rsi/hooks <STAGE>/.claude/mods/asclexis-rsi/replay
git show "$SHA:.claude/mods/asclexis-rsi/hooks/rules.ts"   > <STAGE>/.claude/mods/asclexis-rsi/hooks/rules.ts
git show "$SHA:.claude/mods/asclexis-rsi/replay/cases.ts"  > <STAGE>/.claude/mods/asclexis-rsi/replay/cases.ts
chmod a-w <STAGE>/.claude/mods/asclexis-rsi/hooks/rules.ts <STAGE>/.claude/mods/asclexis-rsi/replay/cases.ts
```

3. Copy `<STAGE>` into the sandbox as `<SANDBOX_COPY>`.
4. Record the `origin/main` SHA the copy came from. Open PR #230 edits both files; if it merges, the copy is stale and must be re-exported from the new SHA.

The two paths:

- `.claude/mods/asclexis-rsi/hooks/rules.ts`
- `.claude/mods/asclexis-rsi/replay/cases.ts`

**Stays out** (executable mod code and its tests): `.claude/mods/asclexis-rsi/hooks/register.ts`, `.claude/mods/asclexis-rsi/hooks/logic.ts`, `rsi.test.ts`. Any other file, including any other file under `.claude/mods/asclexis-rsi/`, needs a new owner gate. Do not add it on your own authority.

### Checklist before any stage 2 run

```bash
find <SANDBOX_COPY> -type f
```

It must print only these two paths and nothing else:

```
<SANDBOX_COPY>/.claude/mods/asclexis-rsi/hooks/rules.ts
<SANDBOX_COPY>/.claude/mods/asclexis-rsi/replay/cases.ts
```

If anything else prints, stop and remove it. Also confirm both files are read-only (`ls -l`, no `w` bit).

## Stage 1: prove the sandbox (needs H2-SETUP only)

No repo content enters the sandbox for this stage.

1. Run harness2's own example task. Research notes a credential-free deterministic demo exists (harness2 repo, README.md lines 93-94 and harness2/demo.py line 15); whether stage 1 uses that or a Vertex-backed example task is the owner's choice.
2. Run an egress test to a host that is **not** on the allow-list, for example `curl -sS --max-time 10 https://<NON_ALLOWED_HOST>/`. It must fail (timeout or connection refused). Paste the command and its output into the PR, or into the stage 1 note the owner keeps. A passing connection means the firewall is wrong: stop, fix it, repeat.
3. Confirm no listener is reachable from outside the sandbox (the LiteLLM bridge is on `127.0.0.1` and no ports are published).

## Stage 2: task over the two copied files

Requires H2-SETUP and the stage 1 egress test passing. H2-SOURCE is answered (c).

1. Run a task over `<SANDBOX_COPY>` only (the `find` checklist above first). harness2 sends task context to Vertex AI, off the machine; that is why only these two files, which hold no patient data, are allowed in.
2. Output: a report plus candidate diffs, under `docs/` or `.claude/` only.
3. Candidates leave the sandbox as text and enter the repo only through an ordinary, owner-reviewed PR. harness2 has no human gate in selection or adoption (research section 4), so nothing it produces is trusted or merged automatically.
4. Any candidate for `.claude/mods/asclexis-rsi/` or `.claude/workflows/rsi-loop.js` is an RSI PR, owner-merged. This runbook's PR is not an RSI PR (it edits no RSI file).

## Teardown

1. Destroy the container or VM and every copy of the two files, including `<STAGE>`.
2. Whether to revoke or delete the ADC credential is the owner's choice. Note that leaving it in place keeps Vertex access open.
3. Remove any allow-list rules the owner added for this run.

## Owner choices not decided here

The plan does not decide these. They are owner choices, listed so none is made by default:

1. Container or VM, and the host (H2-SETUP).
2. Which extra endpoints, if any, to allow beyond Vertex AI and the setup-time package index: ADC OAuth refresh, the `claude_cli` improver endpoint, GitHub and Hugging Face benchmark clones.
3. Which improver channel (`opencode` or `claude_cli`) and which solver, improver and judge models (`HARNESS2_SOLVER_MODEL`, `HARNESS2_IMPROVER_MODEL`, `HARNESS2_JUDGE_MODEL`).
4. Whether stage 1 uses the credential-free demo or a Vertex-backed example.
5. Whether to revoke the ADC credential at teardown.
6. What stage 2 task to give harness2 over the two files, and how many paid Vertex runs to spend.
