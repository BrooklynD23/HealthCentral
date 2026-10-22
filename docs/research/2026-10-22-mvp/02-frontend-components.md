# 02 — Frontend component libraries, charts and accessibility

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** a React 19 upgrade; a new UI primitive library is proposed; `src/frontend/package.json` adds or removes a runtime dependency.

> **Point-in-time research (2026-10-22).** Markers as in [00-README.md](00-README.md). This file builds on the [2026-09-08 frontend research](../2026-09-08/08-frontend.md) (stay on recharts, add `@radix-ui/react-dialog`, defer React 19) and does not repeat it.

## Baseline

`src/frontend/package.json` at `d2843e8`: React 18, Tailwind 4, Vite 7, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-slot`, `class-variance-authority`, `clsx`, `tailwind-merge` (the shadcn pattern), `recharts` ^3.9.1, `framer-motion` ^10, `lucide-react`, React Query 5, Zustand.

Measured build **[V]** (`npm ci && npm run build` on a copy, Node 26.2.0): entry chunk `index-*.js` 575.21 kB, 179.96 kB gzip, over Vite's 500 kB warning. The recharts chunk is 358.54 kB, 105.17 kB gzip, and loads lazily on Trends and Lab Interpreter only. CSS is 72.87 kB. Eleven pages use `React.lazy`. framer-motion sits in the entry chunk because eager pages import it **[A]**. `npm audit --omit=dev` found 0 vulnerabilities **[A]**.

## Gaps seen in the code (accessibility)

These come from a static read. The file:line references are in the L0 bug list.

- Dialogs in DocumentInbox, VerificationWorkbench and SettingsPage have no Escape handling, no focus trap and no `role="dialog"`.
- The icon-only send button in ExplainAssistant has no accessible name, and its input has only a placeholder.
- Trend charts have no text alternative. Verified and unverified points differ only by marker shape.

## Libraries

| Library | Licence | Latest | Size | Fit | Verdict |
|---|---|---|---|---|---|
| Radix Primitives (`radix-ui` unified, or per-component) | MIT **[V]** | `radix-ui` 1.8.1 **[V]** | per-component; whole package 67 kB gzip **[A]** | already in use; WAI-ARIA focus and keyboard handling | **keep**; add `@radix-ui/react-dialog` (and tabs/tooltip only if needed) |
| shadcn/ui (CLI copies source) | MIT **[V]** | CLI 4.22.1 **[V]** | no runtime dependency | the app already follows the pattern; docs say the components are updated for Tailwind v4 **[A]** (ui.shadcn.com/docs/tailwind-v4). The CLI needs the network at dev time only | **use as a source of copied components**; check React 18 compatibility per component |
| sonner (toasts) | MIT **[V]** | 2.0.8 **[V]** | 9.4 kB gzip, 0 deps **[A]** | gives save/verify/import feedback | adopt only if the team wants toasts. An inline `role="alert"` also fixes the silent import failure |
| react-hook-form (+ zod) | MIT **[A]** | v7 **[A]** | small | form validation (verification edit, profile) | defer; a strict numeric check is enough for the MVP |
| Base UI (`@base-ui/react`) | MIT **[V]** | 1.9.0 **[V]** | 166 kB gzip whole package **[A]** | successor-style primitives from the Radix/MUI teams **[A]** | **do not adopt before the showcase** (a second primitive family) |
| React Aria Components | Apache-2.0 **[U]** | 1.22.1 **[A]** | — | the strongest accessibility reference | not for the MVP (second family) |
| Headless UI, Mantine, Tremor, visx, Nivo, TanStack Table | MIT / Apache-2.0 **[A]** | — | — | overlap Radix or recharts, or restyle the app | **do not adopt** |

## Health-chart specifics (no new library)

- **Reference-range band:** recharts `ReferenceArea` "Draws a rectangular area on the chart to highlight a specific range" **[A]** (recharts.github.io/en-US/api/ReferenceArea, page reachable **[V]**). Use it with the observation's `ref_low`/`ref_high`.
- **Out-of-range marker:** a custom `dot` renderer on the line series, with the text "above range" or "below range" in the tooltip as well as the colour.
- **Accessible alternative:** render the same series as a native `<table>` (inside `<details>`), as the 2026-09-08 research proposed. recharts 3 also has an `accessibilityLayer` prop **[A]**; recharts latest is 3.10.1 **[V]**.

## Bundle (post-MVP)

- Use `LazyMotion` + `m` from framer-motion on eager pages, or keep motion out of eager pages. Expected: most of framer-motion leaves the entry chunk **[U]**, so measure before claiming it.
- Optional `manualChunks` for react-router and react-dom, to cache vendor code separately.

## Recommendation

1. Keep Radix + the shadcn pattern + recharts. Add `@radix-ui/react-dialog` for the four dialogs.
2. Use `ReferenceArea` and a data table for trends. Add no chart library.
3. Toasts (sonner) are optional. Fix error display with inline alerts first.

## Sources

- https://ui.shadcn.com/docs/tailwind-v4 ; https://ui.shadcn.com/docs/changelog/2026-02-radix-ui ; https://registry.npmjs.org/shadcn
- https://registry.npmjs.org/radix-ui ; https://github.com/radix-ui/primitives
- https://base-ui.com/ ; https://github.com/mui/base-ui/releases
- https://react-aria.adobe.com/
- https://recharts.github.io/en-US/api/ ; https://recharts.github.io/en-US/api/ReferenceArea/
- https://bundlephobia.com/api/size?package=sonner@2.0.8 ; https://react-hook-form.com/
