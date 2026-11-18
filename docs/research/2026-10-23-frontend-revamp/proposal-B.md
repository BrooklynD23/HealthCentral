# Proposal B: "Quiet Instrument", a frontend revamp for Asclexis

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes and the prototype profile name, replaced by the fixture name "Alex Rivera" (owner UI-FIXTURE-NAME, prompt 45). Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

Author: Designer B (Opus 5.5). Date: 2026-10-23. Base: `main` @ 7749744. I read nothing written by Designer A.
Inputs: `owner-direction.md`, `framing.md`, `ui-review.md`, `COMPONENT_AUDIT.md`, `capture-metrics.json`,
`build-output.txt`, the screenshots in `shots/`, the four `research-*.md` files, `docs/02_frontend_accessibility_plan.md`
(:107 "Clinical Calm", :155 "Restraint with purpose"), and `src/frontend`.
Skills used: `emil-design-eng`, `awwwards`, `animate`, `animation-performance` and `improve-animations`, plus the Impeccable
reference guides `mode-operate`, `craft-floor` and `colorize`, which I read but did not run. `review-animations` cannot
be called by a model (`disable-model-invocation`), so I applied its standards through `animate`. I recommend the owner runs
`/review-animations` on the first motion PR.

The prototype is [`proto-B.patch`](proto-B.patch) in this folder (a diff against `src/frontend` at `7749744`; it ran from `proto-B/frontend` in L0 scratch, on vite port 5182 with a mocked API). Its screenshots were in the L0 scratch `proto-B/shots/` (the ones kept are in `shots/` here, prefixed `B-`) and §10 covers it. Other `proto-B/` paths below (`sizing/`, `probe-*.mjs`, `capture-results.json`) are L0 scratch, not committed.

---

## 0. My position on the central tension

**SaaS craft, yes. SaaS engagement mechanics, no.** These two goals do not conflict once you notice that what makes Linear, Stripe or
Vercel feel engaging is mostly **speed, feedback and orientation**: an instant response to every click, a command palette,
optimistic updates, skeletons that hold the layout steady, and a single place to find everything. Very little of it is
animation. The "Clinical Calm" brief is right about tone and wrong in one detail. The shipped UI fails it through slowness and
inconsistency, and too much motion is not the cause. The worst motion defect today is a **450 ms blank gap on every navigation**
(`probe-log.txt`), and fixing it removes animation.

I reconcile the two directions with one rule, **the Motion Gradient: how much a thing may move goes down as its clinical
weight goes up.**

| Tier | What it covers | Motion allowed |
|---|---|---|
| **T0 Data** | lab values, ranges, units, dates, disclaimers, citation text, verification state | **Never moves after first paint.** No count-ups, no colour pulses, no "abnormal" emphasis motion. The only exception is the once-per-session Range Ribbon draw, which is *value-blind* (every point animates the same way whatever its value). |
| **T1 Structure** | pages, cards, lists | Enter only, ≤240 ms, starting from opacity .35 (never from invisible), with a 6 px rise. No exits on routes. |
| **T2 Chrome and controls** | buttons, nav, palette, sheets, popovers, toasts | Fully tactile: press feedback within one frame (scale .97), CSS-transitioned indicators, interruptible transitions. Things opened 100+ times a day, such as the palette and keyboard actions, get **no** animation. |
| **T3 Moments** | import finished, value verified, unlock | The "delight budget". These are rare, earned by the *user's own action*, and never tied to a health result. |

Concretely, against the existing brief:

- I **reject** "smooth number transitions for trend changes" (`02_frontend_accessibility_plan.md:160`). Counting a glucose value up
  from 92 to 118 flashes numbers that were never measured, and on a lab result that amounts to a fabricated reading.
- I **keep** "one well-orchestrated moment beats scattered animations" and cap signature moments at three.
- I **reject** the 2–4% noise overlay and decorative glassmorphism (`:177`). On a working screen, atmosphere comes from a single
  warm light source on the canvas and from the range-band material.
- I **reject** gamified streak badges such as "Week Warrior" and "Comeback Kid", confetti, nudges and telemetry. This is the
  "engagement" half of SaaS, and the docs already rule it out (`framing.md`). It is listed as an owner question in §9.

---

## 1. DEPTH and RANGE

### DEPTH: what a top product and motion team would do that the brief does not ask for

1. **Fix the feel before adding motion.** Remove `AnimatePresence mode="wait"` and let routes render immediately, with
   enter-only motion and prefetch on hover or focus. Today every click goes fade-out, blank, spinner, fade-in.
2. **Give the app a way back in.** A returning patient whose 60-minute JWT has expired lands on "Create Your Profile"
   (`60-expired-session-landing-1440.png`). A SaaS team would treat that as a severity-1 bug before touching visuals. This is an **owner gate** (auth flow).
3. **Design mobile instead of shrinking desktop.** Every authenticated route currently scrolls horizontally at 390 px
   (scrollWidth 588–1,077).
4. **Make provenance the product's core interaction.** Citations open on tap, click or keyboard (not hover only) and show the exact
   quoted line and page. Trust is the conversion metric for this product.
5. **Build a token system that passes contrast by construction**, with a test that fails the build if any pair drops below 4.5:1.
   The 314 failing axe nodes are a token problem, not 314 separate problems.
6. **Use one overlay primitive.** Six hand-built modals have no Escape handling, no focus trap and no focus return.
7. **Remove dishonest UI:** the placebo "Safety Mode" toggle, dead buttons, the "CBC" tab that shows Glucose, and the model chip that
   names phi-3-mini while answers come from templates.
8. **Browser surfaces:** themed selection, focus rings that appear instantly (the 200 ms `transition-all` fade is a bug),
   tabular numerals everywhere a number is compared, and a favicon (it currently returns 404).

**Raw material:** the real data shapes in `services/types.ts` (`Observation`, `TrendData` with `ref_low/ref_high`, `user_verified`, D4
unverified points), real report-style copy ("This is what your report states"), and real lab panels. The prototype mocks these
shapes exactly, with no lorem ipsum.

**Methods and tools:**
- React 18.3 plus Tailwind v4 tokens, with `@theme inline` over CSS variables so light and dark are composed separately.
- Motion 14 (`motion/react`, `LazyMotion` + `m`, `MotionConfig reducedMotion="user"`) for springs and exits only.
- CSS transitions, keyframes or WAAPI for everything that plays during navigation. These run on the compositor
  (Emil and Vercel's tab-indicator lesson).
- Radix primitives for overlays (already in the stack), Sonner for toasts, cmdk for the palette (with a fix, see §7).
- Custom SVG in place of Recharts for the one chart that matters.

**The goal beyond the goal:** *a stakeholder or grader who has never seen Asclexis imports a lab report and within a minute trusts what
they see, because every number shows where it came from, every click answers in one frame, and nothing on screen tries to alarm or
hook them, so the capstone reads as a product shipped by a disciplined team rather than a student template.*

### RANGE: what I take from other fields

- **Game UI:** zero dead clicks; press feedback on *every* pressable, including raw `<button>`s; a persistent HUD line, which becomes the
  Safety Rail (§5) because it never moves; an instant palette as the "quick menu".
- **Film and motion design:** one choreographed moment per screen (the Ribbon draw: band first, line second, points last at 40 ms
  intervals) with weight from a strong ease-out. No other element competes with it.
- **Native apps:** a bottom tab bar on phones, sheets that rise from the bottom with the iOS drawer curve, optimistic UI on verify,
  native scroll everywhere (**no Lenis**: nested scroll panes, zoom and screen magnifiers matter more than marketing smoothness).
- **Precision instruments** (lab analysers, a good multimeter): this is the name of the art direction. The display is calm, the
  needle is honest, and the scale is printed on the instrument. Here the "scale" is the lab's own reference range, drawn as a band.

---

## 2. Rewritten build brief

> Build Asclexis's frontend as a **quiet instrument**: a local-first health-records app that feels like a top-tier SaaS product
> because it is fast, legible and honest, not because it moves a lot.
>
> **Outcome:** a first-time user imports a report, verifies the values, and reads a result with its provenance within 60 seconds, on a
> 390 px phone or a 1440 px laptop, in light or dark, with a keyboard or a screen reader, and never sees a blank frame, a dead click,
> or a number without a source.
>
> **Must:**
> 1. A responsive shell with grouped navigation (Records / Understand / Care / Share), a phone tab bar, a command palette (Ctrl K and /),
>    a skip link, one h1 per page, and the Safety Rail.
> 2. A token system (colour, type, space, radius, elevation, motion) with tested WCAG 2.2 AA contrast in both themes.
> 3. Primitives for button, field, select, checkbox, switch, dialog, sheet, popover, tooltip, tabs, toast, skeleton, empty state and
>    status chip. These are the only way overlays and form controls appear.
> 4. A Results screen that merges Trends and Interpret and has the Range Ribbon as its hero. Citations use Provenance Peek.
> 5. Every motion follows the Motion Gradient and the token set in §3.5. All motion is transform, opacity or clip-path; reduced motion
>    keeps opacity and drops movement.
> 6. Budgets: CLS < 0.1 (target < 0.05), INP < 200 ms, axe 0 serious or critical on every route in both themes, main chunk ≤ 185 kB gzip
>    (today 180), no horizontal scroll at 390 px.
>
> **Must not:** count up lab values, animate disclaimers or citations, use colour alone for range state, hide anything behind hover only,
> fetch anything at runtime from a network, or change auth, encryption or redaction behaviour without the owner's yes.

---

## 3. Art direction

### 3.1 Colour tokens (light "Paper", dark "Night Lab")

Every theme is composed on its own. The accent is a deeper teal that is still recognisably Asclexis. Range states use **shape and text first**; colour
only supports them. The outside-range colour is a terracotta ink, not an alarm red. Hex values are what I ship. The ratios below were computed with
the WCAG relative-luminance formula by `proto-B/sizing/contrast.mjs`, and these exact values are live in the prototype (`src/frontend/src/proto/tokens.css` in [`proto-B.patch`](proto-B.patch)).

| Role | Light | Dark |
|---|---|---|
| canvas | `#F8F7F3` | `#111413` |
| raised (cards) | `#FFFFFF` | `#181C1A` |
| well (muted fill) | `#F1EFEA` | `#202523` |
| sunken | `#E8E6E0` | `#0C0E0D` |
| fg (ink) | `#1B1D1A` | `#ECEEE9` |
| fg-2 (secondary) | `#4F534D` | `#B9BEB6` |
| fg-3 (tertiary; **fixes 2.69:1**) | `#686C66` | `#979D95` |
| line (decorative dividers) | `#DEDBD3` | `#2C322F` |
| line-strong (control boundaries) | `#8A8D85` | `#6E756F` |
| brand | `#1E6B5E` | `#6CC9B5` |
| brand-ink (brand text) | `#185A4F` | `#7FD3C0` |
| brand-wash | `#E2F0EC` | `#17302A` |
| on-brand | `#FFFFFF` | `#06201A` |
| band (reference range fill) | `#D9EBE5` | `#1C3A33` |
| inrange / wash | `#2E6A45` / `#E7F2EA` | `#93D6A8` / `#16281D` |
| outside / wash | `#94422F` / `#FBECE7` | `#F2A893` / `#33201A` |
| caution / wash | `#7C5214` / `#FAF0DE` | `#E9C57E` / `#2E2615` |
| info / wash | `#2F5C86` / `#E8F0F8` | `#A3C6EC` / `#172433` |

**Contrast ratios, every text/background pair used (AA text ≥ 4.5; UI boundaries ≥ 3):**

| Pair | Light | Dark |
|---|---|---|
| fg on canvas / raised / well | 15.83 / 16.97 / 14.77 | 15.86 / 14.73 / 13.31 |
| fg-2 on canvas / raised / well | 7.32 / 7.84 / 6.83 | 9.80 / 9.10 / 8.22 |
| **fg-3 on canvas / raised / well** | **4.99 / 5.35 / 4.66** (was 2.69 / — / 2.57) | 6.68 / 6.21 / 5.61 |
| brand-ink on brand-wash (active nav; was 4.36) | 6.85 | 8.03 |
| brand-ink on canvas / raised | 7.49 / 8.03 | 10.57 / 9.82 |
| on-brand on brand (primary button; was 4.91) | 6.33 | 8.67 |
| brand (focus ring, icons) on canvas / raised | 5.90 / 6.33 | 9.41 / 8.74 |
| line-strong on raised / canvas (non-text, 1.4.11) | 3.37 / 3.14 | 3.64 / 3.92 |
| inrange on its wash / raised (was 2.60) | 5.60 / 6.43 | 9.17 / 10.19 |
| outside on its wash / raised (was 2.95) | 5.93 / 6.82 | 7.93 / 8.85 |
| caution on its wash / raised (was 2.08) | 6.05 / 6.83 | 9.08 / 10.45 |
| info on its wash / raised (was 3.17) | 6.09 / 7.01 | 8.86 / 9.71 |
| fg / fg-2 / brand on band | 13.71 / 6.34 / 5.11 | 10.56 / 6.52 / 6.26 |

Rules:
- `line` is decorative only. Any boundary that identifies a control (inputs, checkboxes, the secondary-button outline) uses `line-strong`.
- `status-critical` stops being an alias of `attention`. There is no "critical" visual tier at all, because the app does not triage.
- The undefined `status-success`, `status-danger` and `muted-foreground` map to `inrange`, `outside` and `fg-2`. A lint test fails the build on unknown colour utilities.

### 3.2 Typography

Keep the three self-hosted families (`@fontsource`, already local). Change *where* each is used:

| Token | Size / line height | Family and use |
|---|---|---|
| `numeral` | 56 / 1.0 | Fraunces 500, tabular lining figures, −0.03em. **The hero value only.** |
| `h1` | 36 / 40 (28 / 34 on phones) | Fraunces 600, −0.025em, one per page |
| `h2` | 28 / 34 | Fraunces 600 |
| `h3` | 22 / 28 | Fraunces 600, **nothing smaller than 22 in Fraunces** (fixes "serif at 16 px reads as decoration") |
| `lead` | 19 / 28 | Source Sans 3 |
| `body` | 17 / 26.4 | Source Sans 3. The base moves from 16 to 17 for the older-patient audience (`plan :6`). Measure ≤ 68ch. |
| `ui` | 15 / 21.6 | Source Sans 3 500/600: controls, list rows, card subheads |
| `cap` | 13 / 18.4 | Source Sans 3. **Floor size.** `text-[10px]` and `text-[9px]` (17 uses) are banned. |
| mono | 15 | JetBrains Mono **only** for recovery codes and file hashes. Lab values use tabular Source Sans or Fraunces, never mono. |

Sentence case everywhere ("Glucose", never "GLUCOSE"). Raw identifiers (`lab_csv`, `hdl_cholesterol`) never reach the UI. A display-name map
covers them, and a vitest asserts no `snake_case` text node renders on the main routes.

### 3.3 Space, radii, elevation, texture

- **Space:** a 4 px base, using the steps 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 and 96. Page gutter is 16 on phones, 24 on tablets and 40 on desktops. Sections are separated by
  32–48; groups inside a card by 24; rows by 8–12. There is more space above a heading than below it.
- **Radii:** 6 (chips inside controls), 10 (controls and nav items), 14 (popovers, small cards), 18 (content cards), 20 (dialogs and the palette),
  full (status chips only).
- **Elevation is declared once, as a border or a shadow, never both:**
  E0 is the canvas. E1 is a card: `raised` with a 1 px `line` border and no shadow, so cards stop "lifting" on hover because they are not
  pressable. E2 is an overlay (popover, menu, toast): the `shadow-overlay` token, 0 12 32 −12 at 22%. E3 is a modal (dialog, palette, sheet):
  the `shadow-modal` token with a 36% scrim and **no backdrop blur** (blur over a whole viewport is costly and reads as template).
- **Texture:** none. Atmosphere comes from one fixed radial light source (`--glow`, brand at 6–7% from the top left) and from the range band
  material. `subtle-noise`, `glass-card`, `stagger-animation` and `animation-delay-*`, all unused today, are deleted.

### 3.4 Iconography

Lucide, one stroke weight (1.75 at 18 px), and always paired with a label in nav. The heart logo becomes a simple trace mark (see the prototype). It reads
as an instrument, not a dating app.

### 3.5 Motion tokens

| Token | Value | Use |
|---|---|---|
| `--ease-out-expo` | `cubic-bezier(0.23, 1, 0.32, 1)` | all enters and exits, press release |
| `--ease-in-out-strong` | `cubic-bezier(0.77, 0, 0.175, 1)` | on-screen movement (indicator moves, reorders) |
| `--ease-drawer` | `cubic-bezier(0.32, 0.72, 0, 1)` | sheets |
| `ease` | built-in | colour and hover only |
| `--dur-press` | 120 ms | press feedback |
| `--dur-hover` | 150 ms | hover colour |
| `--dur-sm` | 180 ms | popover, tooltip, toast content |
| `--dur-md` | 240 ms | route enter, nav indicator, dropdown, list item |
| `--dur-lg` | 320 ms | dialog and sheet enter (exit = 0.66 × enter) |
| `--dur-draw` | 640 ms | Range Ribbon only (T3 choreography) |
| spring `snappy` | `{ type:'spring', visualDuration:.22, bounce:0 }` | sheet snap, drag release |
| spring `settle` | `{ visualDuration:.35, bounce:.1 }` | the only bounce in the app: the verify check morph (moment 3) |
| stagger | 40 ms, capped at 6 items (≤ 240 ms total), first view per session only | lists |

**Motion recipes** (referenced by code in the §6 map). All use transform, opacity or clip-path only and are interruptible. Each has its reduced-motion form listed.

| Code | Recipe | Reduced motion |
|---|---|---|
| **M0** | none: instant state change | — |
| **M1** | press: `scale(.97)` on `:active`, 120 ms ease-out-expo | no scale; colour change only |
| **M2** | hover: background or colour 150 ms `ease`, behind `@media (hover:hover) and (pointer:fine)` | same |
| **M3** | popover: opacity 0→1 and `scale(.96→1)` from `--radix-*-transform-origin`, 180 ms; exit 120 ms | opacity only |
| **M4** | dialog: opacity and `scale(.97→1)`, centred, 320 ms; scrim opacity 200 ms; exit 200 ms | opacity 150 ms |
| **M5** | sheet (phone): `translateY(100%)→0` 320 ms ease-drawer, drag to dismiss with velocity > 0.11 | opacity 150 ms |
| **M6** | list enter: opacity .35→1 and `translateY(6px)`, 240 ms, 40 ms stagger capped at 6, first view per session | opacity 120 ms, no stagger |
| **M7** | route enter: opacity .35→1 and 6 px rise, 240 ms, **no exit, no `mode="wait"`** | opacity .35→1, 120 ms |
| **M8** | state morph: label crossfade 180 ms with 2 px blur masking (for example "Copy" to "Copied") | opacity only |
| **M9** | indicator: a single element translated by CSS transition 240 ms ease-out-expo (nav pill, tabs underline) | opacity 120 ms |
| **M10** | draw: `clip-path: inset(0 100% 0 0)→inset(0)` 640 ms, then points .6→1 at 40 ms intervals | opacity 120 ms |
| **M11** | toast: Sonner transitions (enter from bottom-right on desktop, bottom on phone, swipe to dismiss, timers paused while the tab is hidden) | Sonner reduced (opacity) |
| **M12** | progress: determinate `scaleX` 240 ms; indeterminate opacity breathing at 1.6 s | **loaders are not frozen**: opacity breathing continues (today the global kill-switch freezes spinners) |
| **M13** | expand: `grid-template-rows 0fr→1fr` 240 ms ease-in-out with opacity (the one sanctioned size animation) | instant, opacity 120 ms |

Global rules:
- Replace the blanket `* { animation-duration: .01ms !important }` kill-switch with per-recipe fallbacks plus
  `MotionConfig reducedMotion="user"`.
- `useReducedMotion` is read synchronously, so the first render honours the preference. Today the hook starts `false`.
- `transition-all` is banned by an eslint rule (`no-restricted-syntax` on class strings).
- Focus rings never transition.
- Framer `x`, `y` and `scale` shorthands are not used on anything that plays during navigation.

---

## 4. Information architecture and navigation

### 4.1 From 12 flat items to 4 labelled groups

| Today (12) | Proposed | Rationale |
|---|---|---|
| Inbox | **Records → Documents** | plain name |
| Verify | **Records → Review values** (with a count badge) | says what you do there |
| Timeline | Records → Timeline | — |
| Pinboards | Records → Pinboards | — |
| Trends + Interpret | **Understand → Results** (merged) | the same data on two pages with overlapping jargon; the interpretation becomes a panel on the result |
| Explain | **Understand → Ask** | a verb, so no clash with "Interpret" |
| Meds | **Care → Medications** | — |
| Alerts | folded into **Medications → Reminders** tab | "Alerts" was per-medication *settings* |
| Tasks | **Care → Follow-ups** | matches the care-task copy |
| Export | **Share → Doctor summary** (the CSV/JSON/FHIR export stays as a section) | outcome name |
| Settings | footer: **Settings**, split into tabs | §4.2 |

That gives 9 destinations in 4 labelled groups, plus Settings. Old URLs redirect (`/trends` and `/interpret` → `/results`, `/notifications` →
`/medications?tab=reminders`), so tests and bookmarks keep working. The active state uses prefix matching, so `/medications/:id` stays lit, which fixes the
exact-match bug. The brand becomes a `<span>`, not an `h1`, so each page has one h1.

**Optional Home** ("what's new since you were last here", "N values waiting for review", "next dose"), built only from existing queries. It is the
first thing I would cut (§9).

### 4.2 Settings sprawl (5,565 px)

Split `SettingsPage.tsx` (1,144 lines, currently eager) into a lazy route with Radix Tabs and sub-routes:

- **Profile & security:** recovery code, password. **OWNER GATE.**
- **Preferences:** timezone, voice, streak visibility, theme.
- **Privacy & data:** backup and restore (**OWNER GATE: encryption**), data donation, external API with break-glass warning (copy and semantics unchanged,
  D12), memory, danger zone (**OWNER GATE**).
- **Advanced:** diagnostics, OCR, model tiers, hardware, RL dataset. This tab is collapsed behind "Show advanced settings", which is off by default. It also fixes the
  self-contradicting tier copy ("gemma4-12b: Template-based interpretations (no AI model)").

### 4.3 Shells

- **≥ 1024 px:** a 264 px sidebar with group labels, a CSS-transitioned active indicator (M9), a profile block ("Alex Rivera's records · Encrypted on this
  device"), a top bar with the palette trigger "Search records or jump to… Ctrl K", and a theme toggle. The placebo **Safety Mode toggle is removed**
  (§0 of the review: a switch reading "Safety Mode OFF" falsely claims the safety guards can be turned off).
- **768–1023 px:** the same shell with the sidebar collapsed to a 72 px icon rail with tooltips (Radix Tooltip, opens on focus as well).
- **< 768 px:** a top bar (wordmark, search, theme) and a **5-slot bottom tab bar**: Records, Results, Ask, Care, More. More opens a sheet (M5)
  with the remaining destinations and Settings. Targets are ≥ 44 px, and the safe-area inset is respected. **Native scroll only.**
- **Safety Rail:** a one-line, never-animated status strip in the chrome: "Educational only, not medical advice. Your records stay on this device."
  It is sticky at the bottom of the content column on desktop and sits above the tab bar on phones (shortened). It lives in the shell, outside the route
  animation, so it is present on every page. That fixes the review finding that `/trends`, `/verify`, `/timeline`, `/export` and pre-generation `/interpret`
  carry no disclaimer. Contextual disclaimers stay on result and answer cards.

### 4.4 Command palette

`Ctrl/Cmd K` or `/` opens it. It has **no open or close animation and no animated highlight** (Raycast rule: it is opened 100+ times a day). Its groups:
- Results: jump to an analyte.
- Go to: the destinations.
- Actions: import a document, log a dose, switch theme, lock now (lock is an **owner gate**).
- Records: full-text search through the existing `/search` service, debounced at 150 ms.

The dialog chunk is lazy-loaded on first open (with a hover/focus prefetch of the trigger).

### 4.5 Unlock and session flow (OWNER GATE: touches auth)

Today an expired session redirects to `/setup` ("Create Your Profile"). Proposal:

1. Add `/unlock`: "Welcome back, Alex." It asks for a password field only and offers "Use your recovery code" as the secondary path. It uses the existing
   `useLogin` and `unlockProfile` (`services/profiles.ts`, currently unused). `ProtectedRoute` routes to `/unlock` when a profile exists and the token has
   expired, and to `/setup` only when no profile exists.
2. Add **Lock now**, in the palette and the profile block. It clears the token and keeps the profile id.
3. Five minutes before expiry, a non-modal toast (M11) says "Your session ends in 5 minutes · Stay signed in". It refreshes only if the backend supports
   refresh. If it does not, the toast is informational.
4. Unlock is signature moment 4 (gated): the app behind recedes (scrim opacity, content `scale(.985)`), and on success it returns. There is no "welcome back"
   theatre beyond that.

**None of this changes auth or encryption logic. It wires existing hooks into new screens, but CLAUDE.md requires the owner's yes before any frontend change to unlock or login.**
Options for the owner are in §9.

---

## 5. Signature moments (3, plus 1 gated)

1. **The Range Ribbon** (Results, T3, **prototyped**). The lab's printed reference range is drawn as a soft band, the analyte's history is drawn
   across it as honest straight segments (not `monotone`, which invents curvature between real readings), and the latest value sits on a static halo.
   On the first view of each analyte per session: band at once, line drawn left to right by clip-path in 640 ms, points settling at 40 ms intervals.
   **Value-blind:** an out-of-range point animates exactly like an in-range one. The signal is *position against the band*, plus a text chip with an icon
   ("Above report range" with an up arrow). Unverified points are hollow and dashed (D4), and a legend appears only when they exist.
   *Why it earns its place:* the review calls Trends "the product's core value" and says it "should be its signature moment" but sits "at the same weight as a
   7-row list". It explains the data rather than decorating it.
2. **Provenance Peek** (every citation, T2, **prototyped**). A citation chip ("1 · Lipid panel, Valley Clinic Lab · p.2") opens a popover
   that scales out of the chip (M3). It shows the quoted line, page and collection date, with "Open document". It opens on tap, click, Enter or Space, closes on Escape,
   and returns focus. *Why:* it replaces the hover-only `CitationTooltip` (unusable on touch, and its animation classes are inert). Trust is the goal beyond the
   goal, and this is where trust becomes something you can touch.
3. **Import to verified handoff** (Documents and Review, T3). While a file is being extracted, its card shows a `border-beam` rotating along the border.
   This is a state signal, and under reduced motion it becomes a static border tint. When extraction finishes, the extracted values arrive in the review list (M6), and each "Verify" press
   morphs the row's status chip from "Not yet checked" to "Checked by you" with a check-stroke draw (`stroke-dashoffset` 240 ms, `settle` spring on the
   chip). The only bounce in the app is reserved for the user's own act of verifying, never for a result. *Why:* it is the product's actual workflow
   (import, verify, trust), and rewarding verification is good for data quality.
4. *(Gated, §4.5)* **Lock and return**: the shell recedes behind the unlock card, then comes back exactly where you were.

Explicitly **not** signature moments: lab values (T0), the palette (no motion), page transitions (enter-only, near-invisible), and empty states (static,
each with one real call to action).

---

## 6. Per-component upgrade map (every COMPONENT_AUDIT row)

Source key:
- **pkg:** an npm dependency (§7).
- **ref:** a motion or interaction reference, reimplemented. Bencho and Morphin are reference only: Bencho's licence is unverified, and Morphin is Pro-gated.
- **custom:** our own code.
- **keep:** the component is already right.

Motion codes are from §3.5. **GATE** means the owner's yes is needed (auth, encryption, privacy or redaction-adjacent; visual changes only, logic untouched).

### 6a. `components/ui`

| Component | Upgrade source | Change | Motion |
|---|---|---|---|
| Button | custom (keep cva) | Variants primary, secondary (`line-strong` outline), ghost, danger. Add a `loading` prop (replaces 69 inline `Loader2`). Remove the hover translate-lift and `transition-all`. | M1, M2, M8 (label to spinner) |
| Card family | custom | Variants `default` (E1 border, no hover), `interactive` (whole card is a link or button: M1 + M2), `inset` (well). Remove `backdrop-blur-xl`. | M2 on interactive only |
| Badge → **StatusChip** + Tag | custom | StatusChip = icon + text + wash, from the range/verify/caution/info roles. Tag = neutral metadata. Maximum two per row. | M8 on state change |
| Input | custom + Radix Label | `focus-visible`, `line-strong` boundary, error clears on valid change (fixes stale setup errors), password-reveal button 44 px | M2 border colour |
| (new) Select, Checkbox, Switch, Textarea, RadioGroup | pkg `@radix-ui/react-select`, `-checkbox`, `-switch` | Replace 8 hand-styled selects, blue native checkboxes and 3 copies of the switch | Switch thumb M9 (transform); Select M3 |
| EmptyState | custom; ref Bencho "Card" blocks | Required `action` prop (one real CTA), optional `illustration` slot (static SVG line art from the band motif) | M6 once |
| Motion primitives | pkg `motion` 14.6 | Rewrite: token-driven, `LazyMotion`, `m.*`, `MotionConfig reducedMotion="user"`; `PageTransition` becomes CSS M7; delete `modalVariants` (Dialog owns it) | M6, M7 |
| Skeleton family | custom | Content-shaped skeletons with `aria-busy` on the region; a shimmer by `translateX` on a pseudo-element; `CardSkeleton` deleted (unused) | M12 |
| `ui/index.ts` barrel | keep | — | — |
| (new) Dialog, AlertDialog, Sheet, Popover, Tooltip, Tabs, Toast | pkg Radix (+ Sonner for toast) | The only overlay path. Escape, focus trap and return, scroll lock, labelled. | M4, M5, M3, M3, M9, M11 |

### 6b. `components/layout`, `components/auth`

| Component | Upgrade source | Change | Motion |
|---|---|---|---|
| AppLayout | custom (**prototyped** as `proto/Shell.tsx`) | Responsive shell, skip link, Safety Rail, route content keyed; **remove `AnimatePresence mode="wait"`**; ErrorBoundary per route | M7 |
| Sidebar | custom; ref Bencho "Collapsing sidebar" | Groups, prefix-match active, CSS indicator (replaces the `layoutId` spring, which drops frames during route loads), icon rail at md | M9, M1, M2 |
| TopBar | custom; ref Bencho "Command bar" | Palette trigger, theme toggle; **Safety Mode toggle removed**; profile block moves to the sidebar footer | M1, M2 |
| (new) MobileTabBar + MoreSheet | custom; ref Bencho "Tab bar" | 5 slots, 44 px+, safe-area | M1; sheet M5 |
| ProtectedRoute | custom, **GATE** | `/unlock` vs `/setup` routing (§4.5) | M0 |
| barrels | keep | — | — |

### 6c. Top level, `documents/`, `lab-interpreter/`

| Component | Upgrade source | Change | Motion |
|---|---|---|---|
| MedicationOverlay | custom | Router `Link` (today a plain `<a>` does a full reload); pills become Tags | M1, M2 |
| MemoryManager | custom + primitives | Fields to primitives; filter chips get `aria-pressed`; delete confirm to AlertDialog | M13 for the add form |
| PageImageOverlay | custom | Image fades in on load (today it pops in); bbox highlight draws its outline once | opacity 180 ms; outline M10 at 320 ms |
| TrendVerificationMarkers | custom → folded into RangeRibbon | Hollow dashed for unverified (keep the D4 semantics); token colours replace hex | M10 (value-blind) |
| CategoryBadge | **delete** (no importer) | — | — |
| EntityDetailView | custom | Table to responsive rows; StatusChip; verify becomes optimistic with undo toast | M8 chip morph; M11 |
| ExtractionConfidenceBadge | custom | Shown only below threshold, as "Low read confidence · check this value" (never "60% · Medium · Lowest extraction confidence") | M0 |
| HighlightChips | keep (logic) / restyle | Tags, maximum 2 + "+N" | M0 |
| AdviceSection | custom | Becomes "Questions you could ask your clinician"; static | M0 (T0) |
| CitationTooltip | **replace** with ProvenancePeek (pkg Radix Popover; **prototyped**) | Tap, click and keyboard; quote and page; 44 px target | M3 |
| DisclaimerBanner | custom | Restyle to a `well` note with a bold lead; **never animated**; `role="note"` (not `alert`, which is announced as urgent on every render) | M0 (T0) |
| InterpretedResultCard | custom → panel inside Results | Advice expander with `aria-expanded`; regenerate uses `Button loading` | M13; M8 |
| InterpretedTrendChart | **replace** with RangeRibbon (custom) | Removes Recharts | M10 |
| PanelInterpretationDashboard | custom | Panel summary card on Results; insight list keeps its stagger | M6 |
| ReferenceRangeComparison | **replace** with RangeTick (custom; **prototyped**) | 64 px glyph: band plus marker, with the text alongside | M0 (T0) |
| formatInterpretationText | keep | — | — |
| barrel | keep | — | — |

### 6d. `medication-coach`

| Component | Upgrade source | Change | Motion |
|---|---|---|---|
| MedicationCard | custom | Real `<a>`/Link (today it is a `div onClick` with no keyboard); a single motion source (today it animates twice) | M6, M1, M2 |
| MedicationForm | custom + primitives | Select and Checkbox primitives | M13 open |
| DoseLoggingModal | pkg Radix Dialog (Sheet on phones) | Fixes no `role`, no Escape, no trap, dead exit; reason chips get `aria-pressed` | M4 / M5; reason panel M13 |
| BadgeToast | **replace** with pkg Sonner | One toast system; 44 px dismiss; pause on hover | M11 |
| AchievementsWidget (+BadgeCard) | custom, **owner question** | Recommended: off by default behind Preferences, neutral copy, no lift on non-interactive tiles | M0 |
| AdherenceDashboard (+AdherenceRing) | custom | The ring draws from 0 once (today it renders final, so its 700 ms transition never runs); token colours | stroke-dashoffset 640 ms once; reduced: static |
| ScheduleEditor | custom + primitives | 44 px controls; labels with `htmlFor`; delete becomes AlertDialog; per-row pending state | M13 |
| StreakDisplay | keep (copy is already neutral) | — | M0 |
| VoiceFirstUseModal | Radix Dialog when it is wired in; currently unused | — | M4 |
| barrel | keep | — | — |

### 6e. `pinboards`, `profile`, `settings`

| Component | Upgrade source | Change | Motion |
|---|---|---|---|
| AddToPinboardButton | keep Radix DropdownMenu, upgrade to 2.2.1 | add `data-state` enter | M3 |
| RecoveryCodeCard (profile) | custom, **GATE** | Code grouped in 4-char blocks that never wrap mid-group; copy morph; Checkbox primitive; warning in `caution` (6.05:1) | M8 |
| AgentSettingsCard | Switch primitive | — | M9 thumb |
| BackupCard | custom, **GATE (encryption)** | Fields and AlertDialog primitives only; flow unchanged | M13 |
| DangerZone | custom; ref Bencho "Slide to confirm" → **hold-to-confirm** (custom), **GATE** | Hold 2 s linear fill by clip-path, release snaps back 200 ms; the typed phrase stays | clip-path 2 s / 200 ms |
| DataDonationCard | Switch + AlertDialog primitives | inline `alertdialog` becomes a real AlertDialog | M4 |
| ExternalApiBreakGlassWarning | custom, **GATE (D12 UI warning)** | Token restyle only; text, role and visibility unchanged; never animated | M0 (T0) |
| RecoveryCodeCard (settings) | custom, **GATE** | Input primitive | M0 |
| TierCapabilities | custom | `text-[10px]` raised to `cap` 13 px; moves to Advanced | M0 |

### 6f. Pages

| Page | Upgrade source | Change | Motion |
|---|---|---|---|
| ProfileSetup | custom, **GATE** | Remove the fake `setTimeout(500)` progress theatre; errors clear on fix; ref Bencho "Password strength" → custom meter (text plus bar); fix the unlinked "Terms of Service" copy | M6 once; meter `scaleX` |
| RecoverProfile | custom, **GATE** | Primitives, 44 px | M7 |
| DocumentInbox → **Documents** | custom + pkg `border-beam` | Lazy; one status chip and one Tag per row; row actions **always visible** (no hover-only); drop zone becomes a first-run onboarding checklist (Import → Review → See results); `window.confirm` becomes AlertDialog | M6, signature 3 |
| VerificationWorkbench → **Review values** | custom | Lazy; responsive (no fixed `grid-cols-3`); out-of-range = icon + "Above report range" text (fixes 1.4.1); Edit to Dialog; optimistic verify | signature 3 |
| TrendsDashboard → **Results** | custom (**prototyped** `proto/ResultsPage.tsx`) | Merge with Interpret; the dead "Last 12 Months" and "Filters" become a real range Select; panel tabs filter the list (fixes the CBC→Glucose mismatch); PNG and SVG export kept (our SVG serialises) | signature 1 |
| TimelinePage | custom | Event cards name the analytes ("Glucose, HbA1c"); remove its duplicate `p-8` wrapper | M6 |
| SearchPage | custom | The query appears in the palette and the page field | M6 |
| LabInterpreter | **merged into Results**; route redirects | — | — |
| MedicationCoach | custom | Lazy; tabs Medications / Reminders; `scrollTo` honours reduced motion | M6, M9 tabs |
| MedicationDetail | custom | Dialog wiring | M7 |
| NotificationSettings | becomes the **Medications → Reminders** tab | Switch primitives; table to rows on phones | M9 |
| CareTasksPage → **Follow-ups** | custom | Done or ignore is optimistic with an undo toast | M11, M8 |
| PinboardsPage | custom | `window.prompt` and `confirm` become Dialog and AlertDialog | M4 |
| ExplainAssistant → **Ask** | custom + pkg `thinking-orbs` | Message list is its own focusable scroll region (fixes the window scroll and the sticky banner overlapping text); send button named; filter fields labelled; citations use ProvenancePeek; the model chip states the truth ("Template answers, no model installed"); pending state is a thinking orb (reduced: static frame) | M6 per message; orb |
| ExportPage → **Doctor summary** | custom | Checkbox primitives; "Full Preview" becomes a Sheet preview; redaction level shown as read-only text (redaction logic untouched) | M5 |
| SettingsPage | custom + Radix Tabs | Lazy, split (§4.2) | M9 tabs |

### 6g. `App.tsx` and inline sub-components

| Component | Upgrade source | Change | Motion |
|---|---|---|---|
| RouteFallback | custom | Content-shaped skeleton per route; intent prefetch so it is rarely seen | M12 |
| BadgeCard | see AchievementsWidget | — | M0 |
| AdherenceRing | see AdherenceDashboard | — | draw once |
| SourceQuote | → ProvenancePeek quote style | — | M0 |
| CandidateCard | Card `inset` + Button | "Add to checklist" is optimistic | M8 |
| TaskCard | Card + StatusChip | Strike-through becomes a state morph | M8 |
| SuggestionCard | Card `inset` | — | M0 |
| MedReconcilePanel | Select primitive | — | M13 |
| ResultCard (Search) | Card `interactive` | Whole card is the link | M1, M2 |
| EventCard | Card `interactive` | — | M1, M2 |
| Document preview dialog | Radix Dialog (Sheet on phones) | Escape, trap, return | M4 / M5 |
| Edit Value modal | Radix Dialog | Label, close button `aria-label` | M4 |
| Export confirmation dialog | Radix AlertDialog | — | M4 |
| Diagnostics fix dialog | Radix Dialog | — | M4 |
| Consent dialog | Radix AlertDialog, **GATE (privacy copy unchanged)** | — | M4 |
| Streaks switch | Switch primitive | `disabled` while saving | M9 |
| Model download progress | Progress primitive (`role="progressbar"`) | `scaleX` instead of width | M12 |
| Panel tablist (Trends) | Radix Tabs | Roving arrows, `tabpanel` | M9 |
| Panel tabs (Interpret) | merged | — | — |
| Typing indicator | → `thinking-orbs` | `role="status"` "Composing an answer" | orb |
| Message bubbles | custom | Feedback thumbs 44 px with `aria-pressed`; undefined tokens fixed | M6 |
| Section toggle buttons (Export) | Checkbox or toggle primitive | `focus-visible` | M2 |

**References considered and rejected:**
- Morphin "orbiting-glow" CTA, Libraries.dev `metal-fx` and `liquid-gooey`: costume on a health tool.
- Morphin "3D bending carousel", "stacked scroll cards with 3D tilt" and Bencho "tilt card": no galleries here, and tilt on data cards moves T0 content.
- Bencho "confetti", "UI sounds" and "emoji reactions": engagement mechanics.
- `img-fx`: needs three.js.
- Aceternity, Spline and Canvas UI: excluded by licence or runtime.
- VGPU: a shader toolkit, not UI.

---

## 7. Dependencies and bundle

Sizes were measured on 2026-10-23 with esbuild 0.27.2: minified, React and react-dom external, `gzip -9`, using the named imports the app would use
(`proto-B/sizing/`). They are indicative. Vite/Rollup output differs by a few kB.

| Package | Version | Licence | gzip | Verdict and why |
|---|---|---|---|---|
| `motion` (replaces `framer-motion` 10.18) | 14.6.0 | MIT | 35.3 kB with `LazyMotion`+`m`+`domAnimation` (full `motion` 47.7; framer 10 today 37.1) | **Adopt.** Successor package with the same mental model. `MotionConfig reducedMotion="user"`. Net ≈ −2 kB. Used only for exits, springs and gestures; most motion is CSS. |
| `@radix-ui/react-dialog` | 1.3.1 | MIT | 14.2 | **Adopt.** Dialog, AlertDialog, Sheet, and cmdk's host |
| `@radix-ui/react-popover` | 1.3.1 | MIT | 24.9 alone | **Adopt.** Provenance Peek |
| `@radix-ui/react-tooltip` | 1.4.1 | MIT | 20.3 alone | **Adopt.** Icon rail labels |
| `@radix-ui/react-tabs` | 1.2.1 | MIT | 9.7 | **Adopt** |
| `@radix-ui/react-switch` / `-checkbox` | 1.4.1 / 1.4.1 | MIT | 5.1 / 6.1 | **Adopt** |
| `@radix-ui/react-select` | 2.4.1 | MIT | 32.5 alone | **Adopt** (lazy pages only) |
| `@radix-ui/react-dropdown-menu` | 2.1.16 → 2.2.1 | MIT | 32.3 | Already present; bump |
| *Radix set above, combined* | — | — | **46.2 total, ≈ +13.9 over today's dropdown** | Popper, focus-scope and dismissable-layer are shared |
| `sonner` | 2.0.8 | MIT | 9.6 | **Adopt.** One toast system (replaces BadgeToast and ad-hoc "Copied" text) |
| `cmdk` | 1.1.1 | MIT | 17.9 alone, **+4.2** over the Radix set | **Adopt in a lazy chunk, with a required fix.** In the prototype axe reports `aria-valid-attr-value` (critical ×2): after typing, `aria-activedescendant` points at an id that no longer exists until the user presses an arrow key (`proto-B/probe-cmdk.mjs`). The row ships a Playwright test for it and a small patch (re-sync on filter). If the patch fails, fall back to our own listbox on Radix Dialog (~120 lines). |
| `border-beam` | 1.4.1 | MIT | 12.8 (lazy, Documents chunk) | **Adopt, once.** In-progress extraction only. Its rotate type needs a manual reduced-motion fallback (README). |
| `thinking-orbs` | 0.3.2 | MIT | 11.2 (lazy, Ask chunk) | **Adopt, once.** Ask pending state; static frame under reduced motion (README) |
| `recharts` | 3.9.1 | MIT | **−110.4** (lazy chunk today 105.2) | **Remove.** RangeRibbon and RangeTick are about 250 lines of SVG (prototyped) |
| `vaul` | 1.1.2 | MIT | — | **Reject.** Last publish 2024-12-14; Sheet = Radix Dialog + transform |
| `lenis` | 1.3.27 | MIT | 6.2 | **Reject.** App shell with nested scrollers; native scroll serves zoom, magnifiers and keyboard better |
| `react-aria-components` | 1.22.1 | Apache-2.0 | (6.9 MB unpacked) | **Reject.** A second primitive family; Radix covers our widgets |
| `@ark-ui/react` | 5.39.3 | MIT | — | **Reject.** Same reason |
| three / R3F / GSAP | — | — | — | **Reject.** No clinical gain from 3D; GSAP would be a second engine |

**Budget, compared with today's 180.0 kB gzip main chunk:**

| Measure | Today | Target | Hard cap |
|---|---|---|---|
| Main chunk (gzip) | 180.0 | **≤ 170** | 185 |
| Library delta in main (measured: baseline libs 69.1 → proposed 90.5) | — | +21.4 | — |
| Offsets: lazy Settings (1,144 lines), Inbox, Verify, palette | — | −25 to −35 (estimated, not measured) | — |
| Results route total JS (main + route + chart) | 289.7 (180 + 4.5 + 105.2) | **≤ 205** | 220 |
| Any lazy route chunk | ≤ 7.6 today | ≤ 30 | 40 |
| CSS (gzip) | 18.3 | ≤ 24 | 28 |

The prototype build measures **209.4 kB gzip main**, which is +29.4 over today. It is *not* the target state. It still ships `framer-motion` 10
for the untouched pages *alongside* `motion`, cmdk and Radix Popover eagerly, and Settings, Inbox and Verify are still eager. The plan removes all
four of those. The Results route in the prototype already avoids the 105 kB Recharts chunk (209.4 versus 289.7 for Trends today).

**React 18 or 19: stay on React 18** (bump 18.2 → 18.3.1 for the deprecation warnings). Nothing I adopt needs React 19: motion, Radix, Sonner,
cmdk, border-beam and thinking-orbs all accept 18. React 19 would unlock R3F 9, HeroUI, the shadcn v4 path, React Router 8 and `<ViewTransition>`, none
of which this plan uses. The cost of upgrading: framer-motion 10 must move first anyway, `@types/react` 19 ref-as-prop churn across about 90 components, a
testing-library and jsdom re-verify of the whole vitest suite, and `react-router-dom` stays on 7 regardless. The risk is a framework-wide regression
during the week of the 2026-10-31 stakeholder build. Revisit it after the demo as its own row (R-1), only if a needed library requires it.

---

## 8. The plan as build-program rows

Rules for every row:
- Test first: a failing vitest or Playwright check, then the code.
- File-disjoint with the other rows in its wave.
- Route tests go through the real router.
- Acceptance always includes the **standard gate**: axe 0 serious or critical on the touched routes in light **and** dark; CLS < 0.1; INP < 200 ms
  (Event Timing, CPU ×4); main ≤ 185 kB gzip (`scripts/bundle-budget.mjs`); a reduced-motion snapshot (`reducedMotion:'reduce'`, assert no element has a
  non-identity transform 50 ms after interaction); no horizontal scroll at 390 px; zero console errors; `npm run build` passes; vitest count reported with its delta.

**Phase A: foundation** (A1 first, then A2–A6 in parallel)

| Row | Files | Test first | Acceptance |
|---|---|---|---|
| A1 Motion migration | `package.json`, 17 files importing `framer-motion`, `hooks/useReducedMotion.ts`, `components/ui/Motion.tsx` | vitest: with matchMedia mocked to `reduce`, the **first** render of `PageTransition` has no transform; grep test: 0 `framer-motion` imports | Suite green; bundle ≤ 180 |
| A2 Tokens | `styles/tokens.css` (new), `styles/globals.css` | vitest `tokens.contrast.test.ts` parses both themes and asserts the §3.1 pairs (≥ 4.5 text, ≥ 3 UI); eslint rule against `text-[9px]`, `text-[10px]` and `transition-all` | axe `color-contrast` 0 on all 29 audited states |
| A3 Theme | `theme/theme.ts`, `index.html` (pre-paint script), `public/favicon.svg` | vitest resolve and persist; Playwright: dark screenshot differs from light, no light flash on load (first-frame colour sampled) | Both themes pass the gate |
| A4 Shell | `components/layout/*`, new `MobileTabBar.tsx` | Playwright: scrollWidth = 390 on **every** route; first Tab = skip link; exactly 1 h1; nav-click opacity samples never < .3 (no blank gap); Safety Rail visible in the viewport on every route | Gate; Safety Mode toggle gone |
| A5 Routing | `App.tsx`, `components/ErrorBoundary.tsx` | Playwright: a thrown route error shows the boundary, not a white screen; bundle script fails above 185 | Main ≤ 185 (Settings, Inbox, Verify lazy); prefetch on intent |
| A6 Fonts | `main.tsx`, `styles/fonts.css` | Playwright CLS on cold load ≤ 0.02 (font swap measured at 0.011 in the prototype) | Fallback metric overrides plus preload of the Latin subsets |

**Phase B: primitives** (parallel, one file family each)

| Row | Files | Test first | Acceptance |
|---|---|---|---|
| B1 Button + IconButton | `ui/Button.tsx`, `ui/IconButton.tsx` | vitest: `loading` sets `aria-busy` and disables; IconButton requires `aria-label` (TS); computed size ≥ 44 | Focus ring has no transition |
| B2 Fields | `ui/Input.tsx`, `ui/Select.tsx`, `ui/Checkbox.tsx`, `ui/Switch.tsx`, `ui/Textarea.tsx` | vitest: label association, `aria-invalid` clears on valid change, Switch is `role=switch` with keyboard | `line-strong` boundaries ≥ 3:1 |
| B3 Feedback | `ui/Skeleton.tsx`, `ui/EmptyState.tsx`, `ui/StatusChip.tsx`, `ui/Progress.tsx` | vitest: StatusChip renders icon **and** text for every state; EmptyState requires an action | Loaders animate under reduced motion (opacity only) |
| B4 Overlays | `ui/Dialog.tsx`, `ui/AlertDialog.tsx`, `ui/Sheet.tsx`, `ui/Popover.tsx`, `ui/Tooltip.tsx` | vitest + Playwright: Escape closes, focus trapped (25 Tabs stay inside), focus returns to the trigger, `aria-modal`, labelled | M3, M4, M5 recipes; exit plays |
| B5 Toast | `ui/toast.ts`, `App.tsx` Toaster slot | vitest: `toast()` renders `role=status`; timer pauses while hidden | Sonner themed by tokens |
| B6 Tabs | `ui/Tabs.tsx` | vitest: roving arrows, `tabpanel` linkage | M9 underline |

**Phase C: navigation**

| Row | Files | Test first | Acceptance |
|---|---|---|---|
| C1 IA and redirects | `App.tsx` routes, `components/layout/nav.ts` | Routing test: `/trends`, `/interpret` → `/results`; `/notifications` → `/medications?tab=reminders`; `/medications/:id` keeps the active state | Old e2e specs still pass |
| C2 Command palette | `components/CommandPalette.tsx` (lazy) | Playwright: Ctrl K and `/` open; **`aria-activedescendant` always resolves to an existing id after typing**; no transition on open | axe 0 on the open palette |
| C3 Settings split | `pages/settings/*` (new), `SettingsPage.tsx` | Routing test for each tab; Advanced hidden by default | 5,565 px → no tab over 2 screens |
| C4 Unlock and lock (**OWNER GATE**) | `pages/Unlock.tsx`, `auth/ProtectedRoute.tsx`, `stores/authStore.ts` (read only) | Playwright: an expired token with an existing profile lands on `/unlock`, never `/setup` | Only after the owner's yes |

**Phase D: content** (each row is one page and its private components)

| Row | Files | Test first | Acceptance |
|---|---|---|---|
| D1 Documents | `pages/DocumentInbox.tsx`, `documents/*` | Playwright: row actions visible with the mouse away (opacity 1); ≤ 2 chips per row; no snake_case text | Signature 3a (beam) with a reduced-motion static border |
| D2 Review values | `pages/VerificationWorkbench.tsx`, `EntityDetailView.tsx` | Playwright: out-of-range rows carry an icon and text (1.4.1); verify is optimistic, failure rolls back with a toast | Signature 3b |
| D3 Ask | `pages/ExplainAssistant.tsx` | Playwright: sending scrolls only the list; banner never overlaps text; send button named; `scrollable-region-focusable` passes | Truthful model chip |
| D4 Medications (+Reminders, dose dialog) | `pages/MedicationCoach.tsx`, `MedicationDetail.tsx`, `NotificationSettings.tsx`, `medication-coach/*` | Playwright: dose dialog Escape and trap; MedicationCard keyboard-activatable | Badges per the owner's answer |
| D5 Timeline, Pinboards, Search, Follow-ups | the four pages | Playwright: no `window.prompt` or `confirm` (stubbed to throw) | Gate |
| D6 Doctor summary | `pages/ExportPage.tsx` | Playwright: "Full Preview" opens a Sheet; no native unstyled checkbox | Redaction logic untouched (diff check on `services/export.ts`) |
| D7 Setup and recover (**GATE**) | `ProfileSetup.tsx`, `RecoverProfile.tsx`, `profile/RecoveryCodeCard.tsx` | vitest: errors clear on fix; no `setTimeout` progress | Only after the owner's yes |

**Phase E: data viz**

| Row | Files | Test first | Acceptance |
|---|---|---|---|
| E1 RangeRibbon + RangeTick | `components/results/RangeRibbon.tsx`, `RangeTick.tsx` | vitest: an out-of-range point gets the **same** animation attributes as an in-range one (value-blind); unverified = dashed; SVG serialises for PNG/SVG export (ChartExport tests ported) | Ribbon draws once per analyte per session |
| E2 Results page | `pages/ResultsPage.tsx`, `lab-interpreter/*` | Playwright: the panel filter matches the list (no CBC→Glucose); the disclaimer is in the DOM at first paint with opacity 1 | Recharts removed from `package.json`; Results route ≤ 205 kB gzip |
| E3 Adherence ring | `AdherenceDashboard.tsx` | vitest: initial offset = full, then final | Reduced: static |

**Phase F: overlays.** F1: migrate the 6 hand-built overlays plus the `window.confirm` and `prompt` calls (one row per host file, already in D-rows' file sets; F1 covers
`SettingsPage` dialogs only). F2: `CitationTooltip` → ProvenancePeek (`lab-interpreter/CitationTooltip.tsx`). Playwright: it opens on **tap** in a
`hasTouch` context, Escape closes it, and focus returns.

**Phase G: micro-interactions.** G1: the M8 state morphs (copy, verify, done). G2: a raw-`<button>` sweep to IconButton (eslint
`no-restricted-syntax` on `<button className=` outside `ui/`). G3: a motion audit with `improve-animations` and the owner's `/review-animations`, plus a
reduced-motion snapshot suite across all routes.

**Order and timing.** A1 → (A2–A6) → B → C1–C3 → E1–E2 → D → F → G. Everything up to E2 is the "demo-critical" slice. C4 and D7 wait for the
owner.

---

## 9. Risks, cuts, owner questions

**Risks**
1. **Deadline.** The stakeholder build is due 2026-10-31, eight days away. The full plan does not fit. My recommendation: the demo-critical slice is
   A1–A6, B1, B4, C1, E1 and E2 (shell, tokens, motion, Results). Everything else follows after the demo.
2. **Motion 10 → 14 migration.** v11 moved the post-mount render to a microtask, so jsdom tests that assert immediately after render may need an
   animation-frame await. A1 must run the whole vitest suite before anything else.
3. **cmdk accessibility defect** (measured, see §7). Mitigated by a test-gated patch or our own listbox.
4. **Removing Recharts** risks the PNG and SVG chart export (`ChartExport.test.tsx`). Our SVG serialises the same way; port the test first.
5. **Owner expectation gap.** "Engaging, animated" may read as *more* motion than this plan ships. I hold the line on T0, but T2 craft and the three moments
   should be demoed side by side with today's 450 ms blank gap. That before-and-after is the "wow".
6. **Font-swap CLS** of 0.011 was measured in the prototype. It is fine, but it is the last remaining shift (row A6).
7. **Dark-mode chart colours** must come from tokens (today there are 21 hard-coded hex values in the charts). E1 removes them.

**What I would cut first, in order:** Home page; `border-beam`; `thinking-orbs`; Pinboards and Timeline restyle; the Settings Advanced re-copy; palette actions
beyond navigation. **Never cut:** the responsive shell, contrast tokens, overlay primitives, the Safety Rail, Provenance Peek, and removing the Safety Mode placebo.

**Owner questions** (written neutrally, with options)
1. **What should "simulate SWE or SaaS" mean for the UI?** (a) Product craft: speed, feedback, navigation, polish. (b) Craft plus engagement features
   (streaks, badges, celebratory animation). (c) Something else. A one-line record in `owner-decisions` would settle the conflict with "Clinical Calm".
2. **Unlock and lock screen** (touches the auth flow). (a) Build `/unlock` with the existing `useLogin` and `unlockProfile` plus "Lock now". (b) Keep the redirect but
   change `/setup` copy to tell returning users to sign in. (c) Defer until after 10-31.
3. **Medication achievement badges.** (a) Keep them as they are. (b) Keep them, off by default, with neutral names. (c) Remove them.
4. **Default theme.** (a) Follow the OS setting. (b) Light by default, dark opt-in. (c) Light only for the demo.
5. **React 19.** (a) Upgrade now. (b) Upgrade after the demo as its own row. (c) Stay on 18 until a dependency requires 19.
6. **Scope before 10-31.** (a) The demo-critical slice only. (b) The full plan, with a feature freeze lifted later. (c) Visual tokens only, no structural change.
7. **Advanced or diagnostic settings for patients.** (a) Hidden behind "Show advanced". (b) A separate developer route. (c) Visible as today.
8. **Merging Trends and Interpret into "Results".** (a) Merge, with redirects. (b) Keep two pages and rename them. (c) Keep as is.

---

## 10. Outside judge: the prototype

**What was built**:
- Where: `proto-B/frontend`, a copy of `src/frontend` with `npm ci`, plus `motion` 14.6.0, `cmdk` 1.1.1 and `@radix-ui/react-popover` 1.3.1.
- About 1,190 lines in `src/proto/*` and `mock-api.ts`.
- `Shell.tsx`: grouped sidebar with the CSS indicator, skip link, top bar with palette trigger, theme toggle, Safety Rail, phone tab bar, and enter-only route motion.
- `CommandPalette.tsx`.
- `ResultsPage.tsx`: analyte rail or phone chip scroller, hero numeral, range chip, contextual disclaimer, actions.
- `RangeRibbon.tsx`, the signature moment, and `ProvenancePeek.tsx`.
- `tokens.css`: the §3 tokens and motion recipes.

The repo itself was not edited. The API is mocked by a Vite middleware with the real `Observation` and `TrendData` shapes, so no backend or Ollama was used.
`globals.css` in the copy loses its blanket reduced-motion kill-switch, as proposed.

**How it was checked** (vite on 127.0.0.1:5182; Playwright 1.58 with Chromium 1200; axe-core 4.10.3 with WCAG 2.0/2.1/2.2 A+AA tags;
scripts `proto-B/capture.mjs`, `probe-cls.mjs`, `probe-inp.mjs`, `probe-cmdk.mjs`; raw output in `proto-B/capture-results.json`):

| State | CLS | scrollWidth | axe serious/critical | console errors |
|---|---|---|---|---|
| results 1440 light / dark | 0.011 / 0.011 | 1440 | 0 / 0 | 0 |
| results 390 light / dark | 0 / 0.021 | **390** | 0 / 0 | 0 |
| peek open 1440 light / 390 dark | 0 / 0.021 | 1440 / 390 | 0 / 0 | 0 |
| keyboard focus on a chart point | 0.011 | 1440 | 0 | 0 |
| LDL selected, HDL scrolled at 390 | 0 / 0.021 | ok | 0 | 0 |
| palette open (dark) | 0 | 1440 | **critical ×2: cmdk `aria-activedescendant`** | 0 |

- **No blank gap on navigation.** Opacity and transform of the route container sampled every 50 ms after clicking "Documents":
  `1.00 → 0.35/6px → 0.81 → 0.96 → 1.00`. Today's sequence is `1.00 … 0.02 0.00 0.00 0.09`. Under `reducedMotion:'reduce'`:
  `1.00 → 0.35 → 0.90 → 1.00` with **transform `none` throughout**.
- **INP proxy** (Event Timing, 5 analyte switches and 4 navigations, **dev build**): max event duration 48 ms at CPU ×1 and 80 ms at CPU ×4.
- **The safety disclaimer** was visible in the viewport at opacity 1 in every captured state.
- **Typecheck** passes (`tsc --noEmit`). `npm run build` passes, with a main chunk of 209.4 kB gzip (explained in §7).
- **Screenshots** (all checked by eye for overlap, overflow and unstyled states). Two problems were found and fixed in the process:
  - the "Report range" label overlapped the line, so it moved to a legend;
  - a mobile grid with min-content width caused a 1,029 px overflow, fixed with `grid-cols-[minmax(0,1fr)]`.

  Two CLS sources were also fixed: a mismatched skeleton header, and the chart resizing after first paint.
  - `proto-B/shots/results-1440-light.png`, `results-1440-dark.png`
  - `proto-B/shots/results-390-light.png`, `results-390-dark.png`
  - `proto-B/shots/results-1440-light-peek-open.png`, `results-390-dark-peek-open.png`
  - `proto-B/shots/results-1440-light-keyboard-point.png`, `results-1440-light-ldl.png`, `results-390-light-hdl-scrolled.png`
  - `proto-B/shots/palette-1440-dark.png`, `nav-to-documents-motion-1440.png`, `nav-to-documents-reduced-1440.png`

**What I could not verify**
- Real-device frame rate, and 120 Hz behaviour. Headless Chromium only; no GPU profile.
- INP on a production build or on real hardware. The numbers above come from a dev build in headless Chromium.
- Screen-reader output (NVDA, VoiceOver) for the chart's focusable points and the live caption.
- Firefox and Safari rendering, including `clip-path` on SVG `<g>` in Safari.
- 200% zoom and 320 px reflow.
- The old pages inside the new shell. They render, but in the old visual language (`nav-to-documents-motion-1440.png`); the rest of the plan restyles them.
- The vitest suite against the copy, which I did not run.
- The library sizes in §7: they are esbuild measurements, not Vite production chunks.
- Bencho's licence. It stays reference-only.
