# Proposal A vs proposal B: what the merged plan takes from each

**Last Updated:** 2026-10-23
**Owner:** repository owner
**Refresh Trigger:** an owner answer that overrides a choice below; a merged `UI-*` row that measures something different from the number quoted here.

Two Opus 5.5 designers worked independently on 2026-10-23, from the same inputs and without seeing each other's work: [proposal A "Ink & Paper"](proposal-A.md) and [proposal B "Quiet Instrument"](proposal-B.md). Both built a runnable prototype ([`proto-A.patch`](proto-A.patch), [`proto-B.patch`](proto-B.patch)). This file records where they agree, which side the merged plan takes where they differ and why, and the defects found in the prototypes. The plan itself is [2026-10-23-frontend-revamp-plan.md](../../plans/2026-10-23-frontend-revamp-plan.md).

Owner answers that override both proposals (prompt 44, 2026-10-23, verbatim in the plan §1): **"Craft + bold showcase"**, **"Full plan, no freeze"**, **"Follow OS setting"**, **"Make it real"**. Both proposals were written before those answers: both assumed craft only, both removed the Safety Mode toggle, and A put dark mode behind a Preview setting. The plan follows the owner where the owner answered.

**Owner answer UI-DEPS (prompt 45, 2026-10-23): "Keep framer-motion 10"** ("No major bump: build the motion system on framer-motion 10 (it also has LazyMotion and reduced-motion support); still add the other listed packages."). Both proposals moved to `motion` 14 (which depends on `framer-motion` 14); the plan does not. It keeps the same `LazyMotion` + `m` pattern on framer-motion 10.18. The proposals below are left as the designers wrote them. **Owner answer UI-FIXTURE-NAME (prompt 45): "Replace with fixture"**: the prototype profile name is now "Alex Rivera" in `proto-B.patch`, `proposal-B.md` and the screenshots.

## 1. Agreements (adopted as written)

| Topic | Both proposals | Evidence |
|---|---|---|
| React | stay on React 18, bump to 18.3.1; React 19 later as its own row | A §7, B §7; `npm view react@18` lists 18.3.1 as the last 18.x (L0 planner, 2026-10-23) |
| Motion library | `framer-motion` 10.18 → `motion` 14.6.0 (`motion/react`, `LazyMotion` + `m`, `MotionConfig reducedMotion="user"`); CSS for everything predetermined | A §7 (measured 9.4 kB gz sync + 18.3 kB async features), B §7 **Overridden by the owner (UI-DEPS): the plan stays on framer-motion 10.18 with the same `LazyMotion` + `m` + `MotionConfig` pattern.** |
| Overlays | Radix Dialog / Popover / Tabs / Switch; one overlay path with Escape, focus trap, focus return | A §6a, B §6a |
| Toasts | `sonner` 2.0.8 | A §7, B §7 |
| Command palette | `cmdk` 1.1.1, lazy on first Ctrl/⌘ K, no open/close animation | A §4.4, B §4.4 |
| Chart | custom SVG **Range Ribbon** replaces Recharts (reference range as a band, straight segments, true time axis, D4 hollow dashed unverified points, table fallback, one value-blind first reveal) | A §5 #2, B §5 #1 |
| Rejected | Lenis, three.js / R3F, GSAP, Spline, Aceternity, Canvas UI, `vaul`, a second primitive system (react-aria, Ark) | A §7, B §7 |
| IA | 9 destinations in 4 groups (Records, Understand, Care, Share); Trends + Interpret merge into **Results**; Explain → **Ask**; Alerts fold into Medications; prefix-matched active state; one h1; skip link | A §4.1, B §4.1 |
| Phone | bottom tab bar + More sheet below the desktop breakpoint; safe-area insets; native scroll | A §4.3, B §4.3 |
| Route motion | delete `AnimatePresence mode="wait"` (the ~450 ms blank gap); enter-only route motion | A §1, B §1 |
| Contrast | remap tokens so every pair passes AA; a vitest that parses the CSS and fails below 4.5:1 / 3:1 | A §3.2, B §3.1 |
| Data never animates | no count-up numbers; disclaimers, citations and range status never animate and are never hover-only | A §3.5, B §0 |
| Settings | split into sections; diagnostics hidden behind "Show advanced/technical" | A §4.2, B §4.2 |
| Honesty fixes | truthful model chip; dead "Last 12 Months"/"Filters"/"Full Preview" wired or deleted; CBC tab mismatch fixed; fake `setTimeout(500)` progress removed | A §6, B §6 |

## 2. Disagreements: the side the plan takes

| # | Topic | A | B | Plan takes | One-line reason |
|---|---|---|---|---|---|
| 1 | Concept | "Ink & Paper": unverified values in pencil, verified in ink | "Quiet Instrument" | **A** | It promotes an existing owner decision (D4's hollow dashed marker) into the visual language of verification, so the concept says something true about the data. |
| 2 | Provenance for a value | **Source Trace** side/bottom sheet with the source row, page and a verify action | **Provenance Peek** popover from a citation chip | **A for values; B's popover for inline citation chips** | A value needs the row, the page and the verify action, which do not fit a popover at 390 px; a chip in running text still opens a popover that links on to the sheet. |
| 3 | Token names | remap the existing names (`ink-tertiary`, `status-*`) so current utilities inherit the fix | new names (`fg`, `fg-2`, `raised`) | **A** | One CSS row fixes the 314 contrast nodes on every page at once without editing components, which reduces, without removing, the half-migrated look the owner accepted with "Full plan, no freeze". |
| 4 | Body size | 16 px plus an optional "Comfort text" setting | 17 px base | **B** | The audience is older patients (`docs/02_frontend_accessibility_plan.md:6`), and a base size needs no extra setting to build. |
| 5 | Route entrance | 180 ms fade from opacity 0 | M7: from opacity .35, 6 px rise, never invisible | **B** | A's own samples hit opacity 0.00 at 390 (a blank frame); B's never dropped below .35. |
| 6 | Motion governance | three zones (Chrome / Data / Safety) | the **Motion Gradient** (T0 Data … T3 Moments) | **B, extended with a Showcase tier** | The gradient is a checklist a reviewer can apply per element; the owner's "bold showcase" needs an explicit tier for non-clinical surfaces, and A's zones map onto it. |
| 7 | Safety copy in the chrome | a top-bar "Educational use · not medical advice" note | a persistent **Safety Rail** on every page, outside the route animation | **B** | It puts the disclaimer on the five pages that have none today and on phones, where A's note is only a chip. |
| 8 | Safety Mode toggle | remove, replace with a static note | remove | **Neither: owner chose "Make it real"** | The toggle stays, relabelled honestly, until the SAFETY-MODE-REAL research gives the owner concrete behaviours. |
| 9 | cmdk accessibility | wrapped `Command` in a Radix Dialog with an sr-only title | measured 2 critical axe failures (`aria-valid-attr-value`), proposed a test-gated patch or an own listbox | **B** | L0 planner re-ran B's probe on A's prototype: A's wrapper still fails (details in §3, DF-5). |
| 10 | `border-beam` | rejected (measured: only 4 fixed palettes) | adopt once, on the extraction card | **The effect, as a CSS reimplementation in token colours** | Owner chose "bold showcase" (border-beam allowed there); the package's `colorVariant` is one of 8 fixed palettes (`colorful`, `mono`, `ocean`, `sunset`, `forest`, `candy`, `ice`, `gold`: `dist/index.d.ts:32`; its README lists only the first four, which is what A counted), none bound to our tokens, with a hue shift by default, so a ~40-line CSS conic-gradient border costs 0 kB JS and stays on tokens. |
| 11 | `thinking-orbs` | rejected ("AI mystique") | adopt on the Ask pending state | **Adopt on showcase surfaces only (import/processing, About)** | The owner limited richer motion to non-clinical surfaces; Ask answers are clinical content, so Ask keeps a plain status line. |
| 12 | Bundle | measured **160.4 kB gz** main **with `motion` 14** after `LazyMotion strict` + route splitting; CI budget ≤ 165 | prototype 209.4 (both motion libraries eager), target ≤ 170, cap 185 | **A's budget, plus B's Results-route total ≤ 205** | A's number is a measured production build of the target state on `motion` 14; on framer-motion 10 (owner UI-DEPS) the plan treats about 160-161 kB as an estimate until UI-ROUTES measures it; B's route total is the one budget A did not set. |
| 13 | Dark mode | behind Settings › Appearance "Preview" until a GA row | theme toggle in the top bar | **Owner: follow the OS, once every page is migrated; light until then** | Owner answer UI-DARK-MODE; the flip row is gated on a test that finds no unmigrated colour. |
| 14 | Landing | **Overview** with a first-run checklist | optional Home, "first thing I would cut" | **A** | First-run onboarding and empty states are owner-named showcase surfaces; Overview is that surface. |
| 15 | Pinboards | under Care | under Records | **B** | Pinboards collect records; they are not care actions. |
| 16 | Names | Review, Tasks | Review values, Follow-ups | **B (open to the owner)** | They say what you do there; names live in one file (`navConfig.ts`), so the owner can change them cheaply (open question in the plan). |
| 17 | Phone tabs | Overview, Results, Documents, Ask, More | Records, Results, Ask, Care, More | **A** | Each tab is a destination, one tap away; group tabs would add a second step. |
| 18 | Tablet (768–1023) | phone shell below 1024 | 72 px icon rail with Radix Tooltips | **A** | One breakpoint means one fewer layout to test, and it drops `@radix-ui/react-tooltip` (20 kB, hover-first). |
| 19 | Unlock | new `/unlock` route (owner gate) | new `/unlock` route (owner gate) | **Neither: the existing SESSION-REENTRY row** | The owner already answered SESSION-REENTRY (a); its Task 1 puts the unlock card on `/setup`. The plan restyles it and adds A's "Lift" moment, no duplicate row. |
| 20 | Verify moment | "Ink": the dashed ring closes and fills, 360 ms, no bounce | check-stroke draw plus the app's only bounce | **A** | The owner did not choose engagement mechanics; a bounce on a lab-value row sits too close to clinical data. |
| 21 | Delete confirm | typed phrase in a dialog | hold-to-confirm, 2 s | **A** | Hold and slide gestures fail people with tremor; both designers rejected slide-to-confirm for that reason. |
| 22 | Brand mark | pencil-to-ink mark | trace mark | **A (open to the owner)** | It follows the concept; the owner may keep the heart (open question). |
| 23 | Medication badges | only when streaks are opted in | off by default behind Preferences | **Keep as today, static (open to the owner)** | Not answered in prompt 44; the owner did not choose engagement, so the `animate-ping` celebration goes and the rest waits for an answer. |
| 24 | Fonts | — | fallback metric overrides + Latin preload (font-swap CLS 0.011) | **B** | Removes the last measured layout shift at no cost. |

## 3. Defects found in the prototypes (become acceptance checks)

Found by L0 in the screenshots, except DF-5 (measured by B, re-verified by the L0 planner on A's prototype) and DF-6 (A's own samples). Each check names the plan row that owns it. The A and B screenshots in this folder were re-captured on 2026-10-23 from the same prototypes with the fixture profile name "Alex Rivera" (owner UI-FIXTURE-NAME); they show the same defects.

| Id | Prototype | What is wrong | Evidence | Acceptance check (plan row) |
|---|---|---|---|---|
| DF-1 | B, 1440 dark | Page text shows through behind the fixed Safety Rail: "…anel — Valley Clinic Lab · p.1" is readable beside the disclaimer | [`shots/B-results-1440-dark.png`](shots/B-results-1440-dark.png) (bottom right) | The rail's computed background alpha is 1 with no `backdrop-filter`; after scrolling `main` to the bottom, `elementFromPoint` at 5 points across the rail returns the rail or a descendant, in light and dark, at 1440 and 390 (UI-SHELL, HC-UISH-005) |
| DF-2 | A | The Source Trace CSV header is clipped at the sheet edge ("collected_dat") | [`shots/A-source-sheet-light-1440.png`](shots/A-source-sheet-light-1440.png) | Every source line in the sheet wraps: `scrollWidth <= clientWidth` for each line element at 1440 and 390 (UI-PROVENANCE, HC-UIPV-004) |
| DF-3 | A, 390 | A toast sits on top of the open More sheet | [`shots/A-mobile-more-sheet-light-390.png`](shots/A-mobile-more-sheet-light-390.png) | Opening any Sheet or Dialog dismisses visible toasts, and the toast layer is below the modal layer: no `[data-sonner-toast]` box intersects the overlay content (UI-PRIM-FEEDBACK HC-UIFB-004; UI-SHELL HC-UISH-007) |
| DF-4 | A, 390 | The Results chart starts below the fold (header copy and status rows push it down) | [`shots/A-results-light-390.png`](shots/A-results-light-390.png) | At 390×844 on first paint, at least 200 px of the Range Ribbon plot is inside the viewport above the tab bar and the Safety Rail (UI-PG-RESULTS, HC-UIRES-004) |
| DF-5 | A and B | cmdk 1.1.1: after typing a filter, `aria-activedescendant` points at an id that no longer exists until an arrow key is pressed; axe `aria-valid-attr-value` critical ×2 | B: `proto-B/probe-cmdk.mjs` (L0 scratch). **A re-run by the L0 planner** (vite on 5191, Playwright 1.58, Chromium 1200, axe-core 4.10.3): open `[]`; after typing `chol`: `INPUT#radix-:r1b: -> radix-:r1h: exists=false`, axe `["aria-valid-attr-value:criticalx2"]`; after ArrowDown: `exists=true`, axe `[]`. A's Radix Dialog wrapper does not fix it | After typing, every `aria-activedescendant` in the palette resolves to an existing element, and axe on the open, filtered palette reports 0 serious/critical; a test-gated patch, else our own listbox on Radix Dialog (UI-PALETTE, HC-UIPAL-002/003) |
| DF-6 | A, 390 | The route fade samples opacity 0.00 (a blank frame) | A §10 table: "1.00 0.00 0.82 0.98 1.00" | Route container opacity sampled every 40 ms after a nav click never drops below 0.3 (UI-SHELL, HC-UISH-003) |

Seen by the L0 planner in the same screenshots, not a defect but carried into the plan: at 390, A shows no disclaimer in the first viewport except an "Educational" chip ([`shots/A-results-light-390.png`](shots/A-results-light-390.png)); B's rail covers it ([`shots/B-results-390-light.png`](shots/B-results-390-light.png)). B's analyte chips scroll sideways at 390 (intentional); the plan requires that scroller to be a labelled, focusable region and the page itself to have no horizontal scroll.

## 4. Before and after

| Before (`main` @ `7749744`) | After (prototypes) |
|---|---|
| [`shots/before-trends-1440.png`](shots/before-trends-1440.png): the placebo "Safety Mode ON" toggle, a smoothed line, the range as a dashed line, "CBC 0" tab showing Glucose | [`shots/B-results-1440-light-peek-open.png`](shots/B-results-1440-light-peek-open.png), [`shots/B-results-1440-dark.png`](shots/B-results-1440-dark.png), [`shots/A-source-sheet-light-1440.png`](shots/A-source-sheet-light-1440.png) |
| [`shots/before-trends-390.png`](shots/before-trends-390.png): two thirds of the phone is sidebar; the page scrolls sideways | [`shots/A-results-light-390.png`](shots/A-results-light-390.png), [`shots/B-results-390-light.png`](shots/B-results-390-light.png), [`shots/A-mobile-more-sheet-light-390.png`](shots/A-mobile-more-sheet-light-390.png) |
