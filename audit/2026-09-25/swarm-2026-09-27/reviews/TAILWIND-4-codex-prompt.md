Read-only adversarial plan review. Do not edit files or git state; run no tests, no npm.

PLAN UNDER REVIEW: audit/2026-09-25/waves/briefs/TAILWIND-4-L1-brief.md (an L1 dispatch brief) together with the plan it amends, docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md. Tree: branch docs/tailwind-4-brief = origin/main eb7de28 + the brief (uncommitted). ROUND 1.

Context: Asclexis is a local-first health app; the frontend is React 18 + Vite 7 + Tailwind 3.4 in src/frontend, served by the Vite dev server on the patient's machine. This phase upgrades Tailwind 3 -> 4 and tailwind-merge 2 -> 3 in one PR. Signed owner rows are in docs/capstone-report/owner-decisions-2026-09-27.md lines 64 and 69-73 (FE-SEQ, DEV-PS1-FIRST, TW4-BROWSERS, MAJORS-TIED, TW4-VISUAL). Background: audit/2026-09-25/waves/scaffold/TAILWIND-4.md and REVIEWS-2026-10-07.md section 1.

Focus:
1. Can every computed-style assert in brief section 4.2 actually fail? Check the target values against Tailwind 3.4 output and the repo's CSS (src/frontend/src/styles/globals.css, tailwind.config.js, index.html, components/ui/*). Flag any assert whose target has an explicit class that masks the default, or whose expected value is wrong for Tailwind 3.
2. Is the commit sequence in section 4.3 (spec on v3 green, tool output red, fix green) sound in CI? Check .github/workflows/ci.yml triggers, the e2e job, retries in src/frontend/playwright.config.ts, and whether CI would actually start the app at commit 2.
3. Tailwind 4 migration gaps the plan and brief miss: theme-variable name collisions in globals.css :root, @apply in globals.css, @layer components / utilities conversion, the config's fontSize / borderRadius / boxShadow / keyframes, automatic content detection vs the v3 `content` list, the `dark` colour namespace vs the `dark:` variant, default ring / shadow / blur renames not covered by the grep loop.
4. tailwind-merge 3 vs 2 drift through src/frontend/src/utils/cn.ts and cva variants; is the section 4.5 check sufficient?
5. Lockfile: the section 4.4 script (correct over nested node_modules keys? scoped names? peer/optional?), the MAJORS-TIED classification, the jiti stop, the Linux native-binary list.
6. Scope vs signed rows: is every file in section 4.1 covered by a signed row; does anything the rows require (e.g. TW4-BROWSERS docs, TW4-VISUAL CI artifacts, "seeded data") fall outside the file list or contradict the plan's "frontend only" constraint?
7. Every file:line cited in the brief is correct at this tree.

Verify each claim against the code before reporting it.

Output: VERDICT APPROVE | REVISE, then one line per finding: [BLOCKER|MAJOR|MINOR] path:line — defect. Evidence: file:line. — fix. End with MODEL / EFFORT as the runtime reports it.
