# Frontend revamp 2026-10-23 — merged plan: Ink & Paper on a Motion Gradient

**Last Updated:** 2026-10-23 (review round 1 of #311: framer-motion 10 kept (owner UI-DEPS), fixture name (owner UI-FIXTURE-NAME), stillness probe G10, UI-AUTH-SCREENS relabelled, test-file ownership, 11 minors)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md); the owner direction and prompt 44's four answers are recorded there as rows UI-DIRECTION, UI-SAAS-MEANING, UI-SCOPE-1031, UI-DARK-MODE and UI-SAFETY-TOGGLE, and prompt 45's two answers as rows UI-DEPS and UI-FIXTURE-NAME (same PR).
**Base measured:** `origin/main` @ `15fe095` (2026-10-23, after #310). `src/frontend` is unchanged since `7749744`, the commit both designers and the UI review read (`git diff --stat 7749744 origin/main -- src/frontend` is empty).
**Refresh Trigger:** an owner answer to a gate in [§11](#11-owner-gates-and-open-questions); a merge of any `UI-*` row (its measured numbers replace the ones quoted here); a merge of SESSION-REENTRY, FE-IMPORT-ERROR, IMPORT-SCANNED-PAGE, FE-VERIFY-NUMERIC, FE-EXPLAIN-ERR, BADGE-TICK, GAUGE-ZERO-WIDTH, AXE-E2E or E2E-UIFULL-CI; any edit to `src/frontend/package.json` outside these rows.

Queue rows: [queue.md, "Planned 2026-10-23, frontend revamp"](2026-10-15-build-program/queue.md#planned-2026-10-23-frontend-revamp). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `fe/` = `src/frontend/src/`, `e2e/` = `src/frontend/e2e/`, `be/` = `src/backend/`.

**Sources.** The research package [docs/research/2026-10-23-frontend-revamp/](../research/2026-10-23-frontend-revamp/00-README.md): the owner's message and pasted guidelines, the framing note, the UI review and component audit of `main` @ `7749744`, four library research notes, and two independent designer proposals with prototypes ([proposal A](../research/2026-10-23-frontend-revamp/proposal-A.md), [proposal B](../research/2026-10-23-frontend-revamp/proposal-B.md), [comparison](../research/2026-10-23-frontend-revamp/comparison.md), [`proto-A.patch`](../research/2026-10-23-frontend-revamp/proto-A.patch), [`proto-B.patch`](../research/2026-10-23-frontend-revamp/proto-B.patch)). The owner's answers to prompt 44 (L0 AskUserQuestion; L0 evidence comment 6374428883 on PR #311) and prompt 45 (L0 evidence comment 6374428087 on PR #311).

**MVP priority** (showcase 2026-10-31, same scale as the [MVP plan](2026-10-22-mvp-rows-plan.md)): **P0** = makes a safety, privacy or lab-value claim false on screen, or leaves a phone user unable to use the app; **P1** = visible on the demo path; **P2** = after the demo is fine. Owner answer UI-SCOPE-1031 ("Full plan, no freeze") means every row is queued now and starts when its own dependencies merge; P0/P1/P2 only orders the picks.

**Ask-first files (CLAUDE.md §1).** No `UI-*` row edits `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, `core/auth.py` or any encryption file. No `UI-*` row edits any backend file. SAFETY-MODE-REAL is research only; whichever behaviour the owner picks gets its own build row with its own ask-first gate. The frontend screens that drive sign-in, recovery, backup and profile deletion are not ask-first files. **Planner reading of CLAUDE.md §1** ("ALWAYS ask before touching … anything auth/encryption"), not an owner instruction: their new layout, their entrance motion and the Lift moment wait on a gate (UI-AUTH-SCREENS, [§11](#11-owner-gates-and-open-questions)). Tokens, primitives and the `m.*` import swap change these screens whatever the answer (UI-TOKENS, UI-PRIM-CONTROLS, UI-MOTION), and their raw colours are swapped for tokens in every outcome, so the gate never blocks dark mode. Logic and requests stay unchanged.

---

## 1. Goal and the owner's answers

**Goal.** Bring the whole frontend to SaaS-grade craft (instant feedback, no blank frames, no dead clicks, a designed phone layout, a keyboard palette, accessible overlays, AA contrast in light and dark), and give the four non-clinical surfaces the owner named a bolder, choreographed showcase. Throughout, every lab value, range, disclaimer and citation stays still and traceable to its source. Ship it as small, file-disjoint rows ordered to reduce how half-migrated `main` looks between merges; the owner accepted that risk ("Higher risk of a half-migrated look").

**Owner direction** (2026-10-23, verbatim in [owner-direction.md](../research/2026-10-23-frontend-revamp/owner-direction.md) and owner-decisions row UI-DIRECTION): the frontend "should be engaging, modern, active like how SaaS has smooth UI/UX experiences with animations & more enganging UI … Be ambitious".

**Prompt 44 (L0 AskUserQuestion, 2026-10-23).** Each answer is the option label the owner chose, followed by that option's description as presented, both verbatim:

| Id | Answer | Option description (verbatim) |
|---|---|---|
| UI-SAAS-MEANING | **"Craft + bold showcase"** | "Craft everywhere, plus richer motion on NON-clinical surfaces only: first-run onboarding, document import/processing, empty states, an About/landing page for the demo (choreographed entrances, border-beam, thinking-orbs). Lab values and safety copy stay still." |
| UI-SCOPE-1031 | **"Full plan, no freeze"** | "Start all waves now; whatever is merged by 10-31 is in the demo. Higher risk of a half-migrated look." |
| UI-DARK-MODE | **"Follow OS setting"** | "Ship dark mode on, following the operating system, once every page is migrated." |
| UI-SAFETY-TOGGLE | **"Make it real"** | "Keep a toggle and wire it to real behaviour. Needs backend changes near ask-first safety modules and a separate plan." |

**Prompt 45 (L0 AskUserQuestion, 2026-10-23; L0 evidence comment 6374428087 on PR #311),** same format:

| Id | Answer | Option description (verbatim) |
|---|---|---|
| UI-DEPS | **"Keep framer-motion 10"** | "No major bump: build the motion system on framer-motion 10 (it also has LazyMotion and reduced-motion support); still add the other listed packages." |
| UI-FIXTURE-NAME | **"Replace with fixture"** | "Replace it with a fixture name (e.g. "Alex Rivera") in the patch, proposal text and screenshots (re-captured or cropped)." |

UI-DEPS means: `framer-motion` stays at ^10.18, `motion` 14 is not adopted, and the other packages of [§5](#5-dependencies-and-bundle-budgets) are approved as listed; any other major comes back to the owner. The designers' proposals in the research package still describe `motion` 14 as they wrote it.

**L0 readings (L0's words, not the owner's), used by this plan:**
- UI-SAAS-MEANING: "Lab values and safety copy stay still" covers values, ranges, units, dates, disclaimers, citations and verification text. The one exception is one explanatory first reveal per analyte per session (the Range Ribbon draw), which is value-blind.
- UI-SCOPE-1031: the token remap and the shell land first and each page migrates completely inside its own row. Between merges `main` still mixes migrated and unmigrated pages, and an unmigrated page's layout shows the new global tokens and primitives: this is the accepted half-migrated risk the option text names, reduced by the order, not removed.
- UI-SAAS-MEANING, stillness: a T0 element never sits inside an animated wrapper (M6, M7, S1). On a route whose first paint has T0 content the route change is instant (M0), lists of T0 items render without M6, and showcase entrances wrap only non-T0 content. Gate G10's stillness probe enforces it.
- UI-SAAS-MEANING, onboarding: the create-profile form counts as first-run onboarding (a showcase surface); the recovery-code step does not, and stays still.
- UI-DARK-MODE: until UI-DARK-FLIP merges, the product renders light whatever the OS says. There is no Preview toggle. The flip is gated on a test that finds no unmigrated colour.
- UI-SAFETY-TOGGLE: the toggle is not designed yet. SAFETY-MODE-REAL researches concrete behaviours and turns them into an owner question; the build waits on that answer plus an ask-first yes. Until then the toggle stays, relabelled so it does not imply that it does anything ([§3.6](#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real)).

**What this supersedes.** The "Clinical Calm, restraint with purpose" motion brief (`docs/02_frontend_accessibility_plan.md`, "Aesthetic Direction" and "Motion & Micro-interactions") is superseded to the extent of UI-SAAS-MEANING: craft everywhere, richer motion on the four non-clinical surfaces. Its intent still governs clinical surfaces. Its "Smooth number transitions for trend changes" is rejected, because a count-up displays values the patient never had (both designers).

---

## 2. Design rules

### 2.1 The Motion Gradient (review checklist)

How much a thing may move goes down as its clinical weight goes up. Proposal B's tiers, extended with a Showcase tier for UI-SAAS-MEANING; proposal A's zones (Chrome / Data / Safety) map onto them. Every PR that adds motion lists each animated element with its tier, and the reviewer checks it against this table.

| Tier | Covers | Allowed | Never |
|---|---|---|---|
| **T0 Data and safety** | lab values, ranges, units, dates, verification text, disclaimers, citations, the Safety Rail, consent and break-glass copy, error text, adherence figures (the ring renders final) | nothing after first paint, including no ancestor that fades or moves (G10). Exception: the Range Ribbon's one value-blind draw per analyte per session (M10, on the plot, not on its text). The Ink marker glyph is T3; the value beside it is T0 | count-ups, colour pulses, emphasis motion on out-of-range values, hover-only disclosure |
| **T1 Structure** | pages, cards, lists | enter only: M6, M7 (from opacity .35, never invisible), and only on containers with no T0 descendant | exit animations on routes, `AnimatePresence mode="wait"` |
| **T2 Chrome and controls** | buttons, nav, sheets, popovers, toasts, tabs | M1-M5, M8, M9, M11-M13; press feedback within one frame | animation on keyboard-initiated or 100+/day actions (palette, keyboard chart moves, focus rings) |
| **T3 Moments** | Ink (verify), Source Trace highlight, Lift (unlock) | the recipes named in [§4.1](#41-signature-moments) only, triggered by the user's own action | bounce on anything near a value; celebration |
| **S Showcase** | first-run onboarding (Overview checklist; the create-profile form, an L0 reading; not the recovery-code step), document import/processing, empty states, the About page | S1-S4 ([§2.6](#26-motion-tokens-and-recipes)) | any T0 element inside a showcase surface (a value, a disclaimer) moves; sound; confetti; parallax; scroll-jacking; 3D |

### 2.2 Colour tokens and contrast (proposal A)

Raw tokens live on `:root` and are redefined under `:root[data-theme='dark']`; `@theme` only points at them, so **existing class names keep working** (`text-ink-secondary`, `bg-status-attention-subtle`, …) and the 106 `ink-tertiary` uses are fixed without editing a component. `status-success`, `status-danger` and `muted-foreground` (undefined today: 10, 9 and 2 uses, counted with `grep` on `15fe095`) become aliases of verified, outside and ink-2. Dark tokens are defined from UI-TOKENS on but only used after UI-DARK-FLIP.

| Role | Token | Light | Dark |
|---|---|---|---|
| Canvas | `--paper` (`bg-surface`) | `#F6F5F1` | `#141412` |
| Card / elevated | `--surface-1` | `#FFFFFF` | `#1C1C19` |
| Muted / sunken | `--surface-2` / `--surface-3` | `#EFEDE7` / `#E7E4DC` | `#262521` / `#302F2A` |
| Text primary / secondary / tertiary | `--ink-1/2/3` | `#1C1B19` / `#4F4C46` / `#68645D` | `#EEECE6` / `#C2BEB5` / `#A29E95` |
| Hairline (decorative) / control border | `--line` / `--line-strong` | `#E2DFD7` / `#8A857B` | `#2F2E2A` / `#77736B` |
| Accent / hover / text-on-subtle / subtle | `--accent` … | `#1D6B5E` / `#185A4F` / `#165247` / `#E2EFEB` | `#6FC6B3` / `#86D1C0` / `#8AD3C2` / `#1D332E` |
| Text on accent | `--on-accent` | `#FFFFFF` | `#0B1D19` |
| Caution text / bg | `--caution` | `#7F5410` / `#FAF0DF` | `#E7B867` / `#2E2615` |
| Outside range text / bg | `--outside` | `#9C3F2E` / `#FAE9E4` | `#F09C88` / `#33201B` |
| Verified text / bg | `--verified` | `#2C6542` / `#E4F1E8` | `#8FCB9F` / `#1C2B21` |
| Info text / bg | `--info` | `#365A80` / `#E6EEF6` | `#9DBEE3` / `#1C2633` |
| Reference band / pencil | `--band` / `--pencil` | `#DCEBE5` / `#68645D` | `#1F3530` / `#A29E95` |
| Layers | `--z-toast` / `--z-modal` | 40 / 50 | same |

Computed WCAG ratios (proposal A §3.2, sRGB relative luminance; UI-TOKENS re-computes every pair in a test):

| Pair | Light | Dark | Needs |
|---|---|---|---|
| ink-1 on paper / surface-1 / surface-2 | 15.78 / 17.21 / 14.70 | 15.61 / 14.46 / 12.98 | 4.5 |
| ink-2 on paper / surface-1 / surface-2 | 7.84 / 8.56 / 7.31 | 9.95 / 9.21 / 8.27 | 4.5 |
| ink-3 on paper / surface-1 / surface-2 / surface-3 (was 2.69) | 5.39 / 5.88 / 5.03 / 4.63 | 6.90 / 6.39 / 5.74 / 5.02 | 4.5 |
| ink-3 on band (chart labels) | 4.78 | 4.88 | 4.5 |
| accent on paper / surface-1 / surface-2 | 5.80 / 6.33 / 5.41 | 9.14 / 8.46 / — | 4.5 |
| accent-ink on accent-subtle (active nav; was 4.36) | 7.62 | 7.78 | 4.5 |
| on-accent on accent / accent-hover (primary button) | 6.33 / 8.03 | 8.64 / 9.88 | 4.5 |
| caution on its bg / surface-1 (was 2.08) | 5.85 / 6.61 | 8.15 / 9.31 | 4.5 |
| outside on its bg / surface-1 / paper (was 2.95) | 5.64 / 6.64 / 6.08 | 7.20 / 7.98 / 8.62 | 4.5 |
| verified on its bg / surface-1 / paper (was 2.60) | 5.92 / 6.89 / 6.32 | 7.91 / 9.12 / — | 4.5 |
| info on its bg / surface-1 (was 3.17) | 6.12 / 7.16 | 7.94 / 8.87 | 4.5 |
| pencil on surface-1 / band | 5.88 / 4.78 | 6.39 / 4.88 | 3 (non-text) |
| line-strong on surface-1 / paper | 3.67 / 3.36 | 3.62 / 3.91 | 3 (1.4.11) |
| focus outline on paper | 5.80 | 10.70 | 3 |
| white on outside (danger button, light) | 6.64 | — | 4.5 |
| on-accent on outside (danger button, dark) | — | 8.15 | 4.5 |

`--line` is decorative and exempt. The danger button uses `--on-status`, never `text-white` (white fails on dark clay). Status is never colour alone: an icon or shape plus words ("Above the reference range (per report)"); "abnormal" and "normal" are not status words.

### 2.3 Type (proposal B's scale)

Self-hosted families only (`@fontsource`, already local). Fraunces never below 22 px. Source Sans 3 carries body and UI with `tabular-nums` wherever numbers are compared. JetBrains Mono only for recovery codes, file hashes and raw source excerpts. Sentence case; raw identifiers (`lab_csv`, `hdl_cholesterol`) never reach the UI. Font-swap CLS is removed with fallback metric overrides (`size-adjust`, `ascent-override`) in `globals.css`.

| Token | Size / line height | Face and use |
|---|---|---|
| `numeral` | 56 / 1.0 | Fraunces 500, tabular lining, the hero value only |
| `h1` | 36 / 40 (28 / 34 on phones) | Fraunces 600, one per page |
| `h2` | 28 / 34 | Fraunces 600 |
| `h3` | 22 / 28 | Fraunces 600 |
| `lead` | 19 / 28 | Source Sans 3 |
| `body` | **17** / 26.4 (was 16) | Source Sans 3, measure ≤ 68ch |
| `ui` | 15 / 21.6 | Source Sans 3 500/600 |
| `cap` | 13 / 18.4 | floor size; `text-[9px]` / `text-[10px]` (19 lines on `15fe095`) banned |

### 2.4 Space, radii, elevation, texture

4 px base (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96); page gutter 16 / 24 / 40 px. Radii 6 (chips), 10 (controls, nav items), 14 (popovers), 16 (cards), 20 (dialogs, sheet tops, palette). Elevation is a border **or** a shadow, never both: E1 card = border, no hover lift unless the whole card is interactive; E2 overlay = `--shadow-2`; E3 modal = `--shadow-3` with a scrim and no viewport-wide blur. No noise, no decorative glass, no gradient text, and no `backdrop-blur`: the top bar and the Safety Rail are opaque (DF-1).

### 2.5 Information density rules

At most two chips per list row; status chips are words plus an icon; confidence is shown only below the threshold, in words ("Low read confidence · check this value"); every empty state has one real action.

### 2.6 Motion tokens and recipes

CSS custom properties in `globals.css`, mirrored in `fe/motion/tokens.ts`. One easing family for UI; `linear` only for progress loops.

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | enters, exits, press release |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | on-screen moves (indicator, reorder) |
| `--ease-drawer` | `cubic-bezier(0.32, 0.72, 0, 1)` | sheets |
| `--dur-press` / `--dur-hover` | 120 / 150 ms | press scale .97 / colour |
| `--dur-sm` | 180 ms | popover, tooltip, toast content, pointer cursor glide |
| `--dur-md` | 240 ms | route enter, nav indicator, list item |
| `--dur-lg` | 320 ms (exit 0.66×) | dialog, sheet |
| `--dur-ink` | 360 ms | Ink (verify) |
| `--dur-draw` | 640 ms | Range Ribbon first reveal only |
| `--dur-show` | 480 ms | Showcase entrances (S tier only) |
| springs (framer-motion 10) | `snappy {type: 'spring', duration: 0.22, bounce: 0}` (`duration` and `bounce` exist in framer-motion 10.18.0 `dist/index.d.ts`:454 and :473; `visualDuration` does not exist in 10.x) | sheet snap, drag release; no bounce anywhere else |
| stagger | 40 ms, cap 6, first view per session (T1); 60 ms, cap 8 (S tier) | lists |

| Code | Recipe | Reduced motion |
|---|---|---|
| M0 | none: instant | — |
| M1 | press: `scale(.97)` on `:active`, 120 ms | colour only |
| M2 | hover: colour/background 150 ms, behind `@media (hover:hover) and (pointer:fine)` | same |
| M3 | popover: opacity + `scale(.96→1)` from the Radix transform origin, 180 ms; exit 120 ms | opacity only |
| M4 | dialog: opacity + `scale(.97→1)`, 320 ms; scrim 200 ms; exit 200 ms | opacity 150 ms |
| M5 | sheet: `translateY(100%)→0` (phone) / `translateX` (desktop side), 320 ms drawer curve | opacity 150 ms |
| M6 | list enter: opacity .35→1 + 6 px rise, 240 ms, stagger 40 ms cap 6, first view per session; never on a list of T0 items | opacity 120 ms, no stagger |
| M7 | route enter: opacity .35→1 + 6 px rise, 240 ms, **no exit**, keyed by pathname; only on routes whose first paint has no T0 element, otherwise M0 | opacity .35→1, 120 ms |
| M8 | state morph: label crossfade 180 ms ("Copy" → "Copied") | opacity only |
| M9 | indicator: one element moved by a CSS transition, 240 ms (nav pill, tab underline); jumps for keyboard | opacity 120 ms |
| M10 | draw: `clip-path: inset(0 100% 0 0)→inset(0)` 640 ms, points .6→1 at 40 ms intervals; once per analyte per session; value-blind | none (final frame) |
| M11 | toast: sonner transitions, swipe to dismiss | sonner reduced (opacity) |
| M12 | progress: determinate `scaleX` 240 ms; indeterminate opacity breathing 1.6 s | breathing continues (loaders never freeze) |
| M13 | expand: `grid-template-rows 0fr→1fr` 240 ms + opacity | instant, opacity 120 ms |
| **S1** | choreographed entrance (wraps non-T0 groups only): groups rise 12 px + opacity 0→1, 480 ms ease-out, stagger 60 ms cap 8, first visit per session (sessionStorage, wrapped in try/catch) | opacity 150 ms, no stagger |
| **S2** | beam: a CSS conic-gradient stroke masked to the card border (`@property --beam-angle`), 2.4 s linear loop, colours from `--accent`, `--accent-ink`, `--band`; runs only while a real process runs (extraction), or as the single accent on the About page; fades out 240 ms when done | static 1 px `--accent` border plus the status text |
| **S3** | thinking orb: `thinking-orbs` `ThinkingOrb` (lazy), `theme="auto"` (follows `data-theme`), canvas `aria-hidden`, always beside a `role="status"` text such as "Reading page 2 of 3" | the library's static frame |
| **S4** | hero draw (About only): an SVG ribbon illustration over **labelled example data** ("Example data, not yours") drawn once by clip-path, 1.2 s | final frame |

Global rules: transform, opacity and clip-path only (plus M13's sanctioned `grid-template-rows`); `transition-all` banned; focus rings never transition; `MotionConfig reducedMotion="user"` (framer-motion 10.18.0 `dist/index.d.ts`:3583, prop :1658, values `"always" | "never" | "user"` :1632) plus per-recipe fallbacks replace the blanket `* { animation-duration: .01ms !important }` kill-switch (which also froze spinners); the repo's `useReducedMotion` hook reads `matchMedia` synchronously so the first render honours the preference (framer-motion's own `useReducedMotion`, :4636, returns `boolean | null`); nothing that plays during navigation uses framer-motion's `x`/`y`/`scale` shorthands (main-thread); no number ever tweens.

---

## 3. Information architecture and navigation

### 3.1 Destinations

9 destinations in 4 groups, plus Overview as the landing page and Settings in the profile menu. Old URLs redirect, so bookmarks and tests keep working.

| Group | Destination | Replaces | Route |
|---|---|---|---|
| — | **Overview** (new; first-run checklist, then "since you were last here") | landing on an empty Inbox | `/overview` (index) |
| Records | **Documents** | Inbox | `/inbox` |
| | **Review values** | Verify | `/verify` |
| | **Timeline** | Timeline | `/timeline` |
| | **Pinboards** | Pinboards | `/pinboards` |
| Understand | **Results** | Trends + Interpret (merged) | `/results` (`/trends`, `/interpret` redirect) |
| | **Ask** | Explain | `/explain` |
| Care | **Medications** (Reminders is a tab) | Meds + Alerts | `/medications`, `/medications?tab=reminders` (`/notifications` redirects) |
| | **Follow-ups** | Tasks | `/care-tasks` |
| Share | **Doctor summary** | Export | `/export` |
| Profile menu | Settings (sections), About, Lock now (SESSION-REENTRY Task 3, gated) | Settings nav item, the "user" icon | `/settings?section=…`, `/about` |

Rules: plain nouns, no "smart" names; prefix-matched active state (`/medications/:id` keeps its pill); the brand is a `<span>`, so each page has exactly one `h1`; a skip link is the first tab stop. Names live in one file (`fe/components/layout/navConfig.ts`); the owner may rename (open question UI-NAV-NAMES).

**Transition nav (L0 reading, so no destination disappears mid-migration):** from UI-SHELL until UI-PG-RESULTS, "Results" points at `/trends` and "Interpret" stays listed under Understand; until UI-MICRO, "Reminders" stays listed under Care and lands on the reminders view.

### 3.2 Shells

- **≥ 1024 px:** 264 px sidebar with group labels and a CSS-transitioned active indicator (M9); profile block in the sidebar footer ("Stored on this device"); a 64 px top bar with search (the palette trigger from UI-PALETTE on) and the relabelled safety toggle.
- **< 1024 px:** the sidebar is replaced, not shrunk. A 64 px top bar (brand mark, search, profile) and a 5-slot bottom tab bar: **Overview, Results, Documents, Ask, More** (Overview appears when UI-OVERVIEW merges; until then the first slot is Documents and Review values joins the bar). Tabs ≥ 56 px tall, `env(safe-area-inset-bottom)` respected. More opens a bottom sheet (M5) with every group as 52 px tiles. Main content gets bottom padding for the tab bar plus the Safety Rail. Native scroll only.

### 3.3 Command palette

Ctrl/⌘ K or `/`, or the top-bar search button. Groups: Results (jump to an analyte, with its latest value as static text), Go to, Actions (import a document, log a dose), Records (full-text through the existing `/search` service, debounced 150 ms; Enter on free text falls through to `/search?q=`). No open/close animation, no animated highlight. Lazy chunk ≤ 8 kB gz. DF-5 must pass ([§6](#6-standard-acceptance-gate-and-defect-checks)).

### 3.4 Settings

`/settings?section=` with Radix Tabs (a sheet on phones): **Profile & security** (recovery code, backup, delete profile; their restyle is UI-PG-SECURITY, gated), **Preferences** (time zone, streaks visibility, voice), **Assistant & privacy** (step-by-step agent, memory, external API with the break-glass warning unchanged, data donation with consent copy unchanged), **Advanced** (OCR/Poppler, hardware, model tiers, training-data export) collapsed behind "Show advanced settings", off by default, with honest tier copy. No appearance setting: the theme follows the OS (UI-DARK-MODE).

### 3.5 Session re-entry

Owned by the existing row **SESSION-REENTRY** (owner answer (a), [MVP plan](2026-10-22-mvp-rows-plan.md#session-reentry--after-60-minutes-or-a-restart-only-the-recovery-code-gets-a-patient-back-in)): Task 1 puts the unlock card on `/setup` (ready, P0); Task 2 is gated by SESSION-AUTH-DIFF. This plan adds no unlock row. It restyles the unlock card and adds the Lift moment in UI-PG-AUTH (gated by UI-AUTH-SCREENS), and proposes **Task 3** ("Lock now" in the profile menu, new gate SESSION-LOCK-NOW) as a delta to that row ([§8.2](#82-delta-to-session-reentry-task-3-lock-now)). The idle-lock warning toast both designers proposed needs `auto_lock_timeout_minutes`, which has no reader (bullet AUTO-LOCK-UNUSED, ask-first auth, not planned here).

### 3.6 The Safety Rail and the safety toggle (until SAFETY-MODE-REAL)

**Safety Rail** (proposal B): a one-line, never-animated strip in the shell, outside the route animation, on every authenticated page: "Educational only, not medical advice. Your records stay on this device." (phones: "Educational only, not medical advice."). Sticky at the bottom of the content column on desktop, above the tab bar on phones. Opaque background, no backdrop blur (DF-1). Contextual disclaimers on result, interpretation and answer cards stay.

**Safety toggle** (owner: "Make it real"; not designed yet). Until a SAFETY-MODE build row merges, the top-bar control keeps its place and is relabelled so it implies nothing:

- Visible label: **"Stricter safety mode"**, a switch rendered **disabled and off**, with the visible note **"Not available yet. The standard safety checks always run."** (on phones the note is in a popover opened from an info button beside the switch).
- Popover text (on click or Enter on the info button): "Asclexis checks every answer for medical advice and against your own records. These checks are always on and cannot be turned off. A stricter mode is being designed; this switch will turn it on when it is ready."
- Semantics: `role="switch"`, `aria-checked="false"`, `aria-disabled="true"`, `aria-describedby` pointing at the note. The words "Safety Mode", "ON" and "OFF" no longer appear; clicking changes no state anywhere.
- Rationale: "off" is true of the stricter mode, and the note says the standard checks are always on, so the switch neither claims a safety guard can be turned off (today's "Safety Mode OFF") nor claims a behaviour that does not exist. An alternative wording is put to the owner (open question SAFETY-LABEL-WORDING, non-blocking).

---

## 4. Signature moments and the showcase surfaces

### 4.1 Signature moments

| Moment | Trigger | Spec | Tier | Reduced motion |
|---|---|---|---|---|
| **Range Ribbon first reveal** | first view of an analyte in a session | band and grid static; line and points revealed left to right (M10, 640 ms), value-blind; then the chart is a slider: ← → Home End jump without animation, pointer cursor glides 180 ms | T0 exception | no reveal |
| **Ink** | the user verifies a value (Review values or Source Trace) | the dashed graphite ring closes and fills with ink, 360 ms ease-out, on the marker only; the value text never moves; every chart, row and chip for that value flips together; a toast confirms ("Glucose, Apr 10, 2026 is now marked as checked") with **no Undo**: the API has no unverify endpoint (`be/api/observations.py:384` is verify only; bullet VERIFY-UNDO) | T3 | instant swap, toast still shows |
| **Source Trace** | "Show source" on any value, or "Open source" in a citation popover | side sheet (desktop, M5 side) / bottom sheet (phone); the source row's highlight draws across the line (clip-path 420 ms, 160 ms delay, once); copy "This is what your report states." | T3 | highlight fades in 150 ms |
| **Lift** (in UI-PG-AUTH, gated) | successful unlock on the SESSION-REENTRY card | the unlock panel fades and lifts 8 px, 240 ms, onto the shell already painted with skeletons | T3 | opacity 150 ms |

Refused: confetti or celebration on verify or adherence (the `BadgeToast` `animate-ping` goes), count-up numbers, motion on out-of-range values, a bounce anywhere near a value, 3D, sound.

### 4.2 Showcase surfaces (UI-SAAS-MEANING)

| Surface | Row | What moves | What stays still |
|---|---|---|---|
| First-run onboarding: **Overview** checklist (Import → Review values → See results) | UI-OVERVIEW | S1 entrance of the checklist cards; the next step is marked in words ("Next step") with a static accent border (S2 marks a running process only, so it is not used here) | the counts and any value shown later ("3 values waiting for review" is T0 text) |
| First-run onboarding: the **create-profile form** (L0 reading) | UI-PG-AUTH (layout and motion gated by UI-AUTH-SCREENS) | S1 entrance of the form groups; no fake progress | the recovery-code step (no S1 at all), the code, the acknowledgement checkbox, every warning |
| **Document import/processing** | UI-PG-DOCUMENTS | S2 beam on the card of a document being extracted; S3 orb (20 px) beside the status line "Reading page 2 of 3"; the import → review handoff (new rows enter with M6) | extracted values, confidence words, error messages (FE-IMPORT-ERROR's alert), the scanned-page warning (IMPORT-SCANNED-PAGE) |
| **Empty states** (every page) | UI-SHOWCASE-KIT (`EmptyState`), used by each page row | S1 entrance of the illustration, sentence and one action | — |
| **About page** for the demo | UI-ABOUT | S1 sections; S4 hero ribbon over labelled example data; S2 on the single call to action; S3 (64 px) beside "How it reads a report" | the safety statement, the local-first statement, the "not medical advice" text |

Not showcase surfaces: Results, Review values, Ask, Medications, Doctor summary, Settings (they are clinical or safety-relevant). Ask's pending state is plain text "Reading your verified results…" (`role="status"`), not an orb.

---

## 5. Dependencies and bundle budgets

Versions, licences and React peers re-read with `npm view` by the L0 planner on 2026-10-23 unless marked; sizes are the designers' measurements unless marked. **Owner UI-DEPS (prompt 45): "Keep framer-motion 10".** Nothing below is a major bump: `framer-motion` stays on 10, React and the dropdown move within their major, and the rest are new packages the owner approved as listed. Any other major comes back to the owner.

| Package | Version | Licence | gzip | Decision |
|---|---|---|---|---|
| `framer-motion` (kept, owner UI-DEPS) | ^10.18.0 (as today) | MIT | 9.5 kB sync for `LazyMotion` + `m` + `MotionConfig` + `AnimatePresence` + `useReducedMotion`; 19.4 kB for `domAnimation` (async); 37.1 kB for the full `motion` component used today. Planner measurement, 2026-10-23: esbuild 0.27.2 `--minify`, React external, `gzip -9`, each entry bundled alone, so code shared between them is counted in both | keep; every `motion.*` moves to `m.*` under `LazyMotion` (UI-MOTION). `motion` 14 is **not** adopted: `motion@14.6.0` depends on `framer-motion@14.6.0`, a major the owner declined |
| `react`, `react-dom` | 18.2 → **18.3.1** (last 18.x; latest is 19.3.1) | MIT | — | bump only; React 19 later as its own row (both designers) |
| `@radix-ui/react-dialog` / `-popover` / `-tabs` / `-switch` / `-checkbox` / `-select` | 1.3.1 / 1.3.1 / 1.2.1 / 1.4.1 / 1.4.1 / 2.4.1 | MIT | combined +13.9 (B) to +21.4 kB (A) over today's dropdown; Select 32.5 alone, lazy pages only | adopt |
| `@radix-ui/react-dropdown-menu` | 2.0.6 → 2.2.1 | MIT | present | bump |
| `@radix-ui/react-tooltip` | 1.4.1 | MIT | 20.2 | **reject** (hover-first; no icon rail, comparison #18) |
| `sonner` | 2.0.8 | MIT | 9.4-9.6 | adopt |
| `cmdk` | 1.1.1 | MIT | 5.6 kB lazy chunk (A) | adopt, lazy, with the DF-5 fix |
| `thinking-orbs` | 0.3.2 | MIT, peer react `>=18`, no runtime deps, no network code (grep of `dist/` for `fetch`/URLs: 0) | 11.2 kB (B, esbuild), lazy | adopt on showcase surfaces only (S3) |
| `border-beam` | 1.4.1 | MIT | 12.5-12.8 | **effect adopted, package not**: `colorVariant` is one of 8 fixed palettes (`colorful`, `mono`, `ocean`, `sunset`, `forest`, `candy`, `ice`, `gold`; `dist/index.d.ts:32`; the README lists only the first four), none bound to our tokens, with a hue shift by default, and its rotate types need manual reduced-motion wiring. S2 is a ~40-line CSS reimplementation in token colours, 0 kB JS |
| `recharts` | 3.9.1 | MIT | 105.2 kB lazy chunk today | remove (UI-CHART-CLEANUP) |
| `@axe-core/playwright` | 4.14.0 | MPL-2.0, dev only | — | via AXE-E2E (owner TEST-DEV-DEPS (a)) |
| Rejected | `lenis` 1.3.27 (nested scrollers, zoom, magnifiers); GSAP (second engine); three / `@react-three/fiber` 9.8.2 (needs react `>=19 <19.4`; no clinical gain); `react-aria-components` 1.22.1, `@ark-ui/react` 5.39.3 (a second primitive system); `vaul` 1.1.2 (last publish 2024-12-14); Aceternity (licence); Spline (CDN runtime; self-host is Enterprise-only); Canvas UI (Commons Clause); Morphin (reference only, never copy Pro code); Bencho (licence unverified, reference only) | | | — |

**Bundle budgets** (today: main 180.0 kB gz, CSS 18.3 kB gz, Recharts chunk 105.2 kB gz, `build-output.txt`). Enforced by `scripts/check-bundle.mjs` from UI-BUDGET on; before it, each row reports main gz from `npm run build` and must not exceed 180.0.

| Budget | Limit (gz) | Basis |
|---|---|---|
| main JS chunk | **≤ 165 kB** | A measured 160.4 kB with **`motion` 14**, `LazyMotion strict` and lazy Inbox/Verify/Settings/Results. For framer-motion 10 this is an **estimate, not a measurement**: the sync LazyMotion set measures 9.5 kB on 10.18 against A's 9.4 kB on 14.6, so the planner expects about 160-161 kB; UI-ROUTES measures the real Vite build |
| any route chunk (excluding shared vendor) | ≤ 30 kB | A |
| Results route total (main + route + chart) | ≤ 205 kB | B; today 289.7 |
| palette chunk | ≤ 8 kB | A (measured 5.6) |
| `thinking-orbs` chunk | ≤ 15 kB, loaded only on Documents and About | B measured 11.2 |
| CSS | ≤ 25 kB | A (prototype 22.5) |
| total first-load JS | ≤ 200 kB | A |

---

## 6. Standard acceptance gate and defect checks

**Gate G** (every `UI-*` row, on every route it touches, with the commands and their output pasted in the PR):

| Id | Check | How (helpers from UI-GATES) |
|---|---|---|
| G1 | axe: 0 serious or critical, WCAG 2.0/2.1/2.2 A+AA, **light and dark** | `@axe-core/playwright`; dark is applied by the harness after load (`setTheme(page, 'dark')`), because the product stays light until UI-DARK-FLIP |
| G2 | CLS < 0.1 over load plus the row's interactions | `layout-shift` PerformanceObserver |
| G3 | INP proxy < 200 ms: max Event Timing duration over the row's interactions, CPU throttled ×4, production build (`vite preview`) | CDP `Emulation.setCPUThrottlingRate`, `PerformanceObserver({type:'event', durationThreshold:16})` |
| G4 | bundle budgets of [§5](#5-dependencies-and-bundle-budgets) | `npm run build:check` (from UI-BUDGET; before it, main gz ≤ 180.0 from the build output) |
| G5 | reduced-motion snapshot: with `reducedMotion: 'reduce'`, no element has a non-identity computed transform 50 ms after each interaction; screenshot per touched screen in the PR | `reducedMotionSnapshot()` |
| G6 | no horizontal scroll at 390×844 **and** 320×640 | `documentElement.scrollWidth <= innerWidth` |
| G7 | zero console errors; no request to a non-localhost origin (local-first) | `consoleAndNetworkGuard()` |
| G8 | `npx tsc --noEmit`, `npm run build`, `npx vitest run` (count and delta; from Windows or CI per RUNBOOK §6.5), the row's Playwright spec | — |
| G9 (from UI-SHELL on) | the Safety Rail is in the viewport at effective opacity 1 at first paint and after each interaction; contextual disclaimers and citations visible without hover | `safetyVisible()` |
| G10 | stillness: every `[data-t0]` element (values, ranges, units, dates, verification text, disclaimers, citations, the Safety Rail) keeps the same `getBoundingClientRect()` (±0.5 px) and an **effective opacity** of 1 (the product of its own and every ancestor's computed opacity) in samples every 16-40 ms for 800 ms after each navigation and interaction. T0 components set `data-t0` | `stillnessProbe()` |

Frontend e2e uses `page.route` mocks typed from `fe/services/types.ts` (`e2e/support/mockApi.ts`). Anything that asserts auth, session or status-code behaviour runs against the real backend through HTTP (`e2e/support/start-backend.mjs`), as CLAUDE.md §4 requires. Existing tests may have selectors or labels updated when markup changes; no assertion is removed or loosened (CLAUDE.md §3). Before claiming done, each row re-reads [recurring-failures.md](../agentic/recurring-failures.md); #1 (a test that could not fail) is why every new check below names its RED state, and #12 (a gate merged beside PRs built before it) is why L0 runs UI-BUDGET's check and UI-TOKENS' contrast test on `origin/main` before merging the next group.

**Defect checks** (found in the prototypes; details in [comparison §3](../research/2026-10-23-frontend-revamp/comparison.md#3-defects-found-in-the-prototypes-become-acceptance-checks)):

| Id | Check | Row |
|---|---|---|
| DF-1 | Safety Rail opaque: computed background alpha 1, no `backdrop-filter`; after scrolling `main` to the bottom, `elementFromPoint` at 5 points across the rail returns the rail or a descendant (light and dark, 1440 and 390) | UI-SHELL (HC-UISH-005) |
| DF-2 | Source Trace: every source line wraps (`scrollWidth <= clientWidth` per line element) at 1440 and 390 | UI-PROVENANCE (HC-UIPV-004) |
| DF-3 | opening a Sheet or Dialog leaves no `[data-sonner-toast]` intersecting the overlay content; the toast layer is below the modal layer | UI-PRIM-FEEDBACK (HC-UIFB-004), UI-SHELL (HC-UISH-007) |
| DF-4 | at 390×844, first paint, ≥ 200 px of the Range Ribbon plot is inside the viewport above the tab bar and the Safety Rail | UI-PG-RESULTS (HC-UIRES-004) |
| DF-5 | after typing in the palette, every `aria-activedescendant` resolves to an existing element; axe on the open, filtered palette 0 serious/critical | UI-PALETTE (HC-UIPAL-002, 003) |
| DF-6 | route container opacity sampled every 40 ms after a nav click never drops below 0.3 | UI-SHELL (HC-UISH-003) |

---

## 7. Rows

**Ordering rule (UI-SCOPE-1031, L0 reading).** Waves are dependency layers (queue rule 3): every row is queued now and starts when its own dependencies have merged. Foundation (tokens, motion, theme) and primitives restyle every page at once; the shell then wraps every page; each page row then migrates one page completely (layout, primitives, overlays, empty state, dark-safe colours, its own tests). The aim is that each page is either in its old layout with the new tokens and primitives, or fully migrated. This is not a guarantee: between merges `main` mixes migrated and unmigrated pages, and an unmigrated page shows the new primitives inside its old layout. That is the half-migrated risk the owner accepted with "Full plan, no freeze".

**File ownership rules.** `src/frontend/package.json` and `package-lock.json`: UI-MOTION, UI-BUDGET (scripts line), UI-CHART-CLEANUP only, never beside AXE-E2E or another `package.json` PR. `fe/App.tsx`: UI-ROUTES, UI-PG-RESULTS, UI-OVERVIEW, UI-ABOUT, in different waves. `fe/components/ui/index.ts`: UI-PRIM-CONTROLS only (other primitives are imported by path). `fe/components/layout/navConfig.ts`: UI-SHELL, UI-PG-RESULTS, UI-OVERVIEW, UI-MICRO, in different waves. `e2e/tailwind4-styles.spec.ts` (owner row TW4-VISUAL, `owner-decisions-2026-09-27.md:73`): UI-TOKENS (TW4-RECOVER border and placeholder, TW4-INBOX body background) and UI-SHELL (TW4-INBOX `aside h1` colour), each a declared contract change that keeps the computed-style check and updates only the value its row changes. `e2e/routing.spec.ts`: UI-SHELL (nav label), UI-PG-RESULTS (Trends heading), UI-OVERVIEW (E2E-ROUTE-001 redirect and heading), UI-MICRO (any remaining h1 renamed to its nav name), in different waves; UI-PG-DOCUMENTS keeps the h1 "Document Inbox" so it does not touch the spec. `fe/__tests__/Gamification.test.tsx`: UI-PG-MEDS, then UI-PG-SETTINGS (which therefore runs after it). `fe/__tests__/RecoveryCodeCard.test.tsx` (it tests the settings card): UI-PG-SECURITY. New tests go in new files named after the row, so two rows rarely share a test file.

### 7.1 Summary

| Wave | Id | Depends on | Owner gate | MVP | Est h |
|---|---|---|---|---|---|
| 0 | [UI-GATES](#ui-gates--the-acceptance-harness-every-ui-row-uses) | AXE-E2E | — | P1 | 3 |
| 0 | [SAFETY-MODE-REAL](#safety-mode-real--research-concrete-behaviours-for-the-safety-toggle-and-turn-them-into-an-owner-question) | — | UI-SAFETY-TOGGLE answered; produces SAFETY-MODE-BEHAVIOUR | P2 | 3 |
| 1 | [UI-TOKENS](#ui-tokens--remap-the-colour-type-and-motion-tokens-so-every-page-passes-aa) | UI-GATES | — | P1 | 3 |
| 1 | [UI-MOTION](#ui-motion--the-motion-system-on-framer-motion-10-lazymotion--m-react-1831-and-the-new-dependencies) | AXE-E2E; never beside the MVP rows on shared files | UI-DEPS answered "Keep framer-motion 10" | P1 | 4 |
| 1 | [UI-THEME](#ui-theme--theme-resolution-light-until-the-flip-and-the-missing-favicon) | — | UI-DARK-MODE answered | P1 | 1.5 |
| 2 | [UI-ROUTES](#ui-routes--lazy-routes-and-an-error-boundary-per-route) | UI-MOTION | — | P1 | 2 |
| 2 | [UI-PRIM-CONTROLS](#ui-prim-controls--button-iconbutton-fields-switch-tabs-card) | UI-TOKENS, UI-MOTION | — | P1 | 3 |
| 2 | [UI-PRIM-OVERLAYS](#ui-prim-overlays--dialog-alertdialog-sheet-popover) | UI-TOKENS, UI-MOTION | — | P1 | 3 |
| 2 | [UI-PRIM-FEEDBACK](#ui-prim-feedback--toasts-skeletons-pending-status-chip-progress-tag) | UI-TOKENS, UI-MOTION | — | P1 | 3 |
| 3 | [UI-SHELL](#ui-shell--responsive-shell-grouped-nav-tab-bar-safety-rail-honest-toggle) | UI-PRIM-*, UI-THEME, E2E-UIFULL-CI | UI-SAFETY-TOGGLE answered | **P0** | 5 |
| 3 | [UI-BUDGET](#ui-budget--a-ci-bundle-budget-that-can-fail) | UI-MOTION, UI-ROUTES; never beside CI-CACHE | owner merges (CI file) | P1 | 1.5 |
| 4 | [UI-PALETTE](#ui-palette--the-lazy-command-palette-with-the-df-5-fix) | UI-SHELL, UI-BUDGET | — | P1 | 3 |
| 4 | [UI-RIBBON](#ui-ribbon--the-range-ribbon-and-range-tick-components) | UI-TOKENS, UI-MOTION | — | P1 | 4 |
| 4 | [UI-PROVENANCE](#ui-provenance--source-trace-sheet-and-citation-popover) | UI-PRIM-OVERLAYS, UI-PRIM-FEEDBACK | — | P1 | 3 |
| 4 | [UI-SHOWCASE-KIT](#ui-showcase-kit--beam-orb-entrance-and-the-empty-state) | UI-MOTION, UI-PRIM-CONTROLS | UI-SAAS-MEANING answered | P1 | 3 |
| 4 | [SESSION-REENTRY Task 3](#82-delta-to-session-reentry-task-3-lock-now) | UI-SHELL, SESSION-REENTRY Task 1 | **SESSION-LOCK-NOW** (new) | P2 | 1 |
| 5 | [UI-PG-RESULTS](#ui-pg-results--results-merges-trends-and-interpret-around-the-range-ribbon) | wave 4 rows, UI-BUDGET; GAUGE-ZERO-WIDTH merged or closed | — | P1 | 5 |
| 5 | [UI-PG-DOCUMENTS](#ui-pg-documents--documents-page-and-the-import-and-processing-showcase) | UI-SHELL, UI-SHOWCASE-KIT, UI-PROVENANCE, FE-IMPORT-ERROR; never beside IMPORT-SCANNED-PAGE | — | P1 | 4 |
| 5 | [UI-PG-REVIEW](#ui-pg-review--review-values-with-ink) | UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT, FE-VERIFY-NUMERIC | — | P1 | 4 |
| 5 | [UI-PG-ASK](#ui-pg-ask--ask-the-chat-owns-its-scroll-citations-open-on-tap) | UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT, FE-EXPLAIN-ERR, BADGE-TICK | — | P1 | 4 |
| 5 | [UI-PG-MEDS](#ui-pg-meds--medications-reminders-tab-dose-sheet) | UI-SHELL, UI-SHOWCASE-KIT | MED-BADGES (open, non-blocking) | P2 | 4 |
| 5 | [UI-PG-CARE](#ui-pg-care--follow-ups) | UI-SHELL, UI-SHOWCASE-KIT | — | P2 | 2 |
| 5 | [UI-PG-RECORDS](#ui-pg-records--timeline-search-pinboards) | UI-SHELL, UI-SHOWCASE-KIT, UI-PALETTE | — | P2 | 3 |
| 5 | [UI-PG-EXPORT](#ui-pg-export--doctor-summary) | UI-SHELL, UI-SHOWCASE-KIT | — | P2 | 2.5 |
| 6 | [UI-PG-SETTINGS](#ui-pg-settings--settings-split-into-sections) | UI-PG-MEDS (`Gamification.test.tsx`), UI-SHELL, UI-SHOWCASE-KIT; never beside DON-COPY-V3 | — | P2 | 5 |
| 6 | [UI-CHART-CLEANUP](#ui-chart-cleanup--delete-the-recharts-chart-and-the-dependency) | UI-PG-RESULTS | — | P2 | 1.5 |
| 6 | [UI-OVERVIEW](#ui-overview--overview-landing-with-the-first-run-checklist) | UI-PG-RESULTS (App.tsx, `routing.spec.ts`), UI-PG-DOCUMENTS | — | P1 | 3 |
| 7 | [UI-PG-SECURITY](#ui-pg-security--profile--security-section-gated) | UI-PG-SETTINGS, MVP-REAUTH-401 | UI-AUTH-SCREENS (new; planner reading of CLAUDE.md §1) | P2 | 3 |
| 6 | [UI-PG-AUTH](#ui-pg-auth--setup-unlock-card-and-recovery-gated) | SESSION-REENTRY Task 1, UI-SHOWCASE-KIT, UI-SHELL | UI-AUTH-SCREENS (new; planner reading of CLAUDE.md §1) | P1 | 3 |
| 7 | [UI-ABOUT](#ui-about--the-about-page-for-the-demo) | UI-OVERVIEW (App.tsx), UI-RIBBON, UI-SHOWCASE-KIT | UI-ABOUT-PLACE (open, non-blocking) | P1 | 3 |
| 8 | [UI-MICRO](#ui-micro--press-target-and-copy-sweep) | every wave 5-7 row | — | P2 | 3 |
| 9 | [UI-DARK-FLIP](#ui-dark-flip--dark-mode-follows-the-os-once-no-unmigrated-colour-remains) | every `UI-*` row above (UI-PG-SECURITY / UI-PG-AUTH in any UI-AUTH-SCREENS outcome) | UI-DARK-MODE answered | P2 | 2 |

30 `UI-*` rows (94 h), SAFETY-MODE-REAL (3 h) and Task 3 on SESSION-REENTRY (1 h): 98 h in total. **Ready now:** SAFETY-MODE-REAL and UI-THEME (no dependencies). UI-GATES and UI-MOTION wait on AXE-E2E (ready, 1.5 h); everything else follows its dependencies.

### 7.2 Wave 0

#### UI-GATES — the acceptance harness every UI row uses

**Files:** `e2e/support/gates.ts` (new: `axeGate`, `setTheme`, `noHorizontalScroll`, `measureCls`, `maxEventDuration` (CDP CPU ×4), `reducedMotionSnapshot`, `routeOpacitySamples`, `consoleAndNetworkGuard`, `safetyVisible`, `stillnessProbe`), `e2e/support/mockApi.ts` (new; `page.route` fixtures typed from `fe/services/types.ts`, the seeded values of the UI review: glucose 92/104/118/101 against 70–99 mg/dL, LDL 142, HbA1c 6.1), `e2e/ui-gates.spec.ts` (new), `src/frontend/playwright.config.ts` (an `HC_E2E_BASE_URL` override for `vite preview` runs, nothing else), `e2e/README.md` (new).
**Depends on:** AXE-E2E merged (adds `@axe-core/playwright`). **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIG-001 | `noHorizontalScroll` fails on a fixture page (`page.setContent`) with a 600 px-wide block at 390, and passes on a fitting one (today's real overflow on `/trends` is each page row's G6, not a mark here) | GREEN (self-test that the helper can fail) |
| HC-UIG-002 | `axeGate` on `/inbox` reports `color-contrast`; `test.fail()` until UI-TOKENS | yes, by design |
| HC-UIG-003 | `routeOpacitySamples` after a nav click records a sample < 0.3 (today 0.00); `test.fail()` until UI-SHELL | yes, by design |
| HC-UIG-004 | `consoleAndNetworkGuard` fails a page that requests `https://example.com` (fixture via `page.setContent`) | GREEN (self-test) |
| HC-UIG-005 | `maxEventDuration` returns a finite number for a click on `/setup` under CPU ×4 | GREEN (self-test) |
| HC-UIG-006 | `stillnessProbe` fails on a fixture `[data-t0]` child of a container that fades from opacity .35, fails on one inside a parent that translates 6 px, and passes on one outside both (it reads ancestor opacity and the bounding rect, not the element's own style) | GREEN (self-test that the probe can fail) |

**Acceptance:** the six ids with output; the harness runs with the mock API and no backend; the README lists every helper and when to use the real backend. **Est:** 3 h. **MVP:** P1.

#### SAFETY-MODE-REAL — research concrete behaviours for the safety toggle and turn them into an owner question

**Kind:** DOCS (research and design; no slot; nothing under `src/`). **Files:** `docs/research/2026-10-23-safety-mode-real/00-README.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. **Depends on:** — . **Gate:** UI-SAFETY-TOGGLE answered "Make it real"; its output is the owner question **SAFETY-MODE-BEHAVIOUR**, and any build row then also needs an ask-first yes on the exact diff (**SAFETY-MODE-DIFF**) for each ask-first file it would touch.

**Task.** Read the safety pipeline as it is on `main` and write, for each candidate behaviour: what the patient sees with the toggle on and off; the files it changes, with `file:line`, and which of them are ask-first; where the setting is stored (per-profile setting with a profile migration, or a request flag) and whether it survives a lock; how it is tested through HTTP; its cost. A conservative constraint, L0 reading: **off must be exactly today's behaviour, and on may only be stricter**; no option may make any check weaker than today's default.

**Starting options** (the planner's list from a first read; the research re-reads every cite and may drop, merge or add options):

| Option | Patient sees when on | Files it would touch (first read) | Ask-first |
|---|---|---|---|
| Stricter checks | answers and interpretations need a higher verified share to be shown; more questions get the "I can't answer that from your records" abstention | `be/modules/faithfulness.py:55` (`min_overall_score 0.6`), `be/modules/verifier_agent.py:85` (`min_faithfulness_score 0.6`), `be/core/config.py:165`, `be/modules/rag.py:940`; the B-3 advice judge's threshold once #264 merges | **yes**: `faithfulness.py`, `verifier_agent.py` (and the judge if B-3 lands in an ask-first file) |
| Template-only explanations | no model-written free text; interpretations use the existing template path and chat answers show the cited fact list | `be/modules/interpret.py` (template path), `be/api/interpretations.py`, `be/api/assistant.py`, `be/modules/agent/nodes/draft.py` | none edited (`interpret_safety.py` keeps running on template text; confirm) |
| Always-on citations view | every answer and interpretation shows its quoted sources expanded inline instead of behind chips | frontend only (`fe/pages/ExplainAssistant.tsx`, `fe/components/lab-interpreter/*`) | none |
| Verified-only data | answers, interpretations and charts use only values the patient has checked; unchecked values are listed but never used | `be/modules/rag.py` retrieval, agent tools under `be/modules/agent/`, `fe/pages/ResultsPage.tsx` | none edited directly (`verifier_agent.py` read only; confirm) |

**Output format:** the owner question in the repo's gate format (question, options each with a one-line description of what changes for the patient, tradeoffs, an analogy), plus one table per option of files and ask-first files. **Acceptance:** `git diff --stat origin/main -- src/` is empty; every `file:line` re-read on the research commit; `python3 scripts/docs_lint.py` passes. **Est:** 3 h. **MVP:** P2 (the research can land before 2026-10-31; the build waits on SAFETY-MODE-BEHAVIOUR and SAFETY-MODE-DIFF).

### 7.3 Wave 1: foundation

#### UI-TOKENS — remap the colour, type and motion tokens so every page passes AA

**Files:** `fe/styles/globals.css` (the [§2.2](#22-colour-tokens-and-contrast-proposal-a) tokens, light and dark; aliases for `status-success`, `status-danger`, `muted-foreground`; type scale with body 17 px and the 13 px floor; motion tokens; `--z-toast`/`--z-modal`; font fallback metric overrides; focus ring with no transition; the blanket reduced-motion kill-switch replaced by `--motion-distance: 0` plus per-recipe rules, so loaders keep breathing; unused `glass-card`, `subtle-noise`, `stagger-animation`, `animation-delay-*` and the six dead `dark-*` tokens deleted), `fe/components/ui/Card.tsx` (`bg-white/80 backdrop-blur-xl` → `bg-surface-elevated`, nothing else), `fe/__tests__/ui-tokens.test.ts` (new), `e2e/ui-tokens.spec.ts` (new), `e2e/ui-gates.spec.ts` (remove the `test.fail()` mark on HC-UIG-002 only), `e2e/tailwind4-styles.spec.ts` (TW4-RECOVER border and placeholder values, TW4-INBOX body background: a declared contract change; the computed-style checks owner row TW4-VISUAL asked for stay, with the new token values).
**Depends on:** UI-GATES. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UITK-001 | the test parses `globals.css` and asserts every pair in the §2.2 table, light and dark: text ≥ 4.5:1, non-text ≥ 3:1 | yes (ink-tertiary 2.69) |
| HC-UITK-002 | every colour utility used in `fe/**/*.tsx` resolves to a defined token (`status-success`, `status-danger`, `muted-foreground` included) | yes (21 undefined uses) |
| HC-UITK-003 | `--text-xs` ≥ 13 px and the body size is 17 px | yes |
| HC-UITK-004 | e2e: axe `color-contrast` = 0 on `/setup`, `/inbox`, `/verify`, `/trends`, `/explain`, `/settings` (light) | yes (314 nodes on 29 states) |
| HC-UITK-005 | e2e: a focus ring is visible 16 ms after Tab on a Button (no fade-in) | yes (200 ms fade) |
| HC-UITK-006 | e2e: cold-load CLS on `/setup` ≤ 0.02 (font swap) | measure; 0.011 in B's prototype |

**Acceptance:** G (G1 light; dark contrast is covered by HC-UITK-001 until each page row runs G1 dark). L0 runs HC-UITK-001 on `origin/main` after merge (recurring-failures #12). **Est:** 3 h. **MVP:** P1.

#### UI-MOTION — the motion system on framer-motion 10 (LazyMotion + m), React 18.3.1 and the new dependencies

**Files:** `src/frontend/package.json`, `src/frontend/package-lock.json` (keep `framer-motion` at ^10.18.0, no major bump (owner UI-DEPS); add `@radix-ui/react-dialog@1.3.1`, `-popover@1.3.1`, `-tabs@1.2.1`, `-switch@1.4.1`, `-checkbox@1.4.1`, `-select@2.4.1`, `sonner@2.0.8`, `cmdk@1.1.1`, `thinking-orbs@0.3.2`; bump `@radix-ui/react-dropdown-menu` to 2.2.1, `react`/`react-dom` to 18.3.1, `@types/react`/`@types/react-dom` to 18.3.x (all within their major); exact versions, re-read with `npm view` at build time), `fe/motion/tokens.ts`, `fe/motion/MotionProvider.tsx`, `fe/motion/features.ts` (new; `LazyMotion strict` with async `domAnimation`, `MotionConfig reducedMotion="user"`; each API checked in framer-motion 10.18.0 `dist/index.d.ts`: `LazyMotion` :3673 with `strict` :3635 and an async `features` loader type :3585, `m` :3457, `domAnimation` :4383, `MotionConfig` :3583 with `reducedMotion` :1658, `useReducedMotion` :4636, `AnimatePresence` :3557), `fe/main.tsx` (wrap in `MotionProvider`), `fe/components/ui/Motion.tsx` (rewrite on `m`; delete `PageTransition` and `modalVariants`), `fe/hooks/useReducedMotion.ts` (synchronous initial read), and the mechanical swap (`motion.*` → `m.*`; imports stay `from 'framer-motion'`) in `fe/components/lab-interpreter/InterpretedResultCard.tsx`, `PanelInterpretationDashboard.tsx`, `fe/components/layout/AppLayout.tsx`, `Sidebar.tsx`, `fe/components/medication-coach/BadgeToast.tsx`, `DoseLoggingModal.tsx`, `MedicationCard.tsx`, `fe/pages/DocumentInbox.tsx`, `ExplainAssistant.tsx`, `ExportPage.tsx`, `LabInterpreter.tsx`, `MedicationDetail.tsx`, `ProfileSetup.tsx`, `SettingsPage.tsx`, `TrendsDashboard.tsx`, `VerificationWorkbench.tsx` (import and element-name lines only), and the test mocks in `fe/__tests__/setup.ts`, `Accessibility.test.tsx`, `ChartExport.test.tsx`, `ExplainAssistant.test.tsx`, `ExplainAssistantHistoryRestore.test.tsx`, `ExportPage.test.tsx`, `ExternalApiBreakGlassWarning.test.tsx`, `Gamification.test.tsx`, `InterpretedResultCard.test.tsx`, `LabInterpreter.test.tsx`, `PageImageOverlay.test.tsx` (mock target only), plus `fe/__tests__/ui-motion.test.tsx` (new), `e2e/ui-motion.spec.ts` (new).
**Depends on:** AXE-E2E merged (`package.json`). **Gate:** UI-DEPS answered "Keep framer-motion 10" (owner prompt 45). **Never beside** SESSION-REENTRY Task 1 (`ProfileSetup.tsx`), FE-IMPORT-ERROR and IMPORT-SCANNED-PAGE (`DocumentInbox.tsx`), FE-VERIFY-NUMERIC (`VerificationWorkbench.tsx`), FE-EXPLAIN-ERR and BADGE-TICK (`ExplainAssistant.tsx` and its test); L0 order: those MVP rows first (each ≤ 1.5 h), then this row merges `origin/main`.

| Id | Check | RED today? |
|---|---|---|
| HC-UIMO-001 | no `motion` component is imported from `framer-motion` and no `<motion.` element exists under `src/` outside `fe/motion/` (grep test); `package.json` still pins `framer-motion` 10.x and has no `motion` package | yes (17 source files use `motion.*`) |
| HC-UIMO-002 | with `matchMedia` mocked to `reduce`, the **first** render of a `FadeIn` has no transform | yes (the hook starts `false`) |
| HC-UIMO-003 | each route renders under `LazyMotion strict` without throwing (a `motion.*` left behind throws) | yes until the swap |
| HC-UIMO-004 | e2e: on `/setup` under reduced motion, no non-identity transform at 60 ms | yes (y-offset kept, `ProfileSetup.tsx:172-184`) |

**Acceptance:** G (G4: main ≤ 180.0 reported; ≤ 165 is expected with UI-ROUTES, see §5); the whole vitest suite green with no assertion removed; `npm ls react` shows 18.3.1 and `npm ls framer-motion` 10.x. **Est:** 4 h. **MVP:** P1.

#### UI-THEME — theme resolution, light until the flip, and the missing favicon

**Files:** `src/frontend/index.html` (a pre-paint script that sets `data-theme` from `fe/theme/theme.ts`'s rule, which returns light while `DARK_MODE_ENABLED` is false; theme-color metas from the tokens; favicon link), `fe/theme/theme.ts` (new: `resolveTheme(pref, osDark, enabled)`, `DARK_MODE_ENABLED = false`, storage access wrapped in try/catch), `src/frontend/public/favicon.svg` (new; `/favicon.svg` returns 404 today), `fe/__tests__/ui-theme.test.ts` (new), `e2e/ui-theme.spec.ts` (new).
**Depends on:** — . **Gate:** UI-DARK-MODE answered ("light until every page is migrated" is the L0 reading this row encodes).

| Id | Check | RED today? |
|---|---|---|
| HC-UITH-001 | `resolveTheme('system', true, false)` is `light` (light until the flip) | yes (no module) |
| HC-UITH-002 | `resolveTheme('system', true, true)` is `dark` and `('system', false, true)` is `light` (the flip contract) | yes |
| HC-UITH-003 | storage that throws falls back to the OS rule without throwing | yes |
| HC-UITH-004 | e2e: with OS dark emulated, `<html data-theme>` is `light` before first paint (read in an init script at `DOMContentLoaded`) | yes (attribute absent) |
| HC-UITH-005 | e2e: `GET /favicon.svg` is 200 | yes (404) |

**Acceptance:** G. **Est:** 1.5 h. **MVP:** P1.

### 7.4 Wave 2: routes and primitives

#### UI-ROUTES — lazy routes and an error boundary per route

**Files:** `fe/App.tsx` (lazy `DocumentInbox`, `VerificationWorkbench`, `SettingsPage`; an `ErrorBoundary` around each route element; content-shaped route fallbacks), `fe/components/ErrorBoundary.tsx` (new), `fe/__tests__/ui-routes.test.tsx` (new). **Depends on:** UI-MOTION. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIRT-001 | a route element that throws renders the boundary ("This page hit a problem" plus a working link to Documents), not a white screen | yes |
| HC-UIRT-002 | HC-ROUTE-001 and HC-ROUTE-002 still pass unchanged | GREEN (pin) |

**Acceptance:** G; the build output lists separate `DocumentInbox-*`, `VerificationWorkbench-*` and `SettingsPage-*` chunks and main ≤ 165 kB gz (A measured 160.4 kB with `motion` 14 plus this splitting; this row measures the framer-motion 10 build and records the number in the PR). **Est:** 2 h. **MVP:** P1.

#### UI-PRIM-CONTROLS — Button, IconButton, fields, Switch, Tabs, Card

**Files:** `fe/components/ui/Button.tsx` (`loading` prop replacing the 49 inline `<Loader2` JSX uses over time, `link` variant, danger on `--on-status`, `transition-property: transform, background-color, color`, M1 press, no hover lift), `ui/IconButton.tsx` (new; `aria-label` required by type; ≥ 44 px), `ui/Input.tsx` (`focus-visible`, `line-strong`, error clears when the `error` prop clears), `ui/Select.tsx`, `ui/Textarea.tsx`, `ui/Checkbox.tsx`, `ui/Switch.tsx`, `ui/Tabs.tsx` (new; Radix), `ui/Card.tsx` (variants `plain` / `interactive` / `inset`), `ui/index.ts` (exports; stops re-exporting Motion helpers so the barrel does not pull Motion into every importer), `fe/__tests__/ui-controls.test.tsx` (new). **Depends on:** UI-TOKENS, UI-MOTION. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIPC-001 | `Button loading` sets `aria-busy="true"` and `disabled` | yes |
| HC-UIPC-002 | `IconButton` without `aria-label` is a type error (`// @ts-expect-error` line) and renders ≥ 44×44 | yes |
| HC-UIPC-003 | `Switch`: `role="switch"`, Space toggles `aria-checked`, `disabled` blocks it | yes |
| HC-UIPC-004 | `Tabs`: arrow keys move focus (roving), each `tabpanel` is `aria-labelledby` its tab | yes |
| HC-UIPC-005 | `Input` with `error` then without: `aria-invalid` goes `true` → absent; the label is associated | yes |
| HC-UIPC-006 | no primitive's class list contains `transition-all` | yes (Button) |

**Acceptance:** G on `/setup` and `/settings` (the pages that use these most). **Est:** 3 h. **MVP:** P1.

#### UI-PRIM-OVERLAYS — Dialog, AlertDialog, Sheet, Popover

**Files:** `fe/components/ui/Dialog.tsx`, `ui/AlertDialog.tsx` (Dialog with `role="alertdialog"`), `ui/Sheet.tsx` (bottom on phones, side on desktop, M5), `ui/Popover.tsx` (M3; opens on click, Enter and Space, never on hover alone), all new; `fe/__tests__/ui-overlays.test.tsx` (new). **Depends on:** UI-TOKENS, UI-MOTION. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIOV-001 | Escape closes each overlay and focus returns to the trigger | yes (0 Escape handlers today) |
| HC-UIOV-002 | focus stays inside an open Dialog or Sheet over 25 Tab presses | yes |
| HC-UIOV-003 | `aria-modal="true"`; an overlay without a title fails the test (Radix's missing-title warning is turned into a test failure) | yes |
| HC-UIOV-004 | under reduced motion, content has opacity only, no transform | yes |
| HC-UIOV-005 | Popover opens on click and on Enter, not on hover | yes |
| HC-UIOV-006 | opening any Dialog, AlertDialog or Sheet dispatches the `asclexis:overlay-open` document event that UI-PRIM-FEEDBACK's toaster listens for (DF-3) | yes |

**Acceptance:** G (rendered on a test route in the e2e harness). **Est:** 3 h. **MVP:** P1.

#### UI-PRIM-FEEDBACK — toasts, skeletons, pending, status chip, progress, tag

**Files:** `fe/components/ui/toast.tsx` (new; sonner `AppToaster` themed by tokens on `--z-toast`, `notify()` helpers, optional action button), `ui/Skeleton.tsx` (`aria-busy` on the container; shapes match final layout; unused `CardSkeleton` deleted), `ui/Pending.tsx` (new; `role="status"` text with M12 breathing), `ui/StatusChip.tsx` (new; icon plus words for in range, above/below the report's range, not yet checked, checked by you, caution, info), `ui/Progress.tsx` (new; `role="progressbar"`, `scaleX`), `ui/Badge.tsx` (neutral Tag only), `fe/__tests__/ui-feedback.test.tsx` (new). **Depends on:** UI-TOKENS, UI-MOTION. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIFB-001 | `notify()` renders `role="status"`; its action button calls the handler | yes |
| HC-UIFB-002 | `StatusChip` renders an icon and text for every state; rendered text never contains "abnormal" or "normal" as a status word | yes |
| HC-UIFB-003 | `Pending` keeps animating opacity under reduced motion (loaders never freeze) | yes (kill-switch freezes) |
| HC-UIFB-004 | DF-3 contract: the toaster's z-index token is below the modal token, and the toaster subscribes to the `asclexis:overlay-open` document event (dispatched by UI-PRIM-OVERLAYS, HC-UIOV-006) and dismisses visible toasts | yes |
| HC-UIFB-005 | `Progress` animates `transform`, never `width` | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1. (The event name is fixed here and in UI-PRIM-OVERLAYS so the two rows stay file-disjoint; UI-SHELL proves the pair with HC-UISH-007.)

### 7.5 Wave 3: shell and budget

#### UI-SHELL — responsive shell, grouped nav, tab bar, Safety Rail, honest toggle

**Files:** `fe/components/layout/AppLayout.tsx` (grid shell; `AnimatePresence mode="wait"` removed; M7 keyed by pathname; skip link; mounts `AppToaster`; bottom padding for tab bar and rail), `Sidebar.tsx` (groups, prefix match, M9 CSS indicator replacing the `layoutId` spring, brand as `<span>`), `TopBar.tsx` (the existing search form restyled, `SafetyModeToggle`, profile menu on phones), `MobileTabBar.tsx`, `MoreSheet.tsx`, `SafetyRail.tsx`, `SafetyModeToggle.tsx`, `ProfileMenu.tsx`, `BrandMark.tsx`, `navConfig.ts` (all new), `layout/index.ts`; `fe/__tests__/ui-shell.test.tsx` (new), `e2e/ui-shell.spec.ts` (new), `e2e/routing.spec.ts` (nav label `Trends` → `Results` only), `e2e/ui-routes-verification.spec.ts` (nav labels only; file from E2E-UIFULL-CI), `e2e/ui-gates.spec.ts` (remove the `test.fail()` mark on HC-UIG-003 only), `e2e/tailwind4-styles.spec.ts` (TW4-INBOX: the `aside h1` colour check moves to the brand `<span>` with its new colour; a declared contract change under TW4-VISUAL).
**Depends on:** UI-PRIM-CONTROLS, UI-PRIM-OVERLAYS, UI-PRIM-FEEDBACK, UI-THEME merged; E2E-UIFULL-CI merged (its spec is edited). **Gate:** UI-SAFETY-TOGGLE answered; the toggle wording of [§3.6](#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real) ships now and SAFETY-LABEL-WORDING (open, non-blocking) may change it in a one-line follow-up.

| Id | Check | RED today? |
|---|---|---|
| HC-UISH-001 | vitest: `navConfig` has the [§3.1](#31-destinations) groups and transition entries; `/medications/abc` marks Medications active | yes |
| HC-UISH-002 | e2e: the first Tab focuses the skip link; exactly one `h1` on each of the 15 routes | yes (2 h1s, no skip link) |
| HC-UISH-003 | e2e (DF-6): route container opacity never < 0.3 after a nav click | yes (0.00 today) |
| HC-UISH-004 | e2e: at 390 and 320 no sidebar is rendered, `main` starts at x = 0 with the viewport's width, the tab bar shows 5 tabs each ≥ 44 px | yes (`pl-64`) |
| HC-UISH-005 | e2e (DF-1): the Safety Rail is opaque and on top (see §6), light and dark, 1440 and 390; it is in the viewport on every route | yes (no rail) |
| HC-UISH-006 | e2e: the texts "Safety Mode", "ON" and "OFF" are absent from the top bar; the switch is `aria-disabled="true"` with an accessible description containing "standard safety checks always run"; clicking it changes no DOM state outside its popover | yes (placebo toggle) |
| HC-UISH-007 | e2e (DF-3): with a toast visible, opening the More sheet leaves no toast intersecting the sheet | yes |
| HC-UISH-008 | e2e: More sheet: Escape closes, focus returns to the More tab, every destination is reachable from it | yes |

**Acceptance:** G on all 15 routes (old page content inside the new shell; G6 failures caused by a page's own content are listed in the PR and owned by that page's row). **Est:** 5 h. **MVP:** **P0** (a phone user cannot use the app today; the placebo toggle claims safety can be switched off).

#### UI-BUDGET — a CI bundle budget that can fail

**Files:** `src/frontend/scripts/check-bundle.mjs` (new; pure `checkBudgets(files, budgets)` plus a CLI reading `dist/assets`), `src/frontend/scripts/__fixtures__/bundle/*` (new, fake assets), `fe/__tests__/ui-budget.test.ts` (new), `src/frontend/package.json` (one script: `"build:check": "npm run build && node scripts/check-bundle.mjs"`), `.github/workflows/ci.yml` (one step in the frontend job). **Depends on:** UI-MOTION, UI-ROUTES; never beside CI-CACHE (`ci.yml`) or another `package.json` PR. **Gate:** owner merges (CI file).

| Id | Check | RED today? |
|---|---|---|
| HC-UIBG-001 | a fixture main chunk of 166 kB gz makes `checkBudgets` fail with the budget name | yes (no script) |
| HC-UIBG-002 | a fixture under every budget passes | yes |
| HC-UIBG-003 | `npm run build:check` on the branch passes (output pasted) | — |

**Acceptance:** the three ids; after merge, L0 runs `npm run build:check` on `origin/main` before merging further UI rows (recurring-failures #12). **Est:** 1.5 h. **MVP:** P1.

### 7.6 Wave 4: palette, chart, provenance, showcase kit

#### UI-PALETTE — the lazy command palette with the DF-5 fix

**Files:** `fe/components/layout/CommandPalette.tsx` (new, lazy), `fe/components/layout/paletteEvents.ts` (new), `TopBar.tsx` (search form → palette trigger button), `AppLayout.tsx` (lazy mount line only), `fe/__tests__/SearchPage.test.tsx` (FE-SRCH-UI-003 only: the header search now opens the palette, and Enter on free text still reaches `/search?q=`), `fe/__tests__/ui-palette.test.tsx` (new), `e2e/ui-palette.spec.ts` (new). **Depends on:** UI-SHELL, UI-BUDGET. **Gate:** none.
**DF-5 fix:** control cmdk's `value` and re-select the first visible item whenever the filter changes, so `aria-activedescendant` always names a rendered item. If HC-UIPAL-002 still fails with that, replace cmdk with our own listbox on the Radix Dialog primitive (about 120 lines; no new dependency) and remove `cmdk` from `package.json` in UI-CHART-CLEANUP. The L0 planner verified that proposal A's Radix Dialog wrapper alone does not fix it ([comparison DF-5](../research/2026-10-23-frontend-revamp/comparison.md#3-defects-found-in-the-prototypes-become-acceptance-checks)).

| Id | Check | RED today? |
|---|---|---|
| HC-UIPAL-001 | Ctrl+K and `/` open it; computed `transition-duration` and `animation-name` on the dialog are `0s` / `none` | yes |
| HC-UIPAL-002 | (DF-5) after typing `chol`, every `aria-activedescendant` resolves to an existing element | yes with cmdk 1.1.1 as shipped (measured) |
| HC-UIPAL-003 | (DF-5) axe on the open, filtered palette: 0 serious/critical | yes (`aria-valid-attr-value` critical ×2) |
| HC-UIPAL-004 | Escape closes and returns focus to the trigger; Enter on free text navigates to `/search?q=…` | yes |

**Acceptance:** G; palette chunk ≤ 8 kB gz. **Est:** 3 h. **MVP:** P1.

#### UI-RIBBON — the Range Ribbon and Range Tick components

**Files:** `fe/components/results/RangeRibbon.tsx`, `fe/components/results/RangeTick.tsx` (new), `fe/__tests__/ui-range-ribbon.test.tsx` (new). **Depends on:** UI-TOKENS, UI-MOTION. **Gate:** none.
**Spec:** input `TrendData` / `TrendPoint` (`fe/services/types.ts`); time-proportional x; the band from each report's `ref_low`/`ref_high`; straight segments (no `monotone`); pencil (hollow, dashed) or ink (filled) per `user_verified` (D4); an out-of-range point gets a static triangle plus the words "Above (or below) the reference range (per report)"; slider semantics with `aria-valuetext` ("Apr 10, 2026: 118 mg/dL, above the report's range, not yet checked"); ← → Home End move without animation, the pointer glides 180 ms; a table fallback with the same values; M10 reveal once per analyte per session; token colours only; the SVG serialises for the existing PNG/SVG export. RangeTick is the 64 px band-plus-marker glyph that replaces the gauge in `ReferenceRangeComparison`.

| Id | Check | RED today? |
|---|---|---|
| HC-UIRR-001 | x positions are proportional to time for unequal gaps | yes (no component) |
| HC-UIRR-002 | the band spans `ref_low`..`ref_high`; an out-of-range point has the triangle and the words | yes |
| HC-UIRR-003 | unverified points are hollow and dashed; verified points are filled | yes |
| HC-UIRR-004 | value-blind: an out-of-range and an in-range point get identical animation attributes | yes |
| HC-UIRR-005 | ArrowRight moves the selection and updates `aria-valuetext`; no transition runs on a keyboard move | yes |
| HC-UIRR-006 | the table fallback lists the same dates and values; no value is ever tweened (each rendered number equals a data value at every frame of the reveal) | yes |
| HC-UIRR-007 | no hex literal in either component's source; `XMLSerializer` output contains the computed token colours (export) | yes |
| HC-UIRR-008 | `RangeTick` with low = high = value, or all zero, renders no `NaN` (the GAUGE-ZERO-WIDTH cases HC-GZW-001/002) | yes |

**Acceptance:** G on a test route. **Est:** 4 h. **MVP:** P1.

#### UI-PROVENANCE — Source Trace sheet and citation popover

**Files:** `fe/components/results/SourceTrace.tsx` (new; the sheet: source file and row or page, the excerpt lines with the matching line highlighted, collected date, range, read confidence in words, "This is what your report states.", and for an unchecked value "It matches, mark as checked" using the existing `useVerifyObservation` (`fe/services/observations.ts:82`) plus "Correct it in Review values"), `fe/components/lab-interpreter/CitationTooltip.tsx` (rewritten on `Popover`, same props, so every caller upgrades at once: opens on tap, click and Enter, 44 px trigger, quote plus page plus "Open source"), `fe/components/PageImageOverlay.tsx` (image fades in on decode; the bbox highlight uses the trace mark), `fe/__tests__/ui-provenance.test.tsx` (new), `fe/__tests__/PageImageOverlay.test.tsx` (selectors only), `e2e/ui-provenance.spec.ts` (new). **Depends on:** UI-PRIM-OVERLAYS, UI-PRIM-FEEDBACK. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIPV-001 | the citation popover opens on click and Enter, not on hover alone; Escape closes and focus returns | yes (hover/focus tooltip) |
| HC-UIPV-002 | e2e in a `hasTouch` context: a tap opens it | yes |
| HC-UIPV-003 | Source Trace shows the source row highlighted, page, date and the "This is what your report states." line | yes |
| HC-UIPV-004 | (DF-2) every excerpt line wraps at 1440 and 390 | yes in proposal A's prototype |
| HC-UIPV-005 | "It matches, mark as checked" sends exactly one `POST /observations/{id}/verify` (mocked HTTP) and shows the confirmation toast; no Undo is offered (no unverify endpoint) | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1.

#### UI-SHOWCASE-KIT — beam, orb, entrance and the empty state

**Files:** `fe/components/ui/BeamBorder.tsx`, `ui/ThinkingOrb.tsx` (lazy wrapper over `thinking-orbs`, canvas `aria-hidden`, requires a `status` text prop), `ui/ShowcaseReveal.tsx` (S1), `ui/showcase.css` (S2 keyframes and `@property`), all new; `ui/EmptyState.tsx` (required `action`, optional static line illustration, S1 entrance); `fe/__tests__/ui-showcase.test.tsx` (new), `e2e/ui-showcase.spec.ts` (new). **Depends on:** UI-MOTION, UI-PRIM-CONTROLS. **Gate:** UI-SAAS-MEANING answered.

| Id | Check | RED today? |
|---|---|---|
| HC-UISK-001 | `BeamBorder` animates only while `active`; under reduced motion it renders a static 1 px accent border and no animation | yes |
| HC-UISK-002 | `BeamBorder`'s colours resolve to `--accent` / `--accent-ink` / `--band` (no hex, no package palette) | yes |
| HC-UISK-003 | `ThinkingOrb` cannot render without a `status` text (type error) and renders that text with `role="status"`; the canvas is `aria-hidden` | yes |
| HC-UISK-004 | `ThinkingOrb` loads `thinking-orbs` in its own lazy chunk (build output) | yes |
| HC-UISK-005 | `ShowcaseReveal` plays once per session (second mount: no transform), and with storage throwing still renders content | yes |
| HC-UISK-006 | `EmptyState` without `action` is a type error; it renders the action as a real button or link | yes (Trends' empty state has no action) |

**Acceptance:** G on a test route; G5 screenshot of each recipe. **Est:** 3 h. **MVP:** P1.

### 7.7 Wave 5: pages (each page migrates completely in its row)

Every page row: rebuild the page on the primitives; replace its hand-built overlays, `window.confirm` / `window.prompt` calls and native unstyled controls; give its empty state an action; remove any raw colour (`bg-white`, `text-white`, palette or hex utilities) so it is dark-safe; run G on its routes in light **and** dark. Its existing test file changes selectors only.

#### UI-PG-RESULTS — Results merges Trends and Interpret around the Range Ribbon

**Files:** `fe/pages/ResultsPage.tsx` (new), `fe/pages/TrendsDashboard.tsx` (delete), `fe/pages/LabInterpreter.tsx` (delete; folded in), `fe/pages/index.ts`, `fe/App.tsx` (`/results`; `/trends` and `/interpret` redirect), `fe/components/layout/navConfig.ts` (Results → `/results`; Interpret entry removed), `fe/components/lab-interpreter/InterpretedResultCard.tsx`, `PanelInterpretationDashboard.tsx`, `AdviceSection.tsx` ("Questions you could ask your clinician"), `DisclaimerBanner.tsx` (`role="note"`, never animated), `ReferenceRangeComparison.tsx` (renders `RangeTick`), `fe/__tests__/TrendsDashboard.test.tsx` and `LabInterpreter.test.tsx` (ported to `ResultsPage` as `fe/__tests__/ResultsPage.test.tsx`; every assertion kept), `InterpretedResultCard.test.tsx` (selectors only), `fe/__tests__/ui-results.test.tsx` (new), `e2e/ui-results.spec.ts` (new), `e2e/routing.spec.ts` (heading only).
**Depends on:** UI-RIBBON, UI-PROVENANCE, UI-SHOWCASE-KIT, UI-SHELL, UI-BUDGET; GAUGE-ZERO-WIDTH merged, or closed by L0 as superseded (its HC-GZW cases live on as HC-UIRR-008). **Gate:** none.
**Motion:** the route change into Results is M0 (its first paint has values); the analyte list has no M6. **Layout:** proposal A's (chart card with the analyte list beside it on desktop; on phones a compact header, the analyte chip scroller as a labelled focusable region, then the chart). Panel tabs filter the list (fixes "CBC" showing Glucose). The dead "Last 12 Months" and "Filters" become one real range select or are deleted. "Explain this result" shows the interpretation card with its DisclaimerBanner and citations. PNG/SVG export kept.

| Id | Check | RED today? |
|---|---|---|
| HC-UIRES-001 | `/trends` and `/interpret` redirect to `/results`, keeping `?analyte=` | yes |
| HC-UIRES-002 | selecting the CBC panel lists only CBC analytes | yes (shows Glucose) |
| HC-UIRES-003 | the contextual disclaimer, the Safety Rail and every value on the page are in the DOM at first paint and pass `stillnessProbe` from the first sample after navigation (effective opacity 1, fixed rect) | yes (no disclaimer on `/trends`; the route fades today) |
| HC-UIRES-004 | (DF-4) at 390×844, ≥ 200 px of the plot is in the first viewport above the tab bar and the rail | yes in proposal A's prototype |
| HC-UIRES-005 | no control on the page lacks a handler (the old "Last 12 Months"/"Filters" are gone or work) | yes |
| HC-UIRES-006 | PNG and SVG export still produce a file (ported `ChartExport` cases) | GREEN (pin, ported) |

**Acceptance:** G; Results route total ≤ 205 kB gz. **Est:** 5 h. **MVP:** P1.

#### UI-PG-DOCUMENTS — Documents page and the import and processing showcase

**Files:** `fe/pages/DocumentInbox.tsx`, `fe/components/documents/CategoryBadge.tsx` (delete; no importer), `ExtractionConfidenceBadge.tsx` (words first, shown only below the threshold), `HighlightChips.tsx` (Tags, max 2 + "+N"), `fe/__tests__/DocumentInbox.test.tsx` (selectors only), `fe/__tests__/ui-documents.test.tsx` (new), `e2e/ui-documents.spec.ts` (new). `EntityDetailView.tsx` belongs to UI-PG-REVIEW.
**Depends on:** UI-SHELL, UI-SHOWCASE-KIT, UI-PROVENANCE; FE-IMPORT-ERROR merged; never beside IMPORT-SCANNED-PAGE (same page): whichever lands second merges `origin/main` and keeps the other's tests green (HC-FIE-001…003, HC-ISP-004). **Gate:** none.
**Showcase:** S2 on the card of a document being extracted, S3 (20 px) beside "Reading page N of M" (text from the existing processing state), M6 for new rows, then the handoff "N values ready to review" linking to Review values. The page h1 stays "Document Inbox" here (UI-MICRO renames it), so this row does not touch `e2e/routing.spec.ts`. Row actions are always visible (no hover-only); preview is a Sheet; `window.confirm` becomes AlertDialog.

| Id | Check | RED today? |
|---|---|---|
| HC-UIDOC-001 | with the mouse away, row actions have opacity 1 and are reachable by Tab | yes (`opacity-0` until hover) |
| HC-UIDOC-002 | at most 2 chips per row; no raw identifier (`lab_csv`) in the text | yes (5 chips) |
| HC-UIDOC-003 | a processing document shows the beam and a `role="status"` text; under reduced motion the border is static and the text stays | yes |
| HC-UIDOC-004 | FE-IMPORT-ERROR's alert and IMPORT-SCANNED-PAGE's warning (whichever has merged) render static, never inside the beam card's animation | GREEN once those rows merge (pin) |
| HC-UIDOC-005 | delete asks through an AlertDialog; `window.confirm` is never called (stubbed to throw) | yes |

**Acceptance:** G; `thinking-orbs` loads only on this route and About. **Est:** 4 h. **MVP:** P1.

#### UI-PG-REVIEW — Review values with Ink

**Files:** `fe/pages/VerificationWorkbench.tsx`, `fe/components/documents/EntityDetailView.tsx` (responsive rows; StatusChip; "Show source" opens Source Trace; Ink on verify), `fe/__tests__/VerificationWorkbench.test.tsx` and `VerificationWorkbenchEdit.test.tsx` (selectors only), `fe/__tests__/ui-review.test.tsx` (new), `e2e/ui-review.spec.ts` (new).
**Depends on:** UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT; FE-VERIFY-NUMERIC merged (its strict parse and error path stay). **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIREV-001 | an out-of-range value carries an icon and the words, not colour alone (WCAG 1.4.1) | yes |
| HC-UIREV-002 | verifying flips the marker from pencil to ink in the row, the chart and the chip together; the value text passes `stillnessProbe` throughout the Ink animation | yes |
| HC-UIREV-003 | the Edit dialog is labelled, traps focus, Escape closes; HC-FVN-001…005 still pass | yes for the dialog; pins for FVN |
| HC-UIREV-004 | no fixed `grid-cols-3` overflow at 390 and 320 (G6) | yes |

**Acceptance:** G. **Est:** 4 h. **MVP:** P1.

#### UI-PG-ASK — Ask: the chat owns its scroll, citations open on tap

**Files:** `fe/pages/ExplainAssistant.tsx`, `fe/__tests__/ExplainAssistant.test.tsx` and `ExplainAssistantHistoryRestore.test.tsx` (selectors only), `fe/__tests__/ui-ask.test.tsx` (new), `e2e/ui-ask.spec.ts` (new).
**Depends on:** UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT; FE-EXPLAIN-ERR and BADGE-TICK merged (same file; their HC-FEE and HC-BTK tests stay green). **Gate:** none.
**Spec:** the message list is its own focusable scroll region; the disclaimer sits under the composer, always visible; citation chips use the popover from UI-PROVENANCE; the pending state is `Pending` text "Reading your verified results…" (no orb: Ask is not a showcase surface); the patient's own message enters with M6, while assistant answers (values and citations, T0) appear without motion; filter date inputs labelled; feedback thumbs are 44 px `IconButton`s with `aria-pressed`.

| Id | Check | RED today? |
|---|---|---|
| HC-UIASK-001 | sending scrolls only the message list; `window.scrollY` is unchanged | yes |
| HC-UIASK-002 | the disclaimer under the composer is in the viewport at 390 and 1440 without scrolling | yes |
| HC-UIASK-003 | axe: `scrollable-region-focusable`, `label`, `button-name` pass | yes |
| HC-UIASK-004 | no `canvas` and no `ThinkingOrb` on the page | GREEN (pin for the tier rule) |
| HC-UIASK-005 | a new answer's values and citations pass `stillnessProbe` from the first sample after they render | yes |

**Acceptance:** G. **Est:** 4 h. **MVP:** P1.

#### UI-PG-MEDS — Medications, reminders tab, dose sheet

**Files:** `fe/pages/MedicationCoach.tsx` (tabs Medications / Reminders via `?tab=`), `fe/pages/MedicationDetail.tsx`, `fe/pages/NotificationSettings.tsx` (becomes a redirect to `/medications?tab=reminders`; its content moves into a `RemindersPanel` inside `fe/components/medication-coach/`), `fe/components/medication-coach/*` (MedicationCard as a real link; DoseLoggingModal → Sheet/Dialog; BadgeToast → `notify()` with no `animate-ping`; AchievementsWidget and AdherenceDashboard on tokens; the adherence ring renders final, with no draw, because adherence figures are T0), `fe/components/MedicationOverlay.tsx` (router `Link` instead of `<a href>`), `fe/__tests__/NotificationSettingsPage.test.tsx`, `Gamification.test.tsx` (selectors only; this row owns `Gamification.test.tsx` in wave 5, and UI-PG-SETTINGS follows it), `fe/__tests__/ui-meds.test.tsx` (new), `e2e/ui-meds.spec.ts` (new).
**Depends on:** UI-SHELL, UI-SHOWCASE-KIT. **Gate:** none; MED-BADGES is open and non-blocking: the row keeps the badges as they are, static, behind the existing streaks setting (C-GAM2B `streaks_hidden`).

| Id | Check | RED today? |
|---|---|---|
| HC-UIMED-001 | MedicationCard is keyboard-activatable (Enter opens the detail) | yes (`div onClick`) |
| HC-UIMED-002 | the dose sheet: Escape closes, focus is trapped and returns; its exit plays | yes |
| HC-UIMED-003 | no `animate-ping` anywhere under `medication-coach/` | yes |
| HC-UIMED-004 | `/notifications` lands on the reminders tab with the same settings | yes |

**Acceptance:** G. **Est:** 4 h. **MVP:** P2.

#### UI-PG-CARE — Follow-ups

**Files:** `fe/pages/CareTasksPage.tsx`, `fe/__tests__/ui-care.test.tsx` (new), `e2e/ui-care.spec.ts` (new). **Depends on:** UI-SHELL, UI-SHOWCASE-KIT. **Gate:** none.
Done and ignore are optimistic with a toast offering Undo (the care-task API has both directions; the row re-reads `fe/services/careTasks.ts` and drops Undo for any action without a reverse call); the strike-through becomes an M8 state morph.

| Id | Check | RED today? |
|---|---|---|
| HC-UIFU-001 | marking done shows the toast; Undo (where the API supports it) restores the task | yes |
| HC-UIFU-002 | the page heading reads "Follow-ups" and the route is unchanged | yes |

**Acceptance:** G. **Est:** 2 h. **MVP:** P2.

#### UI-PG-RECORDS — Timeline, Search, Pinboards

**Files:** `fe/pages/TimelinePage.tsx` (event cards name the analytes, "Glucose, LDL"; duplicate `p-8` removed), `fe/pages/SearchPage.tsx` (query echoed; results are interactive cards), `fe/pages/PinboardsPage.tsx` (`window.prompt`/`confirm` → Dialog/AlertDialog), `fe/components/pinboards/AddToPinboardButton.tsx` (M3 `data-state` enter), `fe/__tests__/PinboardsPage.test.tsx`, `SearchPage.test.tsx` (selectors only; after UI-PALETTE), `fe/__tests__/ui-records.test.tsx` (new), `e2e/ui-records.spec.ts` (new). **Depends on:** UI-SHELL, UI-SHOWCASE-KIT, UI-PALETTE. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIPIN-001 | a timeline card names its analytes | yes ("1 analyte") |
| HC-UIPIN-002 | `window.prompt` and `window.confirm` are never called (stubbed to throw) | yes |
| HC-UIPIN-003 | the search page shows the query it searched | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P2.

#### UI-PG-EXPORT — Doctor summary

**Files:** `fe/pages/ExportPage.tsx` (section toggles → Checkbox/Switch rows; "Full Preview" opens a Sheet or is removed; the redaction level shown as read-only text), `fe/__tests__/ExportPage.test.tsx` (selectors only), `fe/__tests__/ui-export.test.tsx` (new), `e2e/ui-export.spec.ts` (new). **Depends on:** UI-SHELL, UI-SHOWCASE-KIT. **Gate:** none. Redaction is untouched: `git diff origin/main -- src/frontend/src/services/export.ts src/backend` must be empty (pasted).

| Id | Check | RED today? |
|---|---|---|
| HC-UIEXP-001 | "Full Preview" opens a Sheet with the preview, or no such button exists | yes (dead) |
| HC-UIEXP-002 | no native unstyled checkbox on the page | yes |
| HC-UIEXP-003 | the request bodies sent for each export equal today's (recorded fixtures) | GREEN (pin) |

**Acceptance:** G. **Est:** 2.5 h. **MVP:** P2.

#### UI-PG-SETTINGS — Settings split into sections

**Files:** `fe/pages/SettingsPage.tsx` (section host with Tabs, `?section=`), `fe/pages/settings/PreferencesSection.tsx`, `AssistantPrivacySection.tsx`, `AdvancedSection.tsx`, `SecuritySection.tsx` (new; the security section renders today's `RecoveryCodeCard`, `BackupCard`, `DangerZone` unchanged, which UI-PG-SECURITY restyles), `fe/components/MemoryManager.tsx`, `fe/components/settings/AgentSettingsCard.tsx` (Switch), `TierCapabilities.tsx` (honest copy, 13 px floor), `DataDonationCard.tsx` (Switch + AlertDialog; `CONSENT_TEXT_VERSION` and consent text unchanged), `ExternalApiBreakGlassWarning.tsx` (token restyle only; text, role and visibility unchanged, D12), the settings tests for those components (selectors only), `fe/__tests__/Gamification.test.tsx` (the streaks-switch cases, selectors only), `fe/__tests__/ui-settings.test.tsx` (new), `e2e/ui-settings.spec.ts` (new).
**Wave 6** (listed with the page rows): **Depends on:** UI-PG-MEDS (it owns `Gamification.test.tsx` in wave 5), UI-SHELL, UI-SHOWCASE-KIT; never beside DON-COPY-V3 (`DataDonationCard.tsx`). **Gate:** none (auth and encryption cards are left to UI-PG-SECURITY).

| Id | Check | RED today? |
|---|---|---|
| HC-UISET-001 | `/settings` lands on Profile & security; each `?section=` renders its section | yes |
| HC-UISET-002 | Advanced is collapsed by default; Tesseract, GPU and model-tier text is absent until "Show advanced settings" | yes |
| HC-UISET-003 | the break-glass warning's text and role equal today's (snapshot of text + role) and it has no animation | GREEN (pin, D12) |
| HC-UISET-004 | the consent dialog is an AlertDialog with Escape and focus return; consent text and version unchanged | yes for the dialog |
| HC-UISET-005 | no section is taller than 2 viewports at 1440 | yes (5,565 px) |

**Acceptance:** G. **Est:** 5 h. **MVP:** P2.

### 7.8 Wave 6

#### UI-CHART-CLEANUP — delete the Recharts chart and the dependency

**Files:** `fe/components/lab-interpreter/InterpretedTrendChart.tsx`, `fe/components/TrendVerificationMarkers.tsx` (delete; both folded into the Ribbon), their tests `InterpretedTrendChart.test.tsx`, `TrendVerificationMarkers.test.tsx` (each case ported to `ui-range-ribbon.test.tsx` or shown already covered there, listed in the PR), `fe/__tests__/Accessibility.test.tsx`, `ChartExport.test.tsx` (Recharts mocks removed), `fe/components/lab-interpreter/index.ts`, `src/frontend/package.json` and lock (remove `recharts`; remove `cmdk` if UI-PALETTE fell back to its own listbox). **Depends on:** UI-PG-RESULTS. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UICC-001 | no `recharts` import under `src/` and none in `package.json` | yes |
| HC-UICC-002 | every removed test id is mapped to a ported or existing test (table in the PR) | — |

**Acceptance:** G; lazy JS −105 kB gz. **Est:** 1.5 h. **MVP:** P2.

#### UI-OVERVIEW — Overview landing with the first-run checklist

**Files:** `fe/pages/OverviewPage.tsx` (new), `fe/App.tsx` (index → `/overview`), `fe/components/layout/navConfig.ts` (Overview entry and phone tab), `fe/__tests__/Routing.test.tsx` (HC-ROUTE-001 expects `/overview`: a contract change from this plan), `e2e/routing.spec.ts` (E2E-ROUTE-001's redirect target and heading only, the same contract change), `fe/__tests__/ui-landing.test.tsx` (new), `e2e/ui-landing.spec.ts` (new). **Depends on:** UI-PG-RESULTS (`App.tsx`, navConfig), UI-PG-DOCUMENTS. **Gate:** none.
**Spec:** built from existing queries only. Before the first import: the Import → Review values → See results checklist with S1 on the cards (the counts and values sit outside the S1 wrapper); the current step is marked "Next step" in words with a static accent border; each step is a working link. Afterwards: "N values waiting for review", latest results as static text with StatusChips, next dose, each linking to its page.

| Id | Check | RED today? |
|---|---|---|
| HC-UILAND-001 | with no documents, the checklist renders three working links; the current step reads "Next step" and has no animation running | yes |
| HC-UILAND-002 | with data, counts equal the API's; every count and value passes `stillnessProbe` after navigation and through the S1 entrance | yes |
| HC-UILAND-003 | the unknown-path redirect and the index both land on `/overview` | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1.

#### UI-PG-SECURITY — Profile & security section (gated)

**Files:** `fe/components/settings/BackupCard.tsx`, `DangerZone.tsx`, `fe/components/settings/RecoveryCodeCard.tsx`, `fe/pages/settings/SecuritySection.tsx`, `fe/__tests__/DangerZone.test.tsx`, `BackupRestoreFlow.test.tsx`, `RecoveryCodeCard.test.tsx` (it tests this settings card; selectors only), `fe/__tests__/ui-security.test.tsx` (new), `e2e/ui-security.spec.ts` (new; real backend through HTTP). **Wave 7** (UI-PG-SETTINGS moved to wave 6). **Depends on:** UI-PG-SETTINGS; MVP-REAUTH-401 merged (same tests; its HC-RA4 cases stay green). **Gate:** UI-AUTH-SCREENS (new; planner reading of CLAUDE.md §1). The token and raw-colour swap happens in every outcome; the answer decides only the layout change. If the owner picks "No layout change", the row is just that swap.
**Spec:** primitives only; the typed-phrase delete stays (no hold-to-confirm); restore and delete confirmations become AlertDialogs; requests, copy of warnings and the order of steps unchanged.

| Id | Check | RED today? |
|---|---|---|
| HC-UISEC-001 | e2e (real backend): delete with a wrong password shows "Incorrect password" and keeps the session (MVP-REAUTH-401 behaviour) | GREEN after MVP-REAUTH-401 (pin) |
| HC-UISEC-002 | the request sequence for backup, restore and delete equals today's (recorded in the e2e, compared) | GREEN (pin) |
| HC-UISEC-003 | every dialog: Escape, focus trap, focus return | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P2.

#### UI-PG-AUTH — setup, unlock card and recovery (gated)

**Files:** `fe/pages/ProfileSetup.tsx` (the SESSION-REENTRY unlock card restyled; the Lift moment; S1 entrance of the create form only, never on the recovery-code step; errors clear when fixed; the fake `setTimeout(500)` progress removed; the unlinked "Terms of Service" sentence removed), `fe/pages/RecoverProfile.tsx`, `fe/components/profile/RecoveryCodeCard.tsx` (code in 4-character groups that never wrap mid-group; warning in `--caution`), `fe/__tests__/ProfileSetup.test.tsx`, `RecoverProfile.test.tsx` (selectors only), `fe/__tests__/ui-auth.test.tsx` (new), `e2e/ui-auth.spec.ts` (new; real backend). **Depends on:** SESSION-REENTRY Task 1 merged (its HC-SRE-001…004 stay green), UI-SHELL, UI-SHOWCASE-KIT. **Gate:** UI-AUTH-SCREENS (new; planner reading of CLAUDE.md §1): its answer decides the layout, the S1 entrance and the Lift; the token and raw-colour swap happens in every outcome.

| Id | Check | RED today? |
|---|---|---|
| HC-UIAUTH-001 | a fixed field's error disappears on the next valid input | yes (stale errors) |
| HC-UIAUTH-002 | creating a profile shows no progress steps that are not tied to a real request (no `setTimeout` in the flow) | yes |
| HC-UIAUTH-003 | e2e (real backend): unlock succeeds and the shell is visible within one frame of the Lift; under reduced motion opacity only | yes |
| HC-UIAUTH-004 | the recovery code renders in groups with no group split across lines at 320 | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1.

### 7.9 Waves 7-9

#### UI-ABOUT — the About page for the demo

**Files:** `fe/pages/AboutPage.tsx` (new), `fe/App.tsx` (public `/about`, no data, no auth), `fe/components/layout/ProfileMenu.tsx` (one link), `fe/__tests__/ui-about.test.tsx` (new), `e2e/ui-about.spec.ts` (new). **Depends on:** UI-OVERVIEW (`App.tsx`), UI-RIBBON, UI-SHOWCASE-KIT. **Gate:** none; UI-ABOUT-PLACE (open, non-blocking) may add a link before sign-in.
**Content:** what Asclexis is and is not (education, not medical advice, not a medical device; brand guidelines), local-first ("your records stay on this device"), how it works (import → review values → results → ask, with sources), and the capstone context. All assets local; no remote fonts, images or embeds. Showcase per [§4.2](#42-showcase-surfaces-ui-saas-meaning); the hero ribbon uses example data labelled "Example data, not yours".

| Id | Check | RED today? |
|---|---|---|
| HC-UIABT-001 | `/about` renders without a profile and makes no API request | yes |
| HC-UIABT-002 | the "not medical advice" and local-first statements pass `stillnessProbe` through the whole S1 sequence (they sit outside S1 wrappers) | yes |
| HC-UIABT-003 | the example chart is labelled as example data in text | yes |
| HC-UIABT-004 | G7: no request to a non-localhost origin | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1.

#### UI-MICRO — press, target and copy sweep

**Files:** every remaining raw `<button>` under `fe/` moved to `Button` / `IconButton` (the file list is the output of the grep in HC-UIMIC-001, frozen in the PR); `src/frontend/eslint.config.js` (`no-restricted-syntax` on `transition-all`, `text-[9px]`, `text-[10px]` and on `<button className=` outside `fe/components/ui/`); copy pass ("abnormal" → "outside the reference range (per report)"; "AI-powered insights" removed; the model chip says "Template answers, no model installed" when true); `fe/components/layout/navConfig.ts` (the transition "Reminders" entry removed); `fe/__tests__/ui-micro.test.ts` (new). **Depends on:** every wave 5-7 row merged (it touches their files). **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIMIC-001 | `eslint` passes with the new rules (no raw `<button className=` outside `ui/`) | yes |
| HC-UIMIC-002 | rendered text of every route contains none of the forbidden words ("abnormal", "AI-powered") | yes |
| HC-UIMIC-003 | axe `target-size` = 0 on every route | yes (password eye 20 px, citation chip 20 px) |

**Acceptance:** G on all routes. **Est:** 3 h. **MVP:** P2.

#### UI-DARK-FLIP — dark mode follows the OS once no unmigrated colour remains

**Files:** `fe/theme/theme.ts` (`DARK_MODE_ENABLED = true`), `src/frontend/index.html` (the pre-paint script follows the OS), `fe/__tests__/ui-theme.test.ts` (HC-UITH-001 now asserts the flag is on: a contract change from owner answer UI-DARK-MODE), `fe/__tests__/ui-dark-gate.test.ts` (new), `e2e/ui-dark-gate.spec.ts` (new). **Depends on:** every other `UI-*` row merged (UI-PG-SECURITY and UI-PG-AUTH in whatever form UI-AUTH-SCREENS allows). **Gate:** UI-DARK-MODE answered ("Follow OS setting").

| Id | Check | RED today? |
|---|---|---|
| HC-UIDRK-001 | a source scan of `fe/**/*.{ts,tsx}` and `fe/styles/*.css` outside the token block finds no unmigrated colour: `bg-white`, `text-white`, `bg-black`, `text-black`, `(bg\|text\|border\|ring\|fill\|stroke)-(gray\|slate\|zinc\|neutral\|stone\|red\|orange\|amber\|yellow\|lime\|green\|emerald\|teal\|cyan\|sky\|blue\|indigo\|violet\|purple\|fuchsia\|pink\|rose)-\d+`, arbitrary hex in class names (`[#…]`), hex or `rgb(` literals in `style` or SVG attributes; **no allowlist** | yes on `7749744` (the PR pastes the failing count from a checkout of that commit) |
| HC-UIDRK-002 | e2e: with `colorScheme: 'dark'`, every route (the 15, Overview, About, setup, recover) has `data-theme="dark"` and axe 0 serious/critical | — |
| HC-UIDRK-003 | e2e: in dark, no visible element larger than 40×40 px has a computed background with relative luminance > 0.8 (catches a leftover white card) | — |
| HC-UIDRK-004 | e2e: with `colorScheme: 'light'` nothing changes from `origin/main`'s light screenshots taken at this row's merge base, just before the flip (pixel diff below 0.5 % per route) | — |

**Acceptance:** G on every route in both themes. **Est:** 2 h. **MVP:** P2. If HC-UIDRK-001 finds anything, the fix belongs to the row that owns that file; the flip waits.

---

## 8. Session and safety deltas

### 8.1 SAFETY-MODE-REAL

Planned in [§7.2](#safety-mode-real--research-concrete-behaviours-for-the-safety-toggle-and-turn-them-into-an-owner-question). Sequence: research row → owner question SAFETY-MODE-BEHAVIOUR → a build row planned from the answer, with SAFETY-MODE-DIFF for each ask-first file → the build replaces UI-SHELL's disabled switch with a working one. Until then, [§3.6](#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real) holds.

### 8.2 Delta to SESSION-REENTRY: Task 3 "Lock now"

Tasks 1 and 2 of SESSION-REENTRY are unchanged, with their gates (SESSION-REENTRY (a); SESSION-AUTH-DIFF for Task 2). Task 1 ships in today's styles; UI-TOKENS and UI-PRIM-CONTROLS restyle it automatically; UI-PG-AUTH restyles it fully once UI-AUTH-SCREENS is answered.

**Task 3 (new, frontend only, gate SESSION-LOCK-NOW):** a "Lock now" item in the profile menu calls the existing `useLockProfile()` (`fe/services/profiles.ts:181`; backend `POST /profiles/{profile_id}/lock`, `be/api/profiles.py:992`), clears the session the way logout does, and lands on the `/setup` unlock card. No backend change. **Files:** `fe/components/layout/ProfileMenu.tsx`, `fe/__tests__/ProfileMenuLock.test.tsx` (new, HC-SRE-006), `e2e/session-lock-now.spec.ts` (new, real backend, HC-SRE-007). **Checks:** HC-SRE-006 the menu item calls the lock endpoint once and clears the auth store (RED); HC-SRE-007 after Lock now, a protected route shows the unlock card and the password unlocks it (RED). **Depends on:** UI-SHELL, Task 1 merged. **Est:** 1 h. **MVP:** P2.

---

## 9. Reconciliation with rows already on main

| Existing row (status on `15fe095`) | Overlap | Rule |
|---|---|---|
| SESSION-REENTRY (Task 1 ready, P0; Task 2 gated) | unlock UI; `ProfileSetup.tsx` | no new unlock row; UI-PG-AUTH depends on Task 1; Task 3 added as a delta (§8.2); UI-MOTION never beside Task 1 |
| MVP-REAUTH-401 (ready, P0) | `DangerZone.test.tsx`, `BackupRestoreFlow.test.tsx` | UI-PG-SECURITY depends on it; services files untouched by any UI row |
| FE-IMPORT-ERROR (ready, P0), IMPORT-SCANNED-PAGE (blocked) | `DocumentInbox.tsx` | UI-PG-DOCUMENTS depends on FE-IMPORT-ERROR and is never beside IMPORT-SCANNED-PAGE; UI-MOTION never beside either |
| FE-VERIFY-NUMERIC (ready, P1) | `VerificationWorkbench.tsx` | UI-PG-REVIEW depends on it; UI-MOTION never beside it |
| FE-EXPLAIN-ERR (ready, P1), BADGE-TICK (ready, P2) | `ExplainAssistant.tsx` and its test | UI-PG-ASK depends on both; UI-MOTION never beside either |
| GAUGE-ZERO-WIDTH (ready, P2) | `ReferenceRangeComparison.tsx` | UI-PG-RESULTS replaces the gauge with RangeTick; if GAUGE-ZERO-WIDTH is unclaimed when UI-PG-RESULTS starts, L0 may close it as superseded (its cases are HC-UIRR-008) |
| AXE-E2E (ready, P2) | `package.json`; axe in e2e | UI-GATES and UI-MOTION depend on it; its `KNOWN_A11Y` entries are removed by the page rows that fix them (an entry may only be removed) |
| E2E-UIFULL-CI (ready, P1) | `ui-routes-verification.spec.ts` | UI-SHELL depends on it and updates nav labels only |
| CI-CACHE (ready, P2) | `ci.yml` | UI-BUDGET never beside it |
| DON-COPY-V3 (blocked) | `DataDonationCard.tsx` | UI-PG-SETTINGS never beside it; consent text untouched by UI rows |
| FE-A11Y-DIALOGS (bullet, not planned) | dialogs without Escape or focus trap | **planned here**: UI-PRIM-OVERLAYS plus the page rows that own each dialog (Settings export and consent dialogs: UI-PG-SETTINGS; dose modal: UI-PG-MEDS; preview: UI-PG-DOCUMENTS; edit value: UI-PG-REVIEW) |
| CHAT-MODEL-BADGE, INTERP-GROUNDED-MD, INTERP-RENDER-2, VERIFY-DOCS-STALE | done (#295) | their tests stay green inside the page rows that move those components |

**New bullets found while planning (not yet planned):**
- **VERIFY-UNDO:** the Ink moment cannot offer Undo: `be/api/observations.py:384` has verify only and no unverify. Both designers assumed Undo. A backend row (audit-logged, per-profile) if the owner wants it.
- **ICON-RAIL-TABLET:** proposal B's 768–1023 px icon rail is not built (comparison #18); revisit only if tablet use matters.

---

## 10. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Time and a half-migrated look.** 30 rows, 8 days to the demo, and "no freeze" (owner, who accepted "Higher risk of a half-migrated look") | the order reduces the mixed look but does not remove it; P0/P1 first; nothing is promised for 2026-10-31 beyond what merges |
| R2 | UI-MOTION touches 28 files, several shared with ready MVP rows | MVP P0/P1 rows on those files go first (each ≤ 1.5 h); the `m` swap is mechanical. Proposal A proved it on `motion` 14 (vitest 273/275); on framer-motion 10.18 the same APIs exist (typings cited in the row) but the swap and its bundle size are unmeasured until the row runs |
| R3 | A gate row (UI-TOKENS' contrast test, UI-BUDGET) merges beside rows built before it | L0 runs the new gate on `origin/main` before merging the next group (recurring-failures #12) |
| R4 | Dark mode looks broken on any page with a leftover raw colour | it stays off until UI-DARK-FLIP, whose source scan has no allowlist |
| R5 | The custom chart loses Recharts behaviours (tooltips, resize edge cases, export) | the Ribbon has a table fallback, keeps PNG/SVG export (ported tests), and is ~250 lines in both prototypes |
| R6 | Owner expectation: "bold showcase" could drift onto clinical pages | the Motion Gradient is the review checklist; G10's stillness probe (HC-UIG-006 proves it can fail) runs on every route, and HC-UIRES-003, HC-UILAND-002, HC-UIABT-002, HC-UIREV-002 and HC-UIASK-005 pin it where showcase or moment motion sits next to T0 content |
| R7 | The Ink moment animates a marker on a lab value (L0 reading that this is allowed as T3: the marker, not the value, after the user's own action) | the value text passes the stillness probe (HC-UIREV-002); the owner can veto (open question INK-MOMENT) |
| R12 | Clinical routes no longer fade in (G10 makes their route change M0), which is less "smooth" than both prototypes | the shell, sheets, palette and showcase surfaces carry the motion; an L0 reading of "Lab values and safety copy stay still" the owner can revisit |
| R8 | The relabelled toggle could still be read as safety being off | the visible note says the standard checks always run; HC-UISH-006 pins it; SAFETY-LABEL-WORDING lets the owner choose another wording |
| R9 | IA renames break muscle memory, docs and capstone screenshots | old routes redirect; names are one file; open question UI-NAV-NAMES |
| R10 | `thinking-orbs` is a 0.x package | MIT, no runtime dependencies or network code; isolated behind `ThinkingOrb`, lazy, on two routes; replacing it is one file |
| R11 | Results of the INP proxy come from headless Chromium, not real devices | G3 runs on a production build with CPU ×4; real-device checks stay on the "not verified" list |

---

## 11. Owner gates and open questions

None of these is answered. L0 numbers and asks them; the owner's words are recorded verbatim in owner-decisions. Wording is a draft, written neutrally.

**Execution gates (a row waits for the answer):**

- **UI-AUTH-SCREENS** (UI-PG-AUTH, UI-PG-SECURITY). **Planner reading of CLAUDE.md §1** ("ALWAYS ask before touching … anything auth/encryption"), not an owner instruction; L0 decides whether and when to ask. Whatever the answer, UI-TOKENS, UI-PRIM-CONTROLS and UI-MOTION already change these screens (colours, buttons, inputs, import lines), and their raw colours become tokens, so dark mode is never blocked. The question covers only what is left: "The sign-in, recovery, backup, restore and delete-profile screens already get the new colours and controls. Should they also get the new layout, the entrance motion on the create-profile form, and the short 'lift' when you unlock? Requests, steps and warning text stay the same." Options: "Layout, motion and Lift" (new layout; the create-profile form enters with S1; the unlock card lifts away on success; the recovery-code step stays still). "Layout only" (new layout; no entrance motion and no Lift). "No layout change" (today's layout with the new colours and controls). Tradeoffs: these screens protect access to encrypted records, so any change is reviewed against today's request sequence (HC-UISEC-002); "No layout change" leaves them looking older than the rest. Analogy: the front door already has the new paint; the question is whether to also change its shape and add a gentle opening.
- **SESSION-LOCK-NOW** (SESSION-REENTRY Task 3). "Add a 'Lock now' item to the profile menu that closes the profile and returns to the unlock card, using the lock endpoint that already exists?" Options: "Add Lock now" (one menu item; nothing changes in the backend). "Not now" (you stay signed in until the session expires or you log out). Tradeoffs: locking closes the profile on this device; the next action needs the password. Analogy: a "lock screen" button on a shared computer.
- **SAFETY-MODE-BEHAVIOUR** (after SAFETY-MODE-REAL): asked with the research's options; no recommendation until the research exists.
- **SAFETY-MODE-DIFF** (merge or execution, per ask-first file the chosen behaviour touches): asked with the exact diff.

**Open questions (rows proceed with the default stated; the answer may change a file later):**

- **SAFETY-LABEL-WORDING.** "Until the safety toggle does something, how should it read?" Options: "'Stricter safety mode', disabled, with 'Not available yet. The standard safety checks always run.'" (the plan's default) / "'Extra safety checks · coming soon', disabled, with the same note" / "A short note only: 'Safety checks always on', with no switch until the real one is built" (this departs from "keep a toggle").
- **UI-NAV-NAMES.** "Which navigation names should ship?" Options: "Documents, Review values, Results, Ask, Follow-ups, Doctor summary" (default) / "Documents, Review, Results, Ask, Tasks, Doctor summary" / "Today's names (Inbox, Verify, Trends, Explain, Tasks, Export) with only the grouping".
- **UI-BRAND-MARK.** "Keep the heart logo or move to a mark drawn from the pencil-and-ink idea?" Options: "New mark" (default) / "Keep the heart".
- **MED-BADGES.** "The medication badges ('Week Warrior', 'Comeback Kid') lose their celebration animation either way. What should happen to the badges themselves?" Options: "Keep as today, static" (default) / "Off by default, shown only if streaks are turned on" / "Remove them".
- **UI-ABOUT-PLACE.** "Where should the About page be reachable?" Options: "Inside the app, from the profile menu" (default) / "Also before sign-in, from the setup screen" (this edits an auth screen, so it rides on UI-AUTH-SCREENS) / "Only by its address, for the demo".
- **INK-MOMENT.** "When you mark a value as checked, its dot on the chart fills in over a third of a second; the number itself never moves. Keep that, or make the change instant?" Options: "Keep the fill" (default) / "Instant".

**L0 tells the owner (not gates):** the Undo the designers drew on verify needs a backend row (VERIFY-UNDO); the idle-lock warning needs the unread auto-lock setting (AUTO-LOCK-UNUSED, ask-first auth).

Back to: [queue](2026-10-15-build-program/queue.md) · [RUNBOOK](2026-10-15-build-program/RUNBOOK.md) · [research package](../research/2026-10-23-frontend-revamp/00-README.md)
