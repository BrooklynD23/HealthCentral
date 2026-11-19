# Process skills

Only one process skill is vendored here: `resolving-merge-conflicts`, from
[mattpocock/skills](https://github.com/mattpocock/skills) (`skills/engineering/`,
2026-09-08, commit `3cca18b368ae95cdbdebbff572ccafa662551015`, MIT). Its license
is preserved verbatim as `MATTPOCOCK-LICENSE`.

The other process skills come from the
[superpowers](https://github.com/obra/superpowers) Claude Code plugin
(`test-driven-development`, `systematic-debugging`, `writing-plans`,
`executing-plans`, `subagent-driven-development`, `brainstorming`,
`verification-before-completion`, `requesting-code-review`,
`receiving-code-review`, `dispatching-parallel-agents`, `using-git-worktrees`,
`finishing-a-development-branch`, `writing-skills`). Install it once:
`/plugin install superpowers@claude-plugins-official`. Vendored copies were removed on 2026-11-17
because the plugin listed every one of them a second time.

[CLAUDE.md](../../CLAUDE.md) and [AGENT.md](../../AGENT.md#definition-of-done)
are written against the superpowers vocabulary (the Iron Law,
evidence-before-assertion, the plan/execute split).

Project **domain** skills live in [`skills/`](../../skills/README.md) (no dot);
see [AGENT.md](../../AGENT.md#skills).
