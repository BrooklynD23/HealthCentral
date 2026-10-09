**DISPATCH-READY (reviewed, not dispatched; owner answers TW4-O1..O4 recorded 2026-10-09)** — L1 brief for Tailwind 4 (frontend sequence, phase 3 of 3)

# Tailwind 4 — L1 brief

**Last Updated:** 2026-10-09

Built from [../scaffold/TAILWIND-4.md](../scaffold/TAILWIND-4.md), the Tailwind items of [../scaffold/REVIEWS-2026-10-07.md](../scaffold/REVIEWS-2026-10-07.md) §1, the signed owner rows below, and the templates in [../../handoff-2026-09-28-execution-orchestrator.md](../../handoff-2026-09-28-execution-orchestrator.md) §4-§7. Pre-dispatch reviews: Codex plan review ([../../swarm-2026-09-27/reviews/TAILWIND-4-codex.txt](../../swarm-2026-09-27/reviews/TAILWIND-4-codex.txt)) and Fable 5.1 adversarial review ([../../swarm-2026-09-27/reviews/TAILWIND-4-fable.md](../../swarm-2026-09-27/reviews/TAILWIND-4-fable.md)); the disposition of every finding is in §6.

## 1. State on `origin/main` = `eb7de28` (measured 2026-10-09, read only)

| Check | Result |
|---|---|
| NPM-AUDIT-2 #52, DEV-PS1 #55, React Router 7 #57 | merged (`eb7de28` is the #57 merge) |
| `dev.ps1` reinstall | `dev.ps1:628-642`: reinstalls on `lockfile-changed` (hash of `package-lock.json`). DEV-PS1-FIRST satisfied |
| `package.json` | `tailwindcss ^3.4.1`, `tailwind-merge ^2.2.0`, `autoprefixer ^10.4.16`, `postcss ^8.4.33`, `react-router-dom ^7.18.4`, `engines.node >=22` |
| lock | tailwindcss 3.4.19, tailwind-merge 2.6.0, jiti 1.21.7, postcss 8.5.28, vite 7.3.6; no `@tailwindcss/*`, no `lightningcss*` |
| `jiti` consumers in lock | `eslint` (peer `*`, optional), `postcss-load-config` (peer `>=1.21.0`, optional), `tailwindcss` (dep `^1.21.7`), `vite` (peer `>=1.21.0`, optional). Not tailwind-only |
| Tailwind 3 chain, sole consumer `tailwindcss` | `chokidar`, `fast-glob`, `postcss-load-config`, `postcss-nested`, `sucrase` |
| Drift of Tailwind files since plan base `90c502a` | `git diff --stat 90c502a origin/main -- tailwind.config.js postcss.config.js src/styles src/utils/cn.ts src/components/ui index.html` → empty |
| Baselines (handoff 2026-10-09 `:16`) | vitest 197 / 35 files; Playwright chromium 33 listed (all projects 38); backend collected 1381; `npm audit` 7 (2 moderate, 5 high) |
| CI | runs on `pull_request` to `main` only (`ci.yml:3-7`). E2E job (`ci.yml:177-213`) runs `npx playwright test --project chromium`; **no artifact upload step**. Frontend job has no `npm run build` |
| E2E seeding | no data-seeding helper: `e2e/support/auth.ts` creates and resets a profile only. Specs fake data with `page.route` (`assistant.spec.ts:129`) |
| Elements with explicit colours (cannot detect a default change) | `Card.tsx:10` `border border-black/[0.04]`; `Input.tsx:37` `placeholder:text-ink-tertiary` |

## 2. Signed gates (verbatim, `docs/capstone-report/owner-decisions-2026-09-27.md`)

- `:64` NPM-MAJORS-RUN: "NPM-AUDIT-2, then React Router 7, then Tailwind 4, each as its own PR. Largest frontend churn of the three."
- `:69` FE-SEQ: "tailwind-merge 3 is approved by name for the Tailwind 4 PR; any other transitive major bump (dev/test-only or not) comes back to you before it lands. Fable and Codex review the three briefs before dispatch."
- `:70` DEV-PS1-FIRST: "Tailwind 4 refuses to start until it is merged." (merged, #55)
- `:71` TW4-BROWSERS: "The app runs on the patient's own machine in a current browser; state the minimum versions in the README and user docs as part of the PR."
- `:72` MAJORS-TIED: "Pre-approve only (a) new packages pulled in by an approved major and (b) major bumps of packages whose sole consumer is that approved major. Every such package is listed in the PR body from a lockfile diff. Any other major still stops and comes back to you."
- `:73` TW4-VISUAL: "New Playwright checks, run in CI on seeded data, assert computed styles that Tailwind 4 changes by default (card border colour, input placeholder colour, button cursor, 44px touch target). Plus before/after screenshots of the 10 routes from CI artifacts for you to eyeball. No pixel threshold."

Answers to this brief's §7 questions (2026-10-09, L0 AskUserQuestion; rows `TW4-O1`..`TW4-O4` in owner-decisions on `docs/wave4-close`, PR #60 — the L1's Task 0 greps `origin/main` for them, so PR #60 must be merged first):

- TW4-O1 **Yes, add the step**: "One CI step uploads Playwright screenshots. Downside: a CI file edit inside a frontend PR."
- TW4-O4 **Yes, tied**: "jiti 2 ships in the Tailwind PR. Downside: an optional-peer consumer could load jiti 2 unexpectedly; the lockfile script prints each consumer to check."
- TW4-O2 **Real seeding everywhere**: "Most faithful. Downside: open-ended setup work per route." Bounded in §4.7.
- TW4-O3 **Yes**: "Doc matches the code at merge; brand guidelines are a follow-up."

Nothing is left unsigned except the owner's look at the screenshots. The screenshot look is the owner's call at PR time; the L1 never accepts a visual delta.

## 3. What changed from the scaffold brief (scaffold §6.1)

1. Gates Q1 (`tailwind-merge` 3), Q2 (browser floor), Q4 (`dev.ps1`) are signed; Q3 (where screenshots come from) is answered by TW4-VISUAL: CI artifacts.
2. The 0.5% pixel threshold and the local "before/after" capture are gone (TW4-VISUAL: "No pixel threshold"). Evidence = computed-style Playwright asserts in CI + CI screenshot artifacts.
3. The file list grows by: one new Playwright spec, one `ci.yml` upload step (TW4-VISUAL "from CI artifacts", TW4-O1), the README + user docs browser floor (TW4-BROWSERS), `src/frontend/README.md:179`.
4. Break-its move into the commit sequence: the upgrade-tool commit is pushed alone, and CI must go **red** on the style asserts before the fix commit makes it green (§4.3).
5. `$LASTEXITCODE` is escaped (`\$LASTEXITCODE`) in every bash-quoted PowerShell line (REVIEWS §1 item 1).
6. A nested-aware lockfile diff over every `packages` key, with each changed package's consumers, is mandatory; `jiti` 1 → 2 is tied (b) per TW4-O4 (REVIEWS §1 items 2, 3; MAJORS-TIED).
7. The Codex **plan** review is done (this PR); the L1 runs only the Codex **diff** review.

## 4. Plan amendments (L1 commits these to the plan file as commit 0)

Plan: `docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md`. Amend, do not rewrite:

1. `:3`, `:5`: status → approved for execution (`owner-decisions:64`, `:69`-`:73`).
2. Task 0 Step 1: gate = rows `:64`, `:69`, `:70`, `:71`, `:72`, `:73` plus the §7 answers; dependencies = #52 (`f428a99`), #55 (`87accae`), #57 (`eb7de28`) on `origin/main`.
3. `:6`, `:9`, `:55`: "5 high" → the Task 0 measured `npm audit` list.
4. Scope row "Custom CSS layers": 1 consumer `.tsx` (`Sidebar.tsx:68`), not 2. Add rows: `bg-gradient-to-br` (`Sidebar.tsx:44`, `ProfileSetup.tsx:224`), `index.html:19` body classes, `globals.css:66` `outline-none` inside `@apply`, the duplicate `@keyframes slideUp` (`globals.css:110` vs config; Fable verified identical content), `transitionDuration` 250/350, `:root --font-*` (`globals.css:12-14`) sharing names with the `@theme` `--font-display/body/mono` the tool generates (values must stay identical).
5. Task 0 Step 3 grep loop: add bare and explicit `ring`, bare `shadow`, `shadow-xs`, bare `blur`, `blur-sm`, `drop-shadow`, bare `backdrop-blur` (Codex). Report which v4 renames apply to each.
6. Task 0 Step 4 and Task 3 Steps 1-2: replace with §4.2-§4.3 of this brief (CI spec, CI artifacts, no threshold).
7. Task 2 Step 2 compat rules: use the **v3 hex literals**, not `var(--color-gray-*)`: `border-color: #e5e7eb` and `::placeholder { color: #9ca3af }`. v4's gray palette is oklch, and Chromium serialises computed oklch as `oklch(...)`, so `var(--color-gray-200)` can never equal `rgb(229, 231, 235)` (Fable). Replace the tool-injected `var(--color-gray-200, currentcolor)` line too.
8. Task 2 Step 5: add the lockfile diff (§4.4), the token inventory (§4.6) and the Linux native-binary check (run right after Task 1, before the first push).
9. Stop gates: replace "A screenshot delta the owner has not accepted" with "the owner has not looked at the CI screenshot pairs"; add the MAJORS-TIED stop.
10. File list: as §4.1.
11. vitest expectation: absolute numbers from the Task 0 baseline (+1 test, +1 file).

### 4.1 File ownership

| File | Change | Covered by |
|---|---|---|
| `docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md` | §4 amendments | this review |
| `src/frontend/e2e/tailwind4-styles.spec.ts` | **new**: computed-style asserts + screenshots | TW4-VISUAL |
| `.github/workflows/ci.yml` | one `actions/upload-artifact@v4` step in `e2e-tests` after `:210`, `if: always()`, `path: src/frontend/test-results/tw4-shots/**` (workspace-relative; pattern `ci.yml:142`; `.gitignore:130` already ignores `src/frontend/test-results/`) | TW4-VISUAL, TW4-O1 |
| `src/frontend/package.json`, `package-lock.json` | tailwindcss `^4`, `@tailwindcss/postcss` added, autoprefixer removed, tailwind-merge `^3` | `:64`, `:69`, `:72`, TW4-O4 (jiti) |
| `src/frontend/postcss.config.js`, `tailwind.config.js`, `src/styles/globals.css`, `index.html` (only if renamed) | plan Tasks 1-2 | `:64` |
| component / page `.tsx` | class renames only (upper bound 58 files) | `:64` |
| `src/frontend/src/__tests__/cn.test.ts` | **new**, 1 test | plan Task 3 Step 3 |
| `README.md` (Prerequisites, `:316`) and `docs/user/getting-started.md` (Prerequisites, `:3`) | one line each: Safari 16.4+, Chrome 111+, Firefox 128+ | TW4-BROWSERS |
| `src/frontend/README.md:179` | "Implement in `tailwind.config.js`" → the `@theme` block in `src/styles/globals.css` | TW4-O3 |
| `audit/2026-09-25/waves/wave-4-L1-B.md` | L1's phase-3 report section (L1 writes it, not L2) | orchestration §3 |

Not touched: any backend file, `dev.ps1`, `docs/brand/brand-guidelines.md` (`:5`, `:121` go stale; follow-up per TW4-O3).

### 4.2 The style spec (`e2e/tailwind4-styles.spec.ts`)

- Auth state per route: `/setup` and `/recover` unauthenticated (fresh context, no stored session); all others through `openAuthenticatedPage` (`e2e/support/auth.ts:90`). If `/setup` redirects because the E2E profile exists, screenshot what it shows and say so.
- Data for the screenshot set: real seeding through the backend's own write routes, per §4.7 (TW4-O2). The asserts below need no data.
- Each assert targets an element that relies on the **default** and carries **no explicit class for that property**. Cite its `file:line` in the spec. Not valid: `Card.tsx:10`, `Input.tsx:36-43` (`border-black/[0.08]`), any input with a `placeholder:` class (`TopBar.tsx:31`, `ExplainAssistant.tsx:722,799`, `ExportPage.tsx:472`, `DoseLoggingModal.tsx:188`), `Button.tsx:10` for focus (own `focus-visible:outline-none`).
- Asserts (expected values are the Tailwind 3 output; the spec must pass on Tailwind 3 first):
  1. border colour: the recovery-code input `#recover-code` (`RecoverProfile.tsx:136-143`, bare `border`, unauthenticated, no fixtures) → `borderTopColor` = `rgb(229, 231, 235)`;
  2. placeholder colour: the same input → `getComputedStyle(el, '::placeholder').color` = `rgb(156, 163, 175)`;
  3. button cursor: a `<button>` with no `cursor-*` class → `pointer`;
  4. touch target (app-specific check the owner named; it does not prove a Tailwind default, Codex): the Sidebar NavLink (`Sidebar.tsx:66-68`) → `getBoundingClientRect().height >= 44` and computed `min-height` = `44px`;
  5. collision guards: `document.body` `backgroundColor` = `rgb(250, 250, 248)`; one `rounded-lg` element `borderTopLeftRadius` = `8px`; one `text-ink` element `color` = `rgb(31, 31, 31)`;
  6. focus ring on the Sidebar NavLink (relies on `globals.css:65-67`): keyboard-focus it, then `boxShadow !== 'none'` AND (`outlineStyle === 'none'` OR `outlineColor === 'rgba(0, 0, 0, 0)'`). v3 `outline-none` and v4 `outline-hidden` both pass; a visible outline fails.
- Screenshots: 1280×800 full page of `/setup`, `/inbox`, `/trends`, `/verify`, `/explain`, `/medications`, `/settings`, `/timeline`, `/search`, `/recover`, plus the open `DoseLoggingModal`; one extra `/inbox` with `colorScheme: 'dark'` (`Skeleton.tsx:15` is the only `dark:` use). Context `reducedMotion: 'reduce'`, `page.screenshot({ fullPage: true, animations: 'disabled' })` (framer-motion on every route). Write to `test-results/tw4-shots/`. No `toHaveScreenshot`, no threshold: the shots never fail the job.
- Do not add classes for test purposes to the spec file: v4's automatic source detection scans `e2e/` (not gitignored) and v3's `content` list does not, so a class that exists only in the spec renders in one version and not the other.
- Playwright count: chromium 33 → 33 + the spec's test count; state the number. `tsc --noEmit` does not check `e2e/` (`tsconfig.json:31` `include: ["src"]`): `npx playwright test --list --project chromium` is the compile check.

### 4.3 Commit and push sequence (each push runs CI on the draft PR)

| # | Commit | Push | CI must show |
|---|---|---|---|
| 0 | `docs(plans): Tailwind 4 plan amendments` | — | — |
| 1 | `test(frontend): Tailwind computed-style checks and CI screenshots` (spec + `ci.yml` step), still on Tailwind 3 | push, open **draft** PR | E2E green; artifact = **before** shots. Green on v3 proves each assert encodes v3 |
| 2 | `feat(frontend): migrate to Tailwind CSS 4 with the official upgrade tool` (tool output only). L1 runs the §4.4 native check **before** this push | push | **red**. Expected red: border (oklch or currentColor), placeholder, cursor, body background, `rounded-lg` (16px from `:root --radius-lg`), `text-ink` (invalid `31 31 31`); record exactly which. Not expected red: touch target, focus ring. Any assert never red in any run: L1 argues from the tool diff why it can fail, or reports it unproven |
| 3 | `fix(frontend): tailwind-merge 3, drop colliding :root vars, v3 border/cursor/placeholder defaults, @utility blocks` + `cn.test.ts` | push | all 6 CI jobs green; artifact = **after** shots |
| 4 | `docs: Tailwind 4 browser floor and token source` | push | docs-lint green |

The PR body links both artifact runs, lists which asserts were red at #2, and says "screenshots: owner to review, no threshold; browser floor from Tailwind 4 docs, verified in Chromium only (`playwright.config.ts:68-79`)".

### 4.4 Lockfile diff (mandatory, paste output in the PR body)

Read-only, from WSL, stdlib Python, outside the repo. Prints each added / removed / major-moved key and, for added and major lines, every package that depends on it (dependencies, optional, peer; `?` = optional peer):

```bash
git -C <wt> show origin/main:src/frontend/package-lock.json > /tmp/tw4-base.json
python3 -I - /tmp/tw4-base.json <wt>/src/frontend/package-lock.json <<'PY'
import json, sys
a, b = (json.load(open(p))['packages'] for p in sys.argv[1:3])
maj = lambda v: (v or '0').split('.')[0]
name = lambda k: k.rsplit('node_modules/', 1)[-1]
def users(n):
    out = []
    for k, v in b.items():
        for f in ('dependencies', 'optionalDependencies', 'peerDependencies'):
            if n in v.get(f, {}):
                opt = f == 'peerDependencies' and v.get('peerDependenciesMeta', {}).get(n, {}).get('optional')
                out.append((name(k) or '<root>') + ('?' if opt else ''))
    return sorted(set(out))
for k in sorted((set(a) | set(b)) - {''}):
    va, vb = a.get(k, {}).get('version'), b.get(k, {}).get('version')
    if va is None: print('ADDED  ', k, vb, 'used by', users(name(k)))
    elif vb is None: print('REMOVED', k, va)
    elif maj(va) != maj(vb): print('MAJOR  ', k, va, '->', vb, 'used by', users(name(k)))
PY
```

Classify every ADDED and MAJOR line under MAJORS-TIED: (a) pulled in by tailwindcss / `@tailwindcss/*` / tailwind-merge; (b) major bump whose sole consumer is one of them. Anything else STOPS. **jiti**: expected top-level 1.21.7 → 2.x, hard dependency only of `@tailwindcss/node`, optional peer of eslint, vite, postcss-load-config. Owner: tied (b) (TW4-O4) — list it in the PR body with its consumer line. Any other optional-peer major still stops.

Linux natives: the lock must hold `@tailwindcss/oxide-linux-x64-gnu` and `lightningcss-linux-x64-gnu` next to the win32 entries, and still hold `@rollup/rollup-linux-x64-gnu` and `@esbuild/linux-x64`. Missing → stop before pushing commit 2 (CI `npm ci` is the first place it breaks).

### 4.5 `cn()` drift check (throwaway, outside the repo)

In a scratch dir outside the repo, install `tm2@npm:tailwind-merge@2.6.0` and `tm3@npm:tailwind-merge@3`. Extract inputs with the TypeScript compiler API (`typescript` is already a devDependency) from `src/frontend/src`: every string literal argument of `cn(` (39 files), and for every `cva(` call the base string plus the full cartesian product of its variant values (including `defaultVariants`), each also merged with every literal `className` passed to that component. Run both versions on each input and print every input whose outputs differ. Report three numbers: inputs checked, differing, and `cn(` arguments that are non-literal (not covered). Each difference is a v4 rename (expected: name it) or a regression (fix or stop).

### 4.6 Token inventory (Codex)

Before/after table in the PR body, one row per `tailwind.config.js` token: `fontSize` xs-4xl (size and line height), `spacing` 18/88/128, `borderRadius` xl/2xl/3xl, `boxShadow` soft/card/elevated/focus, the 6 animations and keyframes, `transitionDuration` 250/350, the colour groups `surface/ink/accent/status/dark`. Columns: v3 value (config), v4 value (the generated `@theme` line), consumer count (grep), and whether the value appears in the built CSS (`npm run build`, grep `dist/assets/*.css`). Any value that changed: stop. `dark-*` colour classes (e.g. `bg-dark-surface`) are checked separately from the `dark:` variant.

### 4.7 Real seeding per screenshot route (TW4-O2)

Rule: every screenshot route gets its data from the running backend's own write routes, in the spec's `beforeAll`, through Playwright `request` with the token from `ensureE2EProfile` (`e2e/support/auth.ts:19`). **No `page.route` anywhere in the spec** (`grep -c 'page.route' e2e/tailwind4-styles.spec.ts` → `0`, pasted). No new backend route, no direct DB write, no new backend file.

Seed set (measured 2026-10-09; one seed serves several routes):

| Seed | Mechanism (real route) | Content |
|---|---|---|
| S1 lab CSV, 2 imports | `POST /api/v1/documents/` multipart (`api/documents.py:402`); `.csv` → `lab_csv` (`modules/ingest.py:158-159`); parsed by `parse_lab_csv` without OCR or a model (`api/documents.py:710-739`); header format per `tests/test_structured_import.py:69-71` | `Date,Analyte,Value,Unit,Reference Low,Reference High,Flag`; Glucose and Hemoglobin A1c at 3 dates each, one value flagged `H`. Two files, different content (imports dedupe by content hash, `document-import.spec.ts:89-93`) |
| S2 verify part of S1 | `GET /api/v1/observations/` (`api/observations.py:285`), then `POST /api/v1/observations/{id}/verify` (`:381`) for the Glucose rows only | structured imports land `user_verified=False` (`api/documents.py:722`, `:759`); Hemoglobin A1c stays unverified for `/verify` |
| S3 medication | `POST /api/v1/medications/` (`api/medications.py:310`; body `MedicationCreate`, `:91-104`: `name`, `dosage_amount`, `dosage_unit`, `frequency`) + `POST /{id}/schedules` (`:675`) | one active medication with a once-daily schedule |
| S4 assistant | `POST /api/v1/assistant/sessions` (`api/assistant.py:394`) + one `POST /api/v1/assistant/chat` (`:729`) | one real question; the real answer (CI has no model: expect the insufficient-context or abstain text, as `assistant.spec.ts` E2E-RAG-001 shows) is what the shot shows |

| Route | Auth | Seeds it shows |
|---|---|---|
| `/setup` | none | no profile data by design |
| `/recover` | none | no profile data by design |
| `/inbox` (+ dark) | yes | S1 documents |
| `/verify` | yes | S1 Hemoglobin A1c (unverified) |
| `/trends` | yes | S2 Glucose (3 verified, dated points) |
| `/timeline` | yes | S1/S2 observations, S3 medication |
| `/search?q=Glucose` | yes | S1 (local search over the profile DB, `api/search.py:1`, `:55`) |
| `/medications` + `DoseLoggingModal` | yes | S3; open the modal via the quick-log button (`MedicationCoach.tsx:241-243`) |
| `/explain` | yes | S4 session and real response |
| `/settings` | yes | profile settings only; no seed needed |

Ordering: the spec runs after `global-setup.ts:12-13` resets the profile, and `workers: 1` (`playwright.config.ts:56`) runs files one at a time, so no other spec resets mid-file. If another spec already seeded the same CSV, the dedupe returns the existing document: assert on content, not counts.

**Stop rule:** if a route's seed does not render (the route shows its empty state after its seed call returned 2xx), or a seed call fails, or a route turns out to need data no write route can create: STOP, report the route, the call, its status and body. Do not fall back to `page.route`, do not skip the route, do not add a backend route.

**Effort estimate (L1-lead, not measured):** spec with seeding ~150-200 lines, about 2-3 h of L2 time; each CI round trip ~25-40 min (E2E waits on backend tests, `ci.yml:180`). Sequence §4.3 needs 4 pushes, so plan for 2-4 h of CI wall time; the whole phase about one working day if no stop fires.

### 4.8 Merge order vs PR #64

PR #64 (`chore/ponytail-cleanup`, open) edits `src/frontend/package.json`, `src/frontend/package-lock.json` and the root `package-lock.json`. If #64 merges first: rebase `feat/tailwind4` on `origin/main`, **regenerate** `src/frontend/package-lock.json` on Windows (`npm install` from the rebased `package.json`; never resolve lockfile conflicts by hand), re-run §4.4 against the new base, and re-run the Windows acceptance. If Tailwind 4 merges first, #64 does the same. The PONYTAIL removals (`@radix-ui/react-dialog`, `react-tabs`, `react-tooltip`, `date-fns`) are not in this phase's package list; a rebase must not re-add them.

## 5. The brief

```
You are the L1 Wave Orchestrator for the Wave 4 frontend sequence of the
Asclexis execution program. Follow docs/agentic/orchestration.md §3 exactly;
you are L1. This brief covers phase 3 of 3: Tailwind 4.
Read first: audit/2026-09-25/waves/briefs/TAILWIND-4-L1-brief.md (all of
it; §4 is binding), then docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md and
audit/2026-09-25/waves/scaffold/TAILWIND-4.md §7.
Base: origin/main @ <sha at dispatch>. Confirm merged with
`git merge-base --is-ancestor <sha> origin/main; echo $?` for NPM-AUDIT #38
(c4d407e), NPM-AUDIT-2 #52 (f428a99), DEV-PS1 #55 (87accae), React Router 7
#57 (eb7de28). Any
non-zero: STOP.
Signed gates: brief §2 (owner-decisions :64, :69, :70, :71, :72, :73 and
TW4-O1..TW4-O4), verbatim. If `grep -c 'TW4-O' docs/capstone-report/
owner-decisions-2026-09-27.md` on origin/main is not 4 (PR #60 unmerged):
STOP.
Architectural: no (orchestration §5). Owner-directed reviews: the Codex
plan review and the Fable brief review are DONE (brief §6). You run the
Codex diff review before marking the PR ready (handoff §7.2), focus:
"no visible regression; every renamed class keeps its v3 meaning; cn()
still merges; no transitive major outside MAJORS-TIED".
Worktree ../hc-tw4, branch feat/tailwind4, one PR, opened as DRAFT at
brief §4.3 commit 1. Do NOT reuse ../hc-npm-majors or ../hc-tw4-plan.
Host: 12 GB. You are the only code L1 running; no local Linux Playwright
while another L1 runs.
Commit 0 (yourself): the plan amendments in brief §4, pathspec = the plan
file only.
Spawn one implementer: Agent(subagent_type="general-purpose",
model="sonnet") with the L2 brief below; one L2 at a time. Reviewers:
Agent(subagent_type="code-reviewer", model="opus") who also opens every
before/after CI screenshot pair, the §4.5 cn() diff and the §4.6 token
table, and
Agent(subagent_type="security-reviewer", model="opus") for the lockfile
(registry.npmjs.org only, sha512 integrity, install scripts listed) and to
confirm the diff in ProfileSetup, RecoverProfile, ExportPage, SettingsPage
is class names only.
Run the acceptance yourself, FROM WINDOWS (paste all output; every
exit code must print a number):
  powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-tw4\src\frontend; Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue; npm ci; echo ci=\$LASTEXITCODE; npm audit 2>&1 | Select-Object -Last 8; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE; npm run build; echo build=\$LASTEXITCODE; npx vitest run 2>&1 | Select-Object -Last 6; npx playwright test --list --project chromium 2>&1 | Select-Object -Last 1"
A blank after "=" means the line is broken: fix the quoting, do not read
it as 0. Then the plan's Task 0 Step 3 grep loop (WSL, read-only) at base
and at HEAD, side by side; then the brief §4.4 lockfile diff (and its
Linux-native check BEFORE you push commit 2), §4.5 cn() diff, §4.6 token
table. CI has no build step: the Windows `npm run build` is the only
build evidence.
Expected: vitest 197/35 -> 198/36 (use your measured baseline +1/+1);
Playwright chromium 33 -> 33 + N (N = tests in the new spec); backend
collected 1381, delta 0, suite not run; npm audit no longer lists braces,
micromatch, chokidar, fast-glob or tailwindcss (measure; report what stays).
Visual evidence: brief §4.2-§4.3 and §4.7 (real seeding, stop rule) only. CI red at commit 2 on the named
asserts is required; CI green at commit 3; before/after artifacts linked
in the PR body; no pixel threshold; you do not judge the look.
PR body: gates used; lockfile diff with MAJORS-TIED class per line; the
red-at-#2 list; artifact links; grep table; the hover-only-on-hover-media
and browser-floor notes; rollback: `git revert -m 1 <merge>` then
dev.ps1 reinstalls on the lockfile hash change (#55) in both directions.
Merge-order notes: PR #64 (PONYTAIL-CLEANUP) and the RR7-Q3 engines PR
also edit package.json / package-lock.json: brief §4.8 (rebase, regenerate
the lockfile on Windows, re-run §4.4 and acceptance); BG-WARN-INTERP edits the Lab Interpreter
page; W-3 / W-2 cite line ranges in TrendsDashboard, InterpretedTrendChart,
ExportPage. Whoever lands second rebases and re-runs the lockfile diff.
Write audit/2026-09-25/waves/wave-4-L1-B.md (append a phase-3 section).
Do not merge. Do not sign gates. Do not edit files outside brief §4.1.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### 5.1 L2 implementer brief

```
Implement docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md as amended in
commit 0, plus audit/2026-09-25/waves/briefs/TAILWIND-4-L1-brief.md §4.2
(style spec), in worktree /mnt/c/Users/DangT/Documents/GitHub/hc-tw4 on
branch feat/tailwind4. No Python is needed for product work. All npm /
npx / vitest commands run from Windows through powershell.exe, never from
WSL; in any bash-quoted PowerShell line write \$LASTEXITCODE.
Order (L1 pushes between steps; you do not push):
 1. Write e2e/tailwind4-styles.spec.ts per brief §4.2 and the ci.yml
    upload step, on Tailwind 3, with the real seeding of brief §4.7 (no
    page.route; obey its stop rule). Use the target elements brief §4.2 names;
    for each assert cite file:line and show it has no explicit class for
    that property. Run `npx playwright test --list --project chromium`
    (Windows) and paste the count: tsc does not check e2e/.
    Commit: test(frontend): Tailwind computed-style checks and CI screenshots
 2. Clean tree (`git status --short`, paste it), then
    `npx @tailwindcss/upgrade@4`; paste its full output. Commit the tool
    output only: feat(frontend): migrate to Tailwind CSS 4 with the official upgrade tool
 3. Read the tool's whole diff. Report, do not fix silently: any rename not
    in the plan's scope table (candidates: bg-gradient-to-br at Sidebar.tsx:44
    and ProfileSetup.tsx:224; index.html:19; outline-none inside @apply at
    globals.css:66); any `@config` line left; what happened to the duplicate
    @keyframes slideUp (globals.css:110), transitionDuration, and the
    :root --font-* lines vs the generated @theme --font-*.
 4. Test first: write src/__tests__/cn.test.ts
    (cn('outline-none', 'outline-hidden') -> 'outline-hidden'), run it on
    tailwind-merge 2, paste the FAIL; npm install tailwind-merge@^3; paste
    the PASS. Then plan Task 2 Steps 0-5 as amended: compat rules use the
    hex literals #e5e7eb (border) and #9ca3af (placeholder), replacing any
    tool-injected var(--color-gray-200, currentcolor) line. Commit:
    fix(frontend): tailwind-merge 3, drop colliding :root vars, v3 border/cursor/placeholder defaults, @utility blocks
 5. One line each in README.md Prerequisites and
    docs/user/getting-started.md Prerequisites: "Browser: Safari 16.4+,
    Chrome 111+, Firefox 128+"; fix src/frontend/README.md:179 to name the @theme block in
    src/styles/globals.css.
    Commit: docs: Tailwind 4 browser floor and token source
Explicit pathspecs from `git status --short` (never `git add -A`); each
commit ends with: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Class names, CSS, build config, the one spec, the one ci.yml step and the
three doc lines only: no change to component logic, props, copy,
services/api.ts, dev.ps1 or any backend file.
Stop and report, without working around it, if: the tool touches a file
outside src/frontend; a dependency other than tailwindcss,
@tailwindcss/postcss, autoprefixer or tailwind-merge moves in package.json;
the lockfile diff (brief §4.4) shows a major or new package outside
MAJORS-TIED (top-level jiti 1 -> 2 is tied per TW4-O4: list it; any
other optional-peer major stops); a §4.7 seed fails or does not render;
the Linux native
packages are missing; `grep -rn 'var(--\(color\|radius\)' src` is
non-zero; tsc, lint, build or vitest fails; the vitest count is not
baseline + 1; a Task 2 Step 4 count is non-zero and you cannot explain
each hit; no element without an explicit class exists for an assert.
Do NOT spawn agents. Do NOT push.
Return: commits (sha + subject); the tool's full output; the before/after
grep table; ci/tsc/lint/build exit codes as numbers; vitest totals before
and after; `npm audit` last lines before and after; the package.json diff;
the §4.4 lockfile diff output; cn.test.ts RED and GREEN output; per-assert
target element (file:line); the unlisted renames; any deviation with its
reason.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 6. Review dispositions

Codex: `gpt-6-luna`, effort `high` (owner order "6.1 sol" first: `gpt-6.1-sol` returned HTTP 400 "not supported when using Codex with a ChatGPT account"), `-s read-only`, verdict **REVISE**. Fable 5.1: verdict **GO WITH AMENDMENTS**. Raw outputs: [TAILWIND-4-codex.txt](../../swarm-2026-09-27/reviews/TAILWIND-4-codex.txt), [TAILWIND-4-fable.md](../../swarm-2026-09-27/reviews/TAILWIND-4-fable.md). L1-lead spot-checked `RecoverProfile.tsx:136-143`, `Button.tsx:10`, `Sidebar.tsx:66-68` and ran the §4.4 script against a synthetic lock (jiti 1→2 line printed with its 5 consumers).

| # | Reviewer | Sev | Finding | Disposition |
|---|---|---|---|---|
| C1 | Codex | BLOCKER | `page.route` fixtures are not "seeded data" | **Owner: TW4-O2 real seeding everywhere**; bounded in §4.7 with a stop rule |
| C2 | Codex | MAJOR | 44px check cannot show a Tailwind default change | **Accepted:** kept (owner named it), relabelled app-specific, not counted as a break-it (§4.2 item 4, §4.3 row 2) |
| C3 | Codex | MAJOR | No value checks for config tokens | **Accepted:** §4.6 token inventory |
| C4 | Codex | MAJOR | Grep loop omits ring / shadow / blur forms | **Accepted:** §4 amendment 5 |
| C5 | Codex | MAJOR | `cn()` check has no parser, misses cva combinations and dynamic args | **Accepted:** §4.5 (TS compiler API, cartesian product, non-literal count reported) |
| C6 | Codex | MAJOR | Lockfile script cannot prove "sole consumer" | **Accepted:** script prints consumers incl. optional peers (§4.4) |
| C7 | Codex | MAJOR | `wave-4-L1-B.md` outside the file list; README `:179` unsigned | **Accepted:** report added to §4.1; `:179` in scope per TW4-O3 |
| F1 | Fable | MAJOR | Compat rules via `var(--color-gray-*)` serialise as oklch; asserts 1-2 stay red | **Accepted:** hex literals (§4 amendment 7, L2 step 4) |
| F2 | Fable | MAJOR | Assert 6 cannot go green on v4 (`outline-hidden` = `outline-style: none`); Button has own outline class | **Accepted:** either-or outline check + ring, Sidebar NavLink target. Corrects the L1-lead's own draft |
| F3 | Fable | MAJOR | jiti stop will fire mid-phase | **Owner: TW4-O4 tied (b)** |
| F4 | Fable | MAJOR | "Pick by grep" leaves the only valid targets to Sonnet | **Accepted:** `RecoverProfile.tsx:136-143` named, `/recover` added, invalid targets listed |
| F5 | Fable | MAJOR | Fixtures per route are unbounded work | **Owner: TW4-O2**; §4.7 enumerates routes, mechanism, effort, stop rule |
| F6 | Fable | MINOR | `rounded-lg` and `text-ink` also red at #2 | **Accepted** (§4.3 row 2) |
| F7 | Fable | MINOR | upload-artifact path is workspace-relative | **Accepted** (§4.1) |
| F8 | Fable | MINOR | `tsc` does not check `e2e/` | **Accepted:** `playwright test --list` in L2 step 1 |
| F9 | Fable | MINOR | Browser floor unverifiable; Chromium only | **Accepted:** PR-body sentence (§4.3) |
| F10 | Fable | MINOR | Native check too late | **Accepted:** before pushing commit 2 |
| F11 | Fable | MINOR | Missing shas, auth state per route, animations, root `""` key | **Accepted** (§4 item 2, §4.2, §4.4) |

L1-lead addition (not from a reviewer): classes written only in the spec file would render under v4 (auto source detection scans `e2e/`) but not v3 (`content` list), so §4.2 forbids them.

Rejected: none. Fable's "verified no-issue" list (duplicate `slideUp` identical; fontSize / spacing / radius convert 1:1; no `darkMode` key; 0 bare `ring`; audit expectation holds) is recorded so the L1 does not re-open it.

## 7. Owner questions — answered 2026-10-09

O-1 → TW4-O1 "Yes, add the step"; O-2 → TW4-O2 "Real seeding everywhere" (bounded in §4.7); O-3 → TW4-O3 "Yes"; O-4 → TW4-O4 "Yes, tied". Verbatim text in §2. The question wording as asked is in the owner-decisions rows.

## 8. Dispatch readiness

**Dispatch-ready.** Every reviewer finding is applied or answered by the owner. Before dispatch: (1) PR #60 merged, so the TW4-O rows are on `origin/main`; (2) this PR (#63) merged; (3) fill `<sha at dispatch>`; (4) decide #64 order (§4.8). No other code L1 on the 12 GB host while this runs.
