# Asclexis frontend revamp: proposal A ("Ink & Paper")

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

Designer A, 2026-10-23. Repo `main` @ 7749744. Nothing in the repo was edited. The prototype lives in
[`proto-A.patch`](proto-A.patch) in this folder (a diff against `src/frontend` at `7749744`; it ran on port 5181), and its evidence was in the L0 scratch `proto-A/shots/`; the screenshots kept are in `shots/` here, prefixed `A-`.

**Position in one line:** take SaaS *craft* and refuse SaaS *engagement mechanics*. Asclexis should feel as
fast, responsive and finished as Linear, with zero dead clicks, no blank frames, a keyboard palette, undoable
actions and dark mode. Its motion amplitude should stay under the Clinical Calm ceiling, enforced by
**motion zones**: chrome may move, data moves once and only to explain, and safety copy never moves.

**Concept (Awwwards Phase 0), one sentence:** *Asclexis is a lab notebook. Values you haven't checked yet are drawn in
pencil, values you've verified are inked, and every inked number traces back to the line of the report it
came from.* That idea already exists in the codebase: owner decision D4's hollow dashed marker for unverified
points (`TrendVerificationMarkers.tsx`) and the citation/provenance work. The revamp promotes it from an edge case
to the product's visual language.

---

## 1. DEPTH and RANGE analysis

### DEPTH: what a top product and motion team would do that the brief doesn't ask for

| Gap a studio would close | Evidence | What we do |
|---|---|---|
| **The app has no way back in.** An expired session lands on "Create Your Profile". | ui-review §4, `60-expired-session-landing-1440.png`; `useLogin`/`useUnlockProfile`/`useLockProfile` exist in `services/profiles.ts:139-181` and nothing calls them | A lock screen and session flow (**owner gate**, §4.5) |
| **Mobile doesn't exist.** `pl-64` plus a fixed `w-64` sidebar; scrollWidth is 588–1,077 at 390px | `probe-log.txt` | A designed phone shell: bottom tabs plus a More sheet. The sidebar is replaced on phones, not shrunk |
| **A placebo safety switch.** "Safety Mode ON/OFF" is `useState(true)` in `TopBar.tsx:11` | `72-safety-mode-off-1440.png` | Replace it with a static "Educational use · not medical advice" note that opens a plain-language explainer (built in the prototype) |
| **Contrast fails at the token level**, 314 axe nodes on 29/29 pages | ui-review §5 | Remap the tokens without renaming them, so every existing utility inherits the fix (built; axe 0 in the prototype) |
| **A blank ~450 ms on every navigation** from `AnimatePresence mode="wait"` | `probe-log.txt` opacity samples | A 180 ms CSS fade-up of the *new* page with no exit phase. Measured: opacity ≥ 0.82 by ~130 ms, full by ~190 ms (`shots/reveal-timing.txt`) |
| **No overlay, toast or error primitives.** 0 Escape handlers, 0 focus traps | audit §4 | Radix Dialog/Popover-based Sheet, Dialog, Popover, ConfirmDialog; sonner toasts with Undo |
| **The core value (trends) has no hero.** The chart sits at the same weight as a 7-row list, uses `type="monotone"` smoothing, and draws the range as a dashed line | `20-data-trends-1440.png` | **Range Ribbon**: the reference range as a band, a true time axis, straight segments, pencil/ink points, slider semantics, a table fallback |
| **Provenance stays hidden.** Citation detail is a hover/focus tooltip and cannot be opened on touch | `CitationTooltip.tsx:18-21` | **Source Trace**: every value opens the exact source row and page, on tap |
| **Browser surfaces were never designed** (Impeccable craft floor): focus ring fades in over 200 ms, default scrollbars, default caret | ui-review §3 | Instant outline focus ring, themed scrollbar, accent caret, `tabular-nums` (built) |
| **IA leaks implementation**: 12 flat items, Interpret vs Explain vs Trends, Alerts = settings | ui-review §4 | 4 named groups plus Overview, 9 destinations, plain nouns (built) |

**Raw material.** Real data shapes only: `TrendData`/`TrendPoint`/`Observation` from `services/types.ts:154-218`,
and the review's actual seeded values (glucose 92/104/118/101 against 70–99 mg/dL, LDL 142, HbA1c 6.1), plus the
real CSV source rows. There is no lorem ipsum. The prototype fixtures (`components/results/fixtures.ts`) mirror
the seeded CSVs row for row.

**Methods and tools.** React 18 + Vite 7 + Tailwind v4 (kept). **Motion 14** (`motion/react`, `LazyMotion` + `m`,
`MotionConfig reducedMotion="user"`) for exits, layout and drag only. **CSS** (transitions, keyframes,
`clip-path`) for everything predetermined, because it runs off the main thread during route loads
(animation-performance: the Vercel tab-indicator lesson). **Radix primitives** (already in the stack) for overlays.
**cmdk** for the palette, **sonner** for toasts, and **custom SVG** for the chart. The easing family is Emil
Kowalski's strong ease-out, `cubic-bezier(0.23, 1, 0.32, 1)`, and nothing else for UI.

**Outside judge.** axe-core on every state, PerformanceObserver CLS, Event Timing max duration (an INP proxy),
`scrollWidth` at 390, opacity/clip-path sampling of transitions, a reduced-motion emulation pass, the build size,
and the existing vitest suite. All of these were run on the prototype (§10).

### RANGE: what we take from other fields

- **Game UI:** one-frame press feedback on *everything* pressable (`.pressable`, scale 0.97, 120 ms), zero
  dead clicks (the dead "Last 12 Months", "Filters" and "Full Preview" buttons get wired or deleted), and an
  input-aware cursor: the chart cursor glides for the pointer but **jumps for the keyboard**, because animating
  keyboard actions makes them feel slow.
- **Film:** one authored entrance per screen, and only on first view. The Range Ribbon's line is revealed left to
  right with `clip-path` over 640 ms ease-out, once per analyte per session. Switching analytes later gives a
  150 ms fade, because the same reveal on the tenth switch is noise.
- **Native apps:** a bottom tab bar plus a sheet on phones, the iOS drawer curve for sheets
  (`cubic-bezier(0.32,0.72,0,1)`), optimistic verify with Undo, and no layout shift (measured CLS ≤ 0.001).
- **Print and lab notebooks (our own import):** pencil versus ink as the visual grammar for "unchecked"
  versus "verified", ruled lines that appear only where something is measured, and tabular figures.

### The goal beyond the goal

**In its first two minutes, Asclexis should read as a product a real team would ship. It gets there by
making an anxious patient feel more in control, not more entertained.**

---

## 2. The rewritten build brief

> Rebuild the Asclexis frontend to SaaS-grade craft under a clinical motion ceiling. A patient, possibly older and
> possibly anxious, on a laptop or phone, must be able to: get back into their profile; import a report; check
> the numbers against the source; see how each number has moved relative to the report's own reference range; and
> ask a grounded question. Every step needs instant feedback, no blank frames and no dead controls, and every
> number must be traceable to its source line within one tap.
>
> **Ship:** a token system with light and dark palettes, all text pairs ≥ 4.5:1 and non-text ≥ 3:1; a responsive
> shell (sidebar ≥ 1024 px, bottom tabs below it); grouped IA with 9 destinations; a command palette; accessible
> overlay, toast and tab primitives; the Range Ribbon chart and the Results screen that merges Trends and Interpret;
> Source Trace on every value; the pencil-to-ink verification language everywhere a value appears; a lock screen
> (owner gate).
>
> **Motion:** transform, opacity and clip-path only; one easing family; UI ≤ 300 ms, with one authored reveal per
> screen ≤ 640 ms; nothing animates on keyboard-initiated or 100+/day actions; `prefers-reduced-motion` removes all
> movement and keeps opacity and colour; numbers never tween; disclaimers, citations and range status are never
> animated and never hover-only.
>
> **Refuse:** engagement loops, celebration animations on results, 3D, scroll-jacking, decorative glass, gradient
> text, rainbow effects, runtime network.
>
> **Prove:** axe 0 serious/critical, CLS < 0.1, INP < 200 ms, no horizontal scroll at 390 and 320, a reduced-motion
> snapshot per screen, main chunk ≤ 165 kB gz, and route-level Playwright checks through HTTP with a mocked API.

---

## 3. Art direction

### 3.1 Register
"Ink & Paper" is warm paper surfaces, one deep teal ink, graphite for anything unverified, and clay for
"outside the report's range". It evolves Clinical Calm ("luxury wellness retreat meets precision lab",
`02_frontend_accessibility_plan.md:107`) and does not replace it. Depth comes from tonal layering and one
shadow scale. **No noise texture**: the plan asks for 2–4 % noise, but Impeccable's craft floor rightly calls
`feTurbulence` grain amateur, and it costs a full-screen paint layer. **No glass** except the sticky top bar's
`backdrop-blur` (functional: it keeps scrolled content legible under it).

### 3.2 Colour tokens and contrast

Raw tokens live on `:root` and are remapped under `:root[data-theme='dark']`. `@theme` only points at them, so the
**existing class names keep working** (`text-ink-secondary`, `bg-status-attention-subtle`, …) and the 106
`ink-tertiary` uses are fixed without editing a single component. The undefined `status-success`/`status-danger`
classes (19 uses, audit §3b) become aliases. Built in `src/frontend/src/styles/globals.css` in [`proto-A.patch`](proto-A.patch).

| Role | Token | Light | Dark |
|---|---|---|---|
| Canvas | `--paper` (`bg-surface`) | `#F6F5F1` | `#141412` |
| Card / elevated | `--surface-1` | `#FFFFFF` | `#1C1C19` |
| Muted / sunken | `--surface-2` / `--surface-3` | `#EFEDE7` / `#E7E4DC` | `#262521` / `#302F2A` |
| Text primary / secondary / tertiary | `--ink-1/2/3` | `#1C1B19` / `#4F4C46` / `#68645D` | `#EEECE6` / `#C2BEB5` / `#A29E95` |
| Hairline (decorative) / control border | `--line` / `--line-strong` | `#E2DFD7` / `#8A857B` | `#2F2E2A` / `#77736B` |
| Accent (ink) / hover / text-on-subtle / subtle | `--accent` … | `#1D6B5E` / `#185A4F` / `#165247` / `#E2EFEB` | `#6FC6B3` / `#86D1C0` / `#8AD3C2` / `#1D332E` |
| Text on accent | `--on-accent` | `#FFFFFF` | `#0B1D19` |
| Caution (amber) text / bg | `--caution` | `#7F5410` / `#FAF0DF` | `#E7B867` / `#2E2615` |
| Outside range (clay) text / bg | `--outside` | `#9C3F2E` / `#FAE9E4` | `#F09C88` / `#33201B` |
| Verified (sage) text / bg | `--verified` | `#2C6542` / `#E4F1E8` | `#8FCB9F` / `#1C2B21` |
| Info (slate) text / bg | `--info` | `#365A80` / `#E6EEF6` | `#9DBEE3` / `#1C2633` |
| Reference band / pencil | `--band` / `--pencil` | `#DCEBE5` / `#68645D` | `#1F3530` / `#A29E95` |

**Computed WCAG ratios** (script: `scratchpad/tools/contrast.mjs` and `c2.mjs`, L0 scratch, not committed, sRGB relative luminance):

| Pair | Light | Dark | Needs |
|---|---|---|---|
| ink-1 on paper / surface-1 / surface-2 | 15.78 / 17.21 / 14.70 | 15.61 / 14.46 / 12.98 | 4.5 |
| ink-2 on paper / surface-1 / surface-2 | 7.84 / 8.56 / 7.31 | 9.95 / 9.21 / 8.27 | 4.5 |
| **ink-3 on paper / surface-1 / surface-2 / surface-3** (was **2.69**) | **5.39 / 5.88 / 5.03 / 4.63** | 6.90 / 6.39 / 5.74 / 5.02 | 4.5 |
| ink-3 on band (chart labels) | 4.78 | 4.88 | 4.5 |
| accent on paper / surface-1 / surface-2 | 5.80 / 6.33 / 5.41 | 9.14 / 8.46 / — | 4.5 |
| accent-ink on accent-subtle (active nav; was 4.36) | 7.62 | 7.78 | 4.5 |
| accent-ink on paper | 8.25 | 10.70 | 4.5 |
| on-accent on accent / accent-hover (primary button) | 6.33 / 8.03 | 8.64 / 9.88 | 4.5 |
| caution on its bg / on surface-1 (was 2.08) | 5.85 / 6.61 | 8.15 / 9.31 | 4.5 |
| outside on its bg / surface-1 / paper (was 2.95) | 5.64 / 6.64 / 6.08 | 7.20 / 7.98 / 8.62 | 4.5 |
| verified on its bg / surface-1 / paper (was 2.60) | 5.92 / 6.89 / 6.32 | 7.91 / 9.12 / — | 4.5 |
| info on its bg / surface-1 (was 3.17) | 6.12 / 7.16 | 7.94 / 8.87 | 4.5 |
| pencil on surface-1 / band | 5.88 / 4.78 | 6.39 / 4.88 | 3 (non-text) |
| line-strong (input borders) on surface-1 / paper | 3.67 / 3.36 | 3.62 / 3.91 | 3 (1.4.11) |
| focus outline (accent / accent-ink) on paper | 5.80 | 10.70 | 3 |
| white on outside (danger button, light) | 6.64 | — | 4.5 |
| on-accent `#0B1D19` on outside (danger button, dark) | — | 8.15 | 4.5 |
| ink-disabled on surface-1 | 2.48 | — | exempt (1.4.3 disabled) |

`--line` is a decorative separator and exempt. One required code change follows from the table: the danger button
must use a `--on-status` token, not `text-white`, because white on dark-mode clay fails. Status is never colour
alone: every status pairs an icon or shape with words ("Above the reference range (per report)").

### 3.3 Type
Fraunces stays as the **display** face and only at ≥ 24 px (h1/h2). It stops at card titles: the review caught
it reading as decoration at 16 px. Source Sans 3 carries everything else, with `tabular-nums` for every value.
JetBrains Mono is kept **only** for raw source excerpts and the recovery code, where monospace is data, not
costume. Mono for reference ranges goes away (it wrapped "0-149 / mg/dL").

| Role | Size / line-height | Weight | Face |
|---|---|---|---|
| Display (page h1) | 38 / 1.15 (32 on phones) | 500, −0.02em, `text-wrap: balance` | Fraunces |
| Section (h2, analyte name) | 28 / 1.2 | 500 | Fraunces |
| Value readout | 40 / 1.0 | 600, tabular | Source Sans 3 |
| Title (h3, card) | 20 / 1.35 | 600 | Source Sans 3 |
| Body | 16 / 1.6 (17 with "Comfort text" setting) | 400, `text-wrap: pretty` | Source Sans 3 |
| UI / list | 15 / 1.45 | 500 | Source Sans 3 |
| Meta (floor for prose) | 14 / 1.45 | 400–600 | Source Sans 3 |
| Micro (chart ticks, kbd, group labels only) | 13 / 1.4 (`--text-xs` raised from 12) | 600, +0.06em for caps labels | Source Sans 3 |

There are no 10 px badges (17 `text-[10px]` uses are removed).

### 3.4 Space, radii, elevation, texture
- **Spacing:** a 4 px base; the steps 4, 8, 12, 16, 20, 24, 32, 40, 56, 72. Card padding is 20 px on phones and 28 px on desktop. There is more space above a heading than below it.
- **Radii:** 6 for chips and kbd, 10 for controls and nav items, 14 for popovers and the palette, 16 for cards, 20 for sheet tops, pill only for small toggles. Card radii stay at 12–16 (craft floor).
- **Elevation:** declared once, as a border *or* a shadow, never a ghost card with both at full strength.
  `--shadow-1` (resting card, 4 % + 8 %), `--shadow-2` (popover/menu), `--shadow-3` (sheet/palette/dialog). In dark
  mode the shadows become a 1 px inner highlight plus a deep drop shadow, because shadows don't read on charcoal.
- **Texture:** none. The chart's ruled lines are the only "grid", and they are earned, because the chart is a measuring tool.

### 3.5 Motion tokens (CSS custom properties, mirrored in `src/motion/tokens.ts`)

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | all enter/exit, press, cursor, pill |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | on-screen moves (list reorder) |
| `--ease-drawer` | `cubic-bezier(0.32, 0.72, 0, 1)` | sheets |
| `ease` | CSS keyword | colour/hover only |
| `linear` | — | the "reading line" progress loop only |
| `--dur-press` | 120 ms | `:active` scale 0.97 |
| `--dur-hover` | 150 ms | colour/background |
| `--dur-small` | 180 ms | popover, cursor glide, analyte fade |
| `--dur-route` | 180 ms | new page fade-up, 6 px, **no exit** |
| `--dur-overlay` / `-exit` | 240 / 160 ms | dialog, side sheet (exit faster) |
| `--dur-sheet` / `-exit` | 320 / 220 ms | bottom sheet |
| `--dur-ink` | 360 ms | pencil → ink |
| `--dur-reveal` | 640 ms | the one authored data reveal per screen |
| Springs (Motion) | `snappy {visualDuration .25, bounce .12}`, `sheet {visualDuration .35, bounce 0}` | drag-release only |
| Stagger | 40 ms per item, capped at 6 items (240 ms total) | lists that *appear as lists*; never section-by-section |
| `--motion-distance` | 1, or **0** under `prefers-reduced-motion` | multiplied into every translate/scale |

**Zones (the reconciliation rule, written into code comments and review checklists):**

| Zone | Examples | Allowed |
|---|---|---|
| Chrome | nav pill, sheets, palette, toasts, menus, press | transform + opacity, springs for drag |
| Data | chart line, values, tables, lists of results | opacity and `clip-path`, once per view; **numbers never count up** (a count-up from 0 to 142 shows values the patient never had) |
| Safety | disclaimers, citations, range status, "not medical advice" | **nothing**: static, always visible, never hover-only |

**Reduced motion:** movement goes, opacity and colour stay. Spinners become a slow opacity pulse instead of freezing
(audit §2c: the old global rule froze them). The chart reveal is skipped (measured: `clip-path: none` at 60 ms, and
the route becomes an opacity-only fade). `MotionConfig reducedMotion="user"` replaces the custom hook that
initialised to `false` (audit §2a).

**What never animates:** the command palette open/close (keyboard, 100+/day), keyboard chart navigation, focus
rings, tab switches triggered by the keyboard, and any number.

---

## 4. Information architecture and navigation

### 4.1 From 12 flat items to 9 grouped destinations (built)

| Group | Destination | Replaces | Route |
|---|---|---|---|
| — | **Overview** (new) | landing on an empty Inbox | `/overview` (index) |
| Records | **Documents** | Inbox | `/inbox` (keep route) |
| | **Review** | Verify | `/verify` |
| | **Timeline** | Timeline | `/timeline` |
| Understand | **Results** | Trends + Interpret (merged) | `/results` (`/trends`, `/interpret` redirect) |
| | **Ask** | Explain | `/explain` |
| Care | **Medications** (reminders inside) | Meds + Alerts | `/medications`, `/medications/reminders` (`/notifications` redirects) |
| | **Tasks** | Tasks | `/care-tasks` |
| | **Pinboards** | Pinboards | `/pinboards` |
| Share | **Doctor summary** | Export | `/export` |
| Profile menu | Settings, Lock now, Appearance | Settings nav item, the "user" icon | `/settings/:section` |

Rules: plain nouns, no "smart" names (brand guidelines). Active state matches prefixes, so `/medications/:id` keeps
its pill (the audit's exact-match bug). The brand is no longer an `h1`, so each page has exactly one. There is a
skip link, and it is the first tab stop (built).

### 4.2 Settings sprawl → sections
A 5,565 px single scroll becomes `/settings/:section` with a sub-nav (a sheet on phones):
**Profile & security** (recovery code, backup, delete profile, lock timer) · **Preferences** (time zone, text size,
appearance, motion, streaks) · **Reminders** · **Assistant & privacy** (step-by-step agent, memory, external API with
break-glass warning, data donation) · **Diagnostics** (OCR/Poppler, hardware, model tiers, training-data export),
collapsed behind "Show technical diagnostics" with a one-line explanation. Patient settings never sit next to GPU VRAM again.

### 4.3 Mobile shell (built)
Below 1024 px the sidebar is **replaced**: a 64 px top bar (brand mark, search icon, "Educational" note, profile
avatar) and a bottom tab bar with Overview, Results, Documents, Ask and More. Each tab is ≥ 56 px tall, and the bar
respects `env(safe-area-inset-bottom)`. More opens a bottom sheet with every group as 52 px tiles. Main content has
a 112 px bottom padding so nothing hides under the bar. Measured: scrollWidth = 390 in light and dark (`metrics.json`).

### 4.4 Command palette (built, lazy)
**Ctrl/⌘ K**, or click the top-bar search, which is now a button that opens the palette (one search, not two). It
searches results by analyte (with the latest value), destinations and actions (Import document, Log a dose, Ask
about…). Enter on free text falls through to `/search?q=`. **No open/close animation.** cmdk is loaded on first use
(5.6 kB gz chunk).

### 4.5 Unlock and session flow: **OWNER GATE** (auth; not built, only the disabled "Lock now" item is drawn)
Uses only existing endpoints and hooks (`useLogin`, `useUnlockProfile`, `useLockProfile`, `useLogout` in
`services/profiles.ts`). It changes nothing in auth/encryption code; it changes *which screen* users land on.
1. `ProtectedRoute`: if any profile exists (`useProfiles`) and the token is missing or expired, go to **`/unlock`**,
   not `/setup`. `/setup` is reachable from `/unlock` only through "Create another profile".
2. `/unlock`: profile picker (name and initial; never data), password, "Forgot password? Use your recovery code".
   Wrong-password errors name the problem and the recovery path. No shake animation: an error that *moves* reads
   as alarm.
3. **Signature moment 4, "Lift"**: on success the lock panel fades and lifts 8 px (240 ms) to reveal the shell, which
   was already rendered with skeletons behind it, so unlock feels instant. Under reduced motion it is a 150 ms
   opacity fade.
4. Idle lock: at T-2 min a toast says "Locking in 2 minutes to protect your records" with **Stay signed in**. Lock
   keeps the route, so a returning user lands where they were.
5. "Lock now" in the profile menu.

---

## 5. Signature moments (4)

Every one of them expresses the concept; none of them is decoration.

| # | Name | Trigger | Phases and timing | Purpose | Reduced motion | Mobile |
|---|---|---|---|---|---|---|
| 1 | **Ink** | the user verifies a value (Review, Source Trace, or optimistic from a toast) | the dashed graphite ring closes and fills with ink: `fill`, `stroke`, `stroke-dasharray` over 360 ms ease-out. The toast "…is now verified" carries **Undo**. Every chart, row and badge for that value flips together | state indication; it makes "checked by me" a visible, owned property of the data | instant swap; toast still shows | same |
| 2 | **Range Ribbon** | first view of an analyte in a session | ruled grid and band are static; the line and points are revealed L→R by `clip-path` over 640 ms ease-out (measured: 746 px → 260 px → −12 px at ~65/190/660 ms). Then the chart is a **slider**: ← → Home End jump with no animation; the pointer glides the cursor (180 ms) | explanation: the patient watches *time* pass along their own results once, then works with them | no reveal (`clip-path: none` at 60 ms, measured) | full width, 260 px tall, tap to select |
| 3 | **Source Trace** | "Show source" on any value | side sheet (desktop 240 ms) / bottom sheet (phone 320 ms drawer curve); the source row's highlight draws across the line with `clip-path` (420 ms, 160 ms delay). Copy: "This is what your report states." | provenance; the product's thesis (grounded, cited) made tangible, on tap and never hover | highlight fades in 150 ms | bottom sheet |
| 4 | **Lift** (owner gate) | successful unlock | lock panel opacity 1→0 with 8 px lift, 240 ms; shell already painted underneath | spatial continuity; the vault opens onto *your* place | opacity only | same |

**Refused moments:** confetti or celebration on verify or adherence (the BadgeToast `animate-ping` goes);
count-up numbers; any motion on out-of-range values (the clay triangle is static); thinking orbs (an AI mystique
that contradicts "grounded"); a 3D anything.

---

## 6. Per-component upgrade map (all 87 audit rows)

**Source key:** **PKG** = installed package · **REF** = reimplemented from a reference pattern (Emil recipes; Bencho/Morphin
*demos as visual reference only*, never their code) · **CUSTOM** = ours · **KEEP** = already good · **CUT** = delete.
Motion is given as *property · duration · curve*; "RM" is the reduced-motion behaviour. Every overlay listed as
"P2 Dialog/Sheet/Popover" inherits Escape, focus trap, focus return and `aria-modal` from Radix.

### 6a. `components/ui`
| Component | Upgrade source | Motion spec |
|---|---|---|
| Button | CUSTOM v2: add `loading` (replaces 69 inline `Loader2`), `link` variant, `--on-status` for danger; `transition-property: transform, background-color, color` (not `all`) | press scale .97 · 120 ms · ease-out; hover colour 150 ms ease; **no hover lift** (lift on every button is noise); RM: no scale |
| Card family | CUSTOM: `bg-surface-elevated` (kills `bg-white/80 backdrop-blur-xl` on every card), variants `plain / interactive / inset`; hover shadow only on `interactive` | interactive: border-colour 150 ms; none otherwise |
| Badge | CUSTOM → **StatusLabel** (icon + words) for status; Badge stays for neutral metadata only | none (safety zone) |
| Input | CUSTOM: `focus-visible`, `line-strong` border (3.67:1), error clears on valid input; add Select/Textarea/Checkbox primitives | border-colour 150 ms; error text appears with opacity 150 ms, never shakes |
| EmptyState | CUSTOM: requires an `action` (Trends had none); a small authored SVG per state, no illustrations library | content fades 180 ms on first mount only |
| Motion primitives (`Motion.tsx`) | PKG `motion` 14.6.0: rewrite on `m` + tokens; delete `PageTransition` (replaced by CSS `route-in`) and `modalVariants` (overlays move to CSS `data-state`) | stagger 40 ms cap 6; RM via `MotionConfig` |
| Skeleton family | CUSTOM: `aria-busy` on container, shapes match final layout; keep pulse, drop unused `CardSkeleton` | opacity pulse 1.6 s ease-in-out; RM: static |
| Barrel `ui/index.ts` | KEEP (stop re-exporting motion helpers from it, so the barrel doesn't drag Motion into every importer) | — |

### 6b. Layout and auth
| Component | Upgrade source | Motion spec |
|---|---|---|
| AppLayout | CUSTOM (built): grid shell, skip link, `route-in`, mobile padding, ErrorBoundary per route | new page: opacity 0→1 + 6 px rise · 180 ms · ease-out · no exit; RM: opacity only |
| Sidebar | CUSTOM (built) after REF Bencho "Collapsing sidebar" *pattern only*: 4 groups, CSS-transform pill | pill `translateY` · 220 ms · ease-out (compositor; replaces main-thread `layoutId`); RM: instant |
| TopBar | CUSTOM (built): search→palette button, SafetyNote, profile on phones; **remove Safety Mode toggle** | none |
| ProtectedRoute | CUSTOM (**owner gate**): redirect to `/unlock` when a profile exists | — |
| Barrels (`auth`, `layout`) | KEEP | — |

### 6c. Top-level, documents, lab-interpreter
| Component | Upgrade source | Motion spec |
|---|---|---|
| MedicationOverlay | CUSTOM: router `Link` (was `<a href>` full reload), chips → StatusLabel style | colour 150 ms |
| MemoryManager | CUSTOM: use Input/Select primitives, filter chips `aria-pressed`, delete via ConfirmDialog | add/edit panel: opacity + 4 px · 180 ms; RM opacity |
| PageImageOverlay | CUSTOM: image fades when decoded (no pop); bbox highlight uses Source Trace `trace-mark` | image opacity 180 ms; highlight clip-path 420 ms once |
| TrendVerificationMarkers | CUSTOM → folded into RangeRibbon's ink/pencil point; tokens, not hex | Ink 360 ms |
| CategoryBadge | CUT (no importer; raw palette colours) | — |
| EntityDetailView | CUSTOM: table → responsive rows; verify = Ink moment; out-of-range = icon + words | Ink 360 ms; row reorder `layout` (Motion) 240 ms ease-in-out; RM none |
| ExtractionConfidenceBadge | CUSTOM: words first ("Worth a glance", "Read clearly"), % secondary, one badge per row max | none |
| HighlightChips | KEEP logic; restyle to StatusLabel neutral | none |
| AdviceSection | CUSTOM: renamed "What to ask your clinician" framing; copy review | disclosure: CSS grid-rows 0fr→1fr 200 ms (tolerated height case) + opacity |
| CitationTooltip | REF Emil tooltip → **Popover** (P2): opens on click/tap/Enter, Escape closes, 44 px target, `aria-describedby` | popover scale .96→1 + opacity · 180 ms · origin = trigger; RM opacity |
| DisclaimerBanner | KEEP copy; `role="note"` instead of `role="alert"` (it's not an alert); safety zone | **never animated** |
| InterpretedResultCard | CUSTOM: lives inside Results as "Explain this result"; advice toggle gets `aria-expanded` | card opacity 180 ms on generate; no y |
| InterpretedTrendChart | CUSTOM → **RangeRibbon** (drops recharts) | Range Ribbon spec |
| PanelInterpretationDashboard | CUSTOM: panel summary as a Results header strip; insights list stagger | stagger 40 ms cap 6, opacity only (data zone) |
| ReferenceRangeComparison | CUSTOM: band + marker matching Ribbon; marker `transform` not `left` | marker translateX 180 ms on value change; RM instant |
| formatInterpretationText | KEEP | — |
| Barrel `lab-interpreter` | KEEP | — |

### 6d. Medication coach
| Component | Upgrade source | Motion spec |
|---|---|---|
| MedicationCard | CUSTOM: real `<button>`/`Link` (was `div onClick`), single animation owner | press .97 120 ms; list stagger once |
| MedicationForm | CUSTOM: Select/Textarea/Checkbox primitives (kills 4 copy-pasted focus strings) | none |
| DoseLoggingModal | P2 **Sheet** (bottom on phones, dialog on desktop); REF Bencho "Slide to confirm" **rejected** (drag-to-confirm is hostile for tremor and low dexterity); simple Taken / Skipped buttons | sheet 320/220 ms drawer curve; skip-reason panel: grid-rows 200 ms; RM opacity |
| BadgeToast | CUSTOM → a plain sonner toast, **no ping**, only if streaks are opted in (owner Q4) | sonner default enter (transition-based, interruptible) |
| AchievementsWidget | CUSTOM: demoted behind the streaks opt-in, retitled "Your log"; locked badges not shown | none |
| AdherenceDashboard | CUSTOM: ring draws from 0 **once** (stroke-dashoffset is a paint on a 64 px SVG, acceptable) or renders final; tokens | 480 ms ease-out once; RM final |
| ScheduleEditor | CUSTOM: 44 px controls, `htmlFor` labels, ConfirmDialog for delete, per-row pending state | none |
| StreakDisplay | KEEP copy (neutral on broken streaks); tokens | none |
| VoiceFirstUseModal | CUT unless voice ships; if it ships → P2 Dialog | — |
| Barrel `medication-coach` | KEEP | — |

### 6e. Pinboards, profile, settings
| Component | Upgrade source | Motion spec |
|---|---|---|
| AddToPinboardButton | KEEP Radix menu; add CSS `data-state` enter/exit | menu scale .96 + opacity · 180 ms · origin trigger |
| RecoveryCodeCard (profile) | CUSTOM: code in mono, grouped so it never wraps mid-group; Checkbox primitive; warning in `--outside` (5.64:1) | "Copied" label crossfade 150 ms |
| AgentSettingsCard | P2 **Switch** (Radix switch, one primitive replacing 3 copies) | thumb translateX 180 ms ease-out; RM instant |
| BackupCard | CUSTOM: ConfirmDialog for restore; progress uses `Pending` | none |
| DangerZone | CUSTOM: steps as a P2 Dialog with typed phrase; fix `text-muted-foreground` | dialog 240/160 ms |
| DataDonationCard | P2 Switch + ConfirmDialog (`alertdialog`) | as Switch |
| ExternalApiBreakGlassWarning | KEEP (safety zone; D12 requires a UI warning) | **never animated** |
| RecoveryCodeCard (settings) | CUSTOM: Input primitive | none |
| TierCapabilities | CUSTOM: honest copy (fixes "gemma4-12b — Template-based (no AI model)"), 13 px floor | none |

### 6f. Pages
| Page | Upgrade source | Motion spec |
|---|---|---|
| ProfileSetup | CUSTOM (**owner FYI: setup flow**): errors clear when fixed; **remove fake `setTimeout(500)` progress**; generic SaaS bullets → three plain facts; drop unlinked "Terms of Service" line | stagger of form groups once 40 ms; RM opacity |
| RecoverProfile | CUSTOM (**owner gate: auth flow**): Input/Select primitives | none |
| DocumentInbox → "Documents" | CUSTOM: one status per row, human category names, actions always visible on touch; **"reading line"** on processing rows (CSS, replaces the border-beam idea); preview → P2 Sheet; `window.confirm` → ConfirmDialog | new row: opacity + 4 px 180 ms; reading line translateX 1.6 s linear loop; RM opacity pulse |
| VerificationWorkbench → "Review" | CUSTOM: responsive stack below 1024; out-of-range icon + words; Edit → P2 Dialog; queue "In pencil / Inked" with `layout` reorder | Ink 360 ms; reorder 240 ms ease-in-out; RM none |
| TrendsDashboard | CUSTOM → **Results** (built in prototype); dead "Last 12 Months"/"Filters" become a real range filter or are deleted | Range Ribbon spec |
| TimelinePage | CUSTOM: cards name the analytes ("Glucose, LDL"), not "1 analyte"; drop double `p-8` | list stagger once |
| SearchPage | CUSTOM: query echoed in palette/search field; result cards = interactive Card | none |
| LabInterpreter | CUSTOM → merged into Results; fix CBC tab showing Glucose | — |
| MedicationCoach | CUSTOM: reconcile panel folded into a "Compare with a document" sheet | as above |
| MedicationDetail | CUSTOM: tokens, sheet for dose log | none |
| NotificationSettings → Medications › Reminders | CUSTOM: Switch primitives, table → list on phones | none |
| CareTasksPage | CUSTOM: done/ignore with Undo toast instead of instant strike | row: opacity to .6 + `line-through` 150 ms; Undo toast |
| PinboardsPage | CUSTOM: `window.prompt`/`confirm` → Dialog/ConfirmDialog | dialog 240/160 ms |
| ExplainAssistant → "Ask" | CUSTOM: message list owns its scroll (not the window); disclaimer pinned under the composer (always visible); citations → Popover chips; model chip says "Template answers (no model installed)" when true; typing indicator → `Pending` text "Reading your verified results…" | new message: opacity + 6 px 180 ms; `scrollIntoView` honours RM (already does) |
| ExportPage → "Doctor summary" | CUSTOM: section toggles → Switch; "Full Preview" wired to a Sheet or removed; strict-redaction note stays visible | none |
| SettingsPage | CUSTOM → `/settings/:section` (§4.2); its 3 dialogs → P2 | per primitive |

### 6g. `App.tsx` and inline sub-components
| Component | Upgrade source | Motion spec |
|---|---|---|
| RouteFallback | CUSTOM: layout-matched skeleton per route family; ErrorBoundary sibling | skeleton pulse; RM static |
| BadgeCard | CUSTOM (Q4): earned only, no hover lift on a non-interactive tile | none |
| AdherenceRing | see AdherenceDashboard | once, 480 ms |
| SourceQuote | CUSTOM → Source Trace link ("The note says…" opens the sheet) | — |
| CandidateCard | CUSTOM: interactive Card; add → optimistic + Undo | added row: opacity 180 ms |
| TaskCard | CUSTOM: see CareTasksPage | as above |
| SuggestionCard | CUSTOM: same pattern as CandidateCard | as above |
| MedReconcilePanel | CUSTOM: Select primitive; moves to a sheet | sheet spec |
| ResultCard (Search) | CUSTOM: interactive Card + StatusLabel | border-colour 150 ms |
| EventCard (Timeline) | CUSTOM: names analytes; pin via existing menu | none |
| Document preview dialog | P2 Sheet (Escape, focus, return) | 240/160 ms |
| Edit Value modal | P2 Dialog with label and named close button | 240/160 ms |
| Export confirmation dialog | P2 ConfirmDialog | 240/160 ms |
| Diagnostics fix dialog | P2 Dialog (`aria-modal`) | 240/160 ms |
| Consent dialog | P2 Dialog; consent copy is a safety zone | dialog only; copy static |
| Streaks switch | P2 Switch | thumb 180 ms |
| Model download progress | CUSTOM `role="progressbar"`, determinate bar as `scaleX` (not `width`) | scaleX 200 ms ease-out; indeterminate = reading line; RM pulse |
| Panel tablist (Trends) | P2 **Tabs** (Radix: roving arrows, tabpanel) → becomes the Results panel grouping | indicator translateX 200 ms for pointer, instant for keyboard |
| Panel tabs (LabInterpreter) | same Tabs (merged) | same |
| Typing indicator | CUSTOM `Pending` with `role="status"` text | opacity pulse; RM static text |
| Message bubbles | CUSTOM: feedback thumbs get `aria-label`, 44 px, defined success/danger tokens | press .97 |
| Section toggle buttons (Export) | P2 Switch rows | thumb 180 ms |

**Playbook sources I deliberately did not use:** Morphin's orbiting-glow buttons, 3D bending carousels and page-fold menus
(no image galleries exist; a fold menu hides navigation from people who need it predictable); Bencho's confetti,
UI sounds, magnetic dock, tilt cards and slide-to-confirm (a health app for anxious, possibly older users gains
nothing from tilt or sound; slide-to-confirm fails motor-impaired users); libraries.dev metal-fx, liquid-gooey and
img-fx. Bencho and Morphin were used only as named interaction patterns; I did not open or copy their code
(licence unverified / Pro-gated).

---

## 7. Dependencies and bundle

All gzip numbers were **measured by me** (esbuild `--minify` + `gzip -9`, react externalised; `proto-A/frontend/.measure/`, L0 scratch, not committed),
except where marked as a build-chunk measurement.

| Package | Version | Licence | gzip | Decision and why |
|---|---|---|---|---|
| `motion` | 14.6.0 | MIT | **9.4 kB** sync (`LazyMotion` + `m` + `MotionConfig` + `AnimatePresence`); `domAnimation` features **18.3 kB async chunk** (vite build). Full `motion` component = 46.5 kB | **Adopt, replaces `framer-motion` 10.18 (36.2 kB sync).** Peer `react ^18 ‖ ^19`. Only for exits, layout reorder and drag |
| `@radix-ui/react-dialog` | 1.1.15 | MIT | 11.5 alone | **Adopt**: Dialog, Sheet, ConfirmDialog, palette shell |
| `@radix-ui/react-popover` | 1.3.1 | MIT | 24.4 alone (shares floating-ui with the existing dropdown) | **Adopt**: citations, SafetyNote, filters |
| `@radix-ui/react-tabs` | 1.2.1 | MIT | 9.6 alone | **Adopt**: panel tabs, settings sections |
| `@radix-ui/react-switch` | 1.4.1 | MIT | 5.1 alone | **Adopt**: one switch instead of 3 copies |
| ↳ the four above **with** the existing dropdown-menu | — | — | 48.0 vs 26.6 today = **+21.4 kB** | shared internals |
| `@radix-ui/react-tooltip` | 1.4.1 | MIT | 20.2 | **Reject**: tooltips are hover-first; everything that matters opens on tap (Popover) |
| `cmdk` | 1.1.1 | MIT | 15.4 alone; **5.6 kB lazy chunk** in build | **Adopt, lazy** on first Ctrl/⌘ K |
| `sonner` | 2.0.8 | MIT | 9.4 | **Adopt**: Undo toasts, transition-based (interruptible) |
| `recharts` | 3.9.1 | MIT | 106.1 (lazy chunk 105.2 today) | **Remove** after UI-D3; the custom Range Ribbon is ~3 kB in the Results chunk |
| `border-beam` (libraries.dev) | 1.4.1 | MIT | 12.5 | **Reject, measured.** Only 4 fixed palettes (`colorful`/`mono`/`ocean`/`sunset`), none in our hue, rainbow by default; rotate types need manual reduced-motion wiring. Its one good use (a processing state) is the 0 kB CSS "reading line" |
| `thinking-orbs` | 0.3.2 | MIT | n/m | **Reject**: an AI "thinking" orb implies an agent with an inner life; the brand is grounded and cited. Use plain status text |
| `lenis` | 1.3.27 | MIT | 8.2 + 1.7 | **Reject**: an app shell with nested scrollers (chat, tables, sheets); native scroll is better for zoom and assistive tech |
| `@react-three/fiber` 9 / three | 9.x / 0.186 | MIT | ~417 kB | **Reject**: React 19 only, and nothing clinical gains from 3D |
| `react-aria-components` | 1.22.1 | Apache-2.0 | not measured | **Not now**: a second headless system next to Radix. Revisit only for a date-range field |
| `vaul` | 1.1.2 | MIT | — | **Reject**: last publish 2024-12-14 (`npm view`). The Radix Dialog sheet covers it |
| Spline, Aceternity, Canvas UI, Morphin code, Bencho code | — | excluded | — | excluded per brief |

**Bundle budget versus today's 180.0 kB gz main chunk** (`build-output.txt`):

| Build | Main JS gz | Notes |
|---|---|---|
| Today (`main` @ 7749744) | **180.0 kB** | 4 eager pages, framer-motion 10 |
| Prototype, eager (first pass) | 225.6 kB | everything eager: both motion versions, palette, sheets |
| Prototype + route splitting (Inbox/Verify/Settings/Results lazy, palette lazy) | 183.3 kB | still both framer-motion 10 and motion 14 |
| + all imports moved to `motion/react` (full `motion.*`) | 191.6 kB | full `motion` is heavier than v10 |
| **+ `motion.*` → `m.*` under `LazyMotion strict` (final prototype state)** | **160.4 kB** (−19.6) + 18.3 kB async features | **measured**, `npm run build` on the prototype ([`proto-A.patch`](proto-A.patch)) |
| Projected after UI-D3 (recharts gone) | main ≈ 160; **lazy −105 kB** | not measured |

**Budgets (CI-gated in UI-F4):** main ≤ 165 kB gz; any route chunk ≤ 30 kB gz excluding shared vendor; CSS ≤ 25 kB gz
(prototype 22.5, today 18.3); total first-load JS ≤ 200 kB gz.

### React 18 or 19: **stay on React 18** (bump to 18.3.1 as cheap preparation)

- **What 19 would buy:** R3F 9 (we reject 3D), React `<ViewTransition>` (needs 19.3+; CSS route fades already
  remove the blank gap), HeroUI and the shadcn Tailwind-v4 path (we use neither). **None of these is on the plan.**
- **What it would cost:** `@types/react` 19 typing changes across up to 147 TS/TSX files (ref-as-prop, `JSX` namespace,
  `useRef` requiring an argument); `forwardRef` in the ui primitives; re-validating `@testing-library/react` 16
  plus the 275 vitest tests; react-query/zustand/recharts compatibility checks. The risk is a stakeholder MVP date of
  2026-10-31 (owner-decisions MVP-PACKAGING) that is 8 days away.
- **Recommendation:** every dependency above supports 18. Do 19 later as its own isolated row (UI-X1) with zero UI
  changes, so a regression is attributable.

---

## 8. Build-program rows

**Conventions:** IDs are `UI-*`. **Rows in the same wave are file-disjoint**; waves run in order. Every row writes
its tests first (vitest in `src/frontend/src/__tests__/`, Playwright in `src/frontend/e2e/`), runs `npm run build`,
`npx vitest run` and the row's Playwright spec, and reports the actual output.

**Standard gates (G):** axe 0 serious/critical on every touched route in both themes · CLS < 0.1 · INP < 200 ms (Event
Timing max under 4× CPU throttle) · bundle budget (§7) · reduced-motion snapshot of each touched screen at t=60 ms
· no horizontal scroll at 390 **and 320** px · zero console errors · route tests through HTTP
(`tests/support/routes.py` is backend; on the frontend, `page.route` mocks with real `services/types.ts` shapes).

| Wave | ID | Phase | Files (owned) | Test-first checks | Acceptance |
|---|---|---|---|---|---|
| 0 | **UI-F0** | foundation | `e2e/ui-gates.spec.ts`, `e2e/support/mockApi.ts`, `e2e/support/gates.ts` | the harness itself: axe, overflow, CLS, Event Timing, RM screenshot, opacity sampler as reusable helpers; it runs red on `/trends` at 390 today (overflow), proving it can fail | the gates run without a backend in CI; documented in `e2e/README` |
| 1 | **UI-F1** | foundation | `src/styles/globals.css`, `ui/Card.tsx` | vitest `tokens.contrast.test.ts` parses `globals.css` and asserts every text pair ≥ 4.5 and non-text ≥ 3 in both themes; e2e axe `color-contrast` = 0 on 6 routes | axe colour nodes 314 → 0; undefined `status-success/danger` render with colour |
| 1 | **UI-F2** | foundation | `index.html`, `src/theme/theme.ts` | vitest: preference persists; `localStorage` throwing falls back to system; e2e: `data-theme` set before first paint (no flash) | dark mode **hidden behind Settings › Appearance "Preview"** until wave 6 (risk R3) |
| 1 | **UI-F3** | foundation | `package.json`, `src/motion/*`, `ui/Motion.tsx`, `hooks/useReducedMotion.ts`, mechanical import swap in the 17 files that import framer-motion (audit §2b), test mocks | vitest: no `from 'framer-motion'` anywhere (grep test); every page renders under `LazyMotion strict`; e2e RM: no transform at 60 ms on `/setup` | main ≤ 165 kB gz; vitest green apart from intentional contract changes (prototype: 273/275, the 2 failures are UI-F5's intended index-route and header-search changes) |
| 2 | **UI-F4** | foundation | `App.tsx`, `scripts/check-bundle.mjs`, CI workflow step | build fails above budget (prove it by lowering the budget in a test fixture) | Inbox/Verify/Settings lazy; ErrorBoundary `errorElement` per route |
| 2 | **UI-F5** | foundation | `components/layout/*` (AppLayout, Sidebar, TopBar, MobileNav, BrandMark, SafetyNote, ProfileMenu, navConfig) | e2e: skip link is the first tab stop; one `h1` per page; route opacity never < 0.3 for > 1 frame; 15 routes have no overflow at 320/390; vitest: prefix-active nav for `/medications/:id`; update `Routing.test` index → `/overview` | G; Safety Mode toggle gone (owner Q3) |
| 3 | **UI-P1** | primitives | `ui/Button.tsx`, `ui/Input.tsx`, `ui/Select.tsx`, `ui/Textarea.tsx`, `ui/Checkbox.tsx`, `ui/Switch.tsx` | vitest: loading state is `aria-busy` and disabled; press class present; Switch `role=switch` + keyboard | G; 44 px targets |
| 3 | **UI-P2** | primitives | `ui/Dialog.tsx`, `ui/Sheet.tsx`, `ui/Popover.tsx`, `ui/ConfirmDialog.tsx` | vitest + e2e: Escape closes, focus is trapped and returned, `aria-modal`, labelled; RM = opacity only | G |
| 3 | **UI-P3** | primitives | `ui/Toast.tsx` (sonner), `ui/Skeleton.tsx`, `ui/Pending.tsx`, `ui/EmptyState.tsx` | vitest: toast Undo calls handler; EmptyState requires action; Pending is `role=status` | G |
| 3 | **UI-P4** | primitives | `ui/Badge.tsx`, `ui/StatusLabel.tsx`, `ui/Tabs.tsx`, `documents/ExtractionConfidenceBadge.tsx`, delete `documents/CategoryBadge.tsx` | vitest: StatusLabel always renders icon + words; "abnormal" is not in output; Tabs roving focus | G |
| 4 | **UI-N1** | navigation | `layout/CommandPalette.tsx`, `layout/paletteEvents.ts` | e2e: Ctrl+K opens with **no** transition; Enter navigates; Escape returns focus to the trigger | palette chunk lazy ≤ 8 kB gz |
| 4 | **UI-N2** | navigation | `pages/SettingsPage.tsx` → `pages/settings/*` | e2e: each section route; Diagnostics collapsed by default; old `/settings` lands on Profile & security | G; the Settings page shrinks from 5,565 px |
| 4 | **UI-N3** | navigation | `pages/UnlockPage.tsx`, `auth/ProtectedRoute.tsx`, `ProfileMenu` lock item | e2e (mock API): expired token with an existing profile → `/unlock`, not `/setup`; wrong password shows recovery path; Lift is opacity-only under RM | **OWNER GATE: do not start without a yes** |
| 4 | **UI-N4** | navigation | `App.tsx` redirects, `pages/NotificationSettings.tsx` → reminders | e2e: `/notifications` → `/medications/reminders` | G |
| 5 | **UI-D1** | data viz | `components/results/RangeRibbon.tsx` (+ fixtures in tests) | vitest: time-proportional x; band from ref; pencil vs ink per `user_verified`; slider aria-valuetext; ← → Home End; table fallback renders the same values; **no number tweening** | G; reveal once per session (sampler: clip right inset reaches ≤ 0 by 700 ms) |
| 5 | **UI-D2** | data viz | `pages/ResultsPage.tsx`, `pages/TrendsDashboard.tsx` (delete), `pages/LabInterpreter.tsx` (fold in), `App.tsx` redirects | e2e: `/trends` → `/results`; PNG/SVG export still works (keep ChartExport tests); disclaimer visible without interaction; "Explain this result" shows DisclaimerBanner + citations | G; dead "Last 12 Months"/"Filters" gone or wired |
| 5 | **UI-D3** | data viz | `lab-interpreter/InterpretedTrendChart.tsx`, `ReferenceRangeComparison.tsx`, `medication-coach/AdherenceDashboard.tsx`, `TrendVerificationMarkers.tsx`, `package.json` (drop recharts) | vitest: the existing `InterpretedTrendChart`/`TrendVerificationMarkers` tests are ported to the Ribbon | lazy JS −105 kB gz |
| 5 | **UI-D4** | data viz | `components/results/ProvenanceSheet.tsx`, `PageImageOverlay.tsx` | e2e: tap opens the sheet; CSV row highlighted; PDF bbox drawn; verify → Ink + Undo; scroll region focusable | G |
| 6 | **UI-C1** | content | `pages/OverviewPage.tsx` | e2e: first run shows the "Import → Review → Results" checklist with working CTAs | G |
| 6 | **UI-C2** | content | `pages/DocumentInbox.tsx` | e2e: ≤ 2 badges per row; actions visible at 390 without hover; preview is a Sheet with Escape | G |
| 6 | **UI-C3** | content | `pages/VerificationWorkbench.tsx`, `documents/EntityDetailView.tsx` | e2e: out-of-range marked by icon + words; Edit dialog labelled; verify flips Ink | G |
| 6 | **UI-C4** | content | `pages/TimelinePage.tsx`, `pages/SearchPage.tsx` | e2e: timeline card names the analyte | G; update `SearchPage.test` header-search case |
| 6 | **UI-C5** | content | `pages/MedicationCoach.tsx`, `pages/MedicationDetail.tsx`, `components/medication-coach/*` | e2e: MedicationCard keyboard-operable; dose sheet Escape and focus; no `animate-ping` | G; owner Q4 applied |
| 6 | **UI-C6** | content | `pages/ExplainAssistant.tsx` | e2e: message list scrolls, not the window; disclaimer visible at 390 and 1440 without scrolling the rail; citation chip opens on tap; send button named | G |
| 6 | **UI-C7** | content | `pages/ExportPage.tsx`, `pages/PinboardsPage.tsx`, `pages/CareTasksPage.tsx` | e2e: no `window.prompt/confirm`; "Full Preview" works or is gone | G |
| 6 | **UI-C8** | content | `pages/ProfileSetup.tsx`, `pages/RecoverProfile.tsx`, `profile/RecoveryCodeCard.tsx` | e2e: errors clear on fix; no fake progress timers; 44 px eye toggle | **owner FYI/gate (auth flow)** |
| 7 | **UI-O1** | overlays | `pages/SettingsPage` dialogs now in `pages/settings/*`, `settings/DangerZone.tsx`, `settings/DataDonationCard.tsx`, `settings/BackupCard.tsx` | e2e: every overlay passes the P2 contract | 0 hand-rolled overlays remain (grep test: no `fixed inset-0` outside `ui/`) |
| 7 | **UI-O2** | overlays | `lab-interpreter/CitationTooltip.tsx` → Popover, `MemoryManager.tsx`, `VoiceFirstUseModal.tsx` (delete) | as above | G |
| 8 | **UI-M1** | micro | sweep of raw `<button>`s for `.pressable` and 44 px targets | e2e axe `target-size` = 0 | G |
| 8 | **UI-M2** | micro | copy pass: "abnormal" → "outside the reference range (per report)"; model chip honesty; "AI-powered insights" subtitle removed | vitest: forbidden-word list absent from rendered pages | brand-guideline compliant |
| 8 | **UI-M3** | micro | dark mode GA: remove the "Preview" gate | e2e: every route in dark passes axe | G |
| later | **UI-X1** | upgrade | React 19 | the full suite | separate PR, no UI change |

**Definition of done for the programme:** every G gate holds on all 15 routes plus Overview and Unlock in both themes;
Playwright screenshots at 1440/390 in light and dark are reviewed by a human; and the AGENT.md definition of done is met.

---

## 9. Risks, cuts, owner questions

### Risks
| # | Risk | Mitigation |
|---|---|---|
| R1 | **Time.** Stakeholder MVP 2026-10-31 is 8 days out; this is ~30 rows | Ship waves 0–2 plus UI-D1/D2/D4 for the MVP; the rest follows |
| R2 | The motion migration touches 17 files and test mocks | Mechanical, done first, proven in the prototype (vitest 273/275; both failures are intended contract changes) |
| R3 | Half-migrated dark mode (`bg-white/80` cards, hex in charts) looks broken | Token remap fixes most of it; dark mode stays behind "Preview" until UI-M3 |
| R4 | The custom chart loses recharts features (tooltips, responsiveness edge cases) | The Ribbon is small and tested; it keeps PNG/SVG export; a table fallback is always available |
| R5 | IA renames break muscle memory and docs and screenshots in the capstone report | Old routes redirect; owner Q7 can keep the names and take only the grouping |
| R6 | Unlock UX touches the auth surface | Frontend-only; existing endpoints; owner gate; Playwright through HTTP |
| R7 | Removing "Safety Mode" could be read as removing safety | It was a placebo; the SafetyNote states that the checks are always on; owner Q3 |
| R8 | "Engaging" gets read as "add celebrations" later | The motion zones table goes into the review checklist; Ink is the only reward, and it is informational |

### What I would cut first (in order)
1. UI-M3 dark mode GA (keep the tokens, ship light)
2. UI-C1 Overview (index → Results instead)
3. UI-N2 Settings split (collapse Diagnostics into one disclosure instead)
4. UI-N1 palette
5. UI-D3 recharts removal (bundle only; patients don't see it)

**Never cut:** F1 contrast, F5 mobile shell, P2 overlays, UI-N3 unlock (if approved), the disclaimer and Source Trace work.

### Owner questions (neutral, with options)
1. **What does "simulate SaaS" mean for the UI?** (A) SaaS *craft*: speed, polish, feedback, dark mode, palette; no engagement mechanics. (B) Craft plus engagement mechanics: celebrations, streak nudges, badges. (C) Keep Clinical Calm unchanged and polish only. *Proposal A assumes (A); please record the choice in `owner-decisions`.*
2. **Session flow (auth).** (A) Build `/unlock` with the existing endpoints (UI-N3). (B) Keep `/setup` but add a "Sign in to an existing profile" path on it. (C) Defer past the MVP.
3. **Top-bar "Safety Mode" toggle.** (A) Replace it with the static SafetyNote (prototype). (B) Keep a toggle and make it real (needs backend and ask-first modules). (C) Remove it with no replacement.
4. **Medication badges ("Week Warrior", "Comeback Kid").** (A) Show them only when streaks are opted in, without celebration animation. (B) Keep them as they are. (C) Remove them.
5. **Dark mode in the MVP.** (A) Ship it. (B) Ship it behind "Preview". (C) Post-capstone.
6. **Brand mark.** (A) Adopt the pencil-to-ink mark (prototype). (B) Keep the heart.
7. **Navigation names.** (A) Adopt Documents / Review / Results / Ask / Doctor summary. (B) Keep today's names and take only the grouping.
8. **libraries.dev packages the playbook asked for.** (A) Accept the measured rejection. (B) Use `border-beam` `mono` once, on the import processing row.

---

## 10. Prototype result ("prove one moment")

**What was built** (in [`proto-A.patch`](proto-A.patch), a byte copy of `src/frontend` plus these changes): the token system
(light and dark), theme resolution before paint, motion tokens and `MotionProvider`, the responsive shell (grouped
sidebar with the CSS pill, top bar with search→palette and SafetyNote, profile menu with appearance, mobile tab bar
with the More sheet, skip link, CSS route fade, sonner), the lazy cmdk palette, and the **Results** screen with
**Range Ribbon**, **Source Trace** and **Ink** (verify → toast with Undo). The full `framer-motion` → `motion` `m`
migration and route splitting were applied to measure the bundle. Data: fixtures shaped like `TrendData`, no
backend (vite on **5181**; nothing on 8101; Ollama and pytest not touched).

**Measured** (L0 scratch `proto-A/shots/metrics.json`, `reveal-timing.txt`, not committed; Playwright 1.58, Chromium 1200, axe-core 4.10.3, WCAG 2.0/2.1/2.2 A+AA):

| Check | light-1440 | light-390 | dark-1440 | dark-390 |
|---|---|---|---|---|
| axe violations, Results page | 0 | 0 | 0 | 0 |
| axe violations, Source Trace sheet open | 0 | 0 | 0 | 0 |
| Horizontal overflow (scrollWidth) | none (1440) | **none (390)**; today 588–1,077 | none | none |
| CLS (load + interactions) | 0.001 | 0.0003 | 0.001 | 0.0003 |
| Max Event Timing duration (INP proxy, unthrottled) | 56 ms | 40 ms | 40 ms | 32 ms |
| Console errors | 0 | 0 | 0 | 0 |
| Route change (main opacity, ~40 ms samples) | 1.00 0.37 0.82 0.98 1.00 | 1.00 0.00 0.82 0.98 1.00 | same | same |

- The Range Ribbon reveal: clip-path right inset 746 → 504 → 260 → 29 → −12 px at 65/126/189/356/665 ms; under
  reduced motion `clip-path: none` from the first frame and the route fade is opacity-only.
- Production build: main **160.4 kB gz** (today 180.0), `features` 18.3 kB async, Results chunk 6.5 kB gz,
  palette 5.6 kB gz, CSS 22.5 kB gz.
- `npx vitest run` on the prototype copy: **273 passed, 2 failed out of 275**. Both failures are intended contract
  changes: `HC-ROUTE-001` expects index `/inbox` (now `/overview`), and `FE-SRCH-UI-003` expects a header search form
  (now the palette).
- Bugs I found and fixed during the screenshot review: (1) a 533 px overflow at 390 from the top-bar search min-content
  width; (2) cmdk's built-in dialog had no `DialogTitle` (console error), so it was re-wrapped in a Radix Dialog with an
  sr-only title; (3) the source excerpt scroll region was not focusable (axe serious); (4) the in-chart band label
  collided with the line, so it moved to a legend that also explains every shape; (5) the reveal never played because
  `firstView` was recomputed after the effect ran, so it is now captured at mount and keyed by analyte; (6) the card
  stretched to the rail height, fixed with `items-start`.

**Screenshots** (in the L0 scratch `proto-A/shots/`; the ones kept are in `shots/` here, prefixed `A-`):
`A-results-light-1440.png`, `A-results-dark-1440.png`, `A-results-light-390.png`, `A-results-dark-390.png`
(plus `-full` variants), `A-results-reveal-mid-light-1440.png` (line mid-reveal), `A-source-sheet-{light,dark}-{1440,390}.png`,
`A-after-verify-ink-{light,dark}-{1440,390}.png`, `A-results-keyboard-select-*.png`, `A-command-palette-{light,dark}-1440.png`,
`A-safety-note-{light,dark}-1440.png`, `A-mobile-more-sheet-{light,dark}-390.png`, `A-reduced-motion-60ms-light-1440.png`.

**Known issues I'd fix next:** at 390 the chart starts just under the fold (header copy and status rows push it
down; compress the intro on phones); a toast can sit over an open More sheet (dismiss toasts when a sheet opens);
the "outside range" triangle on a point at the top edge is tight against the plot edge.

**Could not verify:** real-device frame rate and INP under throttling (desktop Chromium only, no CPU throttle); screen
readers (NVDA, VoiceOver); 200 % zoom and Windows High Contrast; Firefox and Safari (only Chromium 1200 was run); real
backend data and the PDF bbox path of Source Trace (fixtures only; the CSV path only); dark mode on the
*unmigrated* pages; the unlock flow (owner gate, not built); `review-animations` could not be invoked
(`disable-model-invocation`), so motion was self-reviewed against Emil's checklist instead; Bencho and Morphin pages
were not opened (excluded or reference-only); border-beam was measured and its README read but it was never rendered.
