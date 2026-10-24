# Asclexis frontend: component, motion and token audit

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

Scope: `src/frontend/src/components/**`, `src/frontend/src/pages/**`, `src/App.tsx`, `src/styles/globals.css`, `src/hooks/useReducedMotion.ts`.
Snapshot: branch `main`, HEAD `7749744`. Read-only audit; nothing in the repo was modified. All paths below are relative to `src/frontend/` unless absolute.

Stack as installed (`package.json`): React 18.2, Tailwind 4.3 via `@tailwindcss/postcss`, framer-motion 10.18, `@radix-ui/react-dropdown-menu` + `react-slot`, lucide-react 0.303, recharts 3.9, class-variance-authority, tailwind-merge.

## 0. Scoring rule used (so the numbers are reproducible)

Motion/interaction scale from the brief, applied with one operational rule so that "2" is not handed out for a single ring class:

- 0 = no hover, transition, focus, loading or enter/exit styling of its own (browser default plus the global `*:focus-visible` rule at `src/styles/globals.css:288`, which applies to everything and is therefore not counted per component).
- 1 = exactly one layer: hover-only / `transition-colors` only, or `focus:` ring only, or one bare loading indicator, or "inherits the shared `Button` states and adds nothing".
- 2 = two or more distinct layers among {enter/exit animation, press state (`active:`), `focus-visible` ring, skeleton/pulse/spinner loading state, multi-state transition such as hover+disabled+error}, but with a gap (no exit, no reduced-motion handling, no keyboard path, etc.).
- 3 = enter/exit or equivalent deliberate motion AND reduced-motion handling AND hover/focus/disabled/active coverage, with no obvious missing state.

Layers counted are those in the file itself. Layers inherited from `Button`/`Card`/`Badge` are noted but only counted when the file adds nothing else (score 1).

The "Upgrade candidate" column is intentionally blank, per the brief.

## 1. Component table

Route key (from `src/App.tsx:105-135`): `/setup` ProfileSetup (eager); `/recover` RecoverProfile (lazy); `/inbox` DocumentInbox (eager); `/verify` VerificationWorkbench (eager); `/trends` TrendsDashboard (lazy); `/timeline` TimelinePage (lazy); `/search` SearchPage (lazy); `/interpret` LabInterpreter (lazy); `/medications` MedicationCoach (lazy); `/medications/:medicationId` MedicationDetail (lazy); `/notifications` NotificationSettings (lazy); `/care-tasks` CareTasksPage (lazy); `/pinboards` PinboardsPage (lazy); `/explain` ExplainAssistant (lazy); `/export` ExportPage (lazy); `/settings` SettingsPage (eager). Everything except `/setup` and `/recover` is inside `ProtectedRoute` > `AppLayout`.

"Imports" in the Used-where column were verified by JSX-usage grep (`<Name`), not by name matching.

### 1a. `components/ui` (design-system primitives)

| Component | File path | What it does | Used where | Pattern class | Motion 0-3 | Evidence for score | Upgrade candidate |
|---|---|---|---|---|---|---|---|
| Button (+ `buttonVariants`) | `src/components/ui/Button.tsx` | cva button: 4 variants x 4 sizes, `asChild` via Radix Slot | Imported by ~30 files (nearly every page, all of `settings/*` except two cards, most of `medication-coach/*`, `TopBar`, `EntityDetailView`, `MemoryManager`, `AddToPinboardButton`); `asChild` used in the DocumentInbox error card | button | 3 | `transition-all duration-200 ease-in-out`; `focus-visible:ring-2 ring-accent ring-offset-2`; `disabled:pointer-events-none disabled:opacity-50`; `active:scale-[0.98]` (line 12); primary/secondary/danger add `hover:-translate-y-0.5 hover:shadow-card` + `active:translate-y-0`; ghost is `hover:bg-black/4` only. No built-in loading state (69 inline `Loader2` uses across components/pages). Reduced motion only via the global CSS rule (hover lift becomes an instant jump, still happens). | |
| Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter | `src/components/ui/Card.tsx` | Single glass card (`bg-white/80 backdrop-blur-xl`, `border-black/4`, `shadow-card`) plus layout slots; no variants | Imported by ~35 files (all pages with cards, `settings/*`, `medication-coach/*`, `PageImageOverlay`, `MemoryManager`, `EntityDetailView`, `EmptyState`) | card | 1 | `transition-all duration-300 ease-in-out hover:shadow-elevated hover:border-black/6` applies to every Card, including non-interactive ones. No focus, press, or reduced-motion handling. | |
| Badge (+ `badgeVariants`) | `src/components/ui/Badge.tsx` | Pill badge, 6 variants (default, accent, caution, attention, verified, info) | ~27 files incl. `ExtractionConfidenceBadge`, `HighlightChips`, `MedicationCard`, `TierCapabilities`, most pages | badge | 1 | `transition-colors duration-200` declared on base but there is no hover/state variant to transition. Static. | |
| Input | `src/components/ui/Input.tsx` | Text input with optional label/error/hint, `aria-invalid`, `aria-describedby`, `role="alert"` on error | `MedicationForm`, `ProfileSetup`, `NotificationSettings`, `PinboardsPage`, `SearchPage`, `TimelinePage` | input | 2 | `h-11` (44px); `transition-colors duration-200`; `focus:ring-2 focus:ring-accent/20 focus:border-accent` (focus:, not focus-visible); error variant swaps border/ring to `status-critical`; `disabled:opacity-50 disabled:bg-surface-muted`. No reduced-motion handling beyond global CSS. Select, textarea, checkbox have no primitive. | |
| EmptyState | `src/components/ui/EmptyState.tsx` | Icon + title + description + optional action inside a Card | `CareTasksPage`, `MedicationCoach`, `PinboardsPage`, `NotificationSettings`, `SearchPage`, `TimelinePage` | empty-state | 0 | Static markup. Inherits Card hover shadow only. | |
| Motion primitives (`fadeVariants`, `slideUpVariants`, `staggerContainerVariants`, `PageTransition`, `StaggerGroup`, `StaggerItem`, `modalVariants`, `backdropVariants`) | `src/components/ui/Motion.tsx` | Shared framer-motion variants and 3 wrapper components (see section 2) | `PageTransition`: `AppLayout`. `StaggerGroup/Item`: `AchievementsWidget`, `MedicationCoach`, `NotificationSettings`, `SettingsPage`. `modalVariants/backdropVariants`: `DoseLoggingModal`, `SettingsPage` (x3 dialogs) | layout / list (motion helper) | 3 | `PageTransition` (line 29-46) and `StaggerItem` (line 67-79) switch `slideUpVariants` to `fadeVariants` when `useReducedMotion()` is true; 0.3s easeOut. Caveats: `StaggerGroup` (line 52) has no reduced-motion branch (0.05s stagger kept); `modalVariants` exports no reduced variant, callers must choose (DoseLoggingModal:89 and SettingsPage:1074 do, SettingsPage:899 and :977 do not). | |
| Skeleton, CardSkeleton, ListSkeleton | `src/components/ui/Skeleton.tsx` | `animate-pulse` placeholder blocks (text, circular, rectangular) | `Skeleton`: `App.tsx` RouteFallback, `NotificationSettings` (~20 uses), `SettingsPage` (~15). `ListSkeleton`: `CareTasksPage`, `MedicationCoach`. `CardSkeleton`: unused (no importer) | loader/skeleton | 2 | `animate-pulse bg-black/5 dark:bg-white/5` (line 13). No `role`/`aria-busy` on the components themselves (callers add `role="status"` + `sr-only` text, e.g. App.tsx:82-92). `animate-shimmer` keyframe exists in the theme but Skeleton does not use it. Reduced motion only via global CSS (pulse becomes one 0.01ms iteration). | |
| Barrel `ui/index.ts` | `src/components/ui/index.ts` | Re-exports | n/a | n/a | n/a | Pure barrel, skipped per brief. | |

### 1b. `components/layout`, `components/auth`

| Component | File path | What it does | Used where | Pattern class | Motion 0-3 | Evidence for score | Upgrade candidate |
|---|---|---|---|---|---|---|---|
| AppLayout | `src/components/layout/AppLayout.tsx` | App shell: fixed Sidebar, sticky TopBar, `<main>` with route-keyed page transition | `App.tsx:114` (layout route for all protected pages) | layout | 3 | `AnimatePresence mode="wait"` (line 19) wrapping `PageTransition key={location.pathname}`: enter slide-up/exit, reduced-motion falls back to fade (via Motion.tsx). Shell has `pl-64` and no responsive breakpoints (no `md:`/`lg:` in layout files). | |
| Sidebar | `src/components/layout/Sidebar.tsx` | 12-item nav with shared active pill | `AppLayout` | nav | 3 | `motion.div layoutId` spring pill (line 75-79) with `layoutId={prefersReducedMotion ? undefined : ...}`; `transition-colors duration-200`; `focus-visible:ring-2 ring-accent ring-offset-2`; `min-h-target`. Gap: pill renders only on exact path match (`isActive`, line 58) while the text colour uses NavLink's prefix match, so `/medications/:id` shows accent text with no pill. `fixed w-64`, no collapse. | |
| TopBar | `src/components/layout/TopBar.tsx` | Search form, "Safety Mode" toggle button, profile button | `AppLayout` | nav / form | 2 | Search icon `group-focus-within:text-accent transition-colors`; input `transition-all duration-200 focus:ring-2` (focus:, h-10 = 40px, below 44px target); toggle is a `Button` with `aria-pressed` and a colour swap, no motion on state change. Safe-mode state is local `useState(true)` only (line 11). | |
| ProtectedRoute | `src/components/auth/ProtectedRoute.tsx` | Redirects to `/setup` when unauthenticated or token expired | `App.tsx:113` | layout (guard) | 0 | Renders `<Navigate>` or `<Outlet>`; no UI. | |
| Barrels (`auth/index.ts`, `layout/index.ts`) | n/a | Re-exports | n/a | n/a | n/a | Skipped per brief. | |

### 1c. `components/` top level, `documents/`, `lab-interpreter/`

| Component | File path | What it does | Used where | Pattern class | Motion 0-3 | Evidence for score | Upgrade candidate |
|---|---|---|---|---|---|---|---|
| MedicationOverlay | `src/components/MedicationOverlay.tsx` | Pill links for medications active in a time window | `TrendsDashboard:548` | list / badge | 1 | `hover:bg-accent/10 transition-colors focus:outline-hidden focus:ring-2 focus:ring-accent` (line 34). Plain `<a href>` (full page load, not router `Link`). | |
| MemoryManager | `src/components/MemoryManager.tsx` | CRUD UI for assistant memory items (filter chips, add/edit form, delete confirm) | `SettingsPage` | list / form | 1 | `transition-colors` on filter chips; raw `<input>`/`<textarea>`/`<select>` with `focus:ring-2 focus:ring-accent` (not the `Input` primitive); `Loader2 animate-spin`; add/edit form and delete-confirm swap in with no animation. Filter chips are plain buttons with no `aria-pressed`. | |
| PageImageOverlay | `src/components/PageImageOverlay.tsx` | Fetches a PDF page image blob and draws a bbox highlight | `DocumentInbox` (preview dialog), `VerificationWorkbench` | modal content / image | 1 | `animate-pulse` placeholder (line 143); image toggles `opacity-0` with no transition class, so it pops in; error state is a static Card. | |
| TrendVerificationMarkers (`TrendPointDot`, `UnverifiedTrendNote`) | `src/components/TrendVerificationMarkers.tsx` | Recharts dot (hollow dashed for unverified) and count note | `InterpretedTrendChart`, `TrendsDashboard` | chart | 0 | Static SVG; state conveyed by shape (dashed stroke, `<title>`, `aria-label`), not colour. Hard-coded `#2D7D6F` / `#FFFFFF` (lines 25, 38). | |
| CategoryBadge | `src/components/documents/CategoryBadge.tsx` | Coloured document-category pill | None: no importer (DocumentInbox.tsx:36 only mentions it in a comment) | badge | 0 | Static; uses raw Tailwind palette (`bg-blue-50 text-blue-700`, purple, green, amber, gray) instead of tokens (lines 8-12). | |
| EntityDetailView | `src/components/documents/EntityDetailView.tsx` | Table of extracted entities with confidence badge, quote, highlight chips, verify/reject buttons | `VerificationWorkbench` | table | 1 | No own transitions; row highlight `bg-accent/10` is static; verify/reject are ghost icon `Button`s (inherit hover/focus/disabled). `<table>` with no hover/zebra. | |
| ExtractionConfidenceBadge | `src/components/documents/ExtractionConfidenceBadge.tsx` | Maps confidence to a Badge variant and label | `DocumentInbox`, `VerificationWorkbench`, `EntityDetailView` | badge | 0 | Thin wrapper; no own styles. | |
| HighlightChips | `src/components/documents/HighlightChips.tsx` | Ordered neutral badges for highlight tags with "+N" overflow | `DocumentInbox`, `EntityDetailView` | badge / list | 0 | Static. | |
| AdviceSection | `src/components/lab-interpreter/AdviceSection.tsx` | "Recommendations" paragraphs from advice text | `InterpretedResultCard`, `PanelInterpretationDashboard` | list (text) | 0 | Static. | |
| CitationTooltip | `src/components/lab-interpreter/CitationTooltip.tsx` | Numbered citation button with hover/focus popover | `InterpretedResultCard`, `PanelInterpretationDashboard` | tooltip | 2 | Opens on `onMouseEnter/onFocus`, closes on leave/blur (lines 18-21); `hover:bg-accent/20 transition-colors`; `focus-visible:ring-2`. The popover's `animate-in fade-in-0 zoom-in-95` classes (line 40) belong to tailwindcss-animate / tw-animate-css, which is not installed and not in globals.css, so the popover appears with no animation. No Escape-to-dismiss, no `aria-describedby` link. 20x20px target (`w-5 h-5`). | |
| DisclaimerBanner | `src/components/lab-interpreter/DisclaimerBanner.tsx` | Caution banner "not medical advice" with `role="alert"` | `InterpretedResultCard`, `PanelInterpretationDashboard` | banner | 0 | Static. | |
| InterpretedResultCard | `src/components/lab-interpreter/InterpretedResultCard.tsx` | Per-analyte interpretation card: severity badges, ref-range bar, text, citations, collapsible advice, regenerate | `LabInterpreter` | card | 2 | `motion.div` fade+y8 enter with `initial={prefersReducedMotion ? {} : ...}` (line 67); advice toggle `hover:text-accent-hover transition-colors focus-visible:ring-2`; regenerate shows `Loader2 animate-spin`. Gap: advice expand/collapse is an instant mount/unmount, toggle has no `aria-expanded`. | |
| InterpretedTrendChart | `src/components/lab-interpreter/InterpretedTrendChart.tsx` | Recharts line chart with reference band and unverified markers | `LabInterpreter` | chart | 2 | `animationDuration={prefersReducedMotion ? 0 : 800}` (line 178); loading Card with `Loader2 animate-spin`; recharts default tooltip styled inline with `rgba(0,0,0,0.08)` border. 9 hard-coded hex values (`#2D7D6F`, `#7BA387`, `#6B6B6B`). No hover styling on chart container. | |
| PanelInterpretationDashboard | `src/components/lab-interpreter/PanelInterpretationDashboard.tsx` | Panel-level summary, relationship insights, advice | `LabInterpreter` | card | 2 | Card `motion.div` fade+y8; each insight `motion.div` x-4 fade with `delay: i * 0.05` (line 134-136), both guarded by `prefersReducedMotion ? {} : ...`; loading is a spinner Card, error is a static Card. No hover/focus (nothing interactive except CitationTooltip). | |
| ReferenceRangeComparison | `src/components/lab-interpreter/ReferenceRangeComparison.tsx` | Horizontal ref-range track with value marker | `InterpretedResultCard` | chart (custom) | 0 | Static inline-style positioning (`left: x%`), no `transition` on the marker, so value changes jump. | |
| formatInterpretationText | `src/components/lab-interpreter/formatInterpretationText.ts` | helper: strips `[KB:...]`/`[INT:...]` markers, splits paragraphs and `**bold**` runs | `AdviceSection`, `InterpretedResultCard`, `LabInterpreter` | helper | 0 | Pure function, no UI (n/a). | |
| Barrel `lab-interpreter/index.ts` | n/a | Re-exports | n/a | n/a | n/a | Skipped. | |

### 1d. `components/medication-coach`

| Component | File path | What it does | Used where | Pattern class | Motion 0-3 | Evidence for score | Upgrade candidate |
|---|---|---|---|---|---|---|---|
| MedicationCard | `src/components/medication-coach/MedicationCard.tsx` | Clickable medication row with next dose, badges, quick-log button | `MedicationCoach` (wrapped in `StaggerItem`) | card / list | 2 | `motion.div` fade+y8 with `delay: index * 0.05` (line 45-49), reduced-motion guarded; `hover:shadow-elevated transition-shadow duration-200 cursor-pointer`. Gaps: the card is a `div onClick` (line 55) with no role/tabIndex/keyboard handler; it is animated twice (outer `StaggerItem` variants plus own `initial/animate`). | |
| MedicationForm | `src/components/medication-coach/MedicationForm.tsx` | Add/edit medication form (Input, 3 native selects, textarea, checkbox) | `MedicationCoach` (add and edit) | form | 2 | Selects/textarea each repeat `focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2` (4 occurrences) at `h-[44px]`; `Input` primitive for text; submit shows `Loader2 animate-spin`; form mount/unmount is instant. Checkbox uses `focus:ring-accent` only. | |
| DoseLoggingModal | `src/components/medication-coach/DoseLoggingModal.tsx` | Modal to log a dose as taken/skipped with reason chips and notes | `MedicationCoach:368`, `MedicationDetail:430` | modal | 2 | Backdrop and panel `motion.div` with `backdropVariants`/`modalVariants`, reduced-motion swaps to fade (line 89); skip-reason panel animates height via `AnimatePresence` (line 144); toggle and chips `transition-all` + `focus:ring-2`. Gaps: parents mount it with `{loggingMed && (...)}` and no enclosing `AnimatePresence`, so the exit variants never play; no `role="dialog"`/`aria-modal`; no Escape handler, no focus trap, no initial focus; only the backdrop `onClick` closes it. | |
| BadgeToast | `src/components/medication-coach/BadgeToast.tsx` | Fixed top-right achievement toast with auto-dismiss | `MedicationCoach:365` | toast | 3 | `AnimatePresence` + spring enter/exit (line 37-43), separate reduced-motion initial/exit; `role="status" aria-live="polite"`; 5s auto-dismiss via `setTimeout` (line 31); dismiss button `hover:bg-black/4 transition-colors` and `aria-label`. Minor: `animate-ping` decoration is unguarded in JS (global CSS rule limits it to one 0.01ms iteration); dismiss button is `h-8 w-8` raw `<button>` (32px); no pause-on-hover; the only toast in the app. | |
| AchievementsWidget (+ inline `BadgeCard`) | `src/components/medication-coach/AchievementsWidget.tsx` | Badge grid with streak summary | `MedicationCoach` | card / list | 2 | Grid uses `StaggerGroup/StaggerItem` (reduced-motion aware via Motion.tsx); earned badge `hover:shadow-md hover:-translate-y-0.5 transition-all duration-300` (lines 33-35). Not focusable, hover lift on a non-interactive element. | |
| AdherenceDashboard (+ inline `AdherenceRing`) | `src/components/medication-coach/AdherenceDashboard.tsx` | 7/30-day adherence rings, streaks, totals | `MedicationDetail` | chart / card | 1 | Ring stroke has `transition-all duration-700` but is rendered at its final `strokeDashoffset` on first paint, so there is nothing to animate from; spinner Card for loading. Hard-coded `#7BA387/#D4A574/#C9857A` and `rgba(0,0,0,0.06)`. | |
| ScheduleEditor | `src/components/medication-coach/ScheduleEditor.tsx` | List/add/delete dose schedules | `MedicationDetail` | list / form | 2 | `focus-visible:ring-2` on select/time input (`h-[36px]`, below 44px), `active:` count 1, `hover:text-status-attention` on delete, `Loader2 animate-spin`. Add panel appears instantly; delete has no confirm; `isDeleting` spins every row's icon. Labels have no `htmlFor`. | |
| StreakDisplay | `src/components/medication-coach/StreakDisplay.tsx` | Current/best streak tiles (neutral copy on broken streak) | `AchievementsWidget`, `AdherenceDashboard` | badge / stat | 0 | Static. | |
| VoiceFirstUseModal | `src/components/medication-coach/VoiceFirstUseModal.tsx` | Privacy disclosure modal before microphone use | None: exported from the barrel only, no JSX usage anywhere | modal | 0 | `fixed inset-0 z-70`; no motion, no `role="dialog"`, no Escape, no focus handling. | |
| Barrel `medication-coach/index.ts` | n/a | Re-exports | n/a | n/a | n/a | Skipped. | |

### 1e. `components/pinboards`, `profile`, `settings`

| Component | File path | What it does | Used where | Pattern class | Motion 0-3 | Evidence for score | Upgrade candidate |
|---|---|---|---|---|---|---|---|
| AddToPinboardButton | `src/components/pinboards/AddToPinboardButton.tsx` | Icon button opening a Radix dropdown of pinboards | `DocumentInbox`, `TimelinePage` | dropdown | 2 | Radix `DropdownMenu` provides Escape, arrow-key and focus management; trigger is a ghost icon `Button`; items `hover:bg-surface-muted focus:bg-surface-muted`; spinner while pending. Content has no `data-[state]` enter/exit animation. One of two Radix usages (the other is DocumentInbox). | |
| RecoveryCodeCard (profile) | `src/components/profile/RecoveryCodeCard.tsx` | One-time recovery code display with copy/print and "I have stored this" gate | `ProfileSetup`, `RecoverProfile` | card / form | 1 | Only `Button` states plus "Copied" label swap on a 2s timer (line 38); raw checkbox, no styling. | |
| AgentSettingsCard | `src/components/settings/AgentSettingsCard.tsx` | `role="switch"` toggle for the step-by-step assistant | `SettingsPage` | form (switch) | 2 | `transition-all duration-300` on row, `transition-colors duration-300` on track, `transition-transform duration-300` on thumb; `aria-checked`, `aria-describedby`, `disabled` while saving; error `role="alert"`. No explicit focus style (global ring only). | |
| BackupCard | `src/components/settings/BackupCard.tsx` | Create/list/download/restore backups with password + typed-phrase confirm | `SettingsPage` | card / table / form | 1 | No transitions of its own; `Button` states; `role="status"`/`role="alert"` messages; restore confirm reveals inline instantly. | |
| DangerZone | `src/components/settings/DangerZone.tsx` | Multi-step profile deletion (backup, password, typed phrase) | `SettingsPage` | card / form | 1 | Expand reveal is instant; `Button` states; uses undefined `text-muted-foreground` (lines 90, 107). | |
| DataDonationCard | `src/components/settings/DataDonationCard.tsx` | Per-purpose consent switches with inline `alertdialog` confirm to stop | `SettingsPage` | card / form (switch) | 2 | Same switch pattern as AgentSettingsCard (300ms transitions, `role="switch"`, `aria-checked`, `disabled`); confirm is `role="alertdialog"` rendered inline, no animation. | |
| ExternalApiBreakGlassWarning | `src/components/settings/ExternalApiBreakGlassWarning.tsx` | Warning/notice banner when redaction break-glass is active or unknown | `SettingsPage`, `LabInterpreter`, `ExplainAssistant` | banner | 0 | Static; `role="alert"` or `role="status"`. | |
| RecoveryCodeCard (settings) | `src/components/settings/RecoveryCodeCard.tsx` | Issue/replace recovery code after password confirm | `SettingsPage` | card / form | 1 | `Button` states only; raw `<input className="rounded-md border px-3 py-2 text-sm">` with no focus classes (global ring only). | |
| TierCapabilities | `src/components/settings/TierCapabilities.tsx` | Capability badges for a model tier | `SettingsPage` | badge | 0 | Static; arbitrary `text-[10px]` on badges. | |

### 1f. `pages/` (route-level)

| Component | File path | What it does | Used where | Pattern class | Motion 0-3 | Evidence for score | Upgrade candidate |
|---|---|---|---|---|---|---|---|
| ProfileSetup | `src/pages/ProfileSetup.tsx` | First-run profile creation, password validation, step progress, recovery code handoff | Route `/setup` (eager) | page / form | 2 | Stagger `containerVariants/itemVariants` (lines 172-184) with `staggerChildren: prefersReducedMotion ? 0 : 0.1` but `itemVariants.hidden` keeps `y` offset under reduced motion; step list `transition-opacity duration-300`, active step `animate-pulse`; blurred accent backdrop blobs; `Input` error states. | |
| RecoverProfile | `src/pages/RecoverProfile.tsx` | Recovery-code password reset form | Route `/recover` (lazy) | page / form | 0 | No motion; raw `<select>`/`<input className="w-full rounded-md border px-3 py-2 text-sm">` with no component-level focus styling; `role="alert"` error. | |
| DocumentInbox | `src/pages/DocumentInbox.tsx` | Import (click/drag-drop), document list with row actions, preview dialog | Route `/inbox` (eager) | page / list | 2 | Drop zone `transition-all duration-200` with `isDragging` state and `hover:border-accent/50`; list uses `motion.div` stagger (lines 130-143) with stagger zeroed under reduced motion (y offset kept); row `hover:bg-surface-muted/50 transition-colors`; row actions hidden until hover/focus-within (`sm:[@media(hover:hover)]:opacity-0 sm:group-hover:opacity-100 focus-within:opacity-100`); Radix menu; `window.confirm` for delete; spinners and `animate-pulse` on import. | |
| VerificationWorkbench | `src/pages/VerificationWorkbench.tsx` | Review/correct extracted observations, edit modal, source preview | Route `/verify` (eager) | page / table | 2 | Table rows `motion.tr` fade+y8 `delay: index * 0.05` (lines 590-595) reduced-guarded; expand chevron `rotate-180`; spinners; hover/focus classes ~2 each; fixed `grid grid-cols-3` layout. | |
| TrendsDashboard | `src/pages/TrendsDashboard.tsx` | Panel tabs, recharts line chart, analyte summary list, medication overlay | Route `/trends` (lazy) | page / chart | 2 | `animationDuration={prefersReducedMotion ? 0 : 800}` (line 507); analyte list `motion.button` x-8 fade, `delay: index * 0.05` (564-568), guarded; spinner. "Last 12 Months" and "Filters" buttons (lines 310, 314) have no `onClick`. 7 hard-coded hex values. | |
| TimelinePage | `src/pages/TimelinePage.tsx` | Chronological event list with filters | Route `/timeline` (lazy) | page / list | 2 | Spinner with `role="status"` + `sr-only`; `focus-visible:ring-2` on the native select; `hover:underline` links; no entrance motion; own `p-8 max-w-4xl` wrapper on top of AppLayout's `p-8`. | |
| SearchPage | `src/pages/SearchPage.tsx` | Search with filters and result cards | Route `/search` (lazy), also reached from TopBar search form | page / list | 2 | Spinner `role="status"`; selects `focus-visible:ring-2 ring-accent`; `Input` primitive; four `EmptyState` variants (error, idle, no results); own `p-8` wrapper. | |
| LabInterpreter | `src/pages/LabInterpreter.tsx` | Panel tabs, analyte list, per-analyte interpretation and panel summary | Route `/interpret` (lazy) | page | 2 | Analyte list `motion.button` x-8 fade `delay: index * 0.03` (324-328), guarded; spinners; `grid grid-cols-3` fixed layout. | |
| MedicationCoach | `src/pages/MedicationCoach.tsx` | Medication list, add/edit form, reconcile panel, achievements, dose modal, badge toast | Route `/medications` (lazy) | page / list | 2 | Loading uses raw `animate-pulse` divs plus `ListSkeleton` (lines 256-259); list in `StaggerGroup/StaggerItem` (339-350); modal mounted conditionally (368) with no AnimatePresence. | |
| MedicationDetail | `src/pages/MedicationDetail.tsx` | Single medication: info, dose history, schedules, adherence, edit/delete | Route `/medications/:medicationId` (lazy) | page | 2 | Dose history `motion.div` fade `delay: i * 0.03` (293-297), guarded; spinners; `DoseLoggingModal` mounted at 430 without AnimatePresence. | |
| NotificationSettings | `src/pages/NotificationSettings.tsx` | Per-medication reminder settings and reminder history table with paging | Route `/notifications` (lazy) | page / form / table | 2 | ~20 `Skeleton` placeholders for loading; `StaggerGroup/StaggerItem` columns (271, 272, 565); `<label ... hover:bg-surface-muted transition-colors>` checkbox rows (no switch primitive); table rows `hover:bg-black/1 transition-colors`; success text `animate-fade-in` (449); paging via Previous/Next `Button`s with `h-8`. | |
| CareTasksPage | `src/pages/CareTasksPage.tsx` | Care-task checklist grouped by status, plus suggestions from a chosen document | Route `/care-tasks` (lazy) | page / list | 2 | Loading uses raw `animate-pulse` divs (lines 198-199) plus `ListSkeleton`; select `focus-visible:ring-2`; no entrance motion; cards have no hover. | |
| PinboardsPage | `src/pages/PinboardsPage.tsx` | Pinboard list/detail, rename, delete, packet export | Route `/pinboards` (lazy) | page / list | 1 | Board list buttons have `hover:bg-surface-muted` with no `transition` class (line 116); spinner only for loading; rename/delete use `window.prompt`/`window.confirm` (no modal). | |
| ExplainAssistant | `src/pages/ExplainAssistant.tsx` | Chat UI with citations, feedback, session restore, filters sidebar | Route `/explain` (lazy) | page / chat | 2 | `AnimatePresence mode="popLayout"` messages (522) with reduced-guarded enter; typing indicator `animate-bounce` dots; `scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' })` (307), the only JS scroll guard in the repo; chips `transition-colors`; input `focus:ring-2`; uses undefined `status-danger` tokens (540, 554, 683). 991 lines, 8 raw `<button>`s. | |
| ExportPage | `src/pages/ExportPage.tsx` | CSV/JSON/FHIR export, generated summary with section toggles | Route `/export` (lazy) | page / form | 2 | Summary `motion.div` fade (344) guarded; many spinners (9 `animate-` hits); section buttons `aria-pressed` + `transition-colors`; "Full Preview" button (line ~327) has no `onClick`. | |
| SettingsPage | `src/pages/SettingsPage.tsx` | Settings hub: timezone, voice, streaks, OCR, diagnostics, hardware, model tiers, external API, RL data, memory, recovery, backup, donation, danger zone | Route `/settings` (eager) | page | 2 | 5 `AnimatePresence` blocks (635, 768, 888, 961, 1058); 3 dialogs (see inline rows); `StaggerGroup` columns (220-221, 684); `Skeleton` loading (182-193); `animate-shimmer` indeterminate bar (660); reduced-motion guard present on diag and consent dialogs only. 1144 lines, 11 arbitrary `[..px]` values. | |

### 1g. `App.tsx` and inline sub-components

| Component | File path | What it does | Used where | Pattern class | Motion 0-3 | Evidence for score | Upgrade candidate |
|---|---|---|---|---|---|---|---|
| RouteFallback | `src/App.tsx:80-95` | Suspense fallback for lazy routes: skeleton header + 3 cards | `lazyRoute()` (App.tsx:97-99) wrapping 12 lazy routes | loader/skeleton | 2 | `animate-fade-in` (CSS keyframe, 0.3s) + `Skeleton` pulse; `role="status" aria-live="polite"` + `sr-only` "Loading page..."; not reduced-motion guarded in JS (global CSS covers it). Eager routes (`/inbox`, `/verify`, `/settings`, `/setup`) have no fallback. No ErrorBoundary/`errorElement` anywhere. | |
| BadgeCard (inline in AchievementsWidget) | `src/components/medication-coach/AchievementsWidget.tsx:29` | One achievement tile (earned vs locked) | `AchievementsWidget` | badge / card | 1 | Hover lift only on earned (`hover:-translate-y-0.5`, `transition-all duration-300`); locked tile `opacity-40 grayscale`. | |
| AdherenceRing (inline in AdherenceDashboard) | `src/components/medication-coach/AdherenceDashboard.tsx:15` | SVG progress ring | `AdherenceDashboard` | chart | 1 | See AdherenceDashboard row; percentage label positioned with `-mt-[calc(50%+16px)]`. | |
| SourceQuote (inline in CareTasksPage) | `src/pages/CareTasksPage.tsx:53` | "The note says" quote line | `CandidateCard`, `TaskCard` | text | 0 | Static. | |
| CandidateCard (inline in CareTasksPage) | `src/pages/CareTasksPage.tsx:63` | Suggested care task with "Add to checklist" | CareTasksPage | card / list | 1 | Static bordered row; only the `Button` states. | |
| TaskCard (inline in CareTasksPage) | `src/pages/CareTasksPage.tsx:102` | Checklist row with Done/Ignore/Reopen | CareTasksPage | card / list | 1 | Closed tasks `line-through` (instant); only `Button` states; status change has no transition. | |
| SuggestionCard (inline in MedicationCoach) | `src/pages/MedicationCoach.tsx:52` | Reconciliation suggestion row | `MedReconcilePanel` | card / list | 1 | Static bordered row; `Button` states only. | |
| MedReconcilePanel (inline in MedicationCoach) | `src/pages/MedicationCoach.tsx:110` | Compare a document's medication lines with the list | MedicationCoach | card / form | 2 | Native select `focus-visible:ring-2`; `ListSkeleton` while loading. | |
| ResultCard (inline in SearchPage) | `src/pages/SearchPage.tsx:38` | Search hit card with badges and link | SearchPage | card / list | 1 | `hover:underline` link only; inherits Card hover shadow. | |
| EventCard (inline in TimelinePage) | `src/pages/TimelinePage.tsx:73` | Timeline event card with pin button | TimelinePage | card / list | 1 | `hover:underline` links; embeds `AddToPinboardButton`. | |
| Document preview dialog (inline in DocumentInbox) | `src/pages/DocumentInbox.tsx:460-486` | Fullscreen overlay with `PageImageOverlay` | DocumentInbox (`previewDocId`) | modal | 1 | `role="dialog" aria-modal="true" aria-labelledby`; backdrop click closes, panel stops propagation; no enter/exit animation, no Escape, no focus move or trap. | |
| Edit Value modal (inline in VerificationWorkbench) | `src/pages/VerificationWorkbench.tsx:776-833` | Edit an observation value and verify | VerificationWorkbench | modal | 1 | `role="dialog" aria-modal="true"` with no label; `autoFocus` on the input (the only autofocus in the repo); backdrop does not close; no animation, no Escape; close icon button has no `aria-label`. | |
| Export confirmation dialog (inline in SettingsPage) | `src/pages/SettingsPage.tsx:887-937` | Confirm RL training-data export | SettingsPage | modal | 2 | `AnimatePresence` + `backdropVariants`/`modalVariants` (893, 899) unguarded for reduced motion; no `role="dialog"`; no Escape or focus handling. | |
| Diagnostics fix dialog (inline in SettingsPage) | `src/pages/SettingsPage.tsx:960-1055` | Fix-action steps for a failing diagnostic | SettingsPage | modal | 2 | `AnimatePresence`; `transition={{ type: prefersReducedMotion ? 'tween' : 'spring', duration: prefersReducedMotion ? 0.15 : undefined }}` (line ~979); `role="dialog" aria-labelledby` but no `aria-modal`; no Escape or trap. | |
| Consent dialog (inline in SettingsPage) | `src/pages/SettingsPage.tsx:1057-1141` | Privacy notice before enabling external API | SettingsPage | modal | 2 | `AnimatePresence`; `variants={prefersReducedMotion ? backdropVariants : modalVariants}` (1074); no `role="dialog"`, no Escape or trap. | |
| Streaks switch (inline in SettingsPage) | `src/pages/SettingsPage.tsx:303-330` | `role="switch"` for streak visibility | SettingsPage | form (switch) | 2 | Third copy of the switch pattern (also AgentSettingsCard, DataDonationCard): 300ms track/thumb transitions, `aria-checked`; no `disabled` while saving. | |
| Model download progress (inline in SettingsPage) | `src/pages/SettingsPage.tsx:634-678` | Progress panels for model downloads | SettingsPage | loader / progress | 2 | `AnimatePresence` height 0 to auto and fade; determinate bar `motion.div` width tween 0.5s; indeterminate bar uses `animate-shimmer` (660); no `role="progressbar"`; not guarded in JS. | |
| Panel tablist (inline in TrendsDashboard) | `src/pages/TrendsDashboard.tsx:319-345` | Lab panel switcher | TrendsDashboard | tabs | 1 | `role="tablist"`/`role="tab"`/`aria-selected`; `transition-all duration-200`; `focus:ring-2`. No arrow-key roving, no `tabpanel`, no `tabIndex` management. | |
| Panel tabs (inline in LabInterpreter) | `src/pages/LabInterpreter.tsx:203-225` | Lab panel switcher | LabInterpreter | tabs | 1 | Same classes as Trends tabs but plain buttons with no tab roles/aria. | |
| Typing indicator (inline in ExplainAssistant) | `src/pages/ExplainAssistant.tsx:757-777` | Three bouncing dots while a reply loads | ExplainAssistant | loader | 2 | `motion.div` opacity fade-in; `animate-bounce` dots with inline `animationDelay` 0/150/300ms; no `role="status"`. | |
| Message bubbles (inline in ExplainAssistant) | `src/pages/ExplainAssistant.tsx:522-755` | User/assistant message bubbles with citations, feedback thumbs | ExplainAssistant | list | 2 | `motion.div` enter `{opacity:0,y:12}` guarded; `exit={{opacity:0}}`; feedback buttons `hover:text-status-success`/`hover:text-status-danger` (tokens undefined); thumbs use `title` attributes for tooltips. | |
| Section toggle buttons (inline in ExportPage) | `src/pages/ExportPage.tsx:~680-710` | Include/exclude summary sections | ExportPage | form (toggle) | 1 | `aria-pressed` + `transition-colors duration-200`; no focus-visible class. | |

### 1h. Distribution summary (computed from the tables above)

Counts and distribution are in section 5.

## 2. Motion primitives

### 2a. `src/components/ui/Motion.tsx` exports

- Variants (all `framer-motion` `Variants`): `fadeVariants` (opacity), `slideUpVariants` (opacity + y 12), `staggerContainerVariants` (`staggerChildren: 0.05`), `modalVariants` (opacity + scale 0.95), `backdropVariants` (opacity).
- Components: `PageTransition` (line ~29; div with `initial="initial" animate="animate" exit="exit"`, 0.3s `easeOut`, switches to `fadeVariants` when reduced), `StaggerGroup` (container, no reduced branch), `StaggerItem` (switches to `fadeVariants` when reduced).
- Re-exported through `ui/index.ts` (`export * from './Motion'`).
- Reduced motion: `useReducedMotion` from `@/hooks/useReducedMotion` is imported at line 2 and called at lines 32 and 70. There is no `MotionConfig` (grep: 0 hits in `src/`), no `LazyMotion`, no `m.` components, no shared easing/spring token file.
- The hook (`src/hooks/useReducedMotion.ts`) is custom: `useState(false)` on line 4, then reads `matchMedia('(prefers-reduced-motion: reduce)')` in `useEffect` (line 7) and listens for changes. Consequence: the first render always assumes motion is allowed.
- Adoption: `PageTransition` has 1 consumer (`AppLayout`); `Stagger*` has 4 consumers (AchievementsWidget, MedicationCoach, NotificationSettings, SettingsPage); `modalVariants/backdropVariants` have 2 (DoseLoggingModal, SettingsPage). Four other files define their own variants inline (DocumentInbox:130-141, ProfileSetup:172-184) or inline `initial/animate` props (36 `<motion.*>` elements total outside Motion.tsx).

### 2b. framer-motion imports per file (`from 'framer-motion'`, grep count across `src/`, non-test)

17 files, 1 import each. `AnimatePresence` is used in `AppLayout`, `BadgeToast`, `DoseLoggingModal`, `ExplainAssistant`, `SettingsPage` (5 blocks). `layoutId` is used once (`Sidebar.tsx:77`).

| File | Count |
|---|---|
| src/components/lab-interpreter/InterpretedResultCard.tsx | 1 |
| src/components/lab-interpreter/PanelInterpretationDashboard.tsx | 1 |
| src/components/layout/AppLayout.tsx | 1 |
| src/components/layout/Sidebar.tsx | 1 |
| src/components/medication-coach/BadgeToast.tsx | 1 |
| src/components/medication-coach/DoseLoggingModal.tsx | 1 |
| src/components/medication-coach/MedicationCard.tsx | 1 |
| src/components/ui/Motion.tsx | 1 |
| src/pages/DocumentInbox.tsx | 1 |
| src/pages/ExplainAssistant.tsx | 1 |
| src/pages/ExportPage.tsx | 1 |
| src/pages/LabInterpreter.tsx | 1 |
| src/pages/MedicationDetail.tsx | 1 |
| src/pages/ProfileSetup.tsx | 1 |
| src/pages/SettingsPage.tsx | 1 |
| src/pages/TrendsDashboard.tsx | 1 |
| src/pages/VerificationWorkbench.tsx | 1 |

### 2c. Reduced-motion hooks and queries (grep across `src/`, non-test; test file noted)

`useReducedMotion` call sites (import / call line):

- `src/hooks/useReducedMotion.ts:3` (definition), `:7` (the only JS `prefers-reduced-motion` query)
- `src/components/ui/Motion.tsx:2`, `:32`, `:70`
- `src/components/layout/Sidebar.tsx:19`, `:38`
- `src/components/lab-interpreter/InterpretedTrendChart.tsx:16`, `:35`
- `src/components/lab-interpreter/PanelInterpretationDashboard.tsx:16`, `:42`
- `src/components/lab-interpreter/InterpretedResultCard.tsx:20`, `:61`
- `src/components/medication-coach/BadgeToast.tsx:10`, `:27`
- `src/components/medication-coach/DoseLoggingModal.tsx:7`, `:33` (file shows the call at line ~33)
- `src/components/medication-coach/MedicationCard.tsx:11`, `:40`
- `src/pages/DocumentInbox.tsx:20`, `:40`
- `src/pages/LabInterpreter.tsx:20`, `:46`
- `src/pages/MedicationDetail.tsx:24`, `:58`
- `src/pages/ProfileSetup.tsx:26`, `:79`
- `src/pages/ExportPage.tsx:24`, `:64`
- `src/pages/ExplainAssistant.tsx:27`, `:123`
- `src/pages/VerificationWorkbench.tsx:17`, `:67`
- `src/pages/SettingsPage.tsx:39`, `:123`
- `src/pages/TrendsDashboard.tsx:29`, `:103`

CSS-level: `src/styles/globals.css:257` `@media (prefers-reduced-motion: reduce)` sets `html { scroll-behavior: auto }` and `*, ::before, ::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important }` (lines 257-269). This neutralises CSS transitions/keyframes (including `animate-spin`, `animate-pulse`, `animate-bounce`, `animate-ping`, `animate-shimmer`) but cannot affect framer-motion JS animation, which relies on the hook. Note `animate-spin` is also reduced to one 0.01ms iteration, so loading spinners freeze under reduced motion.

Not present anywhere in `src/`: `motion-safe:` (0), `motion-reduce:` (0), `MotionConfig` (0). A test also references `prefers-reduced-motion`: `src/__tests__/ChartExport.test.tsx`.

Inconsistencies in how the guard is applied:
- Under reduced motion the code usually replaces `initial` with `{}`, so the element just appears; exceptions that keep positional motion: `DocumentInbox.tsx:130-143` and `ProfileSetup.tsx:172-184` zero only the stagger delay, `itemVariants.hidden` still has `y: 12`.
- `SettingsPage.tsx:893-899` (export dialog) and `:968-977` (diag backdrop/variants) use `modalVariants` directly; only `:1074` and the diag `transition` prop (~979) branch on `prefersReducedMotion`.
- `ExplainAssistant.tsx:307` is the only place where a JS API (`scrollIntoView`) honours the preference; `MedicationCoach.tsx:238` (`window.scrollTo({ behavior: 'smooth' })`) does not.
- Recharts animation is guarded in `InterpretedTrendChart.tsx:178` and `TrendsDashboard.tsx:507` (`animationDuration` 0); `AdherenceRing` and `ReferenceRangeComparison` have none.

## 3. Design tokens

### 3a. Where tokens live

- `tailwind.config.*`: does not exist. `ls src/frontend/tailwind.config.*` returns nothing and `find . -name "tailwind.config*"` (excluding `node_modules`) returns nothing. Tailwind v4 is configured entirely in CSS: `src/styles/globals.css` (`@import 'tailwindcss'` line 1, `@theme {}` lines 3-133).
- `docs/brand/brand-guidelines.md` line 5 (Refresh Trigger) and line 121 ("The tokens below are what `src/frontend/tailwind.config.js` actually defines") are stale: that file does not exist. The hex values in the section 6 palette table do match `globals.css:8-40` exactly, so the content is correct but the file reference is wrong. The same doc says "Focus ring: `shadow-focus`" (line 138) but `shadow-focus` is defined (globals.css:66) and used nowhere; focus rings are `ring-accent` / the global `*:focus-visible` rule.
- `postcss.config.js`: only `@tailwindcss/postcss`. No other plugins.
- `index.html`: no fonts or stylesheets; `<body class="bg-surface text-ink antialiased">`; `theme-color` metas `#2D7D6F` (light) and `#1a1a1a` (dark, `media="(prefers-color-scheme: dark)"`) at lines 7-8; `msapplication-TileColor #2D7D6F`.
- `src/main.tsx` lines 4-8: `import './styles/globals.css'` then `@fontsource-variable/fraunces`, `@fontsource-variable/source-sans-3`, `@fontsource/jetbrains-mono`.

### 3b. Colour tokens (`globals.css`)

| Token | Hex | Line |
|---|---|---|
| surface | #fafaf8 | 8 |
| surface-elevated | #ffffff | 9 |
| surface-muted | #f5f5f3 | 10 |
| surface-sunken | #eeedeb | 11 |
| ink | #1f1f1f | 13 |
| ink-secondary | #6b6b6b | 14 |
| ink-tertiary | #9a9a9a | 15 |
| ink-disabled | #bfbfbf | 16 |
| accent | #2d7d6f | 18 |
| accent-subtle | #e8f4f2 | 19 |
| accent-hover | #256b5f | 20 |
| accent-pressed | #1e5a50 | 21 |
| status-caution | #d4a574 | 23 |
| status-caution-subtle | #fdf6ef | 24 |
| status-attention | #c9857a | 25 |
| status-attention-subtle | #fdf2f0 | 26 |
| status-verified | #7ba387 | 27 |
| status-verified-subtle | #f0f7f2 | 28 |
| status-info | #6b8cae | 29 |
| status-info-subtle | #f0f4f8 | 30 |
| status-critical | #c9857a (identical to attention) | 31 |
| status-critical-subtle | #fdf2f0 (identical to attention-subtle) | 32 |
| dark-surface | #1a1a1a | 34 |
| dark-surface-elevated | #242424 | 35 |
| dark-surface-muted | #2e2e2e | 36 |
| dark-ink | #f5f5f5 | 38 |
| dark-ink-secondary | #a0a0a0 | 39 |
| dark-ink-tertiary | #6b6b6b | 40 |

Usage reality (grep of class names in `components`, `pages`, `App.tsx`): `ink-secondary` 273, `ink` 175, `accent` 175, `ink-tertiary` 106, `surface-muted` 98, `status-attention` 45, `accent-subtle` 36, `status-caution` 34, `status-critical` 27, `status-verified` 22. All six `dark-*` tokens and `accent-pressed`, `ink-disabled`: 0 uses.

Undefined tokens used in components (render with no colour, silently): `status-success` (10 uses: `ExplainAssistant.tsx:630,670,671,699`; `SettingsPage.tsx:841,842,860`), `status-danger` / `status-danger-subtle` (9 uses: `ExplainAssistant.tsx:540,554,683,684`; `SettingsPage.tsx:845,846`), `text-muted-foreground` (`DangerZone.tsx:90,107`). None appear in `@theme`.

Base-layer literals (not tokens): default border colour `#e5e7eb` (line 142), placeholder `#9ca3af` (line 152), body radial gradients `rgba(45,125,111,0.03/0.02)` (lines 273-275).

### 3c. Radii, shadows, spacing, type, animation

- Radii (`@theme` 59-61): `--radius-xl: 12px`, `--radius-2xl: 16px`, `--radius-3xl: 24px` (these equal Tailwind v4 defaults, so they are effectively no-ops). Usage counts (components/pages): `rounded-xl` 121, `rounded-lg` 39, `rounded-full` 38, `rounded-2xl` 22, `rounded-sm` 16, `rounded-md` 13.
- Shadows (63-66): `--shadow-soft` `0 2px 8px rgba(0,0,0,.04)`, `--shadow-card` `0 4px 24px rgba(0,0,0,.06)`, `--shadow-elevated` `0 8px 32px rgba(0,0,0,.08)`, `--shadow-focus` `0 0 0 3px rgba(45,125,111,.3)` (unused). Duplicated inside `:root` at lines 244-246. Non-token shadows also used: `shadow-xs` 5, `shadow-lg` 2, `shadow-md`/`xl`/`2xl` 1 each.
- Spacing: no spacing overrides. One custom size: `@utility min-h-target` / `min-w-target` = 44px (lines 216-222), used by `Button.tsx:12` and `Sidebar.tsx` (the only users of the utilities). `--transition-duration-250/350` (lines 75-76) have 0 uses.
- Type: families `--font-display: 'Fraunces Variable', Georgia, serif` (4), `--font-body: 'Source Sans 3 Variable', system-ui, sans-serif` (5), `--font-mono: 'JetBrains Mono', Consolas, monospace` (6); re-declared in `:root` at 239-241. Scale (42-57): xs 0.75rem/1rem, sm 0.875rem/1.25rem, base 1rem/1.6, lg 1.125rem/1.6, xl 1.25rem/1.4, 2xl 1.5rem/1.3, 3xl 1.875rem/1.2, 4xl 2.25rem/1.1. Base layer (278-282): `h1-h4` get `font-family: var(--font-display); font-weight: 500; letter-spacing: -0.02em`; `html` `font-size: 16px`, antialiased (249-255). `font-display` class used 35 times in components/pages.
- Animations / keyframes (68-132): `--animate-fade-in` (fadeIn 0.3s), `--animate-slide-up` (slideUp 0.3s), `--animate-slide-down`, `--animate-scale-in` (0.2s), `--animate-pulse-soft` (2s infinite), `--animate-shimmer` (1.4s infinite). Used in components: `animate-fade-in` x2 (`App.tsx:82`, `NotificationSettings.tsx:449`), `animate-shimmer` x1 (`SettingsPage.tsx:660`); `slide-up`, `slide-down`, `scale-in`, `pulse-soft`: 0 uses. Custom utilities with 0 usages: `glass-card` (167), `subtle-noise` (171), `stagger-animation` (185-214), `animation-delay-*` (224-234), `text-balance` (163). Tailwind built-ins in use: `animate-spin` 49, `animate-pulse` 11, plus `animate-bounce` (ExplainAssistant), `animate-ping` (BadgeToast).
- Global interaction rules: `*:focus-visible { @apply outline-hidden ring-2 ring-accent ring-offset-2 ring-offset-surface }` (288-290); `button:not(:disabled), [role='button']:not(:disabled) { cursor: pointer }` (145-148); `::selection` accent/20 (292-295).
- Focus-class usage (components/pages): `focus-visible:ring` 16 lines vs `focus:ring` 30 lines and `focus:outline-hidden` 29: most custom focus styles use `focus:` (fire on mouse click too) and sit on top of the global `focus-visible` rule.

### 3d. Dark mode

- Mechanism: none configured. `globals.css` has no `@custom-variant dark`, so Tailwind v4's default `dark:` variant (`prefers-color-scheme: dark` media query) is what would apply. There is no `class="dark"` / `data-theme` handling anywhere (grep for `data-theme`, `classList`, `prefers-color-scheme`, `darkMode`, `toggleTheme`, `setTheme` in `src/`: only `index.html` theme-color metas).
- Toggle: does not exist.
- `dark:` utility usage: 1 occurrence, `src/components/ui/Skeleton.tsx:13` (`dark:bg-white/5`).
- The six `--color-dark-*` tokens (lines 34-40) have no consumers. Because `body` uses `bg-surface text-ink` (light tokens) with no dark override, an OS in dark mode renders the light UI; only the Skeleton tint changes.

### 3e. Hard-coded values in components instead of tokens

- Hex literals in `src/components` + `src/pages` (non-test): 21 occurrences on 19 lines in 4 files: `lab-interpreter/InterpretedTrendChart.tsx` 9 lines, `pages/TrendsDashboard.tsx` 7, `TrendVerificationMarkers.tsx` 2 (plus default param), `medication-coach/AdherenceDashboard.tsx` 1. Values: `#7BA387` x8, `#2D7D6F` x5, `#6B6B6B` x4, `#ffffff`/`#FFFFFF` x2, `#D4A574` x1, `#C9857A` x1. All are copies of existing tokens (recharts/SVG props cannot take Tailwind classes). Also `rgba(0,0,0,0.06/0.08)` for grid/axis/tooltip in `InterpretedTrendChart.tsx:109,116,127,129`, `AdherenceDashboard.tsx:37`, `TrendsDashboard.tsx:420,427,438,440`.
- Arbitrary bracket values `[..px|rem|vh|vw|%]`: 33 occurrences in 14 files. Top offenders: `SettingsPage.tsx` 11 lines, `settings/TierCapabilities.tsx` 5, `medication-coach/MedicationForm.tsx` 3, `NotificationSettings.tsx` 2, `ScheduleEditor.tsx` 2, `AchievementsWidget.tsx` 2. By value: `[10px]` x17 (text size on badges), `[44px]` x3 (`h-[44px]` selects in MedicationForm), `[9px]` x2, `[36px]` x2 (ScheduleEditor), `[90vh]`, `[85vh]`, `[80%]`, `[600px]`, `[400px]`, `[38px]` x1 each. Combined `text-[`, `bg-[`, `shadow-[`, `rounded-[` arbitrary count: 20 lines.
- Raw Tailwind palette (non-token) colours: only `documents/CategoryBadge.tsx:8-12` (`bg-blue-50`, `text-blue-700`, `bg-purple-50`, `text-purple-700`, `bg-green-50`, `text-green-700`, `bg-amber-50`, `text-amber-700`, `bg-gray-50`, `text-gray-500`), and that component has no importer.
- Non-standard z-index values: `z-60` (BadgeToast), `z-70` (VoiceFirstUseModal), `z-100` (dropdown content in DocumentInbox and AddToPinboardButton); TopBar `z-40`; modals `z-50`.

## 4. Interaction primitives

### Button (`src/components/ui/Button.tsx`)

- Variants: `primary` (accent fill), `secondary` (elevated surface + `border-black/8`), `ghost` (transparent, `hover:bg-black/4`), `danger` (`bg-status-attention`). Four total. No `link` or `outline` variant.
- Sizes: `sm` `px-3 py-2 text-sm` = 36px natural height, `md` `px-4 py-2.5 text-sm` = 40px, `lg` `px-6 py-3 text-base` = ~50px (12px*2 + 25.6px line height), `icon` `p-2.5` = 36px square with a 16px icon. Base class `min-h-target min-w-target` (44px, line 12) raises `sm`, `md` and `icon` to a 44px minimum; so effective heights are sm 44, md 44, lg ~50, icon 44x44. Overrides such as `h-8`, `h-10` do not go below 44px because `min-height` wins (TopBar `h-10`, NotificationSettings `h-8`, DoseLoggingModal `h-8 w-8` all render 44px). Raw `<button>` elements outside the primitive are below target: BadgeToast dismiss 32px, CitationTooltip 20px, filter chips in MemoryManager and DoseLoggingModal (~28-32px).
- Focus: `focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2` (line 9) on top of the global rule at `globals.css:288`.
- States: hover lift (`-translate-y-0.5` + `shadow-card`) on primary/secondary/danger; `active:scale-[0.98]` on all; `disabled:pointer-events-none disabled:opacity-50`; `transition-all duration-200 ease-in-out`. No loading prop (callers swap children for `Loader2`; 69 uses).

### Input and form controls

- `Input` (`ui/Input.tsx`): `h-11` (44px), `rounded-xl`, `border-black/8`, states: focus (`ring-2 ring-accent/20`, `border-accent`), error (`border-status-critical`, `aria-invalid`, `role="alert"` message), hint, disabled. Optional label via `useId`. Transition `transition-colors duration-200`.
- No primitives for select, textarea, checkbox, radio, switch or slider (`type="range"` grep: 0 hits). Native `<select>` is hand-styled in at least 8 places with differing heights (`h-[44px]` MedicationForm, `h-10` SearchPage, `h-[36px]` ScheduleEditor, `py-2` elsewhere) and some with no focus styling (RecoverProfile, settings/RecoveryCodeCard rely on the global ring). The switch pattern is copy-pasted 3 times (AgentSettingsCard, DataDonationCard, SettingsPage:303-330).

### Skeleton

`animate-pulse bg-black/5 dark:bg-white/5`; variants `text` (h-4), `circular` (h-10 w-10), `rectangular` (rounded-xl); `ListSkeleton` (h-20 pulse rows); `CardSkeleton` (unused). Pages also hand-roll `animate-pulse` blocks (`CareTasksPage`, `MedicationCoach`: `h-8 w-48 bg-black/5 animate-pulse`). 11 `animate-pulse` and 69 `Loader2` spinners overall.

### EmptyState

Icon in a muted circle, `font-display text-lg` title, `max-w-xs` description, optional action, wrapped in `Card` with `py-16`. Used on 6 pages. No illustration or animation. `MemoryManager` and `MedicationOverlay` hand-roll their own empty text.

### Card variants

None. One style plus slots (`CardHeader` `p-6 pb-4`, `CardTitle` `font-display text-xl`, `CardContent` `p-6 pt-0`). Variation is done by className overrides: `border-status-attention/40` (DangerZone), `bg-accent-subtle border-accent/10` (MedicationDetail), `bg-status-critical/5` (DocumentInbox error), `border-2 border-dashed` (DocumentInbox dropzone). The glass look uses `backdrop-blur-xl` on every card.

### Toast

No toast system. The only toast-like component is `BadgeToast` (single purpose, queue held in `MedicationCoach` state via `badgeQueue`). No `sonner`, no toast library in `package.json`. Success/failure feedback elsewhere is inline text (`role="status"` / `role="alert"`: 14 and 11 occurrences) or `animate-fade-in` text (`NotificationSettings.tsx:449`), or label swaps ("Copied", "Thanks!").

### Dialog / modal primitive

None. Six hand-built overlays (DoseLoggingModal, VoiceFirstUseModal (unused), DocumentInbox preview, VerificationWorkbench edit, SettingsPage x3) plus native `window.confirm` x2 (DocumentInbox, PinboardsPage) and `window.prompt` x1 (PinboardsPage).
Code check results across `src/components` and `src/pages`:
- Escape-to-close: 0 handlers. `grep "Escape"` returns nothing; the only keyboard handler in all pages is `onKeyDown` Enter-to-send in `ExplainAssistant.tsx:807`.
- Focus trap / focus return / `inert`: none. `autoFocus` appears once (VerificationWorkbench edit input, line ~804). `.focus()` is never called.
- ARIA: `role="dialog" aria-modal="true"` on DocumentInbox preview (463-464) and VerificationWorkbench edit (779-780, unlabelled); `role="dialog" aria-labelledby` without `aria-modal` on the Settings diagnostics dialog (980-981); no dialog role on DoseLoggingModal, VoiceFirstUseModal, Settings export dialog, Settings consent dialog. `DataDonationCard` uses an inline `role="alertdialog"` (not an overlay).
- Backdrop click closes: DoseLoggingModal, DocumentInbox preview, Settings x3; not VerificationWorkbench edit.
- Scroll lock: none.
- Enter/exit animation: only the three SettingsPage dialogs (in `AnimatePresence`) and DoseLoggingModal enter; DoseLoggingModal exit never plays (no parent `AnimatePresence`; parents render it conditionally at `MedicationCoach.tsx:368` and `MedicationDetail.tsx:430`).
- The only primitive that traps focus and handles Escape is Radix `DropdownMenu` (menus in `DocumentInbox.tsx:3` and `AddToPinboardButton.tsx:1`); those two usages are the only Radix UI components beyond `Slot`.

### Tooltip

No primitive. One hand-rolled `CitationTooltip` (`role="tooltip"`, hover/focus open, no Escape, no `aria-describedby`, intended `animate-in` classes are inert because no animate plugin is installed). Elsewhere native `title=` attributes (18 uses, e.g. ExplainAssistant feedback thumbs at 666) and SVG `<title>` (TrendVerificationMarkers). Recharts' built-in `<Tooltip>` is used in the two charts, styled inline.

### Tabs

No primitive. Two hand-rolled tab strips: `TrendsDashboard.tsx:319-345` (`role="tablist"/"tab"`, `aria-selected`, no arrow-key navigation, no `tabpanel`) and `LabInterpreter.tsx:203-225` (plain buttons, no roles). Filter chips in MemoryManager and ExplainAssistant behave like tabs/toggles without roles or `aria-pressed`. The `ExportPage` section buttons do use `aria-pressed`.

### Other relevant facts

- Layout is desktop-only: `Sidebar` is `fixed w-64`, `AppLayout` `pl-64`, no breakpoints in `components/layout/*`; `VerificationWorkbench` and `LabInterpreter` use fixed `grid-cols-3`. Responsive prefixes (`sm:`/`md:`/`lg:`) are used in a few pages (NotificationSettings 10 lines, SettingsPage 4).
- `TrendsDashboard.tsx:310,314` ("Last 12 Months", "Filters") and `ExportPage.tsx:~327` ("Full Preview") are buttons with no `onClick`.
- Native `window.print()`, `window.confirm`, `window.prompt` are used instead of in-app components (RecoveryCodeCard, DocumentInbox, PinboardsPage).
- No error boundary (`ErrorBoundary`/`errorElement`: 0 hits).

## 5. Counts (computed)

Rows in the section 1 tables: 87, of which 4 are barrel `index.ts` rows marked n/a. The `Card*` family, the `Motion.tsx` exports and `TrendVerificationMarkers` are each one row.

Scored rows: 83. Distribution of motion/interaction score:

| Score | Rows |
|---|---|
| 0 | 16 |
| 1 | 24 |
| 2 | 38 |
| 3 | 5 |

By group (0 / 1 / 2 / 3):

| Group | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| ui primitives | 1 | 2 | 2 | 2 |
| layout + auth | 1 | 0 | 1 | 2 |
| top-level, documents, lab-interpreter | 8 | 4 | 4 | 0 |
| medication-coach | 2 | 1 | 5 | 1 |
| pinboards, profile, settings | 2 | 4 | 3 | 0 |
| pages | 1 | 1 | 14 | 0 |
| App.tsx + inline sub-components | 1 | 12 | 9 | 0 |

File-level breakdown: 62 file rows (45 under components/, 16 pages, plus the `App.tsx` RouteFallback); the remaining 21 scored rows are inline sub-components or inline modals/patterns. Unused components (no importer): `CategoryBadge`, `VoiceFirstUseModal`, `CardSkeleton`.

Score 3 rows: Button (+ `buttonVariants`), Motion primitives (`fadeVariants`, `slideUpVariants`, `staggerContainerVariants`, `PageTransition`, `StaggerGroup`, `StaggerItem`, `modalVariants`, `backdropVariants`), AppLayout, Sidebar, BadgeToast.
