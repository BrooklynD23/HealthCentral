Read-only adversarial diff review. Do not edit files or git state; run no tests, no npm.

DIFF UNDER REVIEW: `git diff origin/main...feat/tailwind4` in this worktree (PR #74, Tailwind CSS 3 -> 4 and tailwind-merge 2 -> 3, frontend sequence phase 3 of 3). Brief: `git show origin/main:audit/2026-09-25/waves/briefs/TAILWIND-4-L1-brief.md` (binding; §4.2 spec rules, §4.3 push order, §4.4 lockfile, §4.5 cn drift, §4.6 tokens). Plan: docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md.

Context: Asclexis is a local-first health app; src/frontend is React 18 + Vite 7. Signed owner rows: docs/capstone-report/owner-decisions-2026-09-27.md :64, :69-:73 and TW4-O1..O4. Only class names, CSS, build config, one e2e spec, one ci.yml upload step, cn.test.ts and doc lines may change.

Focus (owner-directed): "no visible regression; every renamed class keeps its v3 meaning; cn() still merges; no transitive major outside MAJORS-TIED".
1. Every class rename in the .tsx diff keeps its Tailwind 3 rendered value (shadow/rounded/blur/ring/outline scale shifts, bg-gradient-to -> bg-linear-to, arbitrary-value forms like border-black/[0.04] -> border-black/4, important modifier position, variant order).
2. src/frontend/src/styles/globals.css: @theme values equal the deleted tailwind.config.js values; the @layer base compat rules (border #e5e7eb, placeholder #9ca3af, button cursor) reproduce v3 preflight; :root vars do not collide with @theme names in a way that changes a value; @utility conversions keep behaviour; @apply inside base layer; ring default width/colour in the *:focus-visible rule.
3. tailwind-merge 3 through src/frontend/src/utils/cn.ts and cva variants (Button.tsx, Badge.tsx): any merge that now drops or keeps a class differently.
4. Lockfile src/frontend/package-lock.json vs origin/main: any added package or major bump not pulled in by tailwindcss / @tailwindcss/* / tailwind-merge (jiti 1->2 is owner-tied).
5. e2e/tailwind4-styles.spec.ts: each assert targets an element with no explicit class for the asserted property; no page.route; no classes that exist only in the spec; ci.yml upload step path and if: always().
6. Content detection: v4 automatic source detection vs the deleted v3 `content` list — any class now generated that was not before (or vice versa) that would change rendering.

Verify each claim against the code before reporting it.

Output: VERDICT: approve | needs-attention, then one line per finding: [BLOCKER|MAJOR|MINOR] path:line — defect. Evidence: file:line. — fix. End with MODEL / EFFORT as the runtime reports it.
