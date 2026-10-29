# Frontend revamp 2026-10-23 — merged plan: Ink & Paper on a Motion Gradient

**Last Updated:** 2026-10-29 (POPOVER-OPEN-COST widened to dialog opens after the UI-PG-MEDS #398 stop: [delta](#delta-2026-10-29-popover-open-cost-widened-to-dialog-opens-ui-pg-meds-398-stop), planned on `41fa382`; earlier 2026-10-28: owner answers STILLNESS-GAP-BOUND "Fix first, frame waits" and STILLNESS-NAV-70 "Raise it to 70 ms for page changes and keep diagnosing": §7.11 rows GATES-NAV-BOUND (L0) and STILLNESS-NAV-LATE planned on `6b3dd27`; UI-SHELL depends on GATES-NAV-BOUND; §11 answered line); 2026-10-26 (post-merge batch on `0e8b2b2`: GATES-SAMPLE-TIME done (#374), with its review MINOR 3 noted; §7.10 follow-ups planned: POPOVER-OPEN-COST, SETTINGS-DETECT-BLOCKING, GATES-SAMPLE-TIME-MINORS, ALERTDIALOG-CANCEL-FOCUS; SAFETY-LABEL-WORDING answered "Keep plan default (Recommended)" and closed in §11; UI-PHONE-TOGGLE answered "Second row on phones (Recommended)"); 2026-10-24 (SAFETY-MODE build rows planned on `29dca22` from owner prompt 51: SAFETY-MODE-SETTING, -STRICT, -VERIFIED, -TOGGLE, -CITATIONS, -VERIFIED-FE); 2026-10-24 (owner prompt 48: UI-ROUTE-MOTION "Whole-page fade", UI-AUTH-SCREENS "Layout, motion and Lift", SESSION-LOCK-NOW "Add Lock now"); 2026-10-23 (review round 2 of #311: e2e contract-change appendix, `data-t0` owners and M0 route default, overlay rule, fixture screenshot, wave order, base `257e072`); 2026-10-23 (review round 1 of #311: framer-motion 10 kept (owner UI-DEPS), fixture name (owner UI-FIXTURE-NAME), stillness probe G10, UI-AUTH-SCREENS relabelled, test-file ownership, 11 minors)
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. **No owner approval is recorded here.** Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md); the owner direction and prompt 44's four answers are recorded there as rows UI-DIRECTION, UI-SAAS-MEANING, UI-SCOPE-1031, UI-DARK-MODE and UI-SAFETY-TOGGLE, prompt 45's two answers as rows UI-DEPS and UI-FIXTURE-NAME, and prompt 48's three answers as rows UI-ROUTE-MOTION, UI-AUTH-SCREENS and SESSION-LOCK-NOW (same PR).
**Base measured:** `origin/main` @ `257e072` (2026-10-23; merged since the first draft's `15fe095`: #321 MVP-REAUTH-401, #315 CPU-DEFAULT-PHI4, #318 OLLAMA-NUM-CTX, #314 FE-EXPLAIN-ERR, #319 GAUGE-ZERO-WIDTH, #320 INTERP-REGEN-500). The designers and the UI review read `7749744`; since then `src/frontend` changed only through #321 (`services/api.ts`, `profiles.ts`, `backup.ts`), #314 (`ExplainAssistant.tsx`) and #319 (`ReferenceRangeComparison.tsx`) with their tests, and both prototype patches still pass `git apply --check` on `257e072`. Every e2e line cited in [Appendix A](#appendix-a-e2e-assertions-and-the-row-that-changes-each) was read on `257e072` and re-read after #323 (docs) and #312 SESSION-REENTRY Task 1 (`7667439`), which this branch has merged.
**Refresh Trigger:** an owner answer to a gate in [§11](#11-owner-gates-and-open-questions); a merge of any `UI-*` row (its measured numbers replace the ones quoted here); a merge of SESSION-REENTRY, FE-IMPORT-ERROR, IMPORT-SCANNED-PAGE, FE-VERIFY-NUMERIC, BADGE-TICK, AXE-E2E or E2E-UIFULL-CI (MVP-REAUTH-401, FE-EXPLAIN-ERR and GAUGE-ZERO-WIDTH have merged: #321, #314, #319); any edit to a `src/frontend/e2e/*.spec.ts` assertion listed in Appendix A; any edit to `src/frontend/package.json` outside these rows.

Queue rows: [queue.md, "Planned 2026-10-23, frontend revamp"](2026-10-15-build-program/queue.md#planned-2026-10-23-frontend-revamp). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. Path shorthand as in the queue: `fe/` = `src/frontend/src/`, `e2e/` = `src/frontend/e2e/`, `be/` = `src/backend/`.

**Sources.** The research package [docs/research/2026-10-23-frontend-revamp/](../research/2026-10-23-frontend-revamp/00-README.md): the owner's message and pasted guidelines, the framing note, the UI review and component audit of `main` @ `7749744`, four library research notes, and two independent designer proposals with prototypes ([proposal A](../research/2026-10-23-frontend-revamp/proposal-A.md), [proposal B](../research/2026-10-23-frontend-revamp/proposal-B.md), [comparison](../research/2026-10-23-frontend-revamp/comparison.md), [`proto-A.patch`](../research/2026-10-23-frontend-revamp/proto-A.patch), [`proto-B.patch`](../research/2026-10-23-frontend-revamp/proto-B.patch)). The owner's answers to prompt 44 (L0 AskUserQuestion; L0 evidence comment 6374428883 on PR #311) prompt 45 (L0 evidence comment 6374428087 on PR #311) and prompt 48 (L0 evidence comment 6380025171 on PR #311).

**MVP priority** (showcase 2026-10-31, same scale as the [MVP plan](2026-10-22-mvp-rows-plan.md)): **P0** = makes a safety, privacy or lab-value claim false on screen, or leaves a phone user unable to use the app; **P1** = visible on the demo path; **P2** = after the demo is fine. Owner answer UI-SCOPE-1031 ("Full plan, no freeze") means every row is queued now and starts when its own dependencies merge; P0/P1/P2 only orders the picks.

**Ask-first files (CLAUDE.md §1).** No `UI-*` row edits `modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, `core/auth.py` or any encryption file. No `UI-*` row edits any backend file. SAFETY-MODE-REAL is research only; whichever behaviour the owner picks gets its own build row with its own ask-first gate. The frontend screens that drive sign-in, recovery, backup and profile deletion are not ask-first files. Because they are auth and encryption flows (CLAUDE.md §1), their new layout, entrance motion and Lift moment were put to the owner, who answered **UI-AUTH-SCREENS "Layout, motion and Lift"** (prompt 48). Logic, requests, steps and warning text stay unchanged (HC-UISEC-002), and the recovery-code step stays still.

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

**Prompt 48 (L0 AskUserQuestion, 2026-10-24; L0 evidence comment 6380025171 on PR #311),** same format:

| Id | Answer | Option description (verbatim) |
|---|---|---|
| UI-ROUTE-MOTION | **"Whole-page fade"** | "Both prototypes' fade (opacity .35→1, ~200 ms) on every page, values included — an exception to 'stay still' for page changes only." |
| UI-AUTH-SCREENS | **"Layout, motion and Lift"** | "New layout; the create-profile form enters with S1; the unlock card lifts away on success; the recovery-code step stays still." |
| SESSION-LOCK-NOW | **"Add Lock now"** | "One menu item; nothing changes in the backend. Locking closes the profile on this device; the next action needs the password." |

UI-DEPS means: `framer-motion` stays at ^10.18, `motion` 14 is not adopted, and the other packages of [§5](#5-dependencies-and-bundle-budgets) are approved as listed; any other major comes back to the owner. The designers' proposals in the research package still describe `motion` 14 as they wrote it.

**L0 readings (L0's words, not the owner's), used by this plan:**
- UI-SAAS-MEANING: "Lab values and safety copy stay still" covers values, ranges, units, dates, disclaimers, citations and verification text. The one exception is one explanatory first reveal per analyte per session (the Range Ribbon draw), which is value-blind.
- UI-SCOPE-1031: the token remap and the shell land first and each page migrates completely inside its own row. Between merges `main` still mixes migrated and unmigrated pages, and an unmigrated page's layout shows the new global tokens and primitives: this is the accepted half-migrated risk the option text names, reduced by the order, not removed.
- UI-SAAS-MEANING with UI-ROUTE-MOTION, stillness: the one exception to "stay still" is the page change, which the owner answered ("Whole-page fade"): every route enters with M7, an **opacity-only** fade .35→1 in about 200 ms (never a transform on a route with T0 content), finished within 240 ms. Outside that window a T0 element never sits inside an animated wrapper: no re-animation after the fade settles, no M6 on lists of T0 items, no count-up, and showcase entrances (S1) wrap only non-T0 content. Gate G10's stillness probe enforces it on every component listed in [§2.7](#27-t0-marking-which-components-carry-data-t0-and-which-row-adds-it); during the fade window it allows only the route container's own opacity.
- UI-SAAS-MEANING, overlays (L0 reading, not the owner's words): an overlay that holds T0 content (a value, a range, a date, a citation, a disclaimer, consent or warning copy) opens and closes with **M0**: no opacity, scale or translate on its content. M3, M4, M5 and M11 stay for overlays without T0 content (the More sheet, menus, the settings section sheet, toasts that name no value). This is the reading closest to "Lab values and safety copy stay still": the alternative (probe after the overlay settles) would let values slide and fade in. UI-ROUTE-MOTION covers page changes only, so this overlay reading stands. The probe starts sampling at the opening interaction, so any overlay motion on a T0 node fails it.
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
| **T0 Data and safety** | lab values, ranges, units, dates, verification text, disclaimers, citations, the Safety Rail, consent and break-glass copy, error text, adherence figures (the ring renders final) | nothing after the route-enter fade settles, including no ancestor that fades or moves (G10). Owner exception (UI-ROUTE-MOTION): the page change itself, an opacity-only fade of the route container ≤ 240 ms (the Safety Rail is outside it and never fades). Exception: the Range Ribbon's one value-blind draw per analyte per session (M10, on the plot, not on its text). The Ink marker glyph is T3; the value beside it is T0 | count-ups, colour pulses, emphasis motion on out-of-range values, hover-only disclosure |
| **T1 Structure** | pages, cards, lists | enter only: M7 on every route, opacity only (owner UI-ROUTE-MOTION); M6 only on containers with no T0 descendant | exit animations on routes, `AnimatePresence mode="wait"` |
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
| `--dur-route` | 200 ms (must finish ≤ 240 ms) | route enter (M7) |
| `--dur-md` | 240 ms | nav indicator, list item |
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
| M3 | popover: opacity + `scale(.96→1)` from the Radix transform origin, 180 ms; exit 120 ms; only for popovers with no T0 content (others M0) | opacity only |
| M4 | dialog: opacity + `scale(.97→1)`, 320 ms; scrim 200 ms; exit 200 ms; only for dialogs with no T0 content (others M0; the scrim may still fade, it is not an ancestor of the content) | opacity 150 ms |
| M5 | sheet: `translateY(100%)→0` (phone) / `translateX` (desktop side), 320 ms drawer curve; only for sheets with no T0 content (others M0) | opacity 150 ms |
| M6 | list enter: opacity .35→1 + 6 px rise, 240 ms, stagger 40 ms cap 6, first view per session; never on a list of T0 items | opacity 120 ms, no stagger |
| M7 | route enter (owner UI-ROUTE-MOTION, "Whole-page fade"): the route container fades opacity .35→1 in 200 ms `--ease-out`, **no exit**, keyed by pathname, on **every** route; **no transform** (the 6 px rise is dropped because every authenticated route has T0 content: L0 reading, not the owner's words); finished within 240 ms; the shell, nav and Safety Rail do not fade | **instant (M0)**: under reduced motion the page appears at full opacity at once |
| M8 | state morph: label crossfade 180 ms ("Copy" → "Copied") | opacity only |
| M9 | indicator: one element moved by a CSS transition, 240 ms (nav pill, tab underline); jumps for keyboard | opacity 120 ms |
| M10 | draw: `clip-path: inset(0 100% 0 0)→inset(0)` 640 ms, points .6→1 at 40 ms intervals; once per analyte per session; value-blind | none (final frame) |
| M11 | toast: sonner transitions, swipe to dismiss; a toast that names a value or date (the verify confirmation) renders with M0 | sonner reduced (opacity) |
| M12 | progress: determinate `scaleX` 240 ms; indeterminate opacity breathing 1.6 s | breathing continues (loaders never freeze) |
| M13 | expand: `grid-template-rows 0fr→1fr` 240 ms + opacity | instant, opacity 120 ms |
| **S1** | choreographed entrance (wraps non-T0 groups only): groups rise 12 px + opacity 0→1, 480 ms ease-out, stagger 60 ms cap 8, first visit per session (sessionStorage, wrapped in try/catch) | opacity 150 ms, no stagger |
| **S2** | beam: a CSS conic-gradient stroke masked to the card border (`@property --beam-angle`), 2.4 s linear loop, colours from `--accent`, `--accent-ink`, `--band`; runs only while a real process runs (extraction), or as the single accent on the About page; fades out 240 ms when done | static 1 px `--accent` border plus the status text |
| **S3** | thinking orb: `thinking-orbs` `ThinkingOrb` (lazy), `theme="auto"` (follows `data-theme`), canvas `aria-hidden`, always beside a `role="status"` text such as "Reading page 2 of 3" | the library's static frame |
| **S4** | hero draw (About only): an SVG ribbon illustration over **labelled example data** ("Example data, not yours") drawn once by clip-path, 1.2 s | final frame |

Global rules: transform, opacity and clip-path only (plus M13's sanctioned `grid-template-rows`); `transition-all` banned; focus rings never transition; `MotionConfig reducedMotion="user"` (framer-motion 10.18.0 `dist/index.d.ts`:3583, prop :1658, values `"always" | "never" | "user"` :1632) plus per-recipe fallbacks replace the blanket `* { animation-duration: .01ms !important }` kill-switch (which also froze spinners); the repo's `useReducedMotion` hook reads `matchMedia` synchronously so the first render honours the preference (framer-motion's own `useReducedMotion`, :4636, returns `boolean | null`); nothing that plays during navigation uses framer-motion's `x`/`y`/`scale` shorthands (main-thread); no number ever tweens.

### 2.7 T0 marking: which components carry `data-t0`, and which row adds it

Every element in this table renders with `data-t0` so G10's `stillnessProbe` can find it and check that its text, colour, background, clip-path, filter, transform, rect and effective opacity do not change (§6). A route listed in the right column must show at least one `[data-t0]` node once its row has merged; the probe fails on zero.

| Component (T0 content) | Row that adds `data-t0` | Route(s) the probe expects it on |
|---|---|---|
| `SafetyRail`; `SafetyModeToggle` note and its popover text | UI-SHELL | every authenticated route |
| `StatusChip` (range and verification words) | UI-PRIM-FEEDBACK | wherever used |
| `RangeRibbon` text layer (axis labels, value labels, live caption), its table fallback cells; `RangeTick` text | UI-RIBBON | `/results` |
| `SourceTrace` (excerpt lines, result, date, range, read-confidence rows); `CitationTooltip` (chip label, quote, page) | UI-PROVENANCE | `/results`, `/verify`, `/explain` |
| palette Results group (latest value text) | UI-PALETTE | palette open |
| `DisclaimerBanner`, hero value, unit and date, analyte list values, `InterpretedResultCard` body, `PanelInterpretationDashboard` values, `AdviceSection` | UI-PG-RESULTS | `/results` |
| document row date, status words, confidence words; FE-IMPORT-ERROR's alert; IMPORT-SCANNED-PAGE's warning; the "N values ready to review" handoff | UI-PG-DOCUMENTS | `/inbox` |
| `EntityDetailView` value, unit, range and date cells; Edit dialog current value | UI-PG-REVIEW | `/verify` |
| assistant answer bubbles, citation chips, the Ask disclaimer, chat error text | UI-PG-ASK | `/explain` |
| dose, schedule times, adherence figures and ring, reminder times | UI-PG-MEDS | `/medications`, `/medications/:id`, `/medications?tab=reminders` |
| follow-up dates | UI-PG-CARE | `/care-tasks` |
| timeline card dates and analytes, search result values, pinned values | UI-PG-RECORDS | `/timeline`, `/search`, `/pinboards` |
| summary preview values, redaction-level text | UI-PG-EXPORT | `/export` |
| break-glass warning, consent copy, tier availability text | UI-PG-SETTINGS | `/settings?section=assistant-privacy`, `/settings?section=advanced` |
| recovery code, its warnings, backup/restore/delete warnings and errors | UI-PG-SECURITY | `/settings` (Profile & security) |
| create-profile field errors, recovery-code step, unlock errors | UI-PG-AUTH | `/setup`, `/recover` |
| Overview counts and values | UI-OVERVIEW | `/overview` |
| About safety and local-first statements | UI-ABOUT | `/about` |

The stillness guarantee covers **pages whose row has merged**. A page whose row has not merged yet carries no `data-t0` and cannot be probed by G10; it gets the same opacity-only route fade as every page (UI-SHELL's HC-UISH-003 checks the route container on every route), but in-page motion the old page already has (for example `DocumentInbox`'s stagger) stays until that page's row removes it.

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

Owned by the existing row **SESSION-REENTRY** (owner answer (a), [MVP plan](2026-10-22-mvp-rows-plan.md#session-reentry--after-60-minutes-or-a-restart-only-the-recovery-code-gets-a-patient-back-in)): Task 1 puts the unlock card on `/setup` (ready, P0); Task 2 is gated by SESSION-AUTH-DIFF. This plan adds no unlock row. It restyles the unlock card and adds the Lift moment in UI-PG-AUTH (owner UI-AUTH-SCREENS "Layout, motion and Lift"), and adds **Task 3** ("Lock now" in the profile menu; owner SESSION-LOCK-NOW "Add Lock now") as a delta to that row ([§8.2](#82-delta-to-session-reentry-task-3-lock-now)). The idle-lock warning toast both designers proposed needs `auto_lock_timeout_minutes`, which has no reader (bullet AUTO-LOCK-UNUSED, ask-first auth, not planned here).

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
| **Ink** | the user verifies a value (Review values or Source Trace) | the dashed graphite ring closes and fills with ink, 360 ms ease-out, on the marker only; the value text never moves; every chart, row and chip for that value flips together; a toast confirms ("Glucose, Apr 10, 2026 is now marked as checked"), with M0 because it names a value and a date, and with **no Undo**: the API has no unverify endpoint (`be/api/observations.py:384` is verify only; bullet VERIFY-UNDO) | T3 | instant swap, toast still shows |
| **Source Trace** | "Show source" on any value, or "Open source" in a citation popover | side sheet (desktop) / bottom sheet (phone) that opens with **M0** (it holds T0 content); the moment is the highlight behind the source row, a separate background element without `data-t0`, which draws across the line (clip-path 420 ms, 160 ms delay, once) while the text stays still | T3 | highlight fades in 150 ms |
| **Lift** (in UI-PG-AUTH; owner UI-AUTH-SCREENS) | successful unlock on the SESSION-REENTRY card | the unlock panel fades and lifts 8 px, 240 ms, onto the shell already painted with skeletons | T3 | opacity 150 ms |

Refused: confetti or celebration on verify or adherence (the `BadgeToast` `animate-ping` goes), count-up numbers, motion on out-of-range values, a bounce anywhere near a value, 3D, sound.

### 4.2 Showcase surfaces (UI-SAAS-MEANING)

| Surface | Row | What moves | What stays still |
|---|---|---|---|
| First-run onboarding: **Overview** checklist (Import → Review values → See results) | UI-OVERVIEW | S1 entrance of the checklist cards; the next step is marked in words ("Next step") with a static accent border (S2 marks a running process only, so it is not used here) | the counts and any value shown later ("3 values waiting for review" is T0 text) |
| First-run onboarding: the **create-profile form** (L0 reading) | UI-PG-AUTH (owner UI-AUTH-SCREENS "Layout, motion and Lift") | S1 entrance of the label-and-input groups; no fake progress | field errors (rendered in a container outside the S1 wrapper), the recovery-code step (no S1 at all), the code, the acknowledgement checkbox, every warning |
| **Document import/processing** | UI-PG-DOCUMENTS | S2 beam on the border of the card of a document being extracted (the border element only); S3 orb (20 px) beside the status line "Reading page 2 of 3" | document rows (they show dates, status and confidence, so new rows appear with M0, no M6), extracted values, confidence words, error messages (FE-IMPORT-ERROR's alert), the scanned-page warning (IMPORT-SCANNED-PAGE), the handoff text |
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
| G10 | stillness: `stillnessProbe(page, { trigger, expected })` runs `trigger` and samples every 16-40 ms. **Window:** 800 ms from the trigger; on the first visit to a lazy route it is extended until network idle, then 800 ms more. **Per `[data-t0]` node, from the first sample in which it exists:** `textContent`, computed `color`, `background-color`, `clip-path`, `filter` and `transform` stay constant, and `getBoundingClientRect()` stays constant (±0.5 px); this catches a count-up even at fixed width (tabular-nums), a colour pulse, a clip-path or filter reveal and any translate. **Effective opacity** (the product of its own and every ancestor's computed opacity) must be 1, with one exception: when `trigger` is a **navigation**, during the route-fade window each T0 node's effective opacity must equal the route container's own computed opacity (no nested fade). The route container is the element marked `data-route-container`, keyed by pathname; the **240 ms clock starts at the first sample in which the new keyed container exists**, and the probe fails if that container has any transform, or has not reached opacity 1 within 240 ms, or changes opacity again after reaching 1 (UI-ROUTE-MOTION's exception, and only it). For an **interaction** (including opening an overlay) there is no fade window. The probe **fails** when it finds zero `[data-t0]` nodes, or when any selector in `expected` (the route's components from [§2.7](#27-t0-marking-which-components-carry-data-t0-and-which-row-adds-it)) matches no `[data-t0]` node | `stillnessProbe()` |

Frontend e2e uses `page.route` mocks typed from `fe/services/types.ts` (`e2e/support/mockApi.ts`). Anything that asserts auth, session or status-code behaviour runs against the real backend through HTTP (`e2e/support/start-backend.mjs`), as CLAUDE.md §4 requires. Existing tests may have selectors or labels updated when markup changes; no assertion is removed or loosened (CLAUDE.md §3). Every e2e assertion a row changes is listed, old value → new value, in [Appendix A](#appendix-a-e2e-assertions-and-the-row-that-changes-each) and in that row's Files; CI runs every spec (`ci.yml` e2e job), so an unlisted break is a failed row. Before claiming done, each row re-reads [recurring-failures.md](../agentic/recurring-failures.md); #1 (a test that could not fail) is why every new check below names its RED state, and #12 (a gate merged beside PRs built before it) is why L0 runs UI-BUDGET's check and UI-TOKENS' contrast test on `origin/main` before merging the next group.

**Defect checks** (found in the prototypes; details in [comparison §3](../research/2026-10-23-frontend-revamp/comparison.md#3-defects-found-in-the-prototypes-become-acceptance-checks)):

| Id | Check | Row |
|---|---|---|
| DF-1 | Safety Rail opaque: computed background alpha 1, no `backdrop-filter`; after scrolling `main` to the bottom, `elementFromPoint` at 5 points across the rail returns the rail or a descendant (light and dark, 1440 and 390) | UI-SHELL (HC-UISH-005) |
| DF-2 | Source Trace: every source line wraps (`scrollWidth <= clientWidth` per line element) at 1440 and 390 | UI-PROVENANCE (HC-UIPV-004) |
| DF-3 | opening a Sheet or Dialog leaves no `[data-sonner-toast]` intersecting the overlay content; the toast layer is below the modal layer | UI-PRIM-FEEDBACK (HC-UIFB-004), UI-SHELL (HC-UISH-007) |
| DF-4 | at 390×844, first paint, ≥ 200 px of the Range Ribbon plot is inside the viewport above the tab bar and the Safety Rail | UI-PG-RESULTS (HC-UIRES-004) |
| DF-5 | after typing in the palette, every `aria-activedescendant` resolves to an existing element; axe on the open, filtered palette 0 serious/critical | UI-PALETTE (HC-UIPAL-002, 003) |
| DF-6 | route container opacity sampled every 40 ms after a nav click never drops below 0.3 (the owner's route fade starts at 0.35, opacity only) | UI-SHELL (HC-UISH-003) |

---

## 7. Rows

**Ordering rule (UI-SCOPE-1031, L0 reading).** Waves are dependency layers (queue rule 3): every row is queued now and starts when its own dependencies have merged. Foundation (tokens, motion, theme) and primitives restyle every page at once; the shell then wraps every page; each page row then migrates one page completely (layout, primitives, overlays, empty state, dark-safe colours, its own tests). The aim is that each page is either in its old layout with the new tokens and primitives, or fully migrated. This is not a guarantee: between merges `main` mixes migrated and unmigrated pages, and an unmigrated page shows the new primitives inside its old layout. That is the half-migrated risk the owner accepted with "Full plan, no freeze".

**File ownership rules.** `src/frontend/package.json` and `package-lock.json`: UI-MOTION, UI-BUDGET (scripts line), UI-CHART-CLEANUP only, never beside AXE-E2E or another `package.json` PR. `fe/App.tsx`: UI-ROUTES, UI-PG-RESULTS, UI-OVERVIEW, UI-ABOUT, in different waves. `fe/components/ui/index.ts`: UI-PRIM-CONTROLS only (other primitives are imported by path). `fe/components/layout/navConfig.ts`: UI-SHELL, UI-PG-RESULTS, UI-OVERVIEW, UI-MICRO, in different waves. Every `src/frontend/e2e/*.spec.ts` assertion a row breaks is a declared contract change in that row (old value → new value, same assertion kept), listed in [Appendix A](#appendix-a-e2e-assertions-and-the-row-that-changes-each). Spec files are edited by at most one row per wave: `tailwind4-styles.spec.ts` (owner row TW4-VISUAL, `owner-decisions-2026-09-27.md:73`) by UI-TOKENS (w1), UI-SHELL (w3), UI-PG-MEDS (w5), UI-PG-AUTH (w6); `routing.spec.ts` by UI-SHELL (w3), UI-PG-RESULTS (w5), UI-OVERVIEW (w6); `assistant.spec.ts` by UI-PG-ASK (w5), UI-MICRO (w8); `ui-full-verification.spec.ts` by UI-PG-ASK (w5), UI-PG-SETTINGS (w6), UI-MICRO (w8); `settings-smoke.spec.ts` by UI-PG-SETTINGS; `auth.spec.ts` by UI-PG-AUTH. Page rows keep their page's h1 text and UI-MICRO renames the h1s to their nav names, so a heading assertion changes once. `fe/__tests__/Gamification.test.tsx`: UI-PG-MEDS, then UI-PG-SETTINGS (which therefore runs after it). `fe/__tests__/RecoveryCodeCard.test.tsx` (it tests the settings card): UI-PG-SECURITY. New tests go in new files named after the row, so two rows rarely share a test file.

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
| 3 | [UI-SHELL](#ui-shell--responsive-shell-grouped-nav-tab-bar-safety-rail-honest-toggle) | UI-PRIM-*, UI-THEME, E2E-UIFULL-CI, [GATES-NAV-BOUND](#gates-nav-bound--navigation-stillness-probes-allow-70-ms-sampling-gaps) | UI-SAFETY-TOGGLE, UI-ROUTE-MOTION, STILLNESS-NAV-70 answered | **P0** | 5 |
| 3 | [UI-BUDGET](#ui-budget--a-ci-bundle-budget-that-can-fail) | UI-MOTION, UI-ROUTES; never beside CI-CACHE | owner merges (CI file) | P1 | 1.5 |
| 4 | [UI-PALETTE](#ui-palette--the-lazy-command-palette-with-the-df-5-fix) | UI-SHELL, UI-BUDGET | — | P1 | 3 |
| 4 | [UI-RIBBON](#ui-ribbon--the-range-ribbon-and-range-tick-components) | UI-TOKENS, UI-MOTION | — | P1 | 4 |
| 4 | [UI-PROVENANCE](#ui-provenance--source-trace-sheet-and-citation-popover) | UI-PRIM-OVERLAYS, UI-PRIM-FEEDBACK | — | P1 | 3 |
| 4 | [UI-SHOWCASE-KIT](#ui-showcase-kit--beam-orb-entrance-and-the-empty-state) | UI-MOTION, UI-PRIM-CONTROLS | UI-SAAS-MEANING answered | P1 | 3 |
| 4 | [SESSION-REENTRY Task 3](#82-delta-to-session-reentry-task-3-lock-now) | UI-SHELL; SESSION-REENTRY Task 1 (merged, #312) | SESSION-LOCK-NOW answered "Add Lock now" | P2 | 1 |
| 5 | [UI-PG-RESULTS](#ui-pg-results--results-merges-trends-and-interpret-around-the-range-ribbon) | wave 4 rows, UI-BUDGET; GAUGE-ZERO-WIDTH (merged, #319) | — | P1 | 5 |
| 5 | [UI-PG-DOCUMENTS](#ui-pg-documents--documents-page-and-the-import-and-processing-showcase) | UI-SHELL, UI-SHOWCASE-KIT, UI-PROVENANCE, FE-IMPORT-ERROR; never beside IMPORT-SCANNED-PAGE | — | P1 | 4 |
| 5 | [UI-PG-REVIEW](#ui-pg-review--review-values-with-ink) | UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT, FE-VERIFY-NUMERIC | — | P1 | 4 |
| 5 | [UI-PG-ASK](#ui-pg-ask--ask-the-chat-owns-its-scroll-citations-open-on-tap) | UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT, FE-EXPLAIN-ERR (merged, #314), BADGE-TICK | — | P1 | 4 |
| 5 | [UI-PG-MEDS](#ui-pg-meds--medications-reminders-tab-dose-sheet) | UI-SHELL, UI-SHOWCASE-KIT | MED-BADGES (open, non-blocking) | P2 | 4 |
| 5 | [UI-PG-CARE](#ui-pg-care--follow-ups) | UI-SHELL, UI-SHOWCASE-KIT | — | P2 | 2 |
| 5 | [UI-PG-RECORDS](#ui-pg-records--timeline-search-pinboards) | UI-SHELL, UI-SHOWCASE-KIT, UI-PALETTE | — | P2 | 3 |
| 5 | [UI-PG-EXPORT](#ui-pg-export--doctor-summary) | UI-SHELL, UI-SHOWCASE-KIT | — | P2 | 2.5 |
| 6 | [UI-PG-SETTINGS](#ui-pg-settings--settings-split-into-sections) | UI-PG-MEDS (`Gamification.test.tsx`), UI-PG-ASK (`ui-full-verification.spec.ts`), UI-SHELL, UI-SHOWCASE-KIT; never beside DON-COPY-V3 | — | P2 | 5 |
| 6 | [UI-CHART-CLEANUP](#ui-chart-cleanup--delete-the-recharts-chart-and-the-dependency) | UI-PG-RESULTS | — | P2 | 1.5 |
| 6 | [UI-OVERVIEW](#ui-overview--overview-landing-with-the-first-run-checklist) | UI-PG-RESULTS (App.tsx, `routing.spec.ts`), UI-PG-DOCUMENTS | — | P1 | 3 |
| 6 | [UI-PG-AUTH](#ui-pg-auth--setup-unlock-card-and-recovery) | SESSION-REENTRY Task 1 (merged, #312), UI-PG-MEDS (`tailwind4-styles.spec.ts`), UI-SHOWCASE-KIT, UI-SHELL | UI-AUTH-SCREENS answered "Layout, motion and Lift" | P1 | 3 |
| 7 | [UI-PG-SECURITY](#ui-pg-security--profile--security-section) | UI-PG-SETTINGS; MVP-REAUTH-401 (merged, #321) | UI-AUTH-SCREENS answered "Layout, motion and Lift" | P2 | 3 |
| 7 | [UI-ABOUT](#ui-about--the-about-page-for-the-demo) | UI-OVERVIEW (App.tsx), UI-RIBBON, UI-SHOWCASE-KIT | UI-ABOUT-PLACE (open, non-blocking) | P1 | 3 |
| 8 | [UI-MICRO](#ui-micro--press-target-and-copy-sweep) | every wave 5-7 row | — | P2 | 3 |
| 9 | [UI-DARK-FLIP](#ui-dark-flip--dark-mode-follows-the-os-once-no-unmigrated-colour-remains) | every `UI-*` row above  | UI-DARK-MODE answered | P2 | 2 |

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
| HC-UIG-006 | `stillnessProbe` self-test on `page.setContent` fixtures whose animations **start inside the sampling window**: each fixture exposes `window.__start()`, which the probe's `trigger` calls after the first sample, and one fixture runs an infinite animation instead. It must FAIL on (a) a `[data-t0]` child of a container that fades from opacity .35, (b) one inside a parent that translates 6 px, (c) a `[data-t0]` popover that scales in from .96 (the overlay rule), (d) a page with zero `[data-t0]` nodes when `expected` is non-empty, and (e) a page where one `expected` selector matches nothing, (f) a navigation whose route container translates during the fade, (g) a route fade that takes longer than 240 ms, (h) a `[data-t0]` node that re-fades after the route fade settled, (i) a count-up at fixed width (`tabular-nums`, the text changes but the rect does not), (j) a colour pulse on a `[data-t0]` node, (k) a `clip-path` reveal of a `[data-t0]` node, (l) a nested 150 ms translate of a `[data-t0]` node inside the route-fade window; it must PASS on a still `[data-t0]` node beside an animated non-T0 sibling, and on a navigation with a 200 ms opacity-only route fade followed by stillness | GREEN (self-test that the probe can fail) |

**Acceptance:** the six ids with output; the harness runs with the mock API and no backend; the README lists every helper and when to use the real backend. **Est:** 3 h. **MVP:** P1.

#### GATES-SAMPLE-TIME — time each stillness sample when it is read

**Kind:** PRODUCT (e2e harness). **Files:** `e2e/support/gates.ts` (`startSampler` only), `e2e/ui-gates-sampler.spec.ts` (new), `e2e/README.md` (one line). **Depends on:** UI-GATES (done, #350). **Gate:** none.

**Why.** `snapshot()` in `startSampler` reads every `[data-t0]` node's computed style and rect, then stamps the sample with `performance.now()` on its last line. All of a tick's reads see one DOM state (no task runs inside the tick), and that state is the one at the tick's first read. Stamping at the end adds the tick's own style and layout work to the gap before it, so the gap equals the interval plus that work. On #370, L0 measured this on the same production build (`vite preview`, 2026-10-25): page navigations timed with a bare 20 ms `setInterval` showed gaps of 20-30 ms on main and on the branch, apart from `/settings` on the branch (47-48 ms), while the probe reported 41-61 ms. With the stamp moved to the start of `snapshot()`, HC-UIG-006 still passed every case, including (n), a 150 ms block that must fail (the probe reported 154 ms), and most route gaps fell under 40 ms. The gaps that stayed above it (46-93 ms, including `/settings` and the toggle popover) are real work and stay failures.

**Change.** Read `t` at the start of `snapshot()`. Nothing else changes: the 40 ms bound (`STILLNESS_MAX_GAP_MS`), the 20 ms interval, the 800 ms window, the lazy-route rule and `samplingCheck` stay as they are.

| Id | Check | RED today? |
|---|---|---|
| HC-UIG-007 | a `page.setContent` fixture whose page wraps `Element.prototype.getBoundingClientRect` so that one post-trigger call busy-waits 30 ms (nothing else runs long): the probe passes, with `maxGapMs` at most 40. A second fixture busy-waits 60 ms in one call: the probe fails with a sampling gap above 40 ms | yes (stamped at the end, the first fixture's gap is the 20 ms interval plus the 30 ms wait) |

**Acceptance:** HC-UIG-007 RED then GREEN; HC-UIG-001…006 green and unchanged (`git diff origin/main...HEAD -- e2e/ui-gates.spec.ts` is empty); the e2e README says when a sample is timed. **Est:** 1 h. **MVP:** P1 (UI-SHELL's final stillness run waits on it).

**Done 2026-10-25** (#374, `e099a7c`; RED 51 ms, GREEN 30 ms on HC-UIG-007 (a)). As built, the HC-UIG-007 fixtures are served with a fulfilled `page.route` plus `goto` (the `serveFixture` pattern of `ui-gates.spec.ts`), not `page.setContent`; they behave the same here (#374 review MINOR 3, no code change). The other two MINORs are row [GATES-SAMPLE-TIME-MINORS](#gates-sample-time-minors--the-374-review-minors).

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

**Files:** `fe/styles/globals.css` (the [§2.2](#22-colour-tokens-and-contrast-proposal-a) tokens, light and dark; aliases for `status-success`, `status-danger`, `muted-foreground`; type scale with body 17 px and the 13 px floor; motion tokens; `--z-toast`/`--z-modal`; font fallback metric overrides; the global focus ring stays the box-shadow ring of `*:focus-visible` (`globals.css:288-290`) in the accent token, so TW4-FOCUS and TW4-INBOX's outline check keep passing; the blanket reduced-motion kill-switch replaced by `--motion-distance: 0` plus per-recipe rules, so loaders keep breathing; unused `glass-card`, `subtle-noise`, `stagger-animation`, `animation-delay-*` and the six dead `dark-*` tokens deleted), `fe/components/ui/Card.tsx` (`bg-white/80 backdrop-blur-xl` → `bg-surface-elevated`, nothing else), `fe/__tests__/ui-tokens.test.ts` (new), `e2e/ui-tokens.spec.ts` (new), `e2e/ui-gates.spec.ts` (remove the `test.fail()` mark on HC-UIG-002 only), `e2e/tailwind4-styles.spec.ts` (declared contract changes under owner row TW4-VISUAL, same assertions with the new token values: `:138` border `rgb(229, 231, 235)` → `rgb(226, 223, 215)` (`--line`), `:140` placeholder `rgb(156, 163, 175)` → `rgb(104, 100, 93)` (`--ink-3`, `globals.css:150-151`), `:178` body `rgb(250, 250, 248)` → `rgb(246, 245, 241)` (`--paper`), `:181` `aside h1` colour `rgb(31, 31, 31)` → `rgb(28, 27, 25)` (`--ink-1`); Appendix A).
**Depends on:** UI-GATES. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UITK-001 | the test parses `globals.css` and asserts every pair in the §2.2 table, light and dark: text ≥ 4.5:1, non-text ≥ 3:1 | yes (ink-tertiary 2.69) |
| HC-UITK-002 | every colour utility used in `fe/**/*.tsx` resolves to a defined token (`status-success`, `status-danger`, `muted-foreground` included) | yes (21 undefined uses) |
| HC-UITK-003 | `--text-xs` ≥ 13 px and the body size is 17 px | yes |
| HC-UITK-004 | e2e: axe `color-contrast` = 0 on `/setup`, `/inbox`, `/verify`, `/trends`, `/explain`, `/settings` (light) | yes (314 nodes on 29 states) |
| HC-UITK-005 | e2e: TW4-FOCUS and TW4-INBOX's focus checks pass unchanged (the global ring stays a box-shadow ring) | GREEN (pin) |
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
| HC-UIPC-007 | e2e: a focus ring is visible 16 ms after Tab on a Button (no 200 ms fade from `transition-all`) | yes (200 ms fade) |

**Acceptance:** G on `/setup` and `/settings` (the pages that use these most). **Est:** 3 h. **MVP:** P1.

#### UI-PRIM-OVERLAYS — Dialog, AlertDialog, Sheet, Popover

**Files:** `fe/components/ui/Dialog.tsx`, `ui/AlertDialog.tsx` (Dialog with `role="alertdialog"`), `ui/Sheet.tsx` (bottom on phones, side on desktop, M5), `ui/Popover.tsx` (M3; opens on click, Enter and Space, never on hover alone), all new, each with a `still` prop that renders M0 for overlays holding T0 content; `fe/__tests__/ui-overlays.test.tsx` (new). **Depends on:** UI-TOKENS, UI-MOTION. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIOV-001 | Escape closes each overlay and focus returns to the trigger | yes (0 Escape handlers today) |
| HC-UIOV-002 | focus stays inside an open Dialog or Sheet over 25 Tab presses | yes |
| HC-UIOV-003 | `aria-modal="true"`; an overlay without a title fails the test (Radix's missing-title warning is turned into a test failure) | yes |
| HC-UIOV-004 | under reduced motion, content has opacity only, no transform | yes |
| HC-UIOV-005 | Popover opens on click and on Enter, not on hover | yes |
| HC-UIOV-006 | opening any Dialog, AlertDialog or Sheet dispatches the `asclexis:overlay-open` document event that UI-PRIM-FEEDBACK's toaster listens for (DF-3) | yes |
| HC-UIOV-007 | e2e: each primitive with `still` passes `stillnessProbe` on a `[data-t0]` child from the opening click (no opacity, scale or translate on the content) | yes |

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
| HC-UIFB-006 | `notify({ still: true })` (for toasts that name a value or date) renders with no enter transform or opacity change: its `[data-t0]` text passes `stillnessProbe` from the triggering click; `StatusChip` carries `data-t0` | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1. (The event name is fixed here and in UI-PRIM-OVERLAYS so the two rows stay file-disjoint; UI-SHELL proves the pair with HC-UISH-007.)

### 7.5 Wave 3: shell and budget

#### UI-SHELL — responsive shell, grouped nav, tab bar, Safety Rail, honest toggle

**Files:** `fe/components/layout/AppLayout.tsx` (grid shell; `AnimatePresence mode="wait"` removed; route enter M7 (opacity-only fade, owner UI-ROUTE-MOTION) on the route container, marked `data-route-container` and keyed by pathname; skip link; mounts `AppToaster`; bottom padding for tab bar and rail), `Sidebar.tsx` (groups, prefix match, M9 CSS indicator replacing the `layoutId` spring, brand as `<span>`), `TopBar.tsx` (the existing search form restyled, `SafetyModeToggle`, profile menu on phones), `MobileTabBar.tsx`, `MoreSheet.tsx`, `SafetyRail.tsx`, `SafetyModeToggle.tsx`, `ProfileMenu.tsx`, `BrandMark.tsx`, `navConfig.ts` (all new), `layout/index.ts`; `fe/__tests__/ui-shell.test.tsx` (new), `e2e/ui-shell.spec.ts` (new), `e2e/routing.spec.ts` (`:46` nav link name `'Trends'` → `'Results'`; it still lands on `/trends` until UI-PG-RESULTS), `e2e/ui-routes-verification.spec.ts` (nav labels only; file from E2E-UIFULL-CI), `e2e/ui-gates.spec.ts` (remove the `test.fail()` mark on HC-UIG-003 only), `e2e/tailwind4-styles.spec.ts` (TW4-INBOX `:180` selector `aside h1` → `aside [data-brand]`, the brand `<span>`; the colour value set by UI-TOKENS is unchanged). Kept as they are (Appendix A): the nav landmark name "Main navigation", nav links at `min-height: 44px`, and the top-bar profile trigger's accessible name "Profile and settings" with `cursor: pointer`.
**Route motion (owner UI-ROUTE-MOTION, "Whole-page fade"):** M7 on every route: the route container fades opacity .35→1 in 200 ms, finished within 240 ms, with **no transform**, because every authenticated route paints T0 content on first paint (`/inbox` dates and statuses; `/verify` values; `/trends`, `/interpret` and later `/results` values; `/timeline` dates; `/pinboards` pinned values; `/explain` the disclaimer and answers; `/medications`, `/medications/:id` and `/notifications` doses and times; `/care-tasks` dates; `/export` summary values; `/search` values; `/settings` warnings and consent copy). The shell, the nav and the Safety Rail sit outside the route container and do not fade. Under reduced motion the route change is **instant** (M0). Nothing re-animates after the fade.
**Depends on:** UI-PRIM-CONTROLS, UI-PRIM-OVERLAYS, UI-PRIM-FEEDBACK, UI-THEME merged; E2E-UIFULL-CI merged (its spec is edited); [GATES-NAV-BOUND](#gates-nav-bound--navigation-stillness-probes-allow-70-ms-sampling-gaps) merged (owner STILLNESS-NAV-70, 2026-10-28: "Raise it to 70 ms for page changes and keep diagnosing"); then UI-SHELL adds `test.describe.configure({ retries: 0 })` as the first line of every describe in `e2e/ui-shell.spec.ts` that holds an HC-UISH-009 test (on #370 `2148b54e`: `:292` "HC-UISH-003 route fade and HC-UISH-009 rail stillness", which pins HC-UISH-003 too; `:335` "HC-UISH-009 phone toggle label stays still"; and `:851` "Inherited stillness and focus halves", or the `:870` test moved into its own describe); the global `retries` and `ci.yml` are unchanged; the diagnosis [STILLNESS-NAV-LATE](#stillness-nav-late--find-and-fix-why-page-changes-run-late-under-the-stillness-probe) does not block it. **Gate:** UI-SAFETY-TOGGLE and UI-ROUTE-MOTION ("Whole-page fade") answered; STILLNESS-GAP-BOUND and STILLNESS-NAV-70 answered; the toggle wording of [§3.6](#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real) ships now and SAFETY-LABEL-WORDING (open, non-blocking) may change it in a one-line follow-up.

| Id | Check | RED today? |
|---|---|---|
| HC-UISH-001 | vitest: `navConfig` has the [§3.1](#31-destinations) groups and transition entries; `/medications/abc` marks Medications active | yes |
| HC-UISH-002 | e2e: the first Tab focuses the skip link; exactly one `h1` on each of the 15 routes | yes (2 h1s, no skip link) |
| HC-UISH-003 | e2e (DF-6, UI-ROUTE-MOTION) on every route: after a nav click, sampled every 16 ms, the `[data-route-container]`'s transform is `none` in every sample, its opacity is ≥ 0.35 in every sample and reaches 1 within 240 ms of the first sample in which the new keyed container exists, and stays 1 for the rest of the 800 ms window (extended to network idle on a lazy route's first visit); under `reducedMotion: 'reduce'` its opacity is 1 in every sample | yes (0.00 and a transform today) |
| HC-UISH-004 | e2e: at 390 and 320 no sidebar is rendered, `main` starts at x = 0 with the viewport's width, the tab bar shows 5 tabs each ≥ 44 px | yes (`pl-64`) |
| HC-UISH-005 | e2e (DF-1): the Safety Rail is opaque and on top (see §6), light and dark, 1440 and 390; it is in the viewport on every route | yes (no rail) |
| HC-UISH-006 | e2e: the texts "Safety Mode", "ON" and "OFF" are absent from the top bar; the switch is `aria-disabled="true"` with an accessible description containing "standard safety checks always run"; clicking it changes no DOM state outside its popover | yes (placebo toggle) |
| HC-UISH-007 | e2e (DF-3): with a toast visible, opening the More sheet leaves no toast intersecting the sheet | yes |
| HC-UISH-008 | e2e: More sheet: Escape closes, focus returns to the More tab, every destination is reachable from it | yes |
| HC-UISH-009 | e2e: on every authenticated route the Safety Rail keeps opacity 1 and a fixed rect through a nav click, including during the route fade (it is outside the route container); `stillnessProbe` with `expected: ['SafetyRail']` passes; the safety-toggle popover (T0 copy) opens with M0 | yes |

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
| HC-UIPAL-005 | the Results group's latest-value text carries `data-t0` and passes `stillnessProbe` from the Ctrl+K press | yes |

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

**Files:** `fe/components/results/SourceTrace.tsx` (new; the sheet: source file and row or page, the excerpt lines with the matching line highlighted, collected date, range, read confidence in words, "This is what your report states.", and for an unchecked value "It matches, mark as checked" using the existing `useVerifyObservation` (`fe/services/observations.ts:82`) plus "Correct it in Review values"), `fe/components/lab-interpreter/CitationTooltip.tsx` (rewritten on `Popover` with `still` (M0, it holds a quote), same props, so every caller upgrades at once: opens on tap, click and Enter, 44 px trigger, quote plus page plus "Open source"), `fe/components/PageImageOverlay.tsx` (image fades in on decode; the bbox highlight uses the trace mark), `fe/__tests__/ui-provenance.test.tsx` (new), `fe/__tests__/PageImageOverlay.test.tsx` (selectors only), `e2e/ui-provenance.spec.ts` (new). **Depends on:** UI-PRIM-OVERLAYS, UI-PRIM-FEEDBACK. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIPV-001 | the citation popover opens on click and Enter, not on hover alone; Escape closes and focus returns | yes (hover/focus tooltip) |
| HC-UIPV-002 | e2e in a `hasTouch` context: a tap opens it | yes |
| HC-UIPV-003 | Source Trace shows the source row highlighted, page, date and the "This is what your report states." line | yes |
| HC-UIPV-004 | (DF-2) every excerpt line wraps at 1440 and 390 | yes in proposal A's prototype |
| HC-UIPV-005 | "It matches, mark as checked" sends exactly one `POST /observations/{id}/verify` (mocked HTTP) and shows the confirmation toast; no Undo is offered (no unverify endpoint) | yes |
| HC-UIPV-006 | Source Trace (sheet, `still`), the citation popover and the verify toast: every `[data-t0]` node in them passes `stillnessProbe` from the opening click; the source-row highlight (no `data-t0`) is the only thing that moves | yes |

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

**Files:** `fe/pages/ResultsPage.tsx` (new), `fe/pages/TrendsDashboard.tsx` (delete), `fe/pages/LabInterpreter.tsx` (delete; folded in), `fe/pages/index.ts`, `fe/App.tsx` (`/results`; `/trends` and `/interpret` redirect), `fe/components/layout/navConfig.ts` (Results → `/results`; Interpret entry removed), `fe/components/lab-interpreter/InterpretedResultCard.tsx`, `PanelInterpretationDashboard.tsx`, `AdviceSection.tsx` ("Questions you could ask your clinician"), `DisclaimerBanner.tsx` (`role="note"`, never animated), `ReferenceRangeComparison.tsx` (renders `RangeTick`), `fe/__tests__/TrendsDashboard.test.tsx` and `LabInterpreter.test.tsx` (ported to `ResultsPage` as `fe/__tests__/ResultsPage.test.tsx`; every assertion kept), `InterpretedResultCard.test.tsx` (selectors only), `fe/__tests__/ui-results.test.tsx` (new), `e2e/ui-results.spec.ts` (new), `e2e/routing.spec.ts` (`:47` URL `/\/trends$/` → `/\/results$/` and `:48` heading `'Trends Dashboard'` → `'Results'`, Appendix A), `fe/__tests__/ReferenceRangeComparison.test.tsx` (HC-GZW-001…003 from #319 kept green against `RangeTick`; selectors only).
**Depends on:** UI-RIBBON, UI-PROVENANCE, UI-SHOWCASE-KIT, UI-SHELL, UI-BUDGET; GAUGE-ZERO-WIDTH merged (#319): its HC-GZW-001…003 stay green. **Gate:** none.
**Motion:** the route enter is the shared opacity-only fade (owner UI-ROUTE-MOTION); after it settles nothing on the page moves except the Ribbon's first reveal on the plot; the analyte list has no M6. **Layout:** proposal A's (chart card with the analyte list beside it on desktop; on phones a compact header, the analyte chip scroller as a labelled focusable region, then the chart). Panel tabs filter the list (fixes "CBC" showing Glucose). The dead "Last 12 Months" and "Filters" become one real range select or are deleted. "Explain this result" shows the interpretation card with its DisclaimerBanner and citations. PNG/SVG export kept.

| Id | Check | RED today? |
|---|---|---|
| HC-UIRES-001 | `/trends` and `/interpret` redirect to `/results`, keeping `?analyte=` | yes |
| HC-UIRES-002 | selecting the CBC panel lists only CBC analytes | yes (shows Glucose) |
| HC-UIRES-003 | the contextual disclaimer, the Safety Rail and every value on the page are in the DOM at first paint and pass `stillnessProbe` from the moment the opacity-only route fade settles (≤ 240 ms; effective opacity 1 and a fixed rect after that) | yes (no disclaimer on `/trends`; today's route fade also translates and blanks) |
| HC-UIRES-004 | (DF-4) at 390×844, ≥ 200 px of the plot is in the first viewport above the tab bar and the rail | yes in proposal A's prototype |
| HC-UIRES-005 | no control on the page lacks a handler (the old "Last 12 Months"/"Filters" are gone or work) | yes |
| HC-UIRES-006 | PNG and SVG export still produce a file (ported `ChartExport` cases) | GREEN (pin, ported) |

**Acceptance:** G; Results route total ≤ 205 kB gz. **Est:** 5 h. **MVP:** P1.

#### UI-PG-DOCUMENTS — Documents page and the import and processing showcase

**Files:** `fe/pages/DocumentInbox.tsx`, `fe/components/documents/CategoryBadge.tsx` (delete; no importer), `ExtractionConfidenceBadge.tsx` (words first, shown only below the threshold), `HighlightChips.tsx` (Tags, max 2 + "+N"), `fe/__tests__/DocumentInbox.test.tsx` (selectors only), `fe/__tests__/ui-documents.test.tsx` (new), `e2e/ui-documents.spec.ts` (new). `EntityDetailView.tsx` belongs to UI-PG-REVIEW.
**Depends on:** UI-SHELL, UI-SHOWCASE-KIT, UI-PROVENANCE; FE-IMPORT-ERROR merged; never beside IMPORT-SCANNED-PAGE (same page): whichever lands second merges `origin/main` and keeps the other's tests green (HC-FIE-001…003, HC-ISP-004). **Gate:** none.
**Showcase:** S2 on the border element of the card of a document being extracted, S3 (20 px) beside "Reading page N of M" (text from the existing processing state); document rows show dates, status and confidence (T0), so new rows appear with M0 (no M6), and the handoff "N values ready to review" is static text linking to Review values. The preview Sheet holds document content, so it is `still` (M0). The page h1 stays "Document Inbox" here (UI-MICRO renames it), and the empty-state sentence "No documents yet. Import your first lab report", the status words "Pending", "Needs Review", "Verified", "OCR Required", the upload input label "Upload medical documents" and the row menu "More options" → "Review extracted values" are kept, so this row changes no e2e assertion (Appendix A). Row actions are always visible (no hover-only); preview is a Sheet; `window.confirm` becomes AlertDialog.

| Id | Check | RED today? |
|---|---|---|
| HC-UIDOC-001 | with the mouse away, row actions have opacity 1 and are reachable by Tab | yes (`opacity-0` until hover) |
| HC-UIDOC-002 | at most 2 chips per row; no raw identifier (`lab_csv`) in the text | yes (5 chips) |
| HC-UIDOC-003 | a processing document shows the beam and a `role="status"` text; under reduced motion the border is static and the text stays | yes |
| HC-UIDOC-004 | FE-IMPORT-ERROR's alert and IMPORT-SCANNED-PAGE's warning (whichever has merged) render static, never inside the beam card's animation | GREEN once those rows merge (pin) |
| HC-UIDOC-005 | delete asks through an AlertDialog; `window.confirm` is never called (stubbed to throw) | yes |
| HC-UIDOC-006 | `stillnessProbe` with the §2.7 `/inbox` selectors passes across an import that completes (new row appears) and across opening the preview Sheet | yes |

**Acceptance:** G; `thinking-orbs` loads only on this route and About. **Est:** 4 h. **MVP:** P1.

#### UI-PG-REVIEW — Review values with Ink

**Files:** `fe/pages/VerificationWorkbench.tsx`, `fe/components/documents/EntityDetailView.tsx` (responsive rows; StatusChip; "Show source" opens Source Trace; Ink on verify; the Edit dialog is `still` (M0) because it shows the current value), `fe/__tests__/VerificationWorkbench.test.tsx` and `VerificationWorkbenchEdit.test.tsx` (selectors only), `fe/__tests__/ui-review.test.tsx` (new), `e2e/ui-review.spec.ts` (new).
**Depends on:** UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT; FE-VERIFY-NUMERIC merged (its strict parse and error path stay). **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIREV-001 | an out-of-range value carries an icon and the words, not colour alone (WCAG 1.4.1) | yes |
| HC-UIREV-002 | verifying flips the marker from pencil to ink in the row, the chart and the chip together; the value text passes `stillnessProbe` throughout the Ink animation | yes |
| HC-UIREV-003 | the Edit dialog is labelled, traps focus, Escape closes; HC-FVN-001…005 still pass | yes for the dialog; pins for FVN |
| HC-UIREV-004 | no fixed `grid-cols-3` overflow at 390 and 320 (G6) | yes |
| HC-UIREV-005 | the Edit dialog's current value passes `stillnessProbe` from the Edit click | yes |

**Acceptance:** G. **Est:** 4 h. **MVP:** P1.

#### UI-PG-ASK — Ask: the chat owns its scroll, citations open on tap

**Files:** `fe/pages/ExplainAssistant.tsx`, `fe/__tests__/ExplainAssistant.test.tsx` and `ExplainAssistantHistoryRestore.test.tsx` (selectors only), `fe/__tests__/ui-ask.test.tsx` (new), `e2e/ui-ask.spec.ts` (new), `e2e/assistant.spec.ts` (`:61`, `:85`, `:162`, `:220`, `:236`, `:249`, `:261` send-button selector "last button with an svg" → `getByRole('button', { name: 'Send question' })` (the name FE-EXPLAIN-ERR added); `:223` `/searching documents|generating response/i` → `/reading your verified results/i`), `e2e/ui-full-verification.spec.ts` (`:110` the same send-button selector change). Kept: the h1 "Explain Assistant" (UI-MICRO renames it), the placeholder "Ask about your results...", both disclaimer sentences, the native `Document Category` select (so `toHaveValue` still works), the suggested questions.
**Depends on:** UI-SHELL, UI-PROVENANCE, UI-SHOWCASE-KIT; FE-EXPLAIN-ERR (merged, #314) and BADGE-TICK merged (same file; their HC-FEE and HC-BTK tests stay green). **Gate:** none.
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

**Files:** `fe/pages/MedicationCoach.tsx` (tabs Medications / Reminders via `?tab=`), `fe/pages/MedicationDetail.tsx`, `fe/pages/NotificationSettings.tsx` (becomes a redirect to `/medications?tab=reminders`; its content moves into a `RemindersPanel` inside `fe/components/medication-coach/`), `fe/components/medication-coach/*` (MedicationCard as a real link; DoseLoggingModal → Sheet/Dialog; BadgeToast → `notify()` with no `animate-ping`; AchievementsWidget and AdherenceDashboard on tokens; the adherence ring renders final, with no draw, because adherence figures are T0), `fe/components/MedicationOverlay.tsx` (router `Link` instead of `<a href>`), `fe/__tests__/NotificationSettingsPage.test.tsx`, `Gamification.test.tsx` (selectors only; this row owns `Gamification.test.tsx` in wave 5, and UI-PG-SETTINGS follows it), `fe/__tests__/ui-meds.test.tsx` (new), `e2e/ui-meds.spec.ts` (new), `e2e/tailwind4-styles.spec.ts` (TW4-MEDS `:270` close-button radius `'8px'` → `'10px'` (the `IconButton` control radius); the dose dialog keeps its title "Log Dose", the "Log" button and the "Close" name). The dose dialog/sheet shows the dose, so it is `still` (M0). Kept (Appendix A): `a[href^="/medications/"]` links and the detail page's h1/h2 for `medication-detail.spec.ts`.
**Depends on:** UI-SHELL, UI-SHOWCASE-KIT. **Gate:** none; MED-BADGES is open and non-blocking: the row keeps the badges as they are, static, behind the existing streaks setting (C-GAM2B `streaks_hidden`).

| Id | Check | RED today? |
|---|---|---|
| HC-UIMED-001 | MedicationCard is keyboard-activatable (Enter opens the detail) | yes (`div onClick`) |
| HC-UIMED-002 | the dose sheet: Escape closes, focus is trapped and returns; it opens and closes with M0 (`still`), and its dose text passes `stillnessProbe` from the Log click | yes |
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

**Files:** `fe/pages/TimelinePage.tsx` (event cards name the analytes, "Glucose, LDL"; duplicate `p-8` removed), `fe/pages/SearchPage.tsx` (query echoed; results are interactive cards), `fe/pages/PinboardsPage.tsx` (`window.prompt`/`confirm` → Dialog/AlertDialog), `fe/components/pinboards/AddToPinboardButton.tsx` (M3 `data-state` enter), `fe/__tests__/PinboardsPage.test.tsx`, `SearchPage.test.tsx` (selectors only; after UI-PALETTE), `fe/__tests__/ui-records.test.tsx` (new), `e2e/ui-records.spec.ts` (new). **Depends on:** UI-SHELL, UI-SHOWCASE-KIT, UI-PALETTE. **Gate:** none. The timeline card keeps the backend title "Lab results (N analytes)" and adds the analyte names beneath it, so TW4-TIMELINE (`tailwind4-styles.spec.ts:232`) is unchanged.

| Id | Check | RED today? |
|---|---|---|
| HC-UIPIN-001 | a timeline card names its analytes | yes ("1 analyte") |
| HC-UIPIN-002 | `window.prompt` and `window.confirm` are never called (stubbed to throw) | yes |
| HC-UIPIN-003 | the search page shows the query it searched | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P2.

#### UI-PG-EXPORT — Doctor summary

**Files:** `fe/pages/ExportPage.tsx` (section toggles → Checkbox/Switch rows; "Full Preview" opens a Sheet or is removed; the redaction level shown as read-only text), `fe/__tests__/ExportPage.test.tsx` (selectors only), `fe/__tests__/ui-export.test.tsx` (new), `e2e/ui-export.spec.ts` (new). **Depends on:** UI-SHELL, UI-SHOWCASE-KIT. **Gate:** none. The Full Preview sheet shows summary values, so it is `still` (M0). Redaction is untouched: `git diff origin/main -- src/frontend/src/services/export.ts src/backend` must be empty (pasted).

| Id | Check | RED today? |
|---|---|---|
| HC-UIEXP-001 | "Full Preview" opens a Sheet with the preview, or no such button exists | yes (dead) |
| HC-UIEXP-002 | no native unstyled checkbox on the page | yes |
| HC-UIEXP-003 | the request bodies sent for each export equal today's (recorded fixtures) | GREEN (pin) |

**Acceptance:** G. **Est:** 2.5 h. **MVP:** P2.

### 7.8 Wave 6: settings, chart cleanup, overview, auth

#### UI-PG-SETTINGS — Settings split into sections

**Files:** `fe/pages/SettingsPage.tsx` (section host with Tabs, `?section=`), `fe/pages/settings/PreferencesSection.tsx`, `AssistantPrivacySection.tsx`, `AdvancedSection.tsx`, `SecuritySection.tsx` (new; the security section renders today's `RecoveryCodeCard`, `BackupCard`, `DangerZone` unchanged, which UI-PG-SECURITY restyles), `fe/components/MemoryManager.tsx`, `fe/components/settings/AgentSettingsCard.tsx` (Switch), `TierCapabilities.tsx` (honest copy, 13 px floor), `DataDonationCard.tsx` (Switch + AlertDialog; `CONSENT_TEXT_VERSION` and consent text unchanged), `ExternalApiBreakGlassWarning.tsx` (token restyle only; text, role and visibility unchanged, D12), the settings tests for those components (selectors only), `fe/__tests__/Gamification.test.tsx` (the streaks-switch cases, selectors only), `fe/__tests__/ui-settings.test.tsx` (new), `e2e/ui-settings.spec.ts` (new), `e2e/settings-smoke.spec.ts` (E2E-SET-001 `:29-31`, E2E-SET-002 `:41-48`, E2E-SET-004 `:85-102`: open `/settings?section=advanced` and press "Show advanced settings" before the same assertions; E2E-SET-003 `:55-66`: open `/settings?section=assistant-privacy` first), `e2e/ui-full-verification.spec.ts` (E2E-UI-FULL-004 `:127-130`: open the Advanced section first; `:124` subtitle "Configure AI model and hardware preferences" kept). Consent, break-glass and export-confirm dialogs hold safety copy, so they are `still` (M0). `recovery-code.spec.ts` is unchanged: `/settings` still lands on Profile & security with the recovery card.
**Depends on:** UI-PG-MEDS (it owns `Gamification.test.tsx` in wave 5), UI-PG-ASK (it edits `ui-full-verification.spec.ts` in wave 5), UI-SHELL, UI-SHOWCASE-KIT; never beside DON-COPY-V3 (`DataDonationCard.tsx`). **Gate:** none (auth and encryption cards are left to UI-PG-SECURITY).

| Id | Check | RED today? |
|---|---|---|
| HC-UISET-001 | `/settings` lands on Profile & security; each `?section=` renders its section | yes |
| HC-UISET-002 | Advanced is collapsed by default; Tesseract, GPU and model-tier text is absent until "Show advanced settings" | yes |
| HC-UISET-003 | the break-glass warning's text and role equal today's (snapshot of text + role) and it has no animation | GREEN (pin, D12) |
| HC-UISET-004 | the consent dialog is an AlertDialog with Escape and focus return; consent text and version unchanged | yes for the dialog |
| HC-UISET-005 | no section is taller than 2 viewports at 1440 | yes (5,565 px) |

**Acceptance:** G. **Est:** 5 h. **MVP:** P2.

#### UI-CHART-CLEANUP — delete the Recharts chart and the dependency

**Files:** `fe/components/lab-interpreter/InterpretedTrendChart.tsx`, `fe/components/TrendVerificationMarkers.tsx` (delete; both folded into the Ribbon), their tests `InterpretedTrendChart.test.tsx`, `TrendVerificationMarkers.test.tsx` (each case ported to `ui-range-ribbon.test.tsx` or shown already covered there, listed in the PR), `fe/__tests__/Accessibility.test.tsx`, `ChartExport.test.tsx` (Recharts mocks removed), `fe/components/lab-interpreter/index.ts`, `src/frontend/package.json` and lock (remove `recharts`; remove `cmdk` if UI-PALETTE fell back to its own listbox). **Depends on:** UI-PG-RESULTS. **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UICC-001 | no `recharts` import under `src/` and none in `package.json` | yes |
| HC-UICC-002 | every removed test id is mapped to a ported or existing test (table in the PR) | — |

**Acceptance:** G; lazy JS −105 kB gz. **Est:** 1.5 h. **MVP:** P2.

#### UI-OVERVIEW — Overview landing with the first-run checklist

**Files:** `fe/pages/OverviewPage.tsx` (new), `fe/App.tsx` (index → `/overview`), `fe/components/layout/navConfig.ts` (Overview entry and phone tab), `fe/__tests__/Routing.test.tsx` (HC-ROUTE-001 expects `/overview`: a contract change from this plan), `e2e/routing.spec.ts` (E2E-ROUTE-001 `:15` `/\/inbox$/` → `/\/overview$/` and `:16` heading `'Document Inbox'` → `'Overview'`, the same contract change), `fe/__tests__/ui-landing.test.tsx` (new), `e2e/ui-landing.spec.ts` (new). **Depends on:** UI-PG-RESULTS (`App.tsx`, navConfig), UI-PG-DOCUMENTS. **Gate:** none.
**Spec:** built from existing queries only. Before the first import: the Import → Review values → See results checklist with S1 on the cards (the counts and values sit outside the S1 wrapper); the current step is marked "Next step" in words with a static accent border; each step is a working link. Afterwards: "N values waiting for review", latest results as static text with StatusChips, next dose, each linking to its page.

| Id | Check | RED today? |
|---|---|---|
| HC-UILAND-001 | with no documents, the checklist renders three working links; the current step reads "Next step" and has no animation running | yes |
| HC-UILAND-002 | with data, counts equal the API's; every count and value passes `stillnessProbe` from the moment the route fade settles and through the S1 entrance | yes |
| HC-UILAND-003 | the unknown-path redirect and the index both land on `/overview` | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1.

#### UI-PG-AUTH — setup, unlock card and recovery

**Files:** `fe/pages/ProfileSetup.tsx` (the SESSION-REENTRY unlock card restyled; the Lift moment; S1 entrance of the create form only, never on the recovery-code step; errors clear when fixed; the fake `setTimeout(500)` progress removed; the unlinked "Terms of Service" sentence removed), `fe/pages/RecoverProfile.tsx`, `fe/components/profile/RecoveryCodeCard.tsx` (code in 4-character groups that never wrap mid-group; warning in `--caution`), `fe/__tests__/ProfileSetup.test.tsx`, `RecoverProfile.test.tsx` (selectors only), `fe/__tests__/ui-auth.test.tsx` (new), `e2e/ui-auth.spec.ts` (new; real backend), `e2e/auth.spec.ts` (E2E-AUTH-001 `:44` `getByText('Creating secure vault...')` → `getByText('Creating your profile…')`, the Button loading label shown while `POST /profiles` is pending), `e2e/tailwind4-styles.spec.ts` (TW4-RECOVER `:138` border `rgb(226, 223, 215)` → `rgb(138, 133, 123)` once `#recover-code` uses the `Input` primitive's `--line-strong`; TW4-FOCUS unchanged). Kept for `auth.spec.ts` and `session-reentry.spec.ts` (#312): the label "Profile Name", the placeholder "Create a secure password", the button "Create Your Profile", the button "Create a new profile", the "saved this recovery code" checkbox, "Password is required", the post-setup `/inbox` landing, and on the unlock card the text "Unlock your profile", the labels "Profile" and "Unlock password", the button "Unlock" and the post-unlock `/inbox` landing. Field errors render in a container outside the S1 wrapper. **Depends on:** SESSION-REENTRY Task 1 (merged, #312 `7667439`; its HC-SRE-001…004 stay green), UI-PG-MEDS (it edits `tailwind4-styles.spec.ts` in wave 5), UI-SHELL, UI-SHOWCASE-KIT. **Gate:** UI-AUTH-SCREENS answered "Layout, motion and Lift" (owner prompt 48): new layout, S1 on the create-profile form, Lift on unlock; the recovery-code step stays still (HC-UIAUTH-005).

| Id | Check | RED today? |
|---|---|---|
| HC-UIAUTH-001 | a fixed field's error disappears on the next valid input | yes (stale errors) |
| HC-UIAUTH-002 | creating a profile shows no progress steps that are not tied to a real request (no `setTimeout` in the flow) | yes |
| HC-UIAUTH-003 | e2e (real backend): unlock succeeds and the shell is visible within one frame of the Lift; under reduced motion opacity only | yes |
| HC-UIAUTH-004 | the recovery code renders in groups with no group split across lines at 320 | yes |
| HC-UIAUTH-005 | submitting during the S1 entrance and after it: every field error passes `stillnessProbe` from its first render (it sits outside the S1 wrapper); the recovery-code step passes it with `expected` = the code and its warning | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P1.

### 7.9 Waves 7-9: security, about, micro sweep, dark flip

#### UI-PG-SECURITY — Profile & security section

**Files:** `fe/components/settings/BackupCard.tsx`, `DangerZone.tsx`, `fe/components/settings/RecoveryCodeCard.tsx`, `fe/pages/settings/SecuritySection.tsx`, `fe/__tests__/DangerZone.test.tsx`, `BackupRestoreFlow.test.tsx`, `RecoveryCodeCard.test.tsx` (it tests this settings card; selectors only), `fe/__tests__/ui-security.test.tsx` (new), `e2e/ui-security.spec.ts` (new; real backend through HTTP). **Depends on:** UI-PG-SETTINGS; MVP-REAUTH-401 (merged, #321; its HC-RA4 cases stay green). Its dialogs hold warnings, so they are `still` (M0); `recovery-code.spec.ts`'s labels, button names and test ids (`recovery-code-value`, `recovery-code-once-warning`, `recovery-code-replace-warning`) are kept. **Gate:** UI-AUTH-SCREENS answered "Layout, motion and Lift" (owner prompt 48): the new layout applies; the request sequence stays exactly today's (HC-UISEC-002) and the recovery code and its warnings stay still.
**Spec:** primitives only; the typed-phrase delete stays (no hold-to-confirm); restore and delete confirmations become AlertDialogs; requests, copy of warnings and the order of steps unchanged.

| Id | Check | RED today? |
|---|---|---|
| HC-UISEC-001 | e2e (real backend): delete with a wrong password shows "Incorrect password" and keeps the session (MVP-REAUTH-401 behaviour) | GREEN after MVP-REAUTH-401 (pin) |
| HC-UISEC-002 | the request sequence for backup, restore and delete equals today's (recorded in the e2e, compared) | GREEN (pin) |
| HC-UISEC-003 | every dialog: Escape, focus trap, focus return | yes |

**Acceptance:** G. **Est:** 3 h. **MVP:** P2.

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

**Files:** every remaining raw `<button>` under `fe/` moved to `Button` / `IconButton` (the file list is the output of the grep in HC-UIMIC-001, frozen in the PR); `src/frontend/eslint.config.js` (`no-restricted-syntax` on `transition-all`, `text-[9px]`, `text-[10px]` and on `<button className=` outside `fe/components/ui/`); copy pass ("abnormal" → "outside the reference range (per report)"; "AI-powered insights" removed; the model chip says "Template answers, no model installed" when true); `fe/components/layout/navConfig.ts` (the transition "Reminders" entry removed); page h1s renamed to their nav names (`DocumentInbox.tsx` "Document Inbox" → "Documents", `VerificationWorkbench.tsx` "Verification Workbench" → "Review values", `ExplainAssistant.tsx` "Explain Assistant" → "Ask"; any other h1 whose text differs from its nav name, list frozen in the PR); and the e2e assertions on them (Appendix A): `e2e/assistant.spec.ts` (`:52`, `:78`, `:102`, `:121`, `:148`, `:213`, `:229`, `:245`, `:258` `getByText(/explain assistant…/i)` → `getByRole('heading', { level: 1, name: 'Ask' })`), `e2e/ui-full-verification.spec.ts` (`:96` `/verification workbench/i` → heading `'Review values'`; `:105` → heading `'Ask'`), `e2e/session-reentry.spec.ts` (`:81` heading `'Document Inbox'` → `'Documents'`), `e2e/routing.spec.ts` (only if a heading it asserts was renamed; `:52` "Timeline" is not); `fe/__tests__/ui-micro.test.ts` (new). **Depends on:** every wave 5-7 row merged (it touches their files). **Gate:** none.

| Id | Check | RED today? |
|---|---|---|
| HC-UIMIC-001 | `eslint` passes with the new rules (no raw `<button className=` outside `ui/`) | yes |
| HC-UIMIC-002 | rendered text of every route contains none of the forbidden words ("abnormal", "AI-powered") | yes |
| HC-UIMIC-003 | axe `target-size` = 0 on every route | yes (password eye 20 px, citation chip 20 px) |
| HC-UIMIC-004 | each page's h1 equals its nav label (navConfig) on every route | yes |

**Acceptance:** G on all routes. **Est:** 3 h. **MVP:** P2.

#### UI-DARK-FLIP — dark mode follows the OS once no unmigrated colour remains

**Files:** `fe/theme/theme.ts` (`DARK_MODE_ENABLED = true`), `src/frontend/index.html` (the pre-paint script follows the OS), `fe/__tests__/ui-theme.test.ts` (HC-UITH-001 now asserts the flag is on: a contract change from owner answer UI-DARK-MODE), `fe/__tests__/ui-dark-gate.test.ts` (new), `e2e/ui-dark-gate.spec.ts` (new). **Depends on:** every other `UI-*` row merged. **Gate:** UI-DARK-MODE answered ("Follow OS setting").

| Id | Check | RED today? |
|---|---|---|
| HC-UIDRK-001 | a source scan of `fe/**/*.{ts,tsx}` and `fe/styles/*.css` outside the token block finds no unmigrated colour: `bg-white`, `text-white`, `bg-black`, `text-black`, `(bg\|text\|border\|ring\|fill\|stroke)-(gray\|slate\|zinc\|neutral\|stone\|red\|orange\|amber\|yellow\|lime\|green\|emerald\|teal\|cyan\|sky\|blue\|indigo\|violet\|purple\|fuchsia\|pink\|rose)-\d+`, arbitrary hex in class names (`[#…]`), hex or `rgb(` literals in `style` or SVG attributes; **no allowlist** | yes on `7749744` (the PR pastes the failing count from a checkout of that commit) |
| HC-UIDRK-002 | e2e: with `colorScheme: 'dark'`, every route (the 15, Overview, About, setup, recover) has `data-theme="dark"` and axe 0 serious/critical | — |
| HC-UIDRK-003 | e2e: in dark, no visible element larger than 40×40 px has a computed background with relative luminance > 0.8 (catches a leftover white card) | — |
| HC-UIDRK-004 | e2e: with `colorScheme: 'light'` nothing changes from `origin/main`'s light screenshots taken at this row's merge base, just before the flip (pixel diff below 0.5 % per route) | — |

**Acceptance:** G on every route in both themes. **Est:** 2 h. **MVP:** P2. If HC-UIDRK-001 finds anything, the fix belongs to the row that owns that file; the flip waits.

### 7.10 Follow-ups planned 2026-10-26 (post-merge batch)

Planned 2026-10-26 on `0e8b2b2` from the L0 rulings on #370 (UI-SHELL, still in flight) and #374 (GATES-SAMPLE-TIME), and the queue bullet ALERTDIALOG-CANCEL-FOCUS. Queue rows: [Planned 2026-10-26, post-merge batch](2026-10-15-build-program/queue.md#planned-2026-10-26-post-merge-batch). The checks UI-SHELL moved to page rows are recorded in those rows' queue cells, not here.

#### POPOVER-OPEN-COST — the popover open costs more than one 40 ms sampling gap

**Kind:** PRODUCT (frontend). **Files:** `fe/components/ui/Popover.tsx`, `e2e/ui-shell.spec.ts` (HC-UIOV-007 browser case: remove its `test.fixme` only), `fe/__tests__/ui-overlays.test.tsx` (HC-UIOV-007 vitest half: selectors only, if needed). **Depends on:** UI-SHELL merged (#370 adds the marked case). **Gate:** none.

**Why.** L0 ruling 08:46:34Z on #370: the browser half of HC-UIOV-007 (the safety-toggle popover opens with a `[data-t0]` child under `stillnessProbe`) failed 2 of 3 runs on a `vite preview` build, with sampling gaps of 53 and 49 ms. Traces on preview and dev (Chromium, 60 ms window after the click): click dispatch 14-20 ms, microtasks 15-19 ms, style 3-4 ms, layout 0.3-0.4 ms, paint 4-6 ms; no CPU sample in `src/components/layout/`. The cost is React render and commit, Radix Popover (Presence, DismissableLayer) and framer frames, all under `ui/Popover.tsx`, a primitive of the done row UI-PRIM-OVERLAYS. About 13 ms of the busy span comes before the click, from Playwright hit-testing (`elementsFromPoint`). #370 marks the case `test.fixme(true, 'POPOVER-OPEN-COST: …')` (fixme, not fail, because it passes intermittently).

**Change.** Find what the open does in one task and cut it below the bound (systematic-debugging; trace first). Leads, not decisions: a `still` popover may not need `AnimatePresence` or framer frames at all; Presence and DismissableLayer may mount more than the content needs. `still` behaviour (M0, no opacity, scale or translate on T0 content) stays.

| Id | Check | RED today? |
|---|---|---|
| HC-UIOV-007 (browser half) | the `e2e/ui-shell.spec.ts` case with its `test.fixme` removed: `stillnessProbe` from the opening click passes 10 of 10 runs on a `vite preview` build on a quiet box (`uptime` and `ps` pasted), and CI E2E passes it on the final head | yes (2 of 3 on preview, 49-53 ms) |

**Acceptance:** the case above; HC-UIOV-001…007 (vitest) green; HC-UISH-009's popover M0 case green; `STILLNESS_MAX_GAP_MS`, the 20 ms interval and the 800 ms window unchanged (`git diff origin/main...HEAD -- e2e/support/gates.ts` empty). **Est:** 3 h. **MVP:** P1.

#### Delta 2026-10-29: POPOVER-OPEN-COST widened to dialog opens (UI-PG-MEDS #398 stop)

Planned 2026-10-29 on `41fa382` (Opus planner) from the UI-PG-MEDS stop on #398 (L2 comment "review round 1 fixes, stopped on BLOCKER 1", and the `blocked: tell L0` comment after it). **The row keeps its id, POPOVER-OPEN-COST.** It is not renamed to OVERLAY-OPEN-COST: draft #393, its branch `fix/popover-open-cost-popover-open`, and SAFETY-MODE-TOGGLE's never-beside clause (which reads #393's title) all name it. Its scope is now **overlay open cost: Popover, and Dialog, AlertDialog and Sheet (`Modal`)**. #393 has no commits (stopped only on quiet-box load), so the row resumes on it: `build-item {"id":"POPOVER-OPEN-COST","resume_pr":393}`. The section above still applies; this delta adds to it. Where they differ, this delta wins.

**L0 decisions this delta keeps (2026-10-29, not owner rows):**
- No `modal={false}`. It drops the focus trap and the modal semantics, which is an accessibility regression.
- No bound change. The owner answered STILLNESS-GAP-BOUND "Fix first, frame waits", and STILLNESS-NAV-70 raised the bound for page changes only. A dialog open is an interaction, so the 40 ms bound applies.

**Why (#398).** HC-UIMED-002's stillness probe on the dose "Log" click (`kind: 'interaction'`, 40 ms) misses:
- CI run 40820611795: all 3 attempts failed, at 45, 53 and 59 ms.
- Locally, after the row's own fixes: 41-55 ms.

#398's CDP profile at 4x CPU throttle:
- The React flush takes about 150 ms (about 37 ms unthrottled). Style recalc is 77 ms of that.
- Forced restyles come from Radix `Presence` `getAnimationName` and `FocusScope` `focusFirst`.
- The largest comes from react-remove-scroll-bar's `body[data-scroll-locked] { --removed-body-scroll-bar-size: <gap>px }`. That is an inherited custom property, so the whole document restyles. It cost 28.6 ms as a forced restyle, against 0.5 ms for the same rule without the property.
- The lock is on because `Modal` (`fe/components/ui/Dialog.tsx`) runs Radix in modal mode.

**What the library does with the variable** (react-remove-scroll-bar 2.3.8, through react-remove-scroll 2.7.2 and `@radix-ui/react-dialog` 1.3.1; read in `node_modules/react-remove-scroll-bar/dist/es2015/component.js` and `constants.js`):
- It only **writes** the variable, in the last `body[data-scroll-locked]` block of its injected style. It never reads it.
- The scrollbar-gap compensation uses literal pixel values, not the variable:
  - on `body`: `margin-right: <gap>px !important` (`gapMode` 'margin', the default), plus `overflow: hidden !important` and `position: relative`;
  - `.right-scroll-bar-position { right: <gap>px }` and `.width-before-scroll-bar { margin-right: <gap>px }`.
- The constant's own comment calls the variable an opt-in hook for consumers ("might be undefined! use will fallback!").
- On `41fa382`, grep finds no use of `--removed-body-scroll-bar-size`, `width-before-scroll-bar`, `right-scroll-bar-position`, `with-scroll-bars-hidden` or `data-scroll-locked` in `src/frontend/src` or `src/frontend/e2e`. In `node_modules`, the only other file that names the variable is Vite's prebundled copy of the same library (`.vite/deps`).

**So the candidate fix is sound.** Register the variable as non-inheriting. The value on `body` is unchanged, and descendants get `0px` instead of inheriting it. Nothing in the repo or its dependencies reads the variable below `body`. The lock (`overflow: hidden` on `body`) and the gap compensation do not use it, so both are unchanged. A future reader must take the value from `body` (`getComputedStyle(document.body)`), and the rule's comment says so.

**Browser support.** `@property` is supported in Chrome and Edge 85+, Safari 16.4+ and Firefox 128+.
- Playwright 1.58.1's Chromium is 143.0.7499.4. Measured: the rule registers, and a `CSSPropertyRule` with `inherits: false` is present on both dev and a `vite preview` build.
- The build has no `build.target` or browserslist, so Vite 7's default target applies (baseline widely available: Chrome and Edge 107, Firefox 104, Safari 16). Firefox 104-127 and Safari 16.0-16.3 ignore the rule and behave exactly as today: inherited and slower. They lose no function, because nothing reads the variable.
- Prior art: `fe/components/ui/showcase.css:7` registers `@property --beam-angle`.
- The Tailwind 4 / Lightning CSS build keeps the rule. The scratch preview build emitted `@property --removed-body-scroll-bar-size{syntax:"<length>";inherits:false;initial-value:0}`. `0` is a valid `<length>` initial value.

**Measurements (planner, 2026-10-29; evidence only).** Scratch worktree at #398's head `1d209068`, with `node_modules` linked. Nothing was committed, and the worktree was removed afterwards. **None of these ran on a quiet box**: the 1-minute load was 1.6-4.3 and nothing was run under `hold_slots.sh`. So only the in-page timings below are robust. The stillness tallies are noise-bound and are not a RED or GREEN for this row.

| What | Without `@property` | With `@property` |
|---|---|---|
| In-page, on `/medications` (292-303 elements): set `data-scroll-locked` on `body`, then force a restyle (`focus()` plus `offsetHeight`), median of 11, 3 runs; dev | 3.3, 4.0, 5.9 ms | 0.1, 0.1, 0.1 ms |
| The same on a `vite preview` build | 3.8-4.7 ms (8 runs) | 0.1 ms (8 runs) |
| Inserting the library's `<style>` alone, then a forced restyle | 0.1-0.2 ms | 0.1 ms |
| Synthetic page (6,000 elements, token-style variables), lock and forced restyle, median of 15; unthrottled / 4x throttle | 8.2 / 48.7 ms | 2.4 / 12.3 ms |
| HC-UIMED-002 stillness, dev, 8 runs (load 1.8-2.6) | 6 of 8 over 40 ms (35-97) | 7 of 8 over 40 ms (38-61) |
| HC-UIMED-002 stillness, preview, 8 runs | 4 of 8 over 40 ms (38-79; load 2.1-2.6) | 6 of 8 (28-114; load rose to 4.3: discarded) |
| CPU profile of the Log click on dev, `FocusScope` `focusFirst` → `focus` self time | 10.7-10.9 ms | 11.4 ms |
| Lower bound, not a candidate: `modal={false}` in scratch, dev, 6 runs | — | 3 of 6 over 40 ms (31-82); `focus` 4.9-10.1 ms |

**Reading:**
1. The fix removes the lock's restyle cost: about 4 ms per forced restyle unthrottled (about 16 ms at 4x, the G3 throttle), every time the lock attribute changes.
2. On dev, StrictMode runs mount effects twice (`commitDoubleInvokeEffectsInDEV` appears in the profile). The lock is set, removed and set again, so dev pays that restyle more than once per open.
3. It is **not sufficient on its own**. With the lock removed entirely (`modal={false}`, measured only as a floor), the dialog open still missed 40 ms in 3 of 6 runs on a loaded box. The rest is the React render and commit of the opened content, Radix (Presence, FocusScope, DismissableLayer, `hideOthers`), and framer. That is the cost the section above already planned to trace for the Popover.

**Radix `Presence` `getAnimationName`** (`@radix-ui/react-presence` 1.1.11, read in `dist/index.mjs`):
- The ref callback reads `getComputedStyle(node).animationName` when the node mounts. That forces the new subtree's style early, but the frame needs that style anyway, so it is not extra work unless the DOM is dirtied again before paint.
- The passive effect reads it again only when no mount-time value is cached. The profile shows that read only under `commitDoubleInvokeEffectsInDEV` (4-6 ms on dev): a dev StrictMode cost, absent from preview and production builds.
- `forceMount` does not bypass `Presence`: Portal, Overlay and Content each wrap their child in `Presence` whatever its value.
- **No safe in-repo fix exists without patching Radix** (patch-package or a fork), and the row does not do that. The row reuses the section above's lead instead: a `still` overlay may not need `AnimatePresence` or framer at all. This now applies to `Modal` too: under `still`, `Modal` still wraps in `AnimatePresence`, renders `m.div`, and fades the scrim. Trace first, and remove only what the trace charges.

**Files (the narrowest set; replaces the Files line above):**
- `fe/styles/globals.css`: one top-level `@property --removed-body-scroll-bar-size { syntax: '<length>'; inherits: false; initial-value: 0px; }` after `@import 'tailwindcss'`, with a two-line comment naming react-remove-scroll-bar and "read it from body".
- `fe/components/ui/Popover.tsx`: as above.
- `fe/components/ui/Dialog.tsx`, **only if Task 2's trace charges it**: the `still` render path of `Modal`, for example no `AnimatePresence` or `m.div` wrapper when `still`. `DialogPrimitive.Root` stays modal. `role`, `aria-modal`, `onOpenAutoFocus`, `onPointerDownOutside`, `onInteractOutside`, Close and the title guard are unchanged.
- `e2e/ui-shell.spec.ts`: the HC-UIOV-007 browser case. Remove its `test.fixme` only.
- `e2e/ui-provenance.spec.ts`: new HC-UIOV-009, HC-UIOV-010 and HC-UIOV-011, appended after HC-UIPV-006 in one `test.describe` with `retries: 0`. They reuse that file's `mockApi`, `seedSession` and `waitForSettled`, and change no existing case.
- `fe/__tests__/ui-overlays.test.tsx`: selectors only, if needed.

Unchanged: `e2e/support/gates.ts`, every bound, the 20 ms interval and the 800 ms window.

**Tasks.**
1. **Task 1 (the `@property` rule).** RED: HC-UIOV-010. GREEN: add the rule, then rerun HC-UIOV-010 on dev and on preview.
2. **Task 2 (trace the rest; systematic-debugging).** On a quiet box:
   - Profile the HC-UIOV-009 open and the HC-UIOV-007 open on dev and on preview.
   - Before calling any miss load or flake, time the same click with a bare 20 ms timer, as recheck 14 of `docs/agentic/recurring-failures.md` requires. The #370 traces put about 13 ms of Playwright hit-testing (`elementsFromPoint`) before the click.
   - Cut only what the trace charges to `ui/Popover.tsx` or `ui/Dialog.tsx`'s `still` path.
   - If the remaining gap is the harness's own work (the trigger's actionability checks), that is not this row's fix. Stop and tell L0, which routes it to STILLNESS-NAV-LATE. `gates.ts` stays unchanged here.
3. **Stop rule.** If, after Task 2, HC-UIOV-009 or the HC-UIMED-002 check (see Acceptance) still misses 40 ms on a quiet box, and no cut remains in this row's files, stop and tell L0 with the trace. Do not mark anything `fixme`, `skip` or `fail`.

| Id | Check | RED today? |
|---|---|---|
| HC-UIOV-009 (new) | `stillnessProbe` (`kind: 'interaction'`, 40 ms) from the "Open source" click on `/interpret`. The click opens the `still` Source Trace sheet (`fe/components/results/SourceTrace.tsx:163`), a `Modal` with Radix modal mode and the body scroll lock: the only `still` Modal on main. `expected: ['[role="dialog"][aria-modal="true"] [data-t0]']`. The citation popover is opened and settled first (`waitForSettled`), and the button is scrolled into view before the probe, as HC-UIPV-006 does | expected yes: the same `Modal` path as HC-UIMED-002. Task 0 records 10 runs on main's dev server on a quiet box. If it is green 10 of 10, say so; the timing RED is then the HC-UIMED-002 check (see Acceptance) |
| HC-UIOV-010 (new) | With the sheet open, the stylesheets hold a `CSSPropertyRule` named `--removed-body-scroll-bar-size` with `inherits` false. After `document.body.style.setProperty('--removed-body-scroll-bar-size', '17px')`, the dialog content's computed value is `0px` and `body`'s is `17px`. Runs on dev and on preview | yes (the content inherits `17px`, and no rule exists) |
| HC-UIOV-011 (new; guard) | At 390 × 844 on `/interpret` (the page scrolls), with the sheet open: `body` has `data-scroll-locked`, its computed `overflow` is `hidden`, and its `margin-right` equals the gap measured before the open (`innerWidth - documentElement.clientWidth`; 0 when no classic scrollbar, value recorded); `mouse.wheel` over the scrim leaves `scrollY` unchanged. After Escape, the attribute is gone and the wheel scrolls the page. Mutant: `modal={false}` on `DialogPrimitive.Root` fails the case; paste the output, then restore | no (a guard; the mutant shows it can fail) |
| HC-UIOV-007 (browser half) | as above, unchanged | yes |

**Acceptance (replaces the Acceptance line above):**
- **HC-UIOV-009 and HC-UIOV-007:** 10 of 10 runs at 40 ms on a quiet box on main-plus-branch's dev server, and 10 of 10 on a `vite preview` build of the same head. CI E2E passes them on the final head with no flaky entry. These cases run with `retries: 0`, so a retry cannot hide a miss.
- **The HC-UIMED-002 check** (an HC-UIMED-002-like dialog open):
  - In a scratch worktree (nothing committed), apply this row's diff to #398's head.
  - Run HC-UIMED-002's stillness case 10 times on dev and 10 times on preview, on a quiet box. Paste the per-run maximum gap.
  - Every run is at or below 40 ms.
  - This is evidence for UI-PG-MEDS, which still owns HC-UIMED-002's CI pass after it rebases.
- **Unchanged:** the focus trap, `aria-modal`, Escape and focus return, proved green on the branch by:
  - HC-UIOV-001 (Escape closes each overlay; focus returns to the trigger);
  - HC-UIOV-002 (focus stays inside a Dialog or Sheet over 25 Tab presses, with a focusable element outside);
  - HC-UIOV-003 (`aria-modal`, and the title guard);
  - HC-UIOV-008 (AlertDialog opens on Cancel);
  - HC-UIPV-001 (e2e: Escape closes the citation popover and returns focus);
  - HC-UISH-007 (e2e: the More sheet);
  - HC-UIOV-011 (above).
- **No bound or constant changed:** `git diff origin/main...HEAD -- src/frontend/e2e/support/gates.ts` is empty, and no `STILLNESS_*` constant, interval or window changes anywhere.
- **Every existing overlay test green:**
  - `fe/__tests__/ui-overlays.test.tsx` (HC-UIOV-001…008);
  - `e2e/ui-provenance.spec.ts` in full;
  - `e2e/ui-shell.spec.ts` in full (including HC-UISH-009's popover M0 case);
  - full `npx vitest run`, `npx tsc --noEmit`, `npm run build`;
  - CI E2E on the final head.

**Quiet-box rule (every Playwright timing run in this row).** These are the STILLNESS-NAV-LATE box rules:
- L0 holds `/tmp/claude-1000/quiet-box.lock`, and no model-host row runs meanwhile.
- Wrap each Playwright command in `/tmp/claude-1000/hold_slots.sh`.
- Just before each wrapped run, paste `uptime` and `pgrep -fa "playwright|vitest|pytest"`. The 1-minute load must be below 1.5, and no process that is not yours may appear. Otherwise wait up to 30 minutes (`wait_quiet.sh`), then report the processes and stop.
- Never run pytest inside the wrapped command.
- Every run counts: no re-run to get a pass.
- HC-UIOV-010 and HC-UIOV-011 are not timing checks and may run on any box.

**Depends on:** UI-SHELL merged (done, #370).

**Never beside:**
- G1-VERIFY-TRACE-RACE (`e2e/ui-provenance.spec.ts`);
- any open PR that edits `fe/styles/globals.css`, `fe/components/ui/Popover.tsx` or `fe/components/ui/Dialog.tsx`;
- any open PR that edits `e2e/ui-shell.spec.ts` at the HC-UIOV-007 case.

Checked 2026-10-29 with `gh pr diff N --name-only` on every open PR (#239, #264, #316, #393, #398, #399, #400, #401): only #398 touches one of the row's files, `e2e/ui-shell.spec.ts`. Its hunks are the HC-UISH-003 route filter (`:296`), the HC-UISH-007 preview skip (`:791`) and the `PAGE_OVERFLOW` entry (`:972`), none at HC-UIOV-007 (`:855`). #398 is a `[blocked:claude]` draft that now waits for this row and rebases onto it, so the two never build at once. SAFETY-MODE-TOGGLE's existing clause still applies.

**Blocks:** UI-PG-MEDS (#398), added to its depends_on in this delta. UI-PG-MEDS's G3 `/medications` dark at exactly 200 ms on dev (bound `< 200`) may share the cause. G3 runs at 4x CPU throttle, where the lock's restyle is about 16 ms per forced restyle, paid more than once per open on dev. UI-PG-MEDS re-measures G3 after it rebases; this row does not claim it.

**Owner question:** none expected. If the stop rule fires, L0 decides the next step. A neutral draft, for L0 only, not asked:

> **STILLNESS-OVERLAY-OPEN** (draft, not asked). After the scroll-lock and still-path fixes, opening a modal dialog or sheet still takes about N ms before the next frame, against the 40 ms interaction bound (traces attached). Which do you want?
> - (a) Keep 40 ms for overlay opens and keep the dose sheet's stillness check failing until a deeper fix (patching or replacing Radix parts) is planned.
> - (b) Allow overlay opens the page-change bound (70 ms, as in STILLNESS-NAV-70) and keep diagnosing.
> - (c) Something else.

**Est:** 5 h (was 3). **MVP:** P1.

#### SETTINGS-DETECT-BLOCKING — hardware detection blocks the event loop in three settings routes

**Kind:** PRODUCT (backend routes; code slot). **Files:** `be/api/model_settings.py` (only the blocking calls: `selector.detect_hardware_tier()` in `get_model_settings` `:398` and `list_tiers` `:598`; `_diagnostics_list_response()` in `get_environment_diagnostics` `:1200` and `recheck_environment_diagnostics` `:1211`), `be/tests/test_settings_detect_nonblocking.py` (new). **Depends on:** none; never beside another `be/api/model_settings.py` PR. **Gate:** none. Not ask-first (no auth, encryption or safety module); `modules/hardware_detection.py` and `modules/environment_diagnostics.py` are unchanged.

**Why.** L0 ruling 06:35:47Z on #370: `detect_hardware` takes about 2.6 s and runs synchronously inside three `async` handlers (`GET /settings/model`, `GET /settings/model/tiers`, the diagnostics call `modules/environment_diagnostics.py:223`), so the calls serialise on the event loop to about 8-9 s, and every other request waits behind them. E2E-SET-001 (settings page visible within 10 s) takes 10.2 s on main on a cold local backend start; the shell's extra 0.5 s on a cold dev server pushes it over. The 10 s timeout is not raised.

**Change.** Run each blocking call off the loop with `await asyncio.to_thread(...)`, as `PUT /settings/model/provider` already does (`:910`, HC-LUL-001…003). Off-loop rather than a per-process cache (the ruling's other option): a cache would keep stale hardware and model availability after a download, and `POST /diagnostics/recheck` exists to re-run the checks. Response bodies and audit calls are unchanged. If Task 0 finds `detect_hardware` unsafe to run in two threads at once (shared mutable state), stop and report.

| Id | Check | RED today? |
|---|---|---|
| HC-SDB-001 | through `tests/support/routes.py::route_client` (one shared portal loop, the HC-LUL pattern): with `detect_hardware_tier` patched to block on a `threading.Event`, `GET /settings/model` is in flight while a second, light request on the same router (`GET /settings/model/provider?probe=false`, as HC-LUL does) returns 200 within 1 s; then the event is set and the first returns 200 with the same body as today | yes (the second request waits for the first) |
| HC-SDB-002 | the same for `GET /settings/model/tiers` | yes |
| HC-SDB-003 | the same for `GET /settings/model/diagnostics` and `POST /settings/model/diagnostics/recheck`, with `build_environment_diagnostics` patched to block | yes |

**Acceptance:** HC-SDB-001…003 RED then GREEN with output; `test_model_settings_api.py`, `test_audit_read_settings.py`, `test_tier_capabilities.py` and `test_provider_switch_nonblocking.py` green; full backend suite with the collected count and delta; E2E-SET-001 on a cold local backend, main and branch figures pasted, and CI E2E green. **Est:** 2 h. **MVP:** P1.

#### GATES-SAMPLE-TIME-MINORS — the #374 review MINORs

**Kind:** PRODUCT (e2e harness; test + doc). **Files:** `e2e/README.md` (`:71`, one sentence), `e2e/ui-gates-sampler.spec.ts` (`:73`). **Depends on:** GATES-SAMPLE-TIME (done, #374). **Gate:** none.

**Why.** #374 review round 1 (PASS, 3 MINORs): (1) `e2e/README.md:71` says "so a gap counts the page's work between samples, not the probe's own reads in a tick", which claims more than the code does: stamping at the start keeps a tick's reads out of the gap before that sample, but a read that runs past the 20 ms interval still delays the next tick (HC-UIG-007 (a) is that case: a 30 ms read shows as a 30-31 ms gap). (2) HC-UIG-007 (a) checks only the upper bound, so it would pass if the wrapper never fired. (3) is recorded in the GATES-SAMPLE-TIME section above, no change.

**Change.** (1) Replace the sentence with the review's text: "…before its style and layout reads, so those reads are not added to the gap before the sample. A read that runs past the next interval still delays the next sample and shows as a gap (HC-UIG-007)." (2) In (a), also assert `report.maxGapMs >= 25`, so the case proves the block landed in the window.

| Id | Check | RED today? |
|---|---|---|
| HC-UIG-007 (a) | gains `expect(report.maxGapMs).toBeGreaterThanOrEqual(25)`; mutant: with `blockOnceAfterStart(0)` (no block) the case fails, output pasted, then restored | GREEN (a stronger pin; the mutant shows it can fail) |

**Acceptance:** HC-UIG-007 green with `--repeat-each 10`; HC-UIG-001…006 unchanged; the mutant RED pasted. **Est:** 0.5 h. **MVP:** P2.

#### ALERTDIALOG-CANCEL-FOCUS — a destructive AlertDialog opens on Cancel

**Kind:** PRODUCT (frontend; accessibility). **Files:** `fe/components/ui/AlertDialog.tsx`, `fe/components/ui/Dialog.tsx` (`Modal`: accept `onOpenAutoFocus` and pass it to `DialogPrimitive.Content`, nothing else), `fe/__tests__/ui-overlays.test.tsx` (new HC-UIOV-008; the HC-UIOV-002 fixture gains a focusable element outside the overlay). **Depends on:** UI-PRIM-OVERLAYS (done, #363). **Blocks:** UI-PG-SECURITY (DangerZone's destructive confirm) and any destructive-flow consumer (FE-A11Y-DIALOGS). **Gate:** none.

**Why.** #363 L0 review: `AlertDialog.tsx` focuses the first focusable element on open (its own comment: "Radix's AlertDialog focuses Cancel instead, and this one does not. So put the cancel action first: if a destructive action comes first, it gets focus and Enter confirms it."). A rule that depends on the caller's element order is a trap for a destructive confirm. Also, the HC-UIOV-002 focus-trap test passes with `modal={false}`, because its fixture has nothing focusable outside the overlay for Tab to reach.

**Change.** AlertDialog moves initial focus to its cancel action: the element marked `data-alert-cancel` inside the content (an equivalent `cancelRef` prop is fine; the tests pin the behaviour, not the mechanism), through Radix `onOpenAutoFocus` (`preventDefault`, then focus it). With no cancel element it logs `console.error` naming AlertDialog, like the title guard, and keeps the default. Update the component comment. Dialog and Sheet are unchanged. The Dialog close button scrolling away on tall content stays in the queue bullet, not this row.

| Id | Check | RED today? |
|---|---|---|
| HC-UIOV-008 | an AlertDialog whose destructive "Delete" comes before "Cancel" in the DOM: on open, Cancel has focus; Enter calls the cancel handler and not the confirm spy; a missing cancel element logs one `console.error` naming AlertDialog | yes (focus lands on "Delete") |
| HC-UIOV-002 (strengthened) | the fixture has a button outside the overlay; 25 Tab presses never focus it; mutant: `modal={false}` on `DialogPrimitive.Root` fails the case (output pasted), then restored | GREEN (the mutant shows it can fail) |

**Acceptance:** the two ids with output; HC-UIOV-001…007 green; `npx tsc --noEmit` clean. **Est:** 2 h. **MVP:** P2.

### 7.11 Planned 2026-10-28 (owner answers STILLNESS-GAP-BOUND and STILLNESS-NAV-70)

Planned 2026-10-28 on `6b3dd27` from the owner's answers, both recorded in owner-decisions:
- **STILLNESS-GAP-BOUND** (AskUserQuestion): **"Fix first, frame waits"**.
- **STILLNESS-NAV-70** (owner chat the same day, after L0 explained the impact): **"Raise it to 70 ms for page changes and keep diagnosing"**. This supersedes the 40 ms part of the first answer for page changes only; the diagnosis part stands.

Also L0 ruling 6461743542 on #370. Queue rows: [Planned 2026-10-28, planner](2026-10-15-build-program/queue.md#planned-2026-10-28-planner).

**The effective rule** (owner STILLNESS-NAV-70):
- a `stillnessProbe` of kind `'navigation'` allows sampling gaps up to 70 ms;
- every other stillness check keeps 40 ms;
- the minimum-sample rule (`windowMs / 40`) is unchanged.

No row other than GATES-NAV-BOUND changes a bound, and no row marks a check fixme, skip or fail, or counts a miss as flaky.

#### GATES-NAV-BOUND — navigation stillness probes allow 70 ms sampling gaps

**Kind:** PRODUCT (e2e harness). L0 builds it as #390. **Files:** `e2e/support/gates.ts` (`STILLNESS_NAV_MAX_GAP_MS = 70`; `checkSampling` takes `maxGapMs`, default 40; `stillnessProbe` passes 70 for `kind: 'navigation'` only; the minimum stays `windowMs / 40`), `e2e/ui-gates.spec.ts` (new HC-UIG-008), and `e2e/README.md:70` (the gap sentence now says 40 ms, or 70 ms for a navigation). **Depends on:** none. **Gate:** STILLNESS-NAV-70 answered 2026-10-28. **Blocks:** UI-SHELL (#370).

**Acceptance (set by L0's PR):**
- a navigation self-test with a gap above 70 ms still fails;
- an interaction self-test with a gap above 40 ms still fails (HC-UIG-007 (b) unchanged);
- HC-UIG-006 still fails on every case it failed on before;
- CI E2E green.

**MVP:** **P0** (UI-SHELL waits on it).

#### STILLNESS-NAV-LATE — find and fix why page changes run late under the stillness probe

**Kind:** MEASURE (Task 1), then PRODUCT (frontend) or PRODUCT (e2e harness) (Task 2). An `L0 ruling:` after Task 1 picks the kind and names the files. **Files:** Task 1: `docs/reviews/<run date>/stillness-nav-evidence/` (new: `README.md` plus the copied scripts and logs below). Task 2: only the files the L0 ruling names. Likely candidates: `e2e/support/gates.ts` (harness; after GATES-NAV-BOUND); `e2e/support/mockApi.ts` (#370 also edits it); `fe/App.tsx` (lazy routes); `fe/components/layout/AppLayout.tsx` and `fe/components/ui` `PageTransition` (today's route transition; #370 rewrites AppLayout). **Depends on:** GATES-SAMPLE-TIME (done, #374), GATES-SAMPLE-TIME-MINORS (done, #384). Runs alongside GATES-NAV-BOUND, never beside another `e2e/support/gates.ts` PR. **Blocks:** nothing since STILLNESS-NAV-70; UI-SHELL depends on GATES-NAV-BOUND instead. **Gate:** STILLNESS-GAP-BOUND answered 2026-10-28 (the diagnosis); STILLNESS-NAV-70 answered 2026-10-28 ("keep diagnosing"). **Ask-first files:** none expected. If Task 1 points at `interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, auth or encryption, ask the owner first.

**Bound for this row.** The owner raised the navigation bound to 70 ms, but this row's target stays 40 ms on navigation. The goal is that the cause of the late samples ("the errors", in the owner's words) is fixed, so that origin/main's dev server passes the instrumented navigation set at 40 ms in 15 of 15 runs. The row reads each run's maximum gap (`PROBECOST maxGap`, or the probe report's `maxGapMs`) and judges it against 40 ms; whether the probe passes at the effective 70 ms is not this row's measure. The row never lowers or raises a bound itself. If it reaches 15 of 15 at 40 ms, it may propose returning navigation to 40 ms; that is an owner question L0 asks.

**Why.** On #370 every HC-UISH-009 failure on dev was a sampling gap of 41-59 ms, with no sample showing the Safety Rail move. L0 then measured main against the branch on 2026-10-27. Each batch ran on a quiet box under `hold_slots.sh`, with the 1-minute load between 1.13 and 1.49 and no other Playwright, vitest or pytest process. The instrumented probe is a copy of the branch's `gates.ts` that logs `PROBECOST` per run; the bare timer is a 20 ms `setInterval` that only pushes `performance.now()`. Both use the same start pages, navigation, mock API and 1440 × 900 viewport as HC-UISH-009. Each run is one fresh page.

| Set-up (5 routes: `/timeline`, `/search`, `/medications/med-fixture-1`, `/notifications`, `/care-tasks`) | Runs with a gap over 40 ms | Those gaps (ms) | Log |
|---|---|---|---|
| instrumented probe, origin/main dev, no `[data-t0]` node | 9 of 15 | 41, 41, 42, 42, 45, 46, 46, 47, 58 | `probe-runs.log` (`main tag=0`) |
| the same with 3 shell nodes tagged `data-t0` in the page | 8 of 15 | 42-57 | `probe-runs.log` (`main tag=3`) |
| instrumented probe, #370 branch dev | 8 of 15 | 41-51 | `probe-runs.log` (`branch tag=0`) |
| HC-UISH-009 (the branch's own spec), branch dev, control run | 6 of 15 | 44-53 | `probe-control.log` |
| HC-UISH-009, branch `vite preview` build | 2 of 36 | 44, 47 | `t4-preview.log` |
| bare 20 ms timer, main dev | 3 of 25 | 41, 46, 56 | `batch1.log`…`batch5.log` |
| bare timer, branch dev | 0 of 25 | — | same |
| bare timer, branch preview | 1 of 25 | 46 | same |

What the logs already show (facts, not a diagnosis):
- `snapshot()` costs 0.0-0.3 ms per tick on average (mean per run), at most 6.2 ms. On main with no `[data-t0]` node a tick reads nothing per node, yet the probe still missed in 9 of 15 runs.
- Every probe gap ends 22-96 ms after the trigger (`gapEndsAtMs`), so it falls in the page change itself, not in the settled window.
- The bare timer's `longtask` observer recorded no long task in any of its 75 runs, including its 56 ms gap.
- The two set-ups were not interleaved. The bare-timer batches ran from 21:50 to 22:00 and the probe batches from 22:17 to 22:23, so time of run is not ruled out.
- The set-ups differ in more than the sampler:
  - The bare timer starts, waits 100 ms, then triggers. The probe starts its sampler, reads `triggeredAt` in a second `page.evaluate`, and triggers at once.
  - With `lazyRoute: true` the probe attaches `page.on('request' | 'requestfinished' | 'requestfailed')` listeners (`trackRequests`) and polls for network idle in Node. The bare timer attaches none.
  - The probe rounds each sample's stamp with `Math.round` (`gates.ts` `snapshot`). The bare timer rounds only the final gap, so the same pause can read up to 1 ms longer in the probe.

**Evidence to keep.** The scripts and logs live only in L0's scratchpad, `/tmp/claude-1000/-mnt-e-Programming-Github-Repo-HealthCentral/b8becc8c-4942-444f-9c3c-2a03f3900e75/scratchpad/`. `/tmp` can be wiped by a restart. Task 1 step 1 copies them into the repo. If they are gone, Task 1 recreates them from this section and says so. They hard-code that scratchpad path and two worktrees: `hc-ui-shell` (#370) and `hc-measure-main` (origin/main, already removed). Parameterise them or record the paths used. Expected sha256 values (first 12 hex digits):

| Source (under the scratchpad) | sha256 |
|---|---|
| `baretimer/baretimer.spec.ts` | `95c225c36f8a` |
| `baretimer/playwright.config.ts` | `6ed971971960` |
| `baretimer/run_batch.sh` | `4d3506bcf645` |
| `baretimer/wait_quiet.sh` | `3008f372b0fd` |
| `baretimer/t4_preview.sh` | `91916bb4ecc1` |
| `baretimer/batch0.log` (warm-up, load 4.76, not counted) … `batch5.log` | `8bc42a492c2c`, `bacc5213b3b8`, `04a872243e9b`, `9f3e239a9c6a`, `b89f4d07aa63`, `ee72cd494c3d` |
| `baretimer/probe-control.log` | `94e867b7b087` |
| `baretimer/t4-preview.log` | `91e3cf6fa569` |
| `probecost/e2e/support/gates.ts` (the instrumented copy; commit it as `gates.instrumented.ts`) | `b49473df8217` |
| `probecost/main-probe.spec.ts` | `59af43d9db7c` |
| `probecost/playwright.config.ts` | `e253e44fa2bb` |
| `probecost/run_probe.sh` | `0736ce5bd83d` |
| `probecost/probe-runs.log` | `c139049e251b` |

Do not copy `node_modules`, `pw-out*`, `test-results`, `out` or `dist-branch`.

**Box rules (every Playwright run in this row).**
- L0 holds `/tmp/claude-1000/quiet-box.lock`, and no model-host row runs meanwhile.
- Wrap every Playwright command in `/tmp/claude-1000/hold_slots.sh`.
- Just before each wrapped run, paste `uptime` and `pgrep -fa "playwright|vitest|pytest"`. The 1-minute load must be below 1.5, and nothing that is not yours may appear. Otherwise wait up to 30 minutes, then report the processes.
- Never run pytest inside the wrapped command. `wait_quiet.sh` is the waiting pattern.
- Every run counts: no re-run to get a pass.

**Task 1: diagnosis (MEASURE; no product or harness change).** Use systematic-debugging.
1. **Copy the evidence.** Copy the files above into `docs/reviews/<run date>/stillness-nav-evidence/l0-2026-10-27/` and paste `sha256sum` against the table.
2. **Interleaved baseline on origin/main's dev server.** Use the mock API, as HC-UISH-009 does. In each batch, run the instrumented probe set and the bare-timer set back to back, alternating which goes first. Run 3 batches (15 + 15 runs). Record for each run:
   - the max gap;
   - when the gap ends, relative to the trigger;
   - any long tasks;
   - the load.
   If the probe misses 5 or more of 15 and the bare timer 3 or fewer, the difference is reproduced. If the baseline probe misses fewer than 5 of 15 in every batch, stop: report the tallies and box state as 'not reproduced' and run no variants. If both miss alike, the cause is in the page change, not the probe. Then run candidates 6-9 against the bare timer as well.
3. **One variable at a time.** Each variant differs from the baseline probe in one thing only. Where it applies, a second variant adds that one thing to the bare timer. Each variant gets 15 runs, interleaved with a baseline-probe control in the same batches. Variants live in the evidence copy, never in `src/`.

   | # | Candidate | Variant |
   |---|---|---|
   | 1 | Sampler start to trigger | the probe with a 100 ms wait between `startSampler` and the trigger, as the bare timer has |
   | 2 | Request tracking and the network-idle wait | the probe with `lazyRoute: false`; the bare timer with `trackRequests`' three listeners attached |
   | 3 | Playwright and CDP overhead | confirm trace, video and screenshot are off in the run's config (the repo config has `trace: 'on-first-retry'`, `screenshot: 'only-on-failure'`); count the CDP events in the window; a probe with no Node-side listeners |
   | 4 | Timer mechanism and stamp rounding | sampler ticks driven by `requestAnimationFrame` instead of `setInterval`; unrounded stamps (diagnostic only: G10's 16-40 ms spacing and the 40 ms bound stay) |
   | 5 | Per-tick reads | the sampler with `snapshot()` replaced by a bare stamp push |
   | 6 | Mock API response timing | log each mock response's time relative to the trigger and the gap; responses fulfilled after a fixed 50 ms and 150 ms |
   | 7 | Dev-server module work (HMR, on-demand transforms) | the same probe on a `vite preview` build of origin/main; dev with the vite client's HMR socket idle or closed |
   | 8 | Lazy route chunk load and parse | trace whether the gap overlaps the chunk's fetch, compile or evaluate; a variant with the route chunk imported before the trigger (diagnostic only: G10 probes the first visit, so this is never the fix) |
   | 9 | The route transition's commit | main's `AnimatePresence mode="wait"` + `PageTransition` commit in a trace; the probe under `reducedMotion: 'reduce'` |

4. **Name the task.** Take a Chromium performance trace (CDP `Tracing`, `devtools.timeline` categories) of 3 baseline runs that miss. Name the task or tasks that fill the gap: script URL and function, or browser work. A trace adds overhead, so use it to name the work, not to count misses.
5. **Decision rule (fixed now, before any run).** A candidate is the cause when:
   - (i) removing it alone brings the probe set to 15 of 15 at ≤ 40 ms, in batches where the baseline probe misses 5 or more of 15; and
   - (ii) where a bottom-up variant exists, adding it alone to the bare timer brings the bare timer to 5 or more of 15.

   Paste both RED (baseline) and GREEN (variant) outputs. If candidates only explain the misses together, report the combination. If none meets the rule, report "cause not found" with every tally.
6. **Report and stop.** Write `docs/reviews/<run date>/stillness-nav-evidence/README.md`. It holds every variant's tally, the box state per batch, the trace finding, the cause or "not found", and the proposed Task 2 kind and files. Push it, post it as a PR comment headed `## Task 1 report: tell L0`, and stop. Task 2 starts only after an `L0 ruling:` that names the kind and the files.

**Task 2: fix (test-first).**
1. **RED first.** The RED check is the instrumented navigation set: 5 routes × 3 batches on origin/main's dev server, each run's maximum gap judged against 40 ms. It runs from the committed evidence copy, on a quiet box. Paste the RED tally before the fix. If the fix is in `e2e/support/gates.ts`, regenerate `gates.instrumented.ts` from the fixed `gates.ts` plus only the `PROBECOST` logging lines, and paste `diff src/frontend/e2e/support/gates.ts <evidence>/gates.instrumented.ts` for both the RED (pre-fix) and GREEN (post-fix) copies, showing logging lines only.
   - If the fix is in app code and a regression test can pin it (for example a vitest case on the component the trace names), the L0 ruling names that test, and it is written first.
   - A CI spec that enforces 40 ms on navigation is not added: it would undo the owner's 70 ms rule.
2. **The fix, where Task 1 found the cause.**
   - **App code:** the smallest change in the named file, on main. UI-ROUTE-MOTION's opacity-only fade and the T0 rules stay. If the file is one #370 rewrites (`fe/components/layout/*`), the fix still lands on main first and #370 carries it over when it merges `origin/main`; L0 rules on that merge.
   - **Test harness:** the probe must keep its detection power:
     - every stillness self-test stays unchanged and green: HC-UIG-006 (a)-(o) including (h2), and its pass cases, HC-UIG-007 (a)-(b), and GATES-NAV-BOUND's navigation self-tests (`git diff origin/main...HEAD` on their spec files is empty);
     - a mutant that reverts the fix brings the instrumented set back to its RED tally. Paste it, then restore;
     - no bound constant changes: 40 ms, and the 70 ms navigation bound from GATES-NAV-BOUND;
     - a change to how a gap is measured (the `Math.round` on each stamp in `snapshot`, the gap arithmetic or comparison in `checkSampling`, or which samples count as post-trigger) is a bound change: stop and tell L0, who asks the owner;
     - a change to `STILLNESS_SAMPLE_MS`, `STILLNESS_WINDOW_MS`, `NETWORK_IDLE_MS`, the lazy-route rule or `checkSampling` needs the L0 ruling to name it, and G10's "samples every 16-40 ms" must stay true;
     - anything that makes the probe see less is not a fix: stop and tell L0. That includes fewer samples, a sampler that skips the page-change window, and a route visited before the trigger so that its first visit is never probed.
3. **No fix in reach.** Stop and tell L0 if:
   - the cause is outside the app and the harness (the box, WSL, Chromium); or
   - the only fix would change a bound.

**CI retries.** `playwright.config.ts` sets `retries: process.env.CI ? 2 : 0`, and the CI E2E step (`ci.yml`, `npx playwright test --project chromium`) has no `--fail-on-flaky-tests`. A test that fails and then passes on a retry is reported as "flaky", and the job still exits 0. So a green CI E2E job is not evidence that a stillness check passed. UI-SHELL pins `retries: 0` on HC-UISH-009 (below). This row changes neither `ci.yml` nor the global retries; other specs' retries are L0's to raise as a separate row.

**Acceptance:**
- The Task 1 report, and the `L0 ruling:` that followed it.
- The instrumented navigation set RED, then GREEN, with output.
- On a quiet box (box rules above), the branch's dev server, at the row's final head, shows a maximum gap of 40 ms or less in 15 of 15 runs of the instrumented navigation set. Do the same on a `vite preview` build of the same head.
- CI E2E is green on the final head. Read the E2E job log's summary: a `flaky` entry naming any stillness test (HC-UIG-00x, HC-UISH-009, GATES-NAV-BOUND self-tests) counts as a failure. The 40 ms figures are local (box rules); CI enforces the effective bounds, not this row's 40 ms target.
- HC-UIG-001…007 and GATES-NAV-BOUND's self-tests stay green.
- `npx tsc --noEmit` clean.
- `git diff origin/main...HEAD -- src/frontend/e2e/support/gates.ts` changes no bound constant.
- `git diff origin/main...HEAD | grep -E "test\.(fixme|skip|fail)\("` prints nothing.
- The evidence directory is committed.
- If 15 of 15 is reached, the PR body includes a draft owner question on returning navigation to 40 ms. L0 asks it; the row does not change the bound.

**Est:** 6 h (Task 1 about 4 h, Task 2 about 2 h). **MVP:** P1. It blocks no row since STILLNESS-NAV-70; the owner asked to "keep diagnosing".

**#370 (UI-SHELL)** resumes after GATES-NAV-BOUND merges, not after this row, with a new `L0 ruling:`:
- UI-SHELL merges `origin/main` and adds `test.describe.configure({ retries: 0 })` as the first line of every describe in `e2e/ui-shell.spec.ts` that holds an HC-UISH-009 test (on #370 `2148b54e`: `:292` "HC-UISH-003 route fade and HC-UISH-009 rail stillness", which pins HC-UISH-003 too; `:335` "HC-UISH-009 phone toggle label stays still"; and `:851` "Inherited stillness and focus halves", or the `:870` test moved into its own describe). The global `retries` and `ci.yml` are unchanged.
- HC-UISH-009 must pass at the effective bounds (70 ms on navigation, 40 ms elsewhere) on dev and on a `vite preview` build, on a quiet box, with every run counted.
- It must also pass in CI E2E on the final head, with no retry counted as a pass.

---

## 8. Session and safety deltas

### 8.1 SAFETY-MODE-REAL

Planned in [§7.2](#safety-mode-real--research-concrete-behaviours-for-the-safety-toggle-and-turn-them-into-an-owner-question). Sequence: research row → owner question SAFETY-MODE-BEHAVIOUR → a build row planned from the answer, with SAFETY-MODE-DIFF for each ask-first file → the build replaces UI-SHELL's disabled switch with a working one. Until then, [§3.6](#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real) holds. **Build rows planned 2026-10-24** from the owner's answer (prompt 51) in [2026-10-24-safety-mode-build-plan.md](2026-10-24-safety-mode-build-plan.md); SAFETY-MODE-TOGGLE replaces the disabled switch after UI-SHELL.

### 8.2 Delta to SESSION-REENTRY: Task 3 "Lock now"

Tasks 1 and 2 of SESSION-REENTRY are unchanged, with their gates (SESSION-REENTRY (a); SESSION-AUTH-DIFF for Task 2). Task 1 ships in today's styles; UI-TOKENS and UI-PRIM-CONTROLS restyle it automatically; UI-PG-AUTH restyles it fully (owner UI-AUTH-SCREENS "Layout, motion and Lift"). Task 1 merged as #312 (`7667439`).

**Task 3 (new, frontend only; owner SESSION-LOCK-NOW "Add Lock now", prompt 48):** a "Lock now" item in the profile menu calls the existing `useLockProfile()` (`fe/services/profiles.ts:186`; backend `POST /profiles/{profile_id}/lock`, `be/api/profiles.py:992`), clears the session the way logout does, and lands on the `/setup` unlock card. No backend change. **Files:** `fe/components/layout/ProfileMenu.tsx`, `fe/__tests__/ProfileMenuLock.test.tsx` (new, HC-SRE-011), `e2e/session-lock-now.spec.ts` (new, real backend, HC-SRE-012). **Checks** (#312 used HC-SRE-006…010): HC-SRE-011 the menu item calls the lock endpoint once and clears the auth store (RED); HC-SRE-012 after Lock now, a protected route shows the unlock card and the password unlocks it (RED). **Depends on:** UI-SHELL (ProfileMenu); Task 1 merged (#312). Ready as soon as UI-SHELL merges. **Est:** 1 h. **MVP:** P2.

---

## 9. Reconciliation with rows already on main

| Existing row (status on `origin/main` @ `f1fc174`) | Overlap | Rule |
|---|---|---|
| SESSION-REENTRY (Task 1 **merged**, #312 `7667439`; Task 2 gated; Task 3 ready once UI-SHELL merges) | unlock UI; `ProfileSetup.tsx` | no new unlock row; UI-PG-AUTH depends on Task 1; Task 3 added as a delta (§8.2); UI-MOTION never beside Task 1 |
| MVP-REAUTH-401 (**merged**, #321 `fa635f5`) | `DangerZone.test.tsx`, `BackupRestoreFlow.test.tsx`, `services/api.ts` | UI-PG-SECURITY keeps its HC-RA4 cases green; services files untouched by any UI row |
| FE-IMPORT-ERROR (**merged**, #313 `f1fc174`), IMPORT-SCANNED-PAGE (blocked) | `DocumentInbox.tsx`, `e2e/document-import.spec.ts` | UI-PG-DOCUMENTS keeps HC-FIE green and is never beside IMPORT-SCANNED-PAGE; UI-MOTION never beside either |
| FE-VERIFY-NUMERIC (ready, P1) | `VerificationWorkbench.tsx` | UI-PG-REVIEW depends on it; UI-MOTION never beside it |
| FE-EXPLAIN-ERR (**merged**, #314), BADGE-TICK (ready, P2) | `ExplainAssistant.tsx` and its test | UI-PG-ASK keeps HC-FEE green and depends on BADGE-TICK; UI-MOTION never beside BADGE-TICK; UI-PG-ASK's e2e send selector uses the "Send question" name #314 added |
| GAUGE-ZERO-WIDTH (**merged**, #319) | `ReferenceRangeComparison.tsx`, `fe/__tests__/ReferenceRangeComparison.test.tsx` | UI-PG-RESULTS replaces the gauge with RangeTick and keeps HC-GZW-001…003 green; HC-UIRR-008 covers the same cases on RangeTick |
| AXE-E2E (ready, P2) | `package.json`; axe in e2e | UI-GATES and UI-MOTION depend on it; its `KNOWN_A11Y` entries are removed by the page rows that fix them (an entry may only be removed) |
| E2E-UIFULL-CI (ready, P1) | `ui-routes-verification.spec.ts` | UI-SHELL depends on it and updates nav labels only |
| CI-CACHE (ready, P2) | `ci.yml` | UI-BUDGET never beside it |
| DON-COPY-V3 (blocked) | `DataDonationCard.tsx` | UI-PG-SETTINGS never beside it; consent text untouched by UI rows |
| FE-A11Y-DIALOGS (bullet, not planned) | dialogs without Escape or focus trap | **planned here**: UI-PRIM-OVERLAYS plus the page rows that own each dialog (Settings export and consent dialogs: UI-PG-SETTINGS; dose modal: UI-PG-MEDS; preview: UI-PG-DOCUMENTS; edit value: UI-PG-REVIEW) |
| CHAT-MODEL-BADGE, INTERP-GROUNDED-MD, INTERP-RENDER-2, VERIFY-DOCS-STALE (#295); INTERP-REGEN-500 (#320), CPU-DEFAULT-PHI4 (#315), OLLAMA-NUM-CTX (#318): backend only | done | their tests stay green inside the page rows that move those components |

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
| R12 | Every page change fades the whole page, values included, for about 200 ms (owner UI-ROUTE-MOTION, an exception to "stay still" for page changes only); a later change could widen the exception by accident (a transform, a slower fade, a re-fade) | HC-UISH-003 checks every route: opacity only, ≥ 0.35, done within 240 ms, then still; G10 checks each T0 node's text, colour, background, clip-path, filter, transform and rect throughout, allows only the container's own opacity during the fade window, and fails on any other motion; under reduced motion the change is instant. Overlays holding values still open with M0 (an L0 reading the owner's answer does not cover) |
| R8 | The relabelled toggle could still be read as safety being off | the visible note says the standard checks always run; HC-UISH-006 pins it; SAFETY-LABEL-WORDING lets the owner choose another wording |
| R9 | IA renames break muscle memory, docs and capstone screenshots | old routes redirect; names are one file; open question UI-NAV-NAMES |
| R10 | `thinking-orbs` is a 0.x package | MIT, no runtime dependencies or network code; isolated behind `ThinkingOrb`, lazy, on two routes; replacing it is one file |
| R11 | Results of the INP proxy come from headless Chromium, not real devices | G3 runs on a production build with CPU ×4; real-device checks stay on the "not verified" list |

---

## 11. Owner gates and open questions

The gates and questions listed under "Execution gates" and "Open questions" below are not answered; the three answered in prompt 48 are listed first. L0 numbers and asks the open ones; the owner's words are recorded verbatim in owner-decisions. Wording is a draft, written neutrally.

**Answered (prompt 48, L0 evidence comment 6380025171 on PR #311):** UI-ROUTE-MOTION "Whole-page fade", UI-AUTH-SCREENS "Layout, motion and Lift", SESSION-LOCK-NOW "Add Lock now" (§1).

**Answered 2026-10-28 (L0 AskUserQuestion; owner-decisions row STILLNESS-GAP-BOUND):** STILLNESS-GAP-BOUND "Fix first, frame waits", then, the same day in chat, STILLNESS-NAV-70 "Raise it to 70 ms for page changes and keep diagnosing" (owner-decisions row STILLNESS-NAV-70). Effective rule: navigation probes allow sampling gaps up to 70 ms (row [GATES-NAV-BOUND](#gates-nav-bound--navigation-stillness-probes-allow-70-ms-sampling-gaps)), every other stillness check keeps 40 ms, and the minimum-sample rule is unchanged. UI-SHELL waits for GATES-NAV-BOUND. [STILLNESS-NAV-LATE](#stillness-nav-late--find-and-fix-why-page-changes-run-late-under-the-stillness-probe) keeps diagnosing at a 40 ms target and changes no bound.

**Execution gates (a row waits for the answer):**

- **SAFETY-MODE-BEHAVIOUR** (after SAFETY-MODE-REAL): asked with the research's options; no recommendation until the research exists.
- **SAFETY-MODE-DIFF** (merge or execution, per ask-first file the chosen behaviour touches): asked with the exact diff.

**Open questions (rows proceed with the default stated; the answer may change a file later):**

- ~~**SAFETY-LABEL-WORDING.**~~ **Answered 2026-10-26** (L0 AskUserQuestion; owner-decisions row SAFETY-LABEL-WORDING): "Keep plan default (Recommended)", the first option below, so the default stands and the question is closed. As asked, the question carried the appended parenthetical "(The phone layout you just chose is built with the first option.)". Draft as written: "Until the safety toggle does something, how should it read?" Options: "'Stricter safety mode', disabled, with 'Not available yet. The standard safety checks always run.'" (the plan's default) / "'Extra safety checks · coming soon', disabled, with the same note" / "A short note only: 'Safety checks always on', with no switch until the real one is built" (this departs from "keep a toggle").
- **UI-NAV-NAMES.** "Which navigation names should ship?" Options: "Documents, Review values, Results, Ask, Follow-ups, Doctor summary" (default) / "Documents, Review, Results, Ask, Tasks, Doctor summary" / "Today's names (Inbox, Verify, Trends, Explain, Tasks, Export) with only the grouping".
- **UI-BRAND-MARK.** "Keep the heart logo or move to a mark drawn from the pencil-and-ink idea?" Options: "New mark" (default) / "Keep the heart".
- **MED-BADGES.** "The medication badges ('Week Warrior', 'Comeback Kid') lose their celebration animation either way. What should happen to the badges themselves?" Options: "Keep as today, static" (default) / "Off by default, shown only if streaks are turned on" / "Remove them".
- **UI-ABOUT-PLACE.** "Where should the About page be reachable?" Options: "Inside the app, from the profile menu" (default) / "Also before sign-in, from the setup screen" (this adds a link to an auth screen) / "Only by its address, for the demo".
- **INK-MOMENT.** "When you mark a value as checked, its dot on the chart fills in over a third of a second; the number itself never moves. Keep that, or make the change instant?" Options: "Keep the fill" (default) / "Instant".

**L0 tells the owner (not gates):** the Undo the designers drew on verify needs a backend row (VERIFY-UNDO); the idle-lock warning needs the unread auto-lock setting (AUTO-LOCK-UNUSED, ask-first auth).

---

## Appendix A: e2e assertions and the row that changes each

Every assertion in `src/frontend/e2e/*.spec.ts` on `257e072`, re-read after #312 (`7667439`, which added `session-reentry.spec.ts` and shifted `auth.spec.ts` by 8 lines) and #313 (`f1fc174`, which rewrote E2E-DOC-003), grouped by spec, with the first row whose change breaks it (or "kept", with the row that must keep it). Method: `grep -n "expect\|getByRole\|getByText\|getByLabel\|getByPlaceholder\|locator(\|toHaveURL\|toBe("` over each spec, each line read against the rows' Files and Specs. A changed assertion is the same or a stricter assertion with a new value; none is removed or loosened.

| Spec:line | Test | Asserts | Row | Old → new |
|---|---|---|---|---|
| `tailwind4-styles:138` | TW4-RECOVER | `#recover-code` border colour | UI-TOKENS, then UI-PG-AUTH | `rgb(229, 231, 235)` → `rgb(226, 223, 215)` (`--line`) → `rgb(138, 133, 123)` (`Input`, `--line-strong`) |
| `tailwind4-styles:139-141` | TW4-RECOVER | placeholder colour | UI-TOKENS | `rgb(156, 163, 175)` → `rgb(104, 100, 93)` (`--ink-3`) |
| `tailwind4-styles:156` | TW4-FOCUS | focus `box-shadow` not `none` | kept (UI-TOKENS keeps the ring) | — |
| `tailwind4-styles:167` | TW4-INBOX | seeded file name visible on `/inbox` | kept (UI-PG-DOCUMENTS) | — |
| `tailwind4-styles:170-173` | TW4-INBOX | first nav link ≥ 44 px, `min-height: 44px`; landmark "Main navigation" | kept (UI-SHELL) | — |
| `tailwind4-styles:177-178` | TW4-INBOX | body background | UI-TOKENS | `rgb(250, 250, 248)` → `rgb(246, 245, 241)` (`--paper`) |
| `tailwind4-styles:180-181` | TW4-INBOX | brand colour | UI-TOKENS (value), then UI-SHELL (selector) | colour `rgb(31, 31, 31)` → `rgb(28, 27, 25)` (`--ink-1`); selector `aside h1` → `aside [data-brand]` |
| `tailwind4-styles:185-188` | TW4-INBOX | "Profile and settings" button enabled, parent `cursor: auto`, button `cursor: pointer` | kept (UI-SHELL keeps the name on the profile trigger) | — |
| `tailwind4-styles:196-201` | TW4-INBOX | focused nav link has no outline (ring is a box-shadow) | kept (UI-TOKENS) | — |
| `tailwind4-styles:211, 218, 224, 239, 247, 253` | TW4-INBOX-DARK, -VERIFY, -TRENDS, -SEARCH, -EXPLAIN, -SETTINGS | seeded text or a Settings heading visible (screenshots) | kept (`/trends` redirects to `/results` from UI-PG-RESULTS and still shows glucose) | — |
| `tailwind4-styles:232-233` | TW4-TIMELINE | `Lab results (` title and medication name | kept (UI-PG-RECORDS keeps the title) | — |
| `tailwind4-styles:261-266` | TW4-MEDS | medication name, "Log" button, "Log Dose" heading | kept (UI-PG-MEDS) | — |
| `tailwind4-styles:269-270` | TW4-MEDS | "Close" button corner radius | UI-PG-MEDS | `'8px'` → `'10px'` |
| `auth:28-41` | E2E-AUTH-001 | "Create a new profile" button (when a profile exists), "Profile Name" label, "Create a secure password" placeholder, "Create Your Profile" button | kept (UI-PG-AUTH) | — |
| `auth:44` | E2E-AUTH-001 | progress text | UI-PG-AUTH | `'Creating secure vault...'` → `'Creating your profile…'` (the Button loading label, tied to the real request) |
| `auth:50-65` | E2E-AUTH-001 | recovery code shown, continue disabled until the checkbox, lands on `/inbox` | kept (UI-PG-AUTH; SESSION-REENTRY) | — |
| `auth:73-89, 97, 123, 147` | E2E-AUTH-002…005 | "Create a new profile" / "Profile Name"; "Password is required"; redirects to `/setup` | kept | — |
| `session-reentry:22-25` | HC-SRE-004 helper | recovery-path matcher | kept | — |
| `session-reentry:60-64, 76` | HC-SRE-004 | `/setup`, "Unlock your profile", labels "Profile" and "Unlock password", button "Unlock" | kept (UI-PG-AUTH) | — |
| `session-reentry:80` | HC-SRE-004 | lands on `/inbox` | kept | — |
| `session-reentry:81` | HC-SRE-004 | heading `'Document Inbox'` | UI-MICRO | → heading `'Documents'` |
| `session-reentry:82-85` | HC-SRE-004 | no "Your session has ended", no "Access denied", no recovery path, no recovery calls | kept | — |
| `recovery-code:20-72` | E2E-RECOV-001, 002 | "confirm your password" label, create/replace button names, `recovery-code-*` test ids, code not shown after reload | kept (UI-PG-SETTINGS default section; UI-PG-SECURITY) | — |
| `routing:15-16` | E2E-ROUTE-001 | unknown path → URL and h1 | UI-OVERVIEW | `/\/inbox$/`, `'Document Inbox'` → `/\/overview$/`, `'Overview'` |
| `routing:22-23, 43` | E2E-ROUTE-002 | `main` and an h1 visible; nav landmark "Main navigation" | kept (UI-SHELL) | — |
| `routing:46` | E2E-ROUTE-002 | nav link name | UI-SHELL | `'Trends'` → `'Results'` |
| `routing:47-48` | E2E-ROUTE-002 | URL and h1 after the click | UI-PG-RESULTS | `/\/trends$/`, `'Trends Dashboard'` → `/\/results$/`, `'Results'` |
| `routing:50-52, 57` | E2E-ROUTE-002 | Timeline link, URL, h1; main never empty | kept | — |
| `settings-smoke:29-31` | E2E-SET-001 | hardware-detect button on `/settings` | UI-PG-SETTINGS | navigate to `/settings?section=advanced` and press "Show advanced settings" first; same assertion |
| `settings-smoke:41-48` | E2E-SET-002 | tier names visible | UI-PG-SETTINGS | same navigation first |
| `settings-smoke:55-66` | E2E-SET-003 | external API switch and consent text | UI-PG-SETTINGS | navigate to `/settings?section=assistant-privacy` first |
| `settings-smoke:85-102` | E2E-SET-004 | `tier-row-*` rows, one availability state each | UI-PG-SETTINGS | Advanced section first |
| `medication-detail:29-98` | E2E-MED-001…003 | `a[href^="/medications/"]` links, detail URL, an h1/h2, no error text | kept (UI-PG-MEDS: MedicationCard becomes that link) | — |
| `document-import:23-27` | E2E-DOC-001 | `/inbox` URL; "No documents yet… Import your first" | kept (UI-PG-DOCUMENTS) | — |
| `document-import:35-158` | E2E-DOC-002…005 | file input; file name; status words "pending", "needs review", "parsed", "verified", "ocr required" (case-insensitive); E2E-DOC-003 (`:77-84`, #313): a `role="alert"` containing the file name and "Import failed", and no row heading named after the rejected file | kept (UI-PG-DOCUMENTS keeps the alert and the row name as a heading) | — |
| `assistant:52, 78` | E2E-RAG-001, 002 | `/explain assistant\|ask about your results/i` text | UI-MICRO | → `getByRole('heading', { level: 1, name: 'Ask' })` |
| `assistant:102, 121, 148, 213, 229, 245, 258` | E2E-RAG-003…005 and unnamed tests | `/explain assistant/i` text | UI-MICRO | → `getByRole('heading', { level: 1, name: 'Ask' })` |
| `assistant:57, 83, 113, 160, 216, 234, 247, 267` | several | placeholder `/ask about your results/i` | kept (UI-PG-ASK) | — |
| `assistant:61, 85, 162, 220, 236, 249, 261` | several | send button = last button with an svg | UI-PG-ASK | → `getByRole('button', { name: 'Send question' })` |
| `assistant:105-114` | E2E-RAG-003 | suggested question fills the input | kept (UI-PG-ASK) | — |
| `assistant:124-125` | E2E-RAG-004 | "does not provide medical advice", "always consult your healthcare provider" | kept (T0, UI-PG-ASK) | — |
| `assistant:150-153` | E2E-RAG-005 | combobox "Document Category" with value `imaging` | kept (UI-PG-ASK keeps a native select) | — |
| `assistant:223` | loading state | `/searching documents\|generating response/i` | UI-PG-ASK | → `/reading your verified results/i` |
| `assistant:68-69, 91-95, 171, 239, 252, 264, 271` | several | answer or fallback text, the user's message, input clears, send disabled/enabled | kept | — |
| `ui-full-verification:62, 66, 70-72` | E2E-UI-FULL-001 | "Upload medical documents" input; file name; status words (case-sensitive "Needs Review", "OCR Required") | kept (UI-PG-DOCUMENTS) | — |
| `ui-full-verification:80` | E2E-UI-FULL-002 | `main` visible on each route | kept | — |
| `ui-full-verification:92-95` | E2E-UI-FULL-002b | "More options" → "Review extracted values" → `/verify?doc=…&mode=all` | kept (UI-PG-DOCUMENTS) | — |
| `ui-full-verification:96` | E2E-UI-FULL-002b | `/verification workbench/i` | UI-MICRO | → `getByRole('heading', { level: 1, name: 'Review values' })` |
| `ui-full-verification:105` | E2E-UI-FULL-003 | `/explain assistant/i` | UI-MICRO | → heading `'Ask'` |
| `ui-full-verification:110` | E2E-UI-FULL-003 | send button = last svg button | UI-PG-ASK | → `getByRole('button', { name: 'Send question' })` |
| `ui-full-verification:124` | E2E-UI-FULL-004 | "Configure AI model and hardware preferences" | kept (UI-PG-SETTINGS) | — |
| `ui-full-verification:127-130` | E2E-UI-FULL-004 | Detect Hardware, then RAM / Recommended Tier | UI-PG-SETTINGS | open the Advanced section first |
| `health-smoke:6-8` | E2E-HEALTH-001 | `/health` 200 | kept (backend) | — |

`e2e/ui-routes-verification.spec.ts` does not exist on `257e072`; E2E-UIFULL-CI creates it (and may move the `ui-full-verification` assertions above into it). If it does, the same contract changes apply there, and UI-SHELL updates its nav labels.

Back to: [queue](2026-10-15-build-program/queue.md) · [RUNBOOK](2026-10-15-build-program/RUNBOOK.md) · [research package](../research/2026-10-23-frontend-revamp/00-README.md)
