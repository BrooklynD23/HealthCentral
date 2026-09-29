# Vendored process skills

Two upstreams, both MIT, both unmodified except for this file.

| Source | Skills | Vendored |
|---|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `using-superpowers`, `verification-before-completion`, `writing-plans`, `writing-skills` | — |
| [mattpocock/skills](https://github.com/mattpocock/skills) (`skills/engineering/`) | `ask-matt`, `code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `grill-with-docs`, `implement`, `improve-codebase-architecture`, `prototype`, `research`, `resolving-merge-conflicts`, `setup-matt-pocock-skills`, `tdd`, `to-spec`, `to-tickets`, `triage`, `wayfinder`, `wizard` | 2026-09-08, commit `3cca18b368ae95cdbdebbff572ccafa662551015` |

Matt Pocock's license is preserved verbatim as `MATTPOCOCK-LICENSE`.
Project **domain** skills live in [`skills/`](../../skills/README.md) (no dot) — see
[AGENT.md](../../AGENT.md#skills) for the full routing table.

## Overlapping skills — which to reach for

The two upstreams solve some of the same problems differently. Where both
cover a task, this repo's default is the **superpowers** one, because
[CLAUDE.md](../../CLAUDE.md) and [AGENT.md](../../AGENT.md#definition-of-done)
are written against its vocabulary (the Iron Law, evidence-before-assertion,
the plan/execute split). The Pocock skill is the alternative when its specific
shape fits better.

| Task | Default | Alternative | When to prefer the alternative |
|---|---|---|---|
| Test-first work | `test-driven-development` | `tdd` | You want the lighter red-green-refactor loop without the full skill's ceremony |
| Debugging | `systematic-debugging` | `diagnosing-bugs` | Performance regressions specifically — it has a sharper perf loop |
| Reviewing a diff | `requesting-code-review` / `receiving-code-review` | `code-review` | You want a single-pass review rather than the request/receive pair |
| Turning a spec into work | `writing-plans` | `to-spec`, `to-tickets` | The output should be GitHub issues or a standalone spec rather than a plan file |

`code-review` also shares a name with Claude Code's built-in `/code-review`
command. They are different things; the built-in is not affected by this
directory.

## What the Pocock set adds that superpowers does not

`improve-codebase-architecture` (scan for deepening opportunities, report,
then grill the one you pick), `codebase-design` (deep-module vocabulary),
`domain-modeling` (CONTEXT.md and ADRs), `wayfinder` (navigating an
unfamiliar area), `triage`, `prototype`, `grill-with-docs`, and
`resolving-merge-conflicts`. The first three are the reason this set was
installed — see
[docs/research/2026-09-08/FRONTIER-AUDIT-PROMPT.md](../../docs/research/2026-09-08/FRONTIER-AUDIT-PROMPT.md).
