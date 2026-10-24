# Asclexis UI review (current state, 2026-10-23)

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

These notes read the app twice: once as an Awwwards juror would, and once as a SaaS product manager. Every claim points at a screenshot in
`shots/`, a measurement in `capture-metrics.json`, `capture-log.txt` or `probe-log.txt`, or a file:line. The component
inventory is in `COMPONENT_AUDIT.md`, and how the docs frame the product is in `framing.md`.

## How this was captured (and what it was not)

- **Code under test:** `main` @ 7749744. I copied `src/frontend` byte for byte (without `node_modules`) to
  `scratchpad/fe/` (L0 scratch, not committed) and ran `npm ci` there. That kept Linux-only native binaries out of the Windows checkout. No repo file was changed.
- **Backend:** `~/venvs/asclexis-311`, run as uvicorn `main:app` with the CWD set to a throwaway `scratchpad/appdata/` (L0 scratch, not committed), so `data/` (the master DB,
  vaults and JWT secret) lived only there. `LLM_PROVIDER=llama_cpp` with an empty models dir. **No Ollama call was made**: the
  provider never resolved to Ollama, and I never touched the provider switch. SQLCipher was available, so vaults were encrypted.
- **Seed data:** the same API write paths the repo's own `e2e/tailwind4-styles.spec.ts` uses: 3 lab CSVs (13 observations),
  glucose and lipid rows verified, one medication with a schedule, one pinboard, one assistant turn. One extra CSV was uploaded through the UI.
- **Browser:** Playwright 1.58 against an existing Chromium-1200 build (the pinned headless shell was not installed).
  Every authenticated route was shot at 1440×900 and 390×844, in both empty and populated states. axe-core 4.10 (WCAG 2.0/2.1/2.2 A+AA tags) ran on every
  1440 route. CLS came from a `layout-shift` PerformanceObserver.
- **Full-page screenshot artifact:** at 1440 the fixed sidebar stops at 900px in tall shots, and at 390 the image is wider than
  390px because the page overflows horizontally. That overflow is real (see P1). The sidebar cut-off is not a bug; it is how a fixed element renders in a full-page capture.
- **Dark mode:** there is none. With `colorScheme: 'dark'` the app renders identically to light (`50-dark-pref-*.png`), so
  there are no dark screenshots beyond those two.
- **Not tested:** real PDF or OCR import (Tesseract is not installed), a real LLM answer (no model), the Windows `dev.ps1` launcher,
  screen readers, and 200% zoom.

---

## 1. First impression, hierarchy, typography, colour, depth, density

**First impression (setup, `01-setup-1440.png`, `01-setup-390.png`):** this is the strongest screen in the product.
The warm off-white, the deep-teal accent, Fraunces display type and a centred single column look calm and credible. It
fits the "Clinical Calm" brief (`docs/02_frontend_accessibility_plan.md:107`). Its weaknesses:
- The three feature bullets are generic SaaS reassurance ("Private & Secure").
- The footer says "you agree to our Terms of Service", and no terms exist or are linked.
- The decorative blur blob on the right is nearly invisible.

**Inside the app (`20-data-*-1440.png`):** each page is competent, but the pages are interchangeable. Every one follows the same
template: a Fraunces H1 with a grey subtitle, a primary button top-right, and white `rounded-2xl` cards with a 6%-opacity shadow on `#FAFAF8`.
Nothing is the hero of any screen.
- The Trends chart (`20-data-trends-1440.png`) is the product's core value and should be its signature moment. Instead it
  sits in the same card as everything else, at the same weight as a 7-row list.
- An Awwwards juror would score this "clean template". It is not memorable yet.

**Typography:**
- Fraunces is used for every heading level, down to 16px card titles ("Analyte Summary", "Recent Documents"). At that
  size it reads as decoration rather than hierarchy.
- Uppercased analyte titles ("GLUCOSE") clash with the sentence-case list beside them.
- Mono is used for reference ranges in Verify (`20-data-verify-1440.png`), where "0-149 / mg/dL" wraps onto two lines.
- Body text at 12–13px is common: badges, metadata lines, the Explain disclaimer card. That is small for the stated audience of "older
  patients and non-medical users" (`docs/02_frontend_accessibility_plan.md:6`).

**Colour and depth:**
- Accent use is disciplined.
- Status colours are pastel by design ("don't alarm"), but as text they fail contrast everywhere (see §5).
- Depth is one level: card on page. Modals use a heavy grey backdrop blur (`76-dose-log-modal-1440.png`).
- The documented "atmosphere" utilities exist in CSS but nothing uses them: `glass-card`, `subtle-noise`, `stagger-animation` and `animation-delay-*`
  (see `COMPONENT_AUDIT.md` §3).
- The six `dark-*` tokens have no consumers.

**Density:** the density is uneven.
- Inbox rows carry five badges each (`lab_csv` appears twice, "Abnormal lab ×3", "60% · Medium · Lowest extraction
  confidence", "Needs Review"; `20-data-inbox-1440.png`). That is noise, not information.
- Timeline cards (`20-data-timeline-1440.png`) say "Lab results (1 analyte)" without naming the analyte, so ten cards carry almost no information.
- Settings is a single 5,565px scroll (`20-data-settings-1440.png`, crops in `crops/settings-*.png`). It mixes patient preferences with
  developer diagnostics: Tesseract on PATH, Poppler, "DPO/GRPO-ready preference dataset", GPU VRAM, and a model tier list whose
  descriptions contradict themselves ("gemma4-12b — Template-based interpretations (no AI model)").

## 2. Motion

**What exists** (details in `COMPONENT_AUDIT.md`):
- Sidebar active pill: a framer `layoutId` spring (`Sidebar.tsx:77`). This is the best piece of motion in the app.
- Route transition `PageTransition` (`components/ui/Motion.tsx`): a 300ms slide-up and fade inside `AnimatePresence mode="wait"`
  (`AppLayout.tsx:17`).
- The setup screen staggers its children in.
- Buttons have a hover lift and `active:scale-[0.98]`.
- Skeleton pulse appears in the `RouteFallback` and a few pages.
- Recharts' default line animation runs, because `isAnimationActive` is never set.
- `BadgeToast` has an enter/exit transition.

**What is janky:**
- **Every navigation has a blank gap.** `mode="wait"` makes the old page fade fully out before the new one mounts, and lazy routes then
  show a spinner. Sampled opacity of `main > div` after clicking a nav item, every ~50ms:
  `1.00 1.00 1.00 0.66 0.44 0.32 0.11 0.02 0.00 0.00 0.09 0.34` (`probe-log.txt`). That is roughly 450ms of fading out and
  nothing before content comes back. Frames: `35-nav-transition-60ms-1440.png` (old page gone, centred spinner),
  `35-nav-transition-180ms-1440.png` (ghosted new page), `35-nav-transition-400ms-1440.png`. This is the opposite of
  "smooth SaaS". Linear and Vercel-style apps cross-fade, or swap instantly, with skeletons in place.
- The sidebar pill springs out from Inbox to the new item *before* the page changes. Without a shared rhythm, the two motions feel disconnected.
- Explain: sending a message scrolls the whole window rather than the message list. The sticky "Some values are still unverified" banner then
  sits on top of the previous answer's text (`37-explain-pending-300ms-1440.png`).
- `CitationTooltip.tsx:40` uses `animate-in fade-in-0 zoom-in-95`, but no animate plugin is installed, so the tooltip has no motion at all.
- `DoseLoggingModal` is unmounted without `AnimatePresence`, so its exit animation never plays (`COMPONENT_AUDIT.md`).
- Profile creation fakes progress: there are `setTimeout(500)` steps around the real API call (`ProfileSetup.tsx`, `handleCreateProfile`). It is
  harmless, but it is theatre (`05-setup-creating-progress-1440.png`).

**Reduced motion:** partly handled.
- The CSS rule (`globals.css:257-269`) collapses CSS animations and transitions. It also freezes spinners, so loading
  feedback becomes a static icon.
- Framer uses a custom `useReducedMotion` hook that **initialises to `false`**. The first render after mount therefore animates even
  when the user asked for reduced motion.
- There is no `MotionConfig reducedMotion="user"`.
- Recharts' line-draw animation ignores the preference.
- Under `reducedMotion: 'reduce'` the route still fades out and in (`probe-log.txt`). Opacity-only is acceptable, but the
  blank gap remains (`51-reduced-motion-nav-60ms-1440.png`).
- Some call sites zero only the stagger delay and keep the y-offset (`DocumentInbox.tsx:130-143`, `ProfileSetup.tsx:172-184`).

## 3. Feedback states and dead clicks

| State | Observed |
|---|---|
| Hover | Buttons lift. Nav items tint. Inbox row actions (pin, view, more) are `opacity-0` until hover on hover-capable devices (`DocumentInbox.tsx:398`), and `focus-within` reveals them for keyboard users. That is OK, but discoverability is poor (`73-inbox-mouse-away-1440.png`). |
| Press | `active:scale-[0.98]` on `Button` only. Raw `<button>`s (the password eye, citation chips, thumbs) have no press state. |
| Focus | A global `*:focus-visible` ring plus `focus-visible:ring-2` on Button. The ring **fades in over 200ms** because Button uses `transition-all` (`71b-topbar-focus-after-400ms-1440.png` shows it after it settles; captures under ~100ms showed none). Rings are visible on the sidebar (`32-inbox-focus-tab4-1440.png`). |
| Loading | Mostly spinners. Route skeletons appear only on the first lazy load. There are no optimistic updates. |
| Empty | Present and polite on every route (`10-empty-*-1440.png`). Most have **no call to action**: Trends says "Import lab documents to see your trends" with no button (`10-empty-trends-1440.png`). Explain's empty state is the best of them, with suggested questions. |
| Error | Setup validation errors **stay after the fields are fixed**: "Name is required" sits under a filled name field and "Password is required" under a typed password (`03-setup-weak-password-1440.png`). Inline errors are coral `#C9857A` at 2.95:1. |
| Success | Upload shows a clear inline result card with "Preview" and "Review values" plus a duplicate warning (`30-inbox-upload-250ms-1440.png`). That is good. There is no global toast system. |

**Dead or misleading clicks (verified):**
- Trends **"Last 12 Months"** and **"Filters"** have no `onClick` (`TrendsDashboard.tsx:308-315`).
- Export has **"Full Preview"** (`COMPONENT_AUDIT.md` cites `ExportPage.tsx:~327`).
- **The top-bar "Safety Mode" toggle is a placebo.** It is `useState(true)` local to `TopBar.tsx`. Toggling it changes nothing else
  (main text length 603 → 603), and it silently resets to ON after any navigation (`probe-log.txt`, `72-safety-mode-off-1440.png`).
  In a health app, a switch that reads "Safety Mode OFF" claims that the safety guards can be turned off. That claim is false and it erodes trust.
- The panel tab "CBC" is selected while the content shows **Glucose**, and the badge reads "0" with no explanation (`20-data-trends-1440.png`,
  `20-data-interpret-1440.png`). "Interpret CBC Panel" then interprets 2 values that are not on screen (`39-interpret-after-click-1440.png`).
- Classes that resolve to nothing: `status-success` (10 uses) and `status-danger` (9 uses) in `ExplainAssistant.tsx` and
  `SettingsPage.tsx`, and `text-muted-foreground` in `DangerZone.tsx`. These states render with no colour.

## 4. Navigation, onboarding, perceived performance

**Navigation model:**
- There are 12 flat sidebar items with overlapping jargon: **Interpret** vs **Explain** vs **Trends**, and **Alerts** is notification
  *settings*. Search exists only in the top bar, and the top-bar box does not show the query on the results page (`20-data-search-q-glucose-1440.png`).
- There is no grouping (Records / Understand / Act / Account) and no profile identity in the chrome. The "user" icon simply opens Settings.
- Each page has two `<h1>`s, because the sidebar brand is an h1.
- There is **no skip link**, so a keyboard user tabs through 12 nav links before reaching content (`probe-log.txt`).
- The active pill only matches exact paths, so `/medications/:id` loses it.

**Onboarding:** profile creation is good, and the recovery-code gate is genuinely good: the continue button stays disabled until "I have saved this…"
is checked (`06-setup-recovery-code-1440.png`). There are smaller issues: the code wraps awkwardly ("…-J / KX6-RAEW"), and the warning text is coral at 2.95:1.
**The big gap is that the app has no way back in.**
- No login, unlock, lock or sign-out UI exists anywhere. `useLogin` and `unlockProfile` exist in `services/profiles.ts`, but no page uses them.
- The JWT lasts 60 minutes (`capture-log.txt`). When it expires, `ProtectedRoute` sends the user to `/setup`, which offers only "Create Your
  Profile" and a recovery-code link (`60-expired-session-landing-1440.png`).
- So a returning patient sees "Welcome to Asclexis" and is invited to create a *new* profile. The other options are to burn the recovery code
  or to conclude the data is gone. This is the single worst moment in the product.

**After setup:** you land on an empty Inbox with no next-step guidance or checklist. A SaaS onboarding pattern would offer something like "Import your first lab report →
Verify values → See trends" (`10-empty-inbox-1440.png`).

**Perceived performance:**
- CLS is excellent: 0.000 on most routes, worst 0.055 (`/interpret` at 390) and 0.047 after generating an interpretation
  (`capture-metrics.json`).
- The blank route gap (§2) is the main perceived-latency problem; the network is not.
- The main chunk is 575 kB (180 kB gzip), above Vite's warning, partly because `SettingsPage` (1,144 lines) and three other pages are eager (`App.tsx:19`).

## 5. Accessibility (WCAG 2.2 AA) and mobile

**axe-core, 29 audited states at 1440:**

| Rule | Pages | Nodes | Note |
|---|---|---|---|
| color-contrast | 29 / 29 | 314 | token-level, see below |
| label | 2 | 4 | Explain filter date inputs have no label |
| button-name | 3 | 3 | Explain send button (icon-only, no name); a Notifications icon button |
| select-name | 2 | 2 | Settings timezone `<select>` |
| target-size | 1 | 1 | setup password eye toggle, 20×20 |
| scrollable-region-focusable | 1 | 1 | Explain message list |

**Contrast is broken at the token level**, so every page inherits it. Computed ratios:

| Token pair | Ratio | AA text (4.5) |
|---|---|---|
| `ink-tertiary #9A9A9A` on surface | 2.69 | fail |
| `accent` on `accent-subtle` (active nav label) | 4.36 | fail |
| `status-caution #D4A574` on its subtle bg | 2.08 | fail |
| `status-attention/critical #C9857A` on white (errors, warnings, out-of-range values) | 2.95 | fail |
| `status-verified #7BA387` on its subtle bg | 2.60 | fail |
| `status-info #6B8CAE` on its subtle bg | 3.17 | fail |
| `ink-secondary #6B6B6B` on surface | 5.10 | pass |
| white on `accent` (primary button) | 4.91 | pass |

**Other accessibility issues:**
- **Use of colour (1.4.1):** Verify marks out-of-range values only by tinting the number coral, with no icon or label
  (`20-data-verify-1440.png`).
- **Dialogs:** six hand-built overlays and zero `Escape` handlers in the codebase. Nothing traps or returns focus. On opening the dose modal,
  focus stays on the "Log" button behind the backdrop, and after 25 Tabs focus is outside the modal (`probe-log.txt`). `DoseLoggingModal`
  has no `role="dialog"`. Only the Radix dropdown handles this correctly.
- **Target size:** `Button` enforces a 44px minimum (good). Raw buttons fall below it: the password eye is 20px, `CitationTooltip` 20px, the `BadgeToast` dismiss 32px.

**Mobile: not supported.**
- `AppLayout` hard-codes `pl-64`, and the sidebar is a fixed `w-64` with no breakpoint. At 390px, `main` starts at x=256 and is
  493–820px wide, so every authenticated route scrolls horizontally: scrollWidth runs from 588 to 1,077px (`probe-log.txt`,
  `capture-metrics.json`).
- What a phone user sees is two-thirds sidebar (`70-phone-viewport-trends-390.png`, `70-phone-viewport-explain-390.png`).
- Only `/setup` and `/recover` work on a phone (`01-setup-390.png`, `07-recover-390.png`).

## 6. Health-app constraints, checked against today's UI

| Constraint | Today | Evidence |
|---|---|---|
| Disclaimers and citations stay visible, never animated away or hover-only | **Partly.** Explain has a permanent "Important" card (it sits at the bottom of the right rail, below the fold on smaller laptops). A panel interpretation shows an "informational purposes only" box. Answers show "Sources: [1] Your Document" and "1/1 claims verified". **But:** a text scan for "educational / medical advice / healthcare provider" finds **nothing** on `/trends`, `/verify`, `/timeline`, `/export`, or `/interpret` before you generate. The citation detail is a tooltip (`CitationTooltip.tsx:18-21`) that opens on hover or focus only, so a touch user has no way to open it. | `probe-log.txt`, `38-explain-answer-1440.png`, `39-interpret-after-click-1440.png` |
| "Educational, not medical advice" framing | Strong in copy where it exists: Care Tasks ("nothing here is app advice"), Settings and Danger Zone (mechanism-first voice). It is weakened by "Abnormal lab ×N" chips and a "normal" pill, which the plan asks to avoid ("Prefer 'outside the reference range (per report)' over 'abnormal'", `docs/02_frontend_accessibility_plan.md:188`), and by the "AI-powered insights" subtitle. The Explain chip reads "llama_cpp · phi-3-mini" while no model is installed and answers come from the template fallback. Nothing tells the user that the model is unavailable. | `20-data-inbox-1440.png`, `20-data-explain-1440.png` |
| Calm rather than frantic | Mostly calm. Exceptions: gamified badges ("Week Warrior", "Comeback Kid") on Meds; coral "Partially verified" chips that read as alarms; up to five badges per inbox row. | `20-data-medications-1440.png`, `20-data-timeline-1440.png` |
| Local-first: no runtime CDN, remote fonts or telemetry | **Pass.** Fonts come from `@fontsource`. `index.html` has no external links. A URL grep of `dist/` finds only spec namespaces and library error-doc strings. One nit: `index.html` references `/favicon.svg`, and no `public/` dir exists, so it 404s. | `build-output.txt`, `index.html` |
| WCAG 2.2 AA | **Fail.** Token contrast, missing dialog semantics, unlabeled controls, no reflow at 320–390px. | §5 |

## 7. Bundle size (`npm run build`, verbatim tail; full output in `build-output.txt`)

```
vite v7.3.6 building client environment for production...
✓ 2494 modules transformed.
dist/index.html                                                      1.27 kB │ gzip:   0.61 kB
dist/assets/index-B9rVSmCO.css                                      72.87 kB │ gzip:  18.30 kB
dist/assets/EmptyState-D2NpKada.js                                   0.72 kB │ gzip:   0.40 kB │ map:     2.00 kB
dist/assets/RecoverProfile-DwQmiwuK.js                               3.70 kB │ gzip:   1.40 kB │ map:    11.10 kB
dist/assets/PinboardsPage-B8Q4C9D3.js                                4.69 kB │ gzip:   2.03 kB │ map:    13.97 kB
dist/assets/SearchPage-LgXDGSbY.js                                   6.21 kB │ gzip:   2.24 kB │ map:    17.42 kB
dist/assets/CareTasksPage-Dgqz2GyG.js                                6.58 kB │ gzip:   2.38 kB │ map:    20.78 kB
dist/assets/TimelinePage-BwMJasAq.js                                 7.03 kB │ gzip:   2.50 kB │ map:    20.73 kB
dist/assets/TrendsDashboard-B_blRwoW.js                             13.23 kB │ gzip:   4.52 kB │ map:    43.95 kB
dist/assets/MedicationDetail-oTeEAnpE.js                            14.74 kB │ gzip:   4.11 kB │ map:    41.89 kB
dist/assets/NotificationSettings-C4ispsq0.js                        17.00 kB │ gzip:   4.31 kB │ map:    52.28 kB
dist/assets/MedicationCoach-BM6mmW3R.js                             17.72 kB │ gzip:   5.56 kB │ map:    54.55 kB
dist/assets/ExportPage-Dk0_EhcD.js                                  17.89 kB │ gzip:   4.83 kB │ map:    52.32 kB
dist/assets/ExplainAssistant-DajiYGRv.js                            22.17 kB │ gzip:   6.89 kB │ map:    80.30 kB
dist/assets/LabInterpreter-BzHPC9xG.js                              25.18 kB │ gzip:   7.61 kB │ map:    87.97 kB
dist/assets/TrendVerificationMarkers-CMgnz-lB.js                   358.54 kB │ gzip: 105.16 kB │ map: 1,918.69 kB
dist/assets/index-BNaiZsUW.js                                      575.41 kB │ gzip: 180.00 kB │ map: 2,600.26 kB

(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
✓ built in 13.35s
```

- **Initial JS:** 180 kB gzip (react, react-dom, router, react-query, framer-motion, zustand, lucide, plus 4 eager pages).
- **Recharts chunk:** 105 kB gzip, loaded with Trends and Interpret.
- **CSS:** 18 kB gzip.
- **Font files:** about 360 kB in total across woff and woff2 subsets. They load lazily by `unicode-range`, so the runtime cost is only the Latin subsets.
- **Production sourcemaps** are on (`vite.config.ts` `sourcemap: true`).
- **Verdict:** fine for a local desktop app. The only real lever is to make Settings, Inbox and Verify lazy, and to split framer-motion if motion grows.
- **tsc** passed as part of `npm run build`. `vitest` and `tsc --noEmit` were not run separately.

## 8. The 10 highest-leverage problems, ranked

Ranking: harm to a real patient first, then reach (how many screens), then cost to fix.

1. **No way back into an existing profile.** There is no login, unlock, lock or sign-out UI. An expired 60-minute session lands on "Create Your Profile".
   This risks duplicate profiles, burnt recovery codes and "my data is gone" panic. (`60-expired-session-landing-1440.png`;
   `useLogin` and `unlockProfile` are unused.)
2. **The app shell is desktop-only.** A fixed 256px sidebar with `pl-64` and no breakpoints means every authenticated route overflows at 390px
   (scrollWidth 588–1,077). (`70-phone-viewport-*.png`)
3. **The "Safety Mode" toggle is a placebo.** It is local state, changes nothing, and resets on navigation. The UI implies safety guards can be switched off.
   (`TopBar.tsx`, `72-safety-mode-off-1440.png`)
4. **Contrast fails at the token level.** `ink-tertiary` is 2.69, every status colour used as text is 2.1–3.2, and the active nav label is 4.36. axe reports 314 nodes
   across all 29 audited pages. Out-of-range values in Verify are signalled by colour alone.
5. **Educational framing is inconsistent.** There is no disclaimer on Trends, Verify, Timeline, Export or pre-generation Interpret. "Abnormal" and "normal"
   vocabulary goes against the plan. The model chip claims phi-3-mini while answers come from the template fallback. Citation detail opens on hover or focus only, never on tap.
6. **Route transitions blank the page for about 450ms on every click** (`mode="wait"`, a 300ms exit, then a spinner). This undermines the
   "smooth" goal more than any missing animation does. The reduced-motion hook also starts `false`.
7. **There is no overlay, toast or error-boundary primitive.** Six hand-rolled overlays have no Escape handling, no focus trap and no focus return. The dose modal has
   no dialog role and its exit animation is dead. One render error white-screens the app.
8. **Dead and contradictory controls.** These include the "Last 12 Months" and "Filters" buttons, "Full Preview", the "CBC" tab showing Glucose, stale validation errors on setup,
   and undefined `status-success`/`status-danger` classes rendering uncoloured.
9. **The information architecture leaks implementation.** There are 12 flat nav items with overlapping names (Interpret, Explain, Trends; Alerts means settings). Settings is a
   5,565px scroll that mixes patient settings with Tesseract, GPU and DPO/GRPO diagnostics. Raw identifiers show in the UI (`lab_csv`, `hba1c`,
   `hdl_cholesterol`). There is no skip link, and each page has two h1s.
10. **The visual system is clean but undifferentiated.** Every page is the same card template. The trend chart, which is the product's core, has no hero
    treatment, smooths values between draws (`type="monotone"`), and draws the reference range as a single dashed line rather than a band.
    Native controls are unstyled (blue checkboxes on Export, browser date pickers). Dark mode tokens exist but are dead. This is the
    "doesn't feel like a modern SaaS" gap, and it is safe to address only after 1–9.

## 9. What is already good (keep it)

- The copy voice in Settings, Danger Zone, Data donation, Care Tasks and Recovery describes mechanisms instead of offering reassurance. Several products could learn from it.
- The recovery-code acknowledgement gate.
- The upload result card, with "Preview / Review values" and the duplicate-upload warning.
- Near-zero layout shift; 44px minimum button targets; visible focus rings once they settle.
- Fully local fonts and assets, and no telemetry in the bundle.
- The sidebar `layoutId` pill is the right kind of motion: small, spatial and meaningful.
