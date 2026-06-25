# Agent Code-Knowledge Layer (Serena / LSP-over-MCP)

**Owner:** Platform / Dev Experience
**Refresh Trigger:** Serena version bump, a change to `.mcp.json` / `.serena/project.yml`, or a change to the safety-critical module list.
**Last Updated:** 2026-06-25
**Status:** Active (dev tooling only — not a product feature)

## What this is

A **dev-only** knowledge layer that gives coding agents (Claude Code, etc.) precise,
**always-fresh** understanding of this codebase via [Serena](https://github.com/oraios/serena),
an LSP-over-MCP server. It exposes language-server intelligence (find a symbol, find all
references, find implementations/declarations, symbol overviews, diagnostics) as MCP tools.

Why this over a hand-rolled repo-map or a DIY embedding index: those maintain an index that
goes stale and must be regenerated (drift). Serena queries the **live** source through a
language server, so there is no index to rot — it is always current, and its answers are
compiler-grade precise rather than heuristic. It runs fully local and reaches **source code +
docs only** (never patient data), matching the local-first / no-PHI invariants in `CLAUDE.md`.

## How it runs

Prerequisite: [`uv`](https://docs.astral.sh/uv/) (provides `uvx`).

In Claude Code, the repo-root `.mcp.json` auto-launches the server — no manual step. It pins
the PyPI package `serena-agent==1.5.3` and uses `--project-from-cwd` so there is no
hardcoded path:

```
uvx --from serena-agent==1.5.3 serena start-mcp-server --context claude-code --project-from-cwd
```

We pin via **PyPI** (not `git+https://github.com/oraios/serena`) because it is faster, needs
no git clone, and resolves in restricted-network environments. Serena auto-manages the
language servers (pyright for Python, typescript-language-server for TypeScript); the **first**
run downloads them, so one networked run is needed before fully-offline use.

## Configuration

- `.mcp.json` (repo root) — registers Serena as a project-scoped MCP server.
- `.serena/project.yml` — project config. Key settings we set:
  - `languages: [python, typescript]` — Python first (the backend is the primary,
    safety-critical surface); the upstream-generated config only had `typescript`.
  - `ignore_all_files_in_gitignore: true` **plus** an explicit `ignored_paths` allowlist —
    see Privacy below.
  - `initial_prompt` — injects the safety-critical file list (below) on every activation.
  - `read_only: false` — Serena's editing tools remain available. Set this to `true` if you
    want Serena to be navigation-only (Claude Code edits via its own tools regardless).
- `.serena/memories/` — on-demand project notes Serena can read.

## Available knowledge tools

`find_symbol`, `find_referencing_symbols`, `find_implementations`, `find_declaration`,
`get_symbols_overview`, `get_diagnostics_for_file`. Under the `claude-code` context Serena
intentionally drops `read_file` / `list_dir` / `search_for_pattern` because Claude Code
already provides those — Serena's value is the symbol graph, not file IO.

## Privacy guarantee (no PHI)

The knowledge layer must reach **code + docs only**. Two layers enforce this:

1. `ignore_all_files_in_gitignore: true` — `.gitignore` already excludes `data/`,
   `profiles/`, `*.db*`, and `/models/`.
2. An explicit `ignored_paths` list in `.serena/project.yml` re-states the sensitive paths so
   the exclusion holds even if `.gitignore` changes.

Verify with git (prints the path only when ignored):

```
git check-ignore -v profiles/x.db data/x.json src/backend/x.db models/m.gguf
```

All four are reported ignored; source files and `docs/` are not. (Serena's
`project is_ignored_path` CLI has a cosmetic output bug in 1.5.3 — use `git check-ignore`.)

## Safety-critical modules (approval required before editing)

These require maintainer approval before changes (see `CLAUDE.md` / `CONTRIBUTING.md`). The
`initial_prompt` in `.serena/project.yml` lists them so agents are reminded on activation:

- `src/backend/security/**` — auth, validation, rate limiting, headers
- `src/backend/core/profile_database.py` — per-profile SQLCipher encryption
- `src/backend/modules/interpret_safety.py` — clinical safety guardrails
- `src/backend/modules/rag.py` — retrieval / verification
- `src/backend/modules/faithfulness/**` — groundedness checks
- `src/backend/modules/verifier_agent.py` — claim verification

### Blast-radius recipe

Before changing a function, check whether its callers reach a safety-critical module: use
`find_referencing_symbols` on the target symbol and walk the references. If any path leads
into a module above, flag it and confirm before editing.

## Not included (deferred)

Fuzzy natural-language search ("find code about X") is **not** part of this layer — LSP is
structural. If that need is proven later, add a dev-only, code/docs-only semantic index
reusing the existing local embedding stack (`src/backend/modules/embeddings.py`), kept
separate from the patient RAG store. Not built yet.
