# Asclexis Frontend

**Last Updated:** 2026-07-27

Web-based UI for Asclexis, designed to run within a Tauri desktop shell.

For how the frontend fits into the whole system, see the
[frontend architecture diagrams](../../docs/architecture/frontend.md).

## Technology Stack

- **Framework**: React 18+ with TypeScript
- **Styling**: TailwindCSS with custom design tokens
- **Components**: shadcn/ui (accessible by design, extensively customized)
- **Icons**: Lucide React
- **Fonts**: Variable fonts via Google Fonts or Fontsource
- **Motion**: Framer Motion (for React animations)
- **Charts**: Recharts (accessible chart library)
- **State**: Zustand or React Query

## Accessibility Requirements (WCAG 2.2 AA)

Per the Frontend Accessibility Plan, this UI must:

- Large click targets (≥44×44 CSS px)
- Visible focus rings on all interactive elements
- Full keyboard navigation for all workflows
- Screen reader support with proper ARIA labels
- Charts with data table and textual summary alternatives
- Works at 200% zoom without horizontal scroll

## Project Structure

```
src/frontend/
├── src/
│   ├── components/           # Reusable UI components
│   │   ├── ui/              # Base components (Button, Card, Input, Badge, …)
│   │   ├── layout/          # AppLayout, Sidebar, TopBar
│   │   ├── auth/            # ProtectedRoute
│   │   ├── profile/         # RecoveryCodeCard (SEC-RECOV-001)
│   │   ├── settings/        # DangerZone — profile deletion (PROF-DEL-001)
│   │   ├── documents/       # HighlightChips, EntityDetailView, confidence badges
│   │   ├── lab-interpreter/ # Interpreted results, citations, disclaimers
│   │   ├── medication-coach/# Forms, adherence, streaks, badges
│   │   └── pinboards/       # AddToPinboardButton
│   ├── pages/               # Page components (see Screens below)
│   ├── hooks/               # Custom React hooks
│   ├── services/            # API client + React Query hooks
│   │                        #   exported through services/index.ts (the barrel)
│   ├── stores/              # Zustand — session state only
│   ├── types/               # TypeScript types
│   └── utils/               # Utility functions
├── e2e/                     # Playwright specs
├── public/                  # Static assets
└── package.json
```

## Screens

The original six PRD screens, plus everything the post-visit roadmap
(HC-M12…HC-M24) added.

| Screen | Route | Purpose |
|---|---|---|
| **ProfileSetup** | `/setup` | Create an encrypted profile; shows the one-time recovery code |
| **RecoverProfile** | `/recover` | Forgot-password path using the recovery code (SEC-RECOV-001) |
| **DocumentInbox** | `/inbox` | Import and list documents; highlight chips, confidence, duplicate warnings |
| **VerificationWorkbench** | `/verify` | Review and correct extracted values against their source quotes |
| **TrendsDashboard** | `/trends` | Analyte trends with reference ranges and medication overlay |
| **TimelinePage** | `/timeline` | Chronological view of labs, visits, imaging, medication changes (HC-M14) |
| **SearchPage** | `/search` | Cross-record search and filtering (HC-M21) |
| **LabInterpreter** | `/interpret` | Grounded, cited interpretations |
| **MedicationCoach** | `/medications` | Medication list, adherence, streaks |
| **MedicationDetail** | `/medications/:id` | One medication: schedule, doses, related labs |
| **CareTasksPage** | `/care-tasks` | Follow-up task candidates and tracker (HC-M15) |
| **PinboardsPage** | `/pinboards` | User-curated collections (HC-M20) |
| **ExplainAssistant** | `/explain` | Cited Q&A over your own record, with agentic query chips (HC-M24) |
| **ExportPage** | `/export` | Doctor summary, visit-prep packet (HC-M18), FHIR R4 (HC-M22), CSV/JSON |
| **NotificationSettings** | `/notifications` | Medication reminders |
| **SettingsPage** | `/settings` | Model tier, hardware, voice, memory — and the profile Danger Zone |

### Conventions

- **Import hooks from the `services/index.ts` barrel**, not from individual
  service files, so the API surface stays visible in one place.
- **Server state lives in React Query; only session state lives in Zustand.**
  The auth store holds the token, profile id and expiry — nothing the server owns.

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Supported Contributor Verification Path

The audited local proof commands for this repo are run from the repository root so backend and frontend verification stay copy-paste compatible:

```bash
npm --prefix src/frontend install
npx --prefix src/frontend tsc --noEmit -p src/frontend/tsconfig.json
```

Use that root-level form when following `README.md`, GSD task plans, or milestone verification notes.

### WSL / Windows caveat

If the repo is checked out under `/mnt/c/...` and longer-running frontend tests stall on the NTFS mount, treat CI or a native Linux checkout as the source of truth for `vitest` and browser-heavy suites. The type-check command above is the supported local frontend proof used by the environment bootstrap slice.

## Running Tests

```bash
# Run full test suite (deterministic, exits cleanly)
npx vitest run

# Run specific test file
npx vitest run src/__tests__/TrendsDashboard.test.tsx

# Run in watch mode (development)
npx vitest

# Type-check without emitting (from repo root)
npx --prefix src/frontend tsc --noEmit -p src/frontend/tsconfig.json
```

Tests use `pool: 'forks'` for process isolation and a 10-second timeout.
Zustand stores are reset after each test to prevent state leakage.

## Design Tokens

See `src/styles/tokens.css` for:
- Typography scale (16-18px base)
- Spacing system
- Color palette (high contrast)
- Motion preferences (reduced motion support)

---

## UI/UX Aesthetic Guidelines

Asclexis follows a **"Clinical Calm"** aesthetic—refined minimalism with warm, reassuring touches. This avoids generic healthcare aesthetics and creates a memorable, trustworthy experience.

### Design Philosophy
- **Tone**: Refined, trustworthy, quietly confident—never sterile
- **Differentiator**: *"It made me feel in control, not overwhelmed"*
- **Execution**: Intentional restraint with moments of warmth

### Typography (CRITICAL)
**NEVER USE**: Inter, Roboto, Arial, system-ui, or generic sans-serif fonts.

**Required Font Pairings:**
```css
/* Display/Headings - choose ONE with character */
--font-display: 'Fraunces', 'DM Serif Display', 'Newsreader', serif;

/* Body/UI - humanist sans with excellent legibility */
--font-body: 'Source Sans 3', 'Nunito Sans', 'Atkinson Hyperlegible', sans-serif;

/* Monospace for data values */
--font-mono: 'JetBrains Mono', 'IBM Plex Mono', monospace;
```

Install via Fontsource:
```bash
npm install @fontsource-variable/fraunces @fontsource-variable/source-sans-3 @fontsource/jetbrains-mono
```

### Color Palette
**AVOID**: Purple gradients, generic blue healthcare palettes, pure white backgrounds.

**Implement in `tailwind.config.js`:**
```js
colors: {
  surface: {
    DEFAULT: '#FAFAF8',  // Warm off-white, NOT pure white
    elevated: '#FFFFFF',
    muted: '#F5F5F3',
  },
  ink: {
    DEFAULT: '#1F1F1F',  // Rich near-black
    secondary: '#6B6B6B',
    tertiary: '#9A9A9A',
  },
  accent: {
    DEFAULT: '#2D7D6F',  // Deep teal (signature color)
    subtle: '#E8F4F2',
    hover: '#256B5F',
  },
  status: {
    caution: '#D4A574',    // Warm amber (not alarming)
    attention: '#C9857A',  // Soft coral
    verified: '#7BA387',   // Sage green
    info: '#6B8CAE',       // Muted blue
  }
}
```

### Motion & Animation
**Philosophy**: One orchestrated moment beats scattered micro-interactions.

**High-impact animations:**
- **Page load**: Staggered reveal (fade + translateY, 200-300ms, cascading delays)
- **Data transitions**: Smooth number morphing for trend values
- **Hover states**: Gentle lift (translateY: -2px) + shadow expansion
- **Success feedback**: Subtle pulse or checkmark draw animation

**Implementation with Framer Motion:**
```tsx
// Staggered list reveal
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } }
};
```

**REQUIRED**: Respect `prefers-reduced-motion` media query.

### Visual Details & Atmosphere
**AVOID**: Flat solid backgrounds everywhere.

**Create depth:**
- Subtle gradient meshes or soft radial gradients
- Fine noise texture overlay (2-4% opacity)
- Cards with presence: `shadow-lg` equivalent, 12-16px border-radius
- Layered transparencies via backdrop-blur

**Example card styling:**
```css
.card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.04);
}
```

### Spatial Composition
- **Generous whitespace**: Let data breathe; avoid cramped tables
- **Asymmetric balance**: Break grid monotony where appropriate
- **Visual hierarchy**: Clear z-depth through layering
- **Large touch targets**: ≥44x44px (accessibility requirement)

## Component Guidelines

### Accessibility (Non-negotiable)
- Use semantic HTML elements
- Include `aria-label` for icon-only buttons
- Ensure color is not the only indicator of state
- Test with keyboard navigation
- Test with screen reader (NVDA/VoiceOver)

### Styling Standards
- **Buttons**: Satisfying press states, subtle hover lift, generous padding
- **Inputs**: Clear focus rings (accent color), helpful placeholder text
- **Tables**: Alternating row tints, generous cell padding, sortable header affordances
- **Modals**: Backdrop blur, centered with elegant entrance animation
- **Toasts**: Slide-in animation, auto-dismiss with progress indicator
- **Badges/Pills**: Rounded-full, icon + text (never color alone)

### Anti-Patterns to Avoid
- Generic font stacks (Inter, Roboto, Arial)
- Pure white (#FFFFFF) as primary background
- Purple/blue gradients (overused AI aesthetic)
- Jarring color contrasts for status indicators
- Cookie-cutter layouts without visual interest
- Animations without purpose or user benefit

---

## Quality Checklist

**Before PR:**
- [ ] Typography uses designated font families (no system fonts)
- [ ] Colors match design tokens (no hardcoded hex values)
- [ ] Animations respect `prefers-reduced-motion`
- [ ] Keyboard navigation works for entire flow
- [ ] Screen reader announces all interactive elements
- [ ] 200% zoom shows no horizontal scroll
- [ ] Visual design feels distinctive, not generic
