# NPM-MAJORS (a) — Tailwind CSS 3 → 4 Migration Plan

> **For agentic workers:** this plan is **not approved for execution**. Owner gate NPM-MAJORS: "Plans for both migrations this wave; they come back to the owner before running." Do not start Task 0 until owner-decisions records an approval naming this file.

**Status:** plan only, written 2026-10-04 by L1-B (Wave 3). Approval is pending.
**Source:** NPM-AUDIT PR #38. After `npm audit fix`, 5 high advisories remain on the Tailwind 3 chain (GHSA-vfj7-8cjw-p6xm in `braces`, reached through `micromatch`, `chokidar`, `fast-glob` and `tailwindcss` itself). npm's only fix is `tailwindcss@4.3.3`, a semver-major.
**Architectural:** no data path, safety boundary or schema changes. But the visible UI of every page can change, so the owner reviews screenshots before merge.

**Goal:** Move `src/frontend` from Tailwind 3.4 to Tailwind 4.x and clear the 5 tailwind-chain advisories, with no visible regression on the app's pages.

**Architecture:** Use Tailwind's official upgrade tool (`npx @tailwindcss/upgrade`), then a measured review of its diff. The tool:
- moves `tailwind.config.js` into CSS `@theme`;
- swaps `@tailwind` directives for `@import "tailwindcss"`;
- moves the PostCSS plugin to `@tailwindcss/postcss`;
- renames the utilities whose meaning changed.

A before/after screenshot set is the visual check.

**Tech Stack:** Tailwind 3.4.19 → 4.3.x, `@tailwindcss/postcss`, PostCSS 8, Vite 7, `tailwind-merge` 2 → 3, `class-variance-authority`.

## Global Constraints

- Owner gate NPM-AUDIT-SCHED (2026-10-04): "Any breaking major upgrade comes back to you." This plan is that report. NPM-MAJORS (2026-10-04): plans first, owner approves before running.
- **Two majors move together.** `tailwind-merge` 2.x only knows Tailwind 3 class names; its v3 line targets Tailwind 4. `src/frontend/src/utils/cn.ts` (`cn()` = `twMerge(clsx(...))`) is used across `components/ui`, so the approval must name both majors.
- Frontend only. No backend file. No change to component behaviour or copy. Only class names, CSS and build config change.
- All npm commands run from **Windows**. vitest runs there too. E2E runs in CI.
- Explicit pathspecs. Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Measured scope (origin/main `90c502a`, 2026-10-04)

Counts come from `grep -E` over `src/frontend/src` (`*.ts`, `*.tsx`, `*.css`). Before Task 1, re-run the commands in Task 0 Step 3 and use their output, not these numbers.

| Area | Where | v4 change that applies | Count |
|---|---|---|---|
| Directives | `src/styles/globals.css:1-3` | `@tailwind base/components/utilities` → `@import "tailwindcss"` | 1 file |
| Custom CSS layers | `globals.css:5` `@layer base`, `:74` `@layer components` (`.glass-card` with `@apply`, `.subtle-noise`, `.stagger-animation`), `:122` `@layer utilities` (`min-h-target`, `min-w-target`, `animation-delay-*`) | Custom utilities belong in `@utility` blocks. No variant-prefixed use was found (`grep '[a-z-]+:(min-h-target\|…)'` → 0) | 1 file, 2 consumer files |
| JS config | `tailwind.config.js` | Not loaded automatically in v4: becomes `@theme` (colors `surface/ink/accent/status/dark`, fonts, `fontSize`, `spacing 18/88/128`, `borderRadius xl/2xl/3xl`, `boxShadow soft/card/elevated/focus`, 6 animations and keyframes), or is kept through `@config` | 1 file |
| PostCSS | `postcss.config.js` | `tailwindcss: {}` + `autoprefixer` → `'@tailwindcss/postcss': {}`. v4 vendor-prefixes on its own, so `autoprefixer` can go | 1 file |
| `shadow-sm` | 3 files | Renamed `shadow-xs` | 5 |
| `backdrop-blur-sm` | `DoseLoggingModal.tsx:79`, `VoiceFirstUseModal.tsx:18`, `SettingsPage.tsx:836,905,1002` | Renamed `backdrop-blur-xs` | 5 |
| bare `rounded` / `rounded-sm` | 35 files / 1 file | `rounded` → `rounded-sm`, `rounded-sm` → `rounded-xs` | 133 / 1 |
| `outline-none` | 20 files | Becomes `outline-hidden` (v4's `outline-none` now sets `outline-style: none`) | 42 |
| `flex-shrink-*` / `flex-grow-*` | 12 files | Removed: becomes `shrink-*` / `grow-*` | 23 |
| bare `border` (default colour) | 38 files | Default border colour goes from `gray-200` to `currentColor`. Many sites pair it with a colour class (for example `Input.tsx:43` `border-black/[0.08]`); a bare one changes colour | 107 |
| `ring-*` | 23 files | 0 bare `ring` (the default width moves from 3px to 1px), so explicit widths are unaffected. Ring colour default changes; sites use explicit `ring-accent` etc. | 107 |
| `space-x/y-*`, `divide-*` | 35 / 7 files | The selector moves from `> * + *` to `> :not(:last-child)`. Spacing can differ with inline or hidden children | 150 / 16 |
| `placeholder*` | 5 files | Default placeholder colour changes to the current text colour at 50% | 6 |
| buttons | all `<button>` | v4 sets `cursor: default`. `components/ui/Button.tsx` gets `cursor-pointer` if the owner wants the old look | — |
| Not present | — | `*-opacity-*` 0, `overflow-ellipsis` 0, `theme(` 0, `[--var]` arbitrary 0, `!` important prefix 0 in class strings | 0 |

**Runtime and browser floor:** Tailwind 4 targets Safari 16.4+, Chrome 111+ and Firefox 128+ (`@property`, `color-mix`). The app runs in the user's browser from the Vite dev server (`dev.ps1:281-282`), so an older browser shows unstyled parts. The owner decides whether that floor is acceptable.

**Expected audit effect:** v4 drops `chokidar` and the `micromatch`/`fast-glob` scanner in favour of its Rust scanner, so the 5 high advisories should go. Measure it; do not assume it.

## Review Focus

1. **Silent visual drift.** vitest (jsdom) and tsc never see CSS, so a wrong rename passes both. Screenshots (Task 3) are the only signal; the reviewer compares them pair by pair.
2. **`cn()` merge conflicts.** `tailwind-merge` 2 does not know `shadow-xs` or `outline-hidden`, so it can drop a class or keep 2 conflicting ones. Task 2 upgrades it in the same PR, and Task 3 checks a `Button` variant override.
3. **Bare `border` colour.** 107 sites. Either keep the v3 default with the upgrade tool's compatibility base rule, or audit each site. The plan keeps the compatibility rule (smaller diff) and records it.
4. **Custom `@layer utilities` classes** and `@apply` inside `.glass-card` must still build. `npm run build` fails loudly if they don't.
5. **Dark-mode colour names** (`dark.surface`, `dark.ink`) map to `--color-dark-surface` etc. A `grep` for `dark-surface` before and after confirms the class names still resolve.

---

### Task 0: Preconditions (STOP on any failure)

- [ ] **Step 1: Approval and base.** `grep -n 'NPM-MAJORS' docs/capstone-report/owner-decisions-2026-09-27.md` must show an approval naming this plan **and** `tailwind-merge` 3. Then `git worktree add ../hc-tw4 -b feat/tailwind4 origin/main`. PR #38 (NPM-AUDIT) must already be on `origin/main` (`git merge-base --is-ancestor 93def9e origin/main`).
- [ ] **Step 2: Windows baseline.**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-tw4\src\frontend; npm ci; npm audit 2>&1 | Select-Object -Last 1; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE; npm run build; echo build=\$LASTEXITCODE; npx vitest run 2>&1 | Select-Object -Last 4"
```

- [ ] **Step 3: Re-measure the scope table.** Run from `src/frontend/src`, with `S="--include=*.tsx --include=*.ts --include=*.css -r ."`:

```bash
for p in 'shadow-sm\b' 'backdrop-blur-sm\b' 'outline-none' 'flex-(shrink|grow)' '(^|[ "'"'"'`:])rounded(-[trblxyse]{1,2})?([ "'"'"'`]|$)' '(^|[ "'"'"'`:])rounded(-[trblxyse]{1,2})?-sm\b' '(^|[ "'"'"'`:])border([ "'"'"'`]|$)'; do printf '%s files=%s hits=%s\n' "$p" "$(grep -lE "$p" $S | wc -l)" "$(grep -oE "$p" $S | wc -l)"; done
```

Record the output. This is the "before" column for Task 2 Step 4.

- [ ] **Step 4: "Before" screenshots.** Use a throwaway Playwright script outside the repo, or `e2e/support/start-backend.mjs` plus `page.screenshot`, against the CI e2e environment or a Linux box with SQLCipher. Never use an unencrypted Windows run as evidence (recurring-failures §4). Capture 1280×800 full-page shots of these routes: `/setup`, `/inbox`, `/trends`, `/verify`, `/explain`, `/medications`, `/settings`, `/timeline`, `/search`, plus one open modal (`DoseLoggingModal`). Store them outside the repo (`../tw4-shots/before/`).

### Task 1: Run the upgrade tool

- [ ] **Step 1.** On Windows, from `src/frontend` with a clean tree: `npx @tailwindcss/upgrade@4`. Paste its full output.
- [ ] **Step 2.** `git status --short` and `git diff --stat`. Expected files: `package.json`, `package-lock.json`, `postcss.config.js`, `tailwind.config.js` (deleted or reduced), `src/styles/globals.css`, and component files with renamed classes. Any file outside `src/frontend`: STOP.
- [ ] **Step 3.** Confirm `package.json` changes: `tailwindcss` `^4.x`, `@tailwindcss/postcss` added, `autoprefixer` removed or unused. No other dependency moved; if one did, STOP and report.

### Task 2: Complete what the tool leaves

- [ ] **Step 1: `tailwind-merge` 3.** `npm install tailwind-merge@^3` (Windows). This is a named major in the approval. `utils/cn.ts` keeps its API (`twMerge(clsx(inputs))`).
- [ ] **Step 2: Border and button defaults.** If the tool did not add them, add v4's documented compatibility rules to `globals.css` under `@layer base`:
  - `*, ::after, ::before, ::backdrop, ::file-selector-button { border-color: var(--color-gray-200, currentColor); }`
  - `button:not(:disabled), [role="button"]:not(:disabled) { cursor: pointer; }`
- [ ] **Step 3: Custom utilities.** Turn `globals.css` `@layer utilities { .min-h-target … }` into one `@utility min-h-target { … }` block per class, and the same for `min-w-target` and `animation-delay-*`.
- [ ] **Step 4: Re-run Task 0 Step 3.** Expected after the migration: `shadow-sm`, `backdrop-blur-sm`, `outline-none`, `flex-shrink|grow` and the old-meaning bare `rounded` are 0, or appear only under their v4 meaning, with each remaining hit explained in the PR body.
- [ ] **Step 5: Checks** (Windows): `npx tsc --noEmit`, `npm run lint`, `npm run build`, `npx vitest run`, `npm audit`. Paste each. Expected: all rc 0; vitest count equals the Task 0 baseline; `npm audit` no longer lists `braces`, `micromatch`, `chokidar`, `fast-glob` or `tailwindcss`.
- [ ] **Step 6: Commit** in 2 commits, with explicit pathspecs taken from `git status --short`:
  1. `feat(frontend): migrate to Tailwind CSS 4 with the official upgrade tool`
  2. `fix(frontend): tailwind-merge 3, v3 border/cursor defaults, @utility blocks`

### Task 3: Visual verification (blocks the PR)

- [ ] **Step 1.** Capture the "after" screenshots with the same routes, viewport and environment as Task 0 Step 4.
- [ ] **Step 2.** Diff each pair, for example with `npx pixelmatch` or ImageMagick `compare -metric AE` run outside the repo. Record per-route pixel deltas in the PR body, and attach the pairs whose delta is above 0.5% of the pixels.
- [ ] **Step 3.** Check the `cn()` merge: in a vitest run, `cn('shadow-xs', 'shadow-card')` must return `'shadow-card'`. Add this as a test in `src/__tests__/cn.test.ts` (new, 1 test) during Task 2, and observe it failing on tailwind-merge 2 before the upgrade.
- [ ] **Step 4.** Reviews: `code-reviewer` plus a reviewer who opens the screenshot pairs. CI 6/6 (E2E Smoke included).

## Stop gates

- No approval recorded, or `tailwind-merge` 3 not named in it.
- The upgrade tool touches files outside `src/frontend`, or moves a dependency other than tailwindcss, `@tailwindcss/postcss`, autoprefixer or tailwind-merge.
- Any check fails, or vitest's count changes by anything other than +1 (`cn.test.ts`).
- A screenshot delta the owner has not accepted.

## Rollback

One PR: `git revert <merge sha>`, then `npm ci`. No data, schema or API change.

## Out of scope

- A visual redesign, or adopting new v4 features (container queries, `@starting-style`).
- react-router 7 (its own plan: [2026-10-04-NPM-MAJORS-react-router7.md](2026-10-04-NPM-MAJORS-react-router7.md)).
- Serving `dist/` instead of the Vite dev server (`dev.ps1:281-282`; PR #38 security finding M2).
