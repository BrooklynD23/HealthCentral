# Sprint 05 Closeout — Revised Implementation Plan

## Overview

Five sequential phases: stabilize baseline (Phase 0), then three parallel polish streams
(UXQA-001/002/003), then merge to main (Phase C).

---

## Phase 0: Stabilize Flaky Test (BLOCKER — must pass before any new work)

### Problem
`ResponsiveLayout.test.tsx:258` — `TrendsDashboard responsive layout > uses responsive grid classes`
passes in isolation but flakes in the full suite (163/164 passed, 1 timeout). Root cause: TrendsDashboard
dynamic import + heavy Recharts initialization competes for resources when run after 150+ prior tests.

### Fix
**File**: `src/frontend/src/__tests__/ResponsiveLayout.test.tsx`

1. Increase the `waitFor` timeout on line 264 from `15000` → `30000` ms (matching the outer test timeout)
2. Add `vi.setConfig({ testTimeout: 30_000 })` at the top of the TrendsDashboard responsive describe block
3. Verify: full `npx vitest run` must show **164/164 pass** (or 165 if the fix itself adds a sanity check)

### Exit Criteria
- `npx vitest run` — all tests green, zero failures, zero flakes on 2 consecutive runs

---

## Phase 1: UXQA-001 — Accessibility (Split: Structural + Contrast)

The reviewer correctly identified that **axe-core color-contrast checks are unreliable in JSDOM**
(Tailwind utility classes don't compute to rendered colors). We split into two layers:

### 1A: vitest-axe — Structural A11y Rules (JSDOM)

**New dep**: `vitest-axe` (wraps axe-core for vitest matchers)

**File**: `src/frontend/src/__tests__/setup.ts`
- Add `import 'vitest-axe/extend-expect';` to register `toHaveNoViolations` globally

**File**: `src/frontend/src/__tests__/StructuralA11y.test.tsx`
- Run axe on all routable page components with **contrast rules disabled**:
  ```ts
  const results = await axe(container, {
    rules: { 'color-contrast': { enabled: false } },
  });
  ```
- **Pages in scope** (10 routable surfaces from `App.tsx:48-64`):
  | Route | Component | Included |
  |-------|-----------|----------|
  | `/setup` | ProfileSetup | Yes |
  | `/inbox` | DocumentInbox | Yes |
  | `/verify` | VerificationWorkbench | Yes |
  | `/trends` | TrendsDashboard | Yes |
  | `/interpret` | LabInterpreter | Yes |
  | `/medications` | MedicationCoach | Yes |
  | `/medications/:id` | MedicationDetail | No (param-dependent, covered by MedicationCoach) |
  | `/notifications` | NotificationSettings | Yes |
  | `/explain` | ExplainAssistant | Yes |
  | `/export` | ExportPage | Yes |
  | `/search` | SearchPage | Yes |
  | `/settings` | SettingsPage | Yes |
- **Total**: 11 page-level axe structural tests
- Must include standard framer-motion mock + recharts mock + API mocks

### 1B: Playwright axe — Color Contrast (Browser)

**File**: `src/frontend/e2e/contrast-audit.spec.ts`
- Uses `@axe-core/playwright` (already available via Playwright dep chain, or install if needed)
- Tests color contrast on 4 key pages that have the most varied color usage:
  - `/inbox` (status badges, table text)
  - `/trends` (chart labels, panel tabs, badges)
  - `/settings` (form labels, switch controls)
  - `/search` (result highlights, filters)
- Pattern:
  ```ts
  import AxeBuilder from '@axe-core/playwright';
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2aa'])
    .analyze();
  expect(results.violations.filter(v => v.id === 'color-contrast')).toEqual([]);
  ```
- **Note**: These run in CI via the `e2e-tests` job (requires backend). Not part of `vitest run`.

### Exit Criteria
- `npx vitest run` — all existing + new structural a11y tests pass
- `contrast-audit.spec.ts` written (exercised in CI only)

---

## Phase 2: UXQA-002 — PWA Manifest + Service Worker Scaffold

### 2.1: Web App Manifest

**File**: `src/frontend/public/manifest.webmanifest`
```json
{
  "name": "HealthCentral",
  "short_name": "HealthCentral",
  "description": "Your personal medical results companion",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FAFAF8",
  "theme_color": "#2D7D6F",
  "orientation": "any",
  "icons": [
    { "src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any" },
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "categories": ["health", "medical"]
}
```

### 2.2: Icon Assets

**Directory**: `src/frontend/public/icons/`
- Generate `icon-192.png` and `icon-512.png` from existing `favicon.svg` using a simple
  canvas script or placeholder PNGs. Required by Chrome for installability audit.

### 2.3: No-Op Service Worker

**File**: `src/frontend/public/sw.js`
```js
// HealthCentral Service Worker — Scaffold (no caching)
const CACHE_VERSION = 'v0.1.0';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', (event) => {
  // Pass-through — no caching in scaffold version
  event.respondWith(fetch(event.request));
});
```

### 2.4: Link Manifest + Prod-Only SW Registration

**File**: `src/frontend/index.html`
- Add `<link rel="manifest" href="/manifest.webmanifest" />` in `<head>`

**File**: `src/frontend/src/main.tsx`
- Add prod-only SW registration **after** React render:
  ```ts
  if (import.meta.env.PROD && 'serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        // SW registration failed — app continues normally
      });
    });
  }
  ```
- **Why main.tsx instead of index.html**: Uses Vite's `import.meta.env.PROD` for a clean
  prod-only guard. Avoids SW interference with Vite HMR during development.

### Exit Criteria
- `manifest.webmanifest` validates (well-formed JSON, icons referenced)
- SW registration only fires in prod builds (not during `npm run dev`)
- `npx tsc --noEmit` still clean
- No impact on existing test suite

---

## Phase 3: UXQA-003 — Panel Chart + Adherence Visualization

### Blocker Resolution: Data Contracts

**Panel observations** (`PanelResponse.observations`): Mixed analytes with different units
(e.g., CBC has WBC in K/uL, Hgb in g/dL, Plt in K/uL). A raw multi-analyte bar chart with a
shared Y-axis is misleading.

**Solution — Percent-of-Reference Normalization**:
```
normalizedValue = ((value - ref_low) / (ref_high - ref_low)) * 100
```
- 0% = at ref_low, 100% = at ref_high
- Values >100% or <0% indicate out-of-range
- This allows cross-analyte comparison on a shared scale
- Reference band renders as a shaded region at 0-100%
- Only include observations where `value`, `ref_low`, and `ref_high` are all non-null
- Observations with only `value_text` (qualitative results) show in sr-only table but not in chart

**Adherence data**: The `/medications/{id}/stats` endpoint returns only aggregates. The
`/medications/{id}/doses` endpoint returns individual dose records with `taken_at` and
`was_skipped`. The AdherenceChart component will:
- Accept raw `DoseResponse[]` from the existing `list_doses` API (no new backend endpoint)
- Aggregate client-side into daily buckets: group by `taken_at` date → count taken vs skipped
- This is feasible because `limit` is max 100, covering ~3 months of daily doses

### 3.1: PanelChartView Component

**File**: `src/frontend/src/components/PanelChartView.tsx`

Props:
```ts
interface PanelChartViewProps {
  panel: Panel;       // from services/types.ts
  className?: string;
}
```

Implementation:
- Filter observations to those with numeric `value`, `ref_low`, `ref_high`
- Compute `normalizedValue` per observation using percent-of-reference formula
- Render Recharts `BarChart` with:
  - X-axis: analyte display name (`analyte_raw`)
  - Y-axis: normalized % (0-200 range, reference band shaded 0-100%)
  - `ReferenceLine` at y=0 and y=100 (or `ReferenceArea` for the band)
  - Bar color: `status-verified` (green) for in-range, `status-attention` (red) for out-of-range
- sr-only data table with columns: Analyte, Value, Unit, Reference Range, Status
- Empty state when no numeric observations available
- ~140-170 lines

### 3.2: Integrate PanelChartView into TrendsDashboard

**File**: `src/frontend/src/pages/TrendsDashboard.tsx`

Insert between the panel tab bar (line 347) and the main grid (line 349):
```tsx
{panelData && panelData.observations.length > 0 && (
  <PanelChartView panel={panelData} className="mb-6" />
)}
```

### 3.3: AdherenceChart Component

**File**: `src/frontend/src/components/medication-coach/AdherenceChart.tsx`

Props:
```ts
interface AdherenceChartProps {
  doses: Array<{
    taken_at: string;
    was_skipped: boolean;
  }>;
  className?: string;
}
```

Implementation:
- Group doses by date (YYYY-MM-DD from `taken_at`)
- For each date: count taken (not skipped) and skipped
- Render Recharts stacked `BarChart`:
  - X-axis: date (day-of-month label)
  - Y-axis: dose count
  - Two stacked bars: taken (green/`status-verified`), skipped (red/`status-attention`)
- sr-only data table with columns: Date, Taken, Skipped
- Empty state when no doses
- ~120-150 lines
- **No new backend endpoint needed** — uses existing `list_doses` response shape

### 3.4: PanelChartView Tests

**File**: `src/frontend/src/__tests__/PanelChartView.test.tsx`

Tests (~7):
1. Renders chart when panel has numeric observations
2. Shows empty state when panel has zero observations
3. Shows empty state when observations lack ref ranges
4. Normalizes values to percent-of-reference (check data attribute or bar height)
5. Renders sr-only data table with Analyte/Value/Unit/Range/Status columns
6. Out-of-range observations get attention color
7. Panel name appears in component heading

Mocks: recharts `ResponsiveContainer` (existing pattern)

### 3.5: AdherenceChart Tests

**File**: `src/frontend/src/__tests__/AdherenceChart.test.tsx`

Tests (~6):
1. Renders chart when doses array is non-empty
2. Shows empty state when doses is empty
3. Aggregates multiple doses on same date into single bar
4. Renders sr-only data table with Date/Taken/Skipped columns
5. Correctly counts taken vs skipped
6. Chart container has correct test ID

Mocks: recharts `ResponsiveContainer`

### Exit Criteria
- Both components render correctly with mock data
- All new tests pass alongside existing 164
- `tsc --noEmit` clean
- No changes to backend

---

## Phase 4: Documentation + Commit

### 4.1: Update PM Backlog

**File**: `docs/plans/pm-complete-unimplemented-features-2026-02-15.md`
- UXQA-001: "COMPLETE — vitest-axe structural checks (11 pages) + Playwright contrast audit (4 pages)"
- UXQA-002: "COMPLETE — manifest.webmanifest, icon assets, no-op SW, prod-only registration"
- UXQA-003: "COMPLETE — PanelChartView (%-of-ref normalization), AdherenceChart (daily dose aggregation)"
- Sprint 05 overall: "COMPLETE"

### 4.2: Commit

```
feat(S05): final polish — axe-core a11y, PWA scaffold, panel/adherence charts
```

### Exit Criteria
- Working tree clean after commit
- All tests pass (expected ~190 vitest tests)

---

## Phase C: Merge to Main

### C.1: Verify Full Suite
```bash
cd src/frontend
npx tsc --noEmit          # 0 errors
npm run lint              # 0 warnings
npx vitest run            # all pass
```

### C.2: Push + Create PR
```bash
git push -u origin sprint/05-frontend-quality-testing
gh pr create --base main --head sprint/05-frontend-quality-testing \
  --title "feat(S05): Sprint 05 — Frontend Quality, Testing & Final Polish"
```

PR body should include:
- Summary of all 5 UXQA work packages
- Total test counts (vitest + E2E spec files + backend test files)
- Breaking changes: None
- Key architectural decisions (%-of-ref normalization, prod-only SW)

### C.3: Monitor CI Checks
CI pipeline (`.github/workflows/ci.yml`) runs on PR to main:
1. `docs-lint` — Python docs linter
2. `backend-tests` — Python backend with SQLCipher
3. `frontend-tests` — `tsc --noEmit` + `vitest run`
4. `e2e-tests` — Playwright with backend (includes new `contrast-audit.spec.ts`)

### C.4: Merge
Once all checks green, merge (squash-and-merge recommended for sprint closeout).

### Exit Criteria
- All 4 CI jobs green
- PR merged to main
- Sprint 05 complete

---

## Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| `vitest-axe` incompatible with vitest v4 | Medium | Fallback: use `axe-core` directly with custom matcher |
| `@axe-core/playwright` not in deps | Low | `npm install -D @axe-core/playwright` |
| Panel chart misleading with raw values | High | Resolved: percent-of-reference normalization |
| Adherence chart needs new backend endpoint | Medium | Resolved: client-side aggregation from `list_doses` |
| SW interferes with dev HMR | Medium | Resolved: `import.meta.env.PROD` guard in `main.tsx` |
| Flaky test blocks all work | High | Phase 0 addresses first |

---

## File Inventory

### New Files (8)
| File | Lines | Purpose |
|------|-------|---------|
| `src/frontend/src/__tests__/StructuralA11y.test.tsx` | ~250 | axe-core structural a11y (11 pages, no contrast) |
| `src/frontend/e2e/contrast-audit.spec.ts` | ~60 | Playwright axe contrast checks (4 pages) |
| `src/frontend/public/manifest.webmanifest` | ~20 | PWA manifest |
| `src/frontend/public/sw.js` | ~15 | No-op service worker |
| `src/frontend/public/icons/icon-192.png` | — | PWA icon (192x192) |
| `src/frontend/public/icons/icon-512.png` | — | PWA icon (512x512) |
| `src/frontend/src/components/PanelChartView.tsx` | ~160 | Panel multi-analyte normalized chart |
| `src/frontend/src/components/medication-coach/AdherenceChart.tsx` | ~140 | Daily adherence time-series |
| `src/frontend/src/__tests__/PanelChartView.test.tsx` | ~150 | PanelChartView tests (7) |
| `src/frontend/src/__tests__/AdherenceChart.test.tsx` | ~120 | AdherenceChart tests (6) |

### Modified Files (5)
| File | Change |
|------|--------|
| `src/frontend/package.json` | Add `vitest-axe`, `@axe-core/playwright` |
| `src/frontend/src/__tests__/setup.ts` | Add vitest-axe matcher import |
| `src/frontend/src/__tests__/ResponsiveLayout.test.tsx` | Fix flaky timeout |
| `src/frontend/index.html` | Add `<link rel="manifest">` |
| `src/frontend/src/main.tsx` | Add prod-only SW registration |
| `src/frontend/src/pages/TrendsDashboard.tsx` | Import + render PanelChartView |
| `docs/plans/pm-complete-unimplemented-features-2026-02-15.md` | Sprint 05 → COMPLETE |

---

## Execution Order

```
Phase 0 (fix flaky test)
  ↓
  ├── Phase 1 (UXQA-001: structural + contrast) ──┐
  ├── Phase 2 (UXQA-002: PWA scaffold)            ├── Phase 4 (docs + commit)
  └── Phase 3 (UXQA-003: charts)                 ──┘         ↓
                                                        Phase C (merge)
```

Phases 1, 2, 3 are independent and can be parallelized after Phase 0.
