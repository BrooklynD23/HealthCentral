# Frontend UI/UX + Accessibility Plan (Draft v0 — pending PM approval)

## UX goals
- Reduce confusion and anxiety via clarity, provenance, and conservative language
- Make “verify and correct” the default for extracted values
- Optimize for older patients and non-medical users: readable typography, predictable navigation, plain language

Product constraints (from PRD): grounded outputs; no diagnosis/treatment advice; offline-first; provenance everywhere.

---

## Accessibility baseline (non-negotiable)
Target WCAG 2.2 AA behaviors for the UI patterns most likely to fail in desktop web UIs:
- Large, easy targets for primary actions (aim for ≥44×44 CSS px where practical)
- Keyboard focus never hidden behind sticky headers/modals
- Text remains usable at 200% zoom (no broken layouts)
- Reflow principles: avoid two-dimensional scrolling under zoom
- Charts always have accessible alternatives (table + textual summary)

Implementation norms:
- Semantic HTML first; ARIA only when needed.
- Visible focus ring for all interactive elements; no focus traps.
- Full keyboard support for all workflows (import, verify, charts, chat, export).
- Screen-reader labels for all controls; explicit error messages.

---

## Information architecture
Left navigation with 5 top-level areas:
1) **Inbox** (documents)
2) **Verify** (needs-review queue)
3) **Trends** (dashboards)
4) **Explain** (assistant + glossary)
5) **Export** (clinician-ready summary + data files)

Global top bar:
- Profile lock/unlock status
- Search (tests/terms)
- “Safety mode” indicator (conservative phrasing toggle)

---

## Core screens and templates

### 1) First run / profile setup
- Create profile → generate local vault → lock default-on
- Explain offline-first + confidentiality defaults in plain language

### 2) Document inbox
- Import button + drag/drop
- Document list shows:
  - source, date, type, status (parsed / needs verify)
- One-click “Open source” (read-only viewer)

### 3) Verification workbench (primary MVP screen)
Layout: split view
- Left: extracted table (rows = analytes)
- Right: source snippet viewer (page + highlighted span; Phase 1 adds bounding boxes)
- Inline edit controls:
  - value, unit, reference range, timestamp
  - validation errors shown in plain language
- Row badges:
  - “OCR-derived” (Phase 1)
  - “low confidence”
  - “user edited”

UX patterns:
- Progressive disclosure: advanced fields collapsed by default.
- “Explain this test” opens glossary side panel, not a new page.

### 4) Trends dashboard
- Panel tabs (CBC/CMP/BMP/lipids) + filters (timeframe, abnormal-only)
- Per-analyte drilldown:
  - chart + reference range shading
  - delta summary text (last value vs prior, new high/low markers)
  - “Where did this come from?” provenance link per point

Accessibility requirements:
- Chart view must include:
  - keyboard-navigable legend
  - data table view
  - generated textual summary (last value, change, range status)

### 5) Explain (assistant + glossary)
Chat is always context-scoped:
- Selected analyte/panel + timeframe shown above chat
- Toggle: include general references vs “report-only”
- Response formatting:
  - “What the report shows” (must cite user documents)
  - “General information” (cite local reference corpus)
  - “Uncertainties / missing info”

Hard rules:
- No factual claims about user results without citations.
- UI shows citation list and lets user click to open the source snippet.

### 6) Export
- Clinician-ready summary preview (1–2 pages)
- Export as PDF and copyable text
- “Questions to ask” section is opt-in and framed as discussion prompts only

---

## Design system (implementation-ready)

### Aesthetic Direction
HealthCentral adopts a **"Clinical Calm"** aesthetic—refined minimalism with warm, reassuring touches that reduce anxiety while maintaining medical credibility. This is NOT generic healthcare blue-on-white. Think: luxury wellness retreat meets precision lab.

**Core Identity:**
- **Tone**: Refined, trustworthy, quietly confident—never sterile or cold
- **Differentiation**: The one thing users remember: *"It made me feel in control, not overwhelmed"*
- **Philosophy**: Intentional restraint with moments of warmth; elegance through precision

### Typography
**AVOID**: Inter, Roboto, Arial, system-ui, or any generic sans-serif.

**REQUIRED** distinctive pairings:
- **Display/Headings**: A refined serif or geometric sans with character (e.g., Fraunces, DM Serif Display, Newsreader, Sora, or Satoshi)
- **Body/Data**: A humanist sans with excellent legibility at small sizes (e.g., Source Sans 3, Nunito Sans, or Atkinson Hyperlegible for accessibility)
- **Monospace (for values)**: JetBrains Mono or IBM Plex Mono

Tokens:
- Base: 16–18px; allow user scaling
- Line height: 1.5–1.6 for body; 1.2 for headings
- Letter spacing: Slightly relaxed for data tables

### Color & Theme
**AVOID**: Purple gradients on white, generic blue healthcare palettes, or washed-out pastels.

**Direction**: Warm neutrals with a signature accent.
- **Primary palette**: Deep warm grays, soft ivory backgrounds, NOT pure white (#FAFAF8 over #FFFFFF)
- **Accent**: A single bold, memorable accent (options: terracotta, sage green, or deep teal—pick ONE and commit)
- **Status colors**: Muted, desaturated versions that don't alarm (amber caution, soft coral for attention, sage for verified)
- **Dark mode**: Rich charcoal backgrounds (#1A1A1A), not pure black

Implement via CSS custom properties for consistency:
```css
--color-surface: #FAFAF8;
--color-surface-elevated: #FFFFFF;
--color-text-primary: #1F1F1F;
--color-text-secondary: #6B6B6B;
--color-accent: #2D7D6F; /* Deep teal example */
--color-accent-subtle: #E8F4F2;
```

High contrast ratios remain non-negotiable (4.5:1 minimum).

### Spatial Composition & Layout
- **Generous negative space**: Let content breathe; avoid cramped data displays
- **Asymmetric balance**: Offset alignments where appropriate; break rigid grid monotony
- **Visual hierarchy**: Clear z-depth through subtle shadows and layering
- **Cards with presence**: Soft shadows (0 4px 24px rgba(0,0,0,0.06)), rounded corners (12–16px)

### Motion & Micro-interactions
**Philosophy**: Restraint with purpose. One well-orchestrated moment beats scattered animations.

- **Page transitions**: Staggered reveals on load (subtle fade + translate, 200–300ms, animation-delay for sequence)
- **Hover states**: Gentle lifts, color shifts—never jarring
- **Data updates**: Smooth number transitions for trend changes
- **Feedback**: Subtle pulse or glow on successful actions
- **Respect `prefers-reduced-motion`**: All animations must degrade gracefully

No essential information conveyed via animation alone.

### Backgrounds & Visual Details
**AVOID**: Flat solid colors everywhere.

**Create atmosphere:**
- Subtle gradient meshes or soft radial gradients on primary backgrounds
- Fine noise texture overlay (2–4% opacity) for organic warmth
- Geometric accent patterns in empty states (SVG, very subtle)
- Layered transparencies for depth (glassmorphism-lite: backdrop-blur where appropriate)

### Core Components
All components combine accessibility with distinctive styling:

- `A11yButton` — Large targets, satisfying press states, subtle hover lift
- `A11yDialog` — Centered modal with backdrop blur, elegant entrance animation
- `A11yTable` — Alternating row tints, generous padding, sortable headers with refined icons
- `A11yTabs` — Animated underline indicator, smooth panel transitions
- `A11yToast` — Slide-in from bottom-right, auto-dismiss with progress indicator
- `ProvenanceLink` — Opens source panel at page/span/box; styled as subtle inline citation
- `GlossaryTerm` — Inline definitions with hover tooltip + click-to-expand; dotted underline affordance
- `TrendChart` — Animated line draw on load, interactive hover states with value callouts
- `StatusBadge` — Pill-shaped, color + icon (never color alone), refined typography

Copy rules:
- Prefer “outside the reference range (per report)” over “abnormal”.
- Avoid catastrophic language; emphasize “discuss with clinician” framing.
- Use consistent, reversible phrasing: “This is what your report states.”

---

## Audit Results (A11Y-001)

**Audit date:** 2026-02-12

### Fixes Applied

| Component | Fix | Category |
|-----------|-----|----------|
| TrendsDashboard panel selector | Added `role="tablist"` + `role="tab"` + `aria-selected` | Keyboard/Semantic |
| TrendsDashboard loading | Added `role="status"` + `aria-live="polite"` + sr-only text | Screen reader |
| MedicationDetail loading | Added `role="status"` + `aria-live="polite"` + sr-only text | Screen reader |
| VerificationWorkbench loading | Added `role="status"` + `aria-live="polite"` + sr-only text | Screen reader |
| ExportPage section toggles | Added `aria-pressed` + descriptive `aria-label` | Semantic |
| MedicationOverlay links | Added `aria-label` per medication link | Screen reader |
| MedicationDetail related labs | Added `aria-label` per lab result link | Screen reader |
| All framer-motion animations | Already respect `useReducedMotion()` | Reduced motion |

### Automated Tests

File: `src/frontend/src/__tests__/Accessibility.test.tsx`

- Panel tablist/tab roles present
- Active tab has `aria-selected="true"`
- Loading states have `role="status"`
- Verification workbench buttons have aria-labels
- Export buttons have accessible names

---

## QA acceptance checklist
- Keyboard-only completion of import → verify → trends → export
- Screen-reader sanity pass on all primary screens
- Zoom 200% with no horizontal scroll for core flows
- Focus never obscured by fixed UI elements
- Click targets meet sizing guidance for critical actions
