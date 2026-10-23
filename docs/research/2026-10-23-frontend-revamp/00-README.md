# Frontend revamp research package (2026-10-23)

**Last Updated:** 2026-10-23
**Owner:** repository owner
**Refresh Trigger:** an owner answer to a gate or open question in the plan's §11; a merged `UI-*` row that measures a number quoted here differently; a new major version of `motion`, `cmdk`, `thinking-orbs` or the Radix primitives.

> **Owner answer UI-DEPS (prompt 45): "Keep framer-motion 10".** Both proposals and `research-motion.md` describe a move to `motion` 14; the plan stays on framer-motion 10.18 with the same `LazyMotion` + `m` pattern. The copies here are left as written.
>
> **Point-in-time research (2026-10-23).** Planning and documentation only. No product code changed. Both designers worked on scratch copies of `src/frontend` at `main` @ `7749744`; the repository was not edited by them. The merged plan is [docs/plans/2026-10-23-frontend-revamp-plan.md](../../plans/2026-10-23-frontend-revamp-plan.md); the owner's answers are rows UI-DIRECTION, UI-SAAS-MEANING, UI-SCOPE-1031, UI-DARK-MODE and UI-SAFETY-TOGGLE in [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md).

## The question

The owner asked for a complete, ambitious update of the frontend, "engaging, modern, active like how SaaS has smooth UI/UX experiences", researched against current component, motion and scroll libraries and the Awwwards, Impeccable and Emil Kowalski design skills, with two Opus designers working independently and compared ([owner-direction.md](owner-direction.md)). The constraints that do not move: local-first (no runtime CDN, remote fonts or telemetry), WCAG 2.2 AA, reduced motion, no medical-advice framing, disclaimers and citations always visible, no ask-first file without the owner's yes.

## Index

| File | What it is |
|---|---|
| [owner-direction.md](owner-direction.md) | the owner's message and the three pasted guideline documents, verbatim |
| [framing.md](framing.md) | how the repo's docs frame the product ("Clinical Calm", local-first, capstone), with file:line quotes; why "SaaS" needed an owner decision |
| [ui-review.md](ui-review.md) | review of the current UI at `7749744`: screenshots at 1440 and 390, axe on 29 states, CLS, the 450 ms blank route gap, the placebo Safety Mode toggle, the ten highest-leverage problems |
| [COMPONENT_AUDIT.md](COMPONENT_AUDIT.md) | inventory of all 87 components with pattern class and upgrade candidate (Phase 0 of the owner's Component Upgrade Playbook) |
| [research-components.md](research-components.md) | component sources: Morphin, Bencho, libraries.dev, Radix, shadcn, react-aria, Ark, others, with licences and peers |
| [research-motion.md](research-motion.md) | Motion (framer-motion successor), CSS/WAAPI, springs, reduced motion, bundle |
| [research-scroll-3d.md](research-scroll-3d.md) | Lenis, GSAP ScrollTrigger, scroll-driven CSS, three.js / R3F, Spline, VGPU |
| [research-skills.md](research-skills.md) | the Impeccable, Emil Kowalski and Awwwards skills: repos, licences, install risks (runtime binary download, telemetry) |
| [proposal-A.md](proposal-A.md) | Designer A, "Ink & Paper", with prototype [`proto-A.patch`](proto-A.patch) |
| [proposal-B.md](proposal-B.md) | Designer B, "Quiet Instrument", with prototype [`proto-B.patch`](proto-B.patch) |
| [comparison.md](comparison.md) | A vs B: agreements, each disagreement with the side taken and why, and the six defects found in the prototypes |
| `shots/` | eight screenshots, before and after (listed below) |

## Method and provenance

1. **Before the designers started,** the current UI was captured (Playwright 1.58, Chromium 1200, axe-core 4.10 with WCAG 2.0/2.1/2.2 A+AA, a `layout-shift` observer) against a throwaway backend with seeded synthetic data, and the UI review, the component audit and the framing note were written (the files do not record which agent wrote them). L0 verified the stack facts on npm (motion 14.6.0 MIT react `^18 || ^19`; react-aria-components 1.22.1; @ark-ui/react 5.39.3; border-beam 1.4.1 and thinking-orbs 0.3.2 MIT react `>=18`; lenis 1.3.27; @react-three/fiber 9.8.2 needs react `>=19 <19.4`; react latest 19.3.1).
2. **Research agents** wrote the four research notes from primary sources (npm registry, official sites, GitHub); each note marks what it could not verify.
3. **Two Opus 5.5 designers** each wrote a proposal and built a prototype on a scratch copy of `src/frontend`, independently: A on vite port 5181 with fixtures, B on 5182 with a mocked API. Neither read the other's work.
4. **The owner answered prompt 44** (four questions, L0 AskUserQuestion, 2026-10-23) after both proposals existed.
5. **The Opus 5.5 planner** (this package's author) read every input and the screenshots, merged the proposals into one plan, re-read the npm versions, licences and React peers of every planned dependency (`npm view`, 2026-10-23), read the `border-beam` and `thinking-orbs` READMEs and type definitions, and re-ran proposal B's cmdk probe against proposal A's prototype (vite on 127.0.0.1:5191 with the API proxy pointed at a dead port; result in [comparison DF-5](comparison.md#3-defects-found-in-the-prototypes-become-acceptance-checks)).

**The patches.** `proto-A.patch` (37 files) and `proto-B.patch` (12 files) are `git diff`s of each prototype's `src/frontend` against `src/frontend` at `7749744`, source files only: no `node_modules`, no `dist`, no measurement directories, no logs and no `package-lock.json` (each prototype's `package.json` diff names the added packages; run `npm install` after applying). Line endings were normalised to LF. Both apply cleanly to `origin/main` @ `15fe095` (`git apply --check`, run by the planner). They are prototypes: fixtures stand in for the API, B's lives under `src/proto/`, and neither is a PR. `proto-B.patch` was regenerated after the prototype's hard-coded profile name was replaced by "Alex Rivera" / "AR" (owner UI-FIXTURE-NAME).

**Copied files.** The ten markdown files above are copies of the scratch originals, unchanged except for a one-paragraph note under each title, the path rewrites that note describes, and in `proposal-B.md` the prototype profile name replaced by the fixture name "Alex Rivera" (owner UI-FIXTURE-NAME, prompt 45). Nothing from the scratch `skills-download/` directory (third-party skill text) is in this folder.

**Screenshots.**

| File | Source | Shows |
|---|---|---|
| `shots/before-trends-1440.png` | UI review `20-data-trends-1440.png` | today's Trends: placebo toggle, smoothed line, dashed range line, "CBC 0" tab showing Glucose |
| `shots/before-trends-390.png` | UI review `70-phone-viewport-trends-390.png` | today's phone view: two thirds sidebar, horizontal scroll |
| `shots/A-results-light-390.png` | proposal A | A's Results at 390; the chart starts below the fold (DF-4) |
| `shots/A-source-sheet-light-1440.png` | proposal A | Source Trace; the CSV header is clipped (DF-2) |
| `shots/A-mobile-more-sheet-light-390.png` | proposal A | the More sheet with a toast on top of it (DF-3) |
| `shots/B-results-1440-dark.png` | proposal B | B's Results in dark; page text shows through the Safety Rail (DF-1) |
| `shots/B-results-1440-light-peek-open.png` | proposal B | Provenance Peek popover open |
| `shots/B-results-390-light.png` | proposal B | B's phone layout with the Safety Rail above the tab bar |

All eight are under 300 KB as captured (largest 170 KB), so none was recompressed. The four prototype screenshots `A-results-light-390.png`, `A-source-sheet-light-1440.png`, `A-mobile-more-sheet-light-390.png` and `B-results-1440-dark.png` were **re-captured on 2026-10-23** by the planner from the same prototypes (vite on 127.0.0.1:5191 and :5192, Playwright 1.58, Chromium 1200) with the fixture profile name "Alex Rivera" instead of the owner's name (owner UI-FIXTURE-NAME); nothing was cropped or covered, and each was checked by viewing it. They still show DF-1 to DF-4. `B-results-1440-light-peek-open.png` and `B-results-390-light.png` show no profile name and are unchanged.

## What was not verified

- **Real devices.** Frame rate, 120 Hz behaviour and INP were measured only in headless Chromium on a desktop (A unthrottled; B on a dev build, CPU ×1 and ×4). The plan's G3 asks each row for a production build under CPU ×4.
- **Browsers other than Chromium.** Firefox and Safari were not run, including `clip-path` on SVG groups in Safari.
- **Assistive technology.** No screen reader (NVDA, VoiceOver), 200 % zoom or Windows High Contrast pass.
- **Real data paths.** Both prototypes used fixtures; Source Trace's PDF bounding-box path, the real backend and the unmigrated pages in dark were not exercised.
- **The prototypes' test suites.** A ran vitest on its copy (273 of 275; both failures intended contract changes); B did not run vitest. The planner ran neither.
- **Library sizes.** A's main-chunk figure (160.4 kB gz) is a Vite production build; most per-package sizes are esbuild measurements and differ from Vite's by a few kB. `thinking-orbs` was measured by B but rendered by neither prototype; `border-beam` was measured and read, never rendered.
- **Third-party sites.** Morphin and Bencho pages were not opened by the designers (reference only, licences unknown); their code was not copied.
- **The `review-animations` skill** could not be invoked by a model (`disable-model-invocation`); both designers self-reviewed motion against its standards instead.
- **The owner's three guideline documents** are pasted social-media and essay text; their claims about third-party libraries were checked only where the research notes cite a primary source.
