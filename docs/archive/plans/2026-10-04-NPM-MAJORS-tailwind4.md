# NPM-MAJORS (a) — Tailwind CSS 3 → 4 Migration Plan

> **Historical Reference** — executed (Tailwind 4 is in `src/frontend/package.json`; screenshot review OW-2 / #74 done per `docs/features/TASK_LIST.md`); retained for history, not an active tracker. Moved from `docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md` on 2026-10-22.

> **For agentic workers:** owner-decisions `:64` NPM-MAJORS-RUN records the approval of this plan for execution ("This approves both NPM-MAJORS plans for execution"), refined by `:69` FE-SEQ, `:70` DEV-PS1-FIRST, `:71` TW4-BROWSERS, `:72` MAJORS-TIED, `:73` TW4-VISUAL and TW4-O1..TW4-O4. It runs as amended by `audit/2026-09-25/waves/briefs/TAILWIND-4-L1-brief.md` §4; where they differ, the brief wins.

**Status:** approved for execution per owner-decisions `:64`, `:69`-`:73`. Written 2026-10-04 by L1-B (Wave 3); amended 2026-10-11 per the brief §4.
**Source:** NPM-AUDIT PR #38. Task 0 measured `npm audit` on `4cb7470` (2026-10-11): 7 vulnerabilities (2 moderate, 5 high), all on the Tailwind 3 chain. High: `braces` (GHSA-vfj7-8cjw-p6xm), `chokidar`, `micromatch`, `fast-glob`, `tailwindcss`. Moderate: `postcss-selector-parser` (GHSA-rj75-hqrm-r3gf), `postcss-nested`. npm's only fix is `tailwindcss@4.3.3`, a semver-major.
**Architectural:** no data path, safety boundary or schema changes. But the visible UI of every page can change, so the owner reviews screenshots before merge.

**Goal:** Move `src/frontend` from Tailwind 3.4 to Tailwind 4.x and clear the 7 tailwind-chain advisories measured in Task 0 (5 high, 2 moderate), with no visible regression on the app's pages.

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
| **CSS variable collision** | `globals.css:7-10` (`--color-surface`, `--color-surface-elevated`, `--color-ink`, `--color-accent` as bare RGB triplets such as `250 250 248`) and `:16-19` (`--radius-sm/md/lg/xl` = 8/12/16/24px), inside `@layer base` `:root` | v4 generates its theme as CSS variables with these **same names** (`--color-*`, `--radius-*`). The `base` layer wins over `theme`, so `bg-surface`, `text-ink`, `bg-accent/20` (and `body`, `:49`) would resolve to an invalid colour (transparent), and `rounded-md/lg/xl` (169 hits, 43 files) would move from 6/8/12px to 12/16/24px. `grep -rn 'var(--\(color\|radius\)' src` → **0 consumers**, so the 8 lines are dead in v3 and can be deleted. (`--font-*` is read at `:27,56,62`; `--shadow-*` values equal the config: harmless) | 8 lines |
| Directives | `src/styles/globals.css:1-3` | `@tailwind base/components/utilities` → `@import "tailwindcss"` | 1 file |
| Custom CSS layers | `globals.css:5` `@layer base`, `:74` `@layer components` (`.glass-card` with `@apply`, `.subtle-noise`, `.stagger-animation`), `:122` `@layer utilities` (`min-h-target`, `min-w-target`, `animation-delay-*`) | Custom utilities belong in `@utility` blocks. No variant-prefixed use was found (`grep '[a-z-]+:(min-h-target\|…)'` → 0) | 1 file, 1 consumer `.tsx` (`Sidebar.tsx:68`) |
| `bg-gradient-to-*` | `Sidebar.tsx:44`, `ProfileSetup.tsx:224` | Renamed `bg-linear-to-*` | 2 |
| `index.html` body classes | `index.html:19` | Scanned by v4 source detection; a renamed class there is renamed too | 1 file |
| `outline-none` inside `@apply` | `globals.css:66` | Same rename as in class strings (`outline-hidden`) | 1 |
| Duplicate `@keyframes slideUp` | `globals.css:110` vs `tailwind.config.js` | Identical content (Fable verified); one copy becomes redundant in `@theme` | 1 |
| `transitionDuration` 250/350 | `tailwind.config.js` | Must reach `@theme` with the same values | 2 |
| `:root --font-*` | `globals.css:12-14` | Same names as the `@theme` `--font-display/body/mono` the tool generates; values must stay identical | 3 lines |
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
| Placeholders | inputs with a `placeholder` attribute and **no** `placeholder:` class (`grep placeholder` → 29 hits, 16 files; the 5 files / 6 hits with `placeholder:` classes are the unaffected ones) | Default placeholder colour changes to the current text colour at 50% | 29 |
| `hover:` | 27 files | v4 applies `hover:` only under `@media (hover: hover)`: touch devices lose tap-hover styles | 78 |
| buttons | all `<button>` | v4 sets `cursor: default`. `components/ui/Button.tsx` gets `cursor-pointer` if the owner wants the old look | — |
| Not present | — | `*-opacity-*` 0, `overflow-ellipsis` 0, `theme(` 0, `[--var]` arbitrary 0, `!` important prefix 0 in class strings | 0 |

**Runtime and browser floor:** Tailwind 4 targets Safari 16.4+, Chrome 111+ and Firefox 128+ (`@property`, `color-mix`). The app runs in the user's browser from the Vite dev server (`dev.ps1:281-282`), so an older browser shows unstyled parts. The owner decides whether that floor is acceptable.

**Expected audit effect:** v4 drops `chokidar` and the `micromatch`/`fast-glob` scanner in favour of its Rust scanner, so the 7 measured advisories (high: braces, chokidar, micromatch, fast-glob, tailwindcss; moderate: postcss-selector-parser, postcss-nested) should go. Measure it; do not assume it.

## Review Focus

0. **Transparent colours from the variable collision** (scope row 1). Task 2 Step 0 deletes the 8 dead variables; Task 3 checks the `body` background is `#FAFAF8`, not transparent.
1. **Silent visual drift.** vitest (jsdom) and tsc never see CSS, so a wrong rename passes both. Screenshots (Task 3) are the only signal; the reviewer compares them pair by pair.
2. **`cn()` merge conflicts.** `tailwind-merge` 2 does not know `shadow-xs` or `outline-hidden`, so it can drop a class or keep 2 conflicting ones. Task 2 upgrades it in the same PR, and Task 3 checks a `Button` variant override.
3. **Bare `border` colour.** 107 sites. Either keep the v3 default with the upgrade tool's compatibility base rule, or audit each site. The plan keeps the compatibility rule (smaller diff) and records it.
4. **Custom `@layer utilities` classes** and `@apply` inside `.glass-card` must still build. `npm run build` fails loudly if they don't.
5. **Dark-mode colour names** (`dark.surface`, `dark.ink`) map to `--color-dark-surface` etc. A `grep` for `dark-surface` before and after confirms the class names still resolve.

---

### Task 0: Preconditions (STOP on any failure)

- [ ] **Step 1: Approval and base.** Gate = owner-decisions rows `:64` NPM-MAJORS-RUN, `:69` FE-SEQ (names `tailwind-merge` 3), `:70` DEV-PS1-FIRST, `:71` TW4-BROWSERS, `:72` MAJORS-TIED, `:73` TW4-VISUAL, plus TW4-O1..TW4-O4 (`grep -c 'TW4-O'` ≥ 4). Dependencies on `origin/main`: #52 (`f428a99`), #55 (`87accae`), #57 (`eb7de28`) — `git merge-base --is-ancestor <sha> origin/main` each 0. Then `git worktree add ../hc-tw4 -b feat/tailwind4 origin/main`. PR #38 (NPM-AUDIT) must already be on `origin/main` (`git merge-base --is-ancestor 93def9e origin/main`).
- [ ] **Step 2: Windows baseline.**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-tw4\src\frontend; npm ci; npm audit 2>&1 | Select-Object -Last 1; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE; npm run build; echo build=\$LASTEXITCODE; npx vitest run 2>&1 | Select-Object -Last 4"
```

- [ ] **Step 3: Re-measure the scope table.** Run from `src/frontend/src`, with `S="--include=*.tsx --include=*.ts --include=*.css -r ."`:

```bash
for p in 'shadow-sm\b' 'backdrop-blur-sm\b' 'outline-none' 'flex-(shrink|grow)' '(^|[ "'"'"'`:])rounded(-[trblxyse]{1,2})?([ "'"'"'`]|$)' '(^|[ "'"'"'`:])rounded(-[trblxyse]{1,2})?-sm\b' '(^|[ "'"'"'`:])border([ "'"'"'`]|$)' '(^|[ "'"'"'`:])ring([ "'"'"'`]|$)' '(^|[ "'"'"'`:])ring-[0-9]+\b' '(^|[ "'"'"'`:])shadow([ "'"'"'`]|$)' 'shadow-xs\b' '(^|[ "'"'"'`:])blur([ "'"'"'`]|$)' 'blur-sm\b' 'drop-shadow' '(^|[ "'"'"'`:])backdrop-blur([ "'"'"'`]|$)'; do printf '%s files=%s hits=%s\n' "$p" "$(grep -lE "$p" $S | wc -l)" "$(grep -oE "$p" $S | wc -l)"; done
```

Record the output. This is the "before" column for Task 2 Step 4. v4 renames for the added patterns: bare `ring` 3px → 1px (explicit `ring-N` unchanged); bare `shadow` → `shadow-sm`, `shadow-sm` → `shadow-xs`; bare `blur` → `blur-sm`, `blur-sm` → `blur-xs` (here every `blur-sm` hit is `backdrop-blur-sm`); `drop-shadow` → `drop-shadow-sm`; bare `backdrop-blur` → `backdrop-blur-sm`. Measured on `4cb7470`: bare `ring` 0, `ring-N` 41 hits / 23 files, bare `shadow` 0, `shadow-xs` 0, bare `blur` 0, `blur-sm` 5 / 3, `drop-shadow` 0, bare `backdrop-blur` 0.

- [ ] **Step 4: "Before" evidence (amended, brief §4.2-§4.3).** No local capture, no pixel threshold. New spec `e2e/tailwind4-styles.spec.ts` asserts the computed styles Tailwind 4 changes by default (border colour, placeholder colour, button cursor, 44px touch target, collision guards, focus ring) on elements with no explicit class for that property, and writes 1280×800 full-page screenshots of `/setup`, `/inbox`, `/trends`, `/verify`, `/explain`, `/medications`, `/settings`, `/timeline`, `/search`, `/recover`, the open `DoseLoggingModal` and a dark `/inbox` to `test-results/tw4-shots/`, on data seeded through the backend's own write routes (brief §4.7; no `page.route`). One `actions/upload-artifact@v4` step in `ci.yml` uploads them (TW4-O1). Pushed on Tailwind 3 first: CI green = the **before** shots.

### Task 1: Run the upgrade tool

- [ ] **Step 1.** On Windows, from `src/frontend` with a clean tree: `npx @tailwindcss/upgrade@4`. Paste its full output.
- [ ] **Step 2.** `git status --short` and `git diff --stat`. Expected files: `package.json`, `package-lock.json`, `postcss.config.js`, `tailwind.config.js` (deleted or reduced), `src/styles/globals.css`, and component files with renamed classes. Any file outside `src/frontend`: STOP.
- [ ] **Step 3.** Confirm `package.json` changes: `tailwindcss` `^4.x`, `@tailwindcss/postcss` added, `autoprefixer` removed or unused. No other dependency moved; if one did, STOP and report.

### Task 2: Complete what the tool leaves

- [ ] **Step 0: Delete the colliding variables.** Re-run `grep -rn 'var(--\(color\|radius\)' src` (expect 0 lines), then delete `globals.css:7-10` and `:16-19` (keep `--font-*` and `--shadow-*`). If the grep is non-zero, STOP: a consumer exists and needs its own decision.
- [ ] **Step 1: `tailwind-merge` 3.** `npm install tailwind-merge@^3` (Windows). This is a named major in the approval. `utils/cn.ts` keeps its API (`twMerge(clsx(inputs))`).
- [ ] **Step 2: Border and button defaults.** Add the compatibility rules to `globals.css` under `@layer base` with the **v3 hex literals**, not `var(--color-gray-*)`: v4's gray palette is oklch and Chromium serialises a computed oklch colour as `oklch(...)`, so it can never equal the v3 `rgb(...)` (Fable). Replace any tool-injected `var(--color-gray-200, currentcolor)` line:
  - `*, ::after, ::before, ::backdrop, ::file-selector-button { border-color: #e5e7eb; }`
  - `button:not(:disabled), [role="button"]:not(:disabled) { cursor: pointer; }`
  - `input::placeholder, textarea::placeholder { color: #9ca3af; }`
- [ ] **Step 3: Custom utilities.** Turn `globals.css` `@layer utilities { .min-h-target … }` into one `@utility min-h-target { … }` block per class, and the same for `min-w-target` and `animation-delay-*`.
- [ ] **Step 4: Re-run Task 0 Step 3.** Expected after the migration: `shadow-sm`, `backdrop-blur-sm`, `outline-none`, `flex-shrink|grow` and the old-meaning bare `rounded` are 0, or appear only under their v4 meaning, with each remaining hit explained in the PR body.
- [ ] **Step 5: Checks** (Windows): `npx tsc --noEmit`, `npm run lint`, `npm run build`, `npx vitest run`, `npm audit`. Paste each. Expected: all rc 0; vitest 200 tests / 36 files (Task 0 baseline on `4cb7470`) → 201 / 37 (`cn.test.ts`); `npm audit` no longer lists `braces`, `micromatch`, `chokidar`, `fast-glob` or `tailwindcss`. Also: the lockfile diff with each changed package's consumers and its MAJORS-TIED class (brief §4.4), the token inventory (brief §4.6), and the Linux native-binary check (brief §4.4) run right after Task 1, before the tool commit is pushed.
- [ ] **Step 6: Commit** in 2 commits, with explicit pathspecs taken from `git status --short`:
  1. `feat(frontend): migrate to Tailwind CSS 4 with the official upgrade tool`
  2. `fix(frontend): tailwind-merge 3, drop colliding :root vars, v3 border/cursor/placeholder defaults, @utility blocks`

### Task 3: Visual verification (blocks the PR)

- [ ] **Step 1 (amended, brief §4.3).** Draft PR push sequence: spec on Tailwind 3 → CI green (before shots); tool commit alone → CI red on the named asserts; fix commit → CI green (after shots). Both artifact runs are linked in the PR body.
- [ ] **Step 2 (amended).** No pixel diff and no threshold (TW4-VISUAL). The owner looks at the before/after CI screenshot pairs; the L1 never accepts a visual delta.
- [ ] **Step 3.** Check the `cn()` merge: in a vitest run, `cn('outline-none', 'outline-hidden')` must return `'outline-hidden'` (tailwind-merge 2 reads `outline-hidden` as a colour and keeps both; 3 knows it as an outline style). Do **not** use a custom shadow such as `shadow-card`: tailwind-merge files it as a shadow *colour*, so it never merges with a size class in either version (already true today for `shadow-sm` + `shadow-card`). Add this as a test in `src/__tests__/cn.test.ts` (new, 1 test) during Task 2, paste it RED on tailwind-merge 2 and GREEN on 3.
- [ ] **Step 4.** Reviews: `code-reviewer` plus a reviewer who opens the screenshot pairs. CI 6/6 (E2E Smoke included).

## Stop gates

- No approval recorded, or `tailwind-merge` 3 not named in it.
- The upgrade tool touches files outside `src/frontend`, or moves a dependency other than tailwindcss, `@tailwindcss/postcss`, autoprefixer or tailwind-merge.
- Any check fails, or vitest's count changes by anything other than +1 (`cn.test.ts`).
- The owner has not looked at the CI screenshot pairs.
- MAJORS-TIED (`:72`): a lockfile ADDED or MAJOR package that is neither (a) pulled in by tailwindcss / `@tailwindcss/*` / tailwind-merge nor (b) a major whose sole consumer is one of them. Top-level `jiti` 1 → 2 is tied (b) per TW4-O4; any other optional-peer major stops.

## File list (brief §4.1)

`docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md`; `src/frontend/e2e/tailwind4-styles.spec.ts` (new); `.github/workflows/ci.yml` (one upload step); `src/frontend/package.json`, `src/frontend/package-lock.json`; `src/frontend/postcss.config.js`, `tailwind.config.js`, `src/styles/globals.css`, `index.html` (only if renamed); component / page `.tsx` (class renames only); `src/frontend/src/__tests__/cn.test.ts` (new); `README.md` and `docs/user/getting-started.md` (browser floor line); `src/frontend/README.md:179`; `audit/2026-09-25/waves/wave-4-L1-B.md` (L1 report). Nothing else.

## Rollback

One PR: `git revert -m 1 <merge sha>` (the repo merges with merge commits), then `npm ci`. No data, schema or API change.

## Out of scope

- A visual redesign, or adopting new v4 features (container queries, `@starting-style`).
- react-router 7 (its own plan: [2026-10-04-NPM-MAJORS-react-router7.md](2026-10-04-NPM-MAJORS-react-router7.md)).
- Serving `dist/` instead of the Vite dev server (`dev.ps1:281-282`; PR #38 security finding M2).
