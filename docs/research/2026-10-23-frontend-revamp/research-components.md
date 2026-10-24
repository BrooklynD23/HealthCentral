# UI component sources: research for a local-first health app revamp

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

Date of research: 2026-10-23. Stack: React 18.2, Vite 7, Tailwind v4, framer-motion 10, Radix primitives, lucide.
Constraints: no runtime CDN/remote fonts/telemetry; WCAG 2.2 AA; prefers-reduced-motion; permissive licences only.

Method: npm data from `https://registry.npmjs.org/<pkg>` (latest dist-tag, peerDependencies, license). The `modified` field is the packument's last-modified time, used here as a proxy for last activity, not a strict "last release" date. Site claims come from WebFetch of the official site. Anything I could not confirm is marked **not verified**.

Two names I first guessed were wrong and I dropped them: npm `morphin` (2022, MIT, lodash deps) and npm `bencho` (0.2.0, a CLI benchmarking tool) are unrelated to the products. npm `magic-ui`, `origin-ui` and `aceternity-ui` are also not the official packages (`magic-ui` and `origin-ui` are unrelated; `aceternity-ui` 0.2.2 is an unofficial third-party CLI, not verified as official).

---

## 1. Morphin (morphin.dev)

- **What:** "production-ready motion UI patterns, micro-interactions, and polished React components" for product interfaces: buttons, sliders, cards, charts, pricing sections, page transitions. Component titles mention React, Tailwind CSS, shadcn/ui, Framer Motion, GSAP, Three.js. https://morphin.dev
- **Pro gating:** Yes, partly. Some listings carry a "PRO" label, others do not. The page says "Upgrade for full access to all features" with a "Get Pro" link to /pricing. Price not stated on the page. https://morphin.dev
- **Free-tier licence:** **not verified.** The page links to Terms & Conditions, which I did not read.
- **Install model:** **not verified.** No install instructions were on the page.
- **Verdict:** Not a candidate until its licence is read. Pro gating plus unknown licence fails the "permissive licences only" rule.

## 2. Bencho (bencho.dev)

- **Catalogue:** 137 blocks, described as "A library of interactive React components and micro-interactions you can explore and take straight into your projects." Blocks are tagged by interaction type (Press, Hover, Drag, Loading, Type, Select, Swipe, Slide, Loop); no categories are named. https://bencho.dev
- **Source shown?** The page says "Every block on Bencho is a React component you paste into your own project," so the model is copy-paste. Whether full source is visible on each block page was **not verified**.
- **Licence:** **not stated** on the site. **Not verified.**
- **MCP server:** The site confirms one exists: "Ask your AI assistant for a block and it pastes the real component into your project." https://bencho.dev/mcp. The install command and the list of tools it exposes are **not verified**; the site has no setup docs I could reach (https://bencho.dev/docs returned no setup content).
- **Verdict:** Excluded. The licence is unknown and the catalogue cannot be vetted from the site.

## 3. Libraries.dev (libraries.dev)

Install names are from the site FAQ ("Install any of them with `npm install border-beam`, `thinking-orbs`, `liquid-gooey`, `metal-fx` or `img-fx`") and from the npm registry. All five are MIT. https://libraries.dev/

| Package | Version (latest) | Licence | Peer range | Runtime deps | Unpacked size (registry, not gzip) | Last activity (packument) |
|---|---|---|---|---|---|---|
| `border-beam` | 1.4.1 | MIT | react >=18.0.0, react-dom >=18.0.0 | none | 198,683 B | 2026-09-22 |
| `thinking-orbs` | 0.3.2 | MIT | react >=18.0.0 only | none | 130,686 B | 2026-09-22 |
| `liquid-gooey` | 0.2.2 | MIT | react >=18, react-dom >=18 | none | 745,911 B | 2026-09-22 |
| `metal-fx` | 2.0.11 | MIT | react >=18.0.0, react-dom >=18.0.0 | none | 303,406 B | 2026-09-22 |
| `img-fx` | 0.5.1 | MIT | react >=18.0.0, react-dom >=18.0.0, **three >=0.149.0** | none | 206,723 B | 2026-09-04 |

Sources: https://registry.npmjs.org/border-beam, https://registry.npmjs.org/thinking-orbs, https://registry.npmjs.org/liquid-gooey, https://registry.npmjs.org/metal-fx, https://registry.npmjs.org/img-fx

- **Gzipped size:** The site gives only one figure: "All five together weigh about 83 KB gzipped" (https://libraries.dev/). Per-package gzip sizes are **not stated / not verified**.
- **React 18:** The site says "React 18 or newer" and the peer ranges allow 18. No React 19 claim is made. Works on 18 by peer range; I did not run it.
- **Reduced motion (from package READMEs):**
  - `border-beam`: pulse types ship a built-in `prefers-reduced-motion: reduce` block; rotate types "respect `prefers-reduced-motion` when implemented by the consumer", so you must wire it for rotate types. https://registry.npmjs.org/border-beam
  - `thinking-orbs`: reduced motion renders a static frame. https://registry.npmjs.org/thinking-orbs
  - `liquid-gooey`: transitions collapse to instant snaps under reduced motion. https://registry.npmjs.org/liquid-gooey
  - `metal-fx`, `img-fx`: reduced motion **not mentioned** in README. Not verified.
- **Pro:** The site says "Pro adds skills that teach your agent each library's full parameter vocabulary" (https://libraries.dev/). Whether the five component packages are fully free was not stated separately. A separate npm package `libraries-dev` 0.1.2 (MIT) installs the agent skill; not evaluated.
- **Local-first (fonts/CDN/analytics):** not checked against the built pages. Not verified.
- **Note:** `img-fx` pulls in `three` as a peer, which is a heavy addition.

## 4. Aceternity UI (ui.aceternity.com)

- **Licence:** **Custom, not permissive.** The licence page describes "an ongoing, non-exclusive, worldwide license." It allows "unlimited end products" and commercial sale, but forbids redistributing the item as stock or source files and forbids creating templates/derivatives for marketplaces. https://ui.aceternity.com/licence. Fails "permissive licences only".
- **Model:** Copy-paste, installed "with the shadcn CLI". MCP setup documented at /docs/cli#mcp-server. https://ui.aceternity.com
- **Dependencies:** "built with React, Tailwind CSS and Motion." No versions stated; React 19 requirement not stated. https://ui.aceternity.com
- **Verdict:** Excluded on licence grounds. Good visual inspiration only.

## 5. Other libraries

### Magic UI
- Copy-paste model: "a collection of re-usable components that you can copy and paste into your web apps." Source on GitHub. Licence **not stated** on the docs page; **not verified** (did not check the GitHub LICENSE). Paid "Pro templates" exist. https://magicui.design/docs
- npm: no official package found. `magicui-cli` (0.1.6, MIT, 2024-07-08) exists but its official status is **not verified**.
- Verdict: Not in shortlist (licence unverified, install model unclear).

### shadcn/ui
- Copy-paste via CLI into your repo. Registry CLI `shadcn` 4.22.1, MIT, peer none (https://registry.npmjs.org/shadcn).
- Tailwind fit: official docs say "Only new projects start with Tailwind v4 and React 19." "Your existing apps with Tailwind v3 and React 18 will still work," and "new components stay on Tailwind v3 and React 18 until you upgrade." So Tailwind v4 + React 18 is **not** the documented path. https://ui.shadcn.com/docs/tailwind-v4
- React 19 changes: forwardRef removed and `data-slot` attributes added; migration needed to keep React 18 compatibility. https://ui.shadcn.com/docs/tailwind-v4
- **Flag: React 19 required for the documented v4 path.** On React 18 you must hand-port.

### Origin UI
- originui.com now 301-redirects to coss.com/ui, which describes "coss ui", "a new, modern UI component library built on top of Base UI." https://coss.com/ui. Origin UI's licence and install model are **not verified** after the redirect.
- npm `origin-ui` is an unrelated Vue 2 package. Not verified as the source.

### Radix Themes vs Radix primitives
- **Radix Themes** `@radix-ui/themes` 3.3.0, MIT, peer react `16.8 || ^17 || ^18 || ^19`, deps include `@radix-ui/colors` and `radix-ui`; unpacked 4.9 MB. Install: `npm install @radix-ui/themes`; must import `@radix-ui/themes/styles.css` globally. https://www.radix-ui.com/themes/docs/overview/getting-started, https://registry.npmjs.org/@radix-ui/themes
- **Radix primitives** `radix-ui` 1.8.1, MIT, peer react `^16.8 || ^17 || ^18 || ^19`. Unstyled. https://registry.npmjs.org/radix-ui
- Radix Themes ships its own styles, so it clashes more with a Tailwind v4 design system. Primitives are the better fit since Radix is already in the stack. Theming/font defaults in Themes: **not verified**.

### React Aria Components
- `react-aria-components` 1.22.1, **Apache-2.0**, peer react `^16.8 || ^17 rc || ^18 || ^19 rc`. Deps: `react-aria` 3.53.1, `react-stately` 3.51.0, `@react-types/shared`, `@internationalized/date`, `use-sync-external-store`; unpacked 6.9 MB; last activity 2026-10-09. https://registry.npmjs.org/react-aria-components
- Accessibility (vendor claims): "React Aria is designed with accessibility as a top priority"; "extensively tested using many popular screen readers and devices"; follows the W3C ARIA APG (https://react-aria.adobe.com/). These are vendor claims, not an independent audit.
- Model: unstyled, npm install. Tailwind fit: good (you style the classes).

### Ark UI
- `@ark-ui/react` 5.39.3, MIT, peer react `>=18.0.0` and react-dom `>=18.0.0`, built on Zag.js (`@zag-js/*` 1.45.0). Unpacked 3.3 MB; last activity 2026-10-06. https://registry.npmjs.org/@ark-ui/react
- Ark's own docs pages returned 404 on the URLs I tried; site claims **not verified**.
- Park UI (built on Ark) uses Panda CSS, not Tailwind: its installation page says "ensure that your Panda project is set up," and it installs with `npx @park-ui/cli init` / `npm install @ark-ui/react lucide-react`. Its Tailwind plugin `@park-ui/tailwind-plugin` 0.20.1 declares peer `tailwindcss 3.x`. https://park-ui.com/docs/installation, https://registry.npmjs.org/@park-ui/tailwind-plugin. **Park UI is a poor fit for Tailwind v4.**

### HeroUI
- `@heroui/react` 3.2.6, MIT, peer **react >=19.0.0**, tailwindcss >=4. https://registry.npmjs.org/@heroui/react
- **Flag: needs React 19.** Not usable on the current React 18.2 stack without an upgrade. Site install page returned 404; not verified there.

### Untitled UI (found by search, not verified)
- Dashboard templates built on React Aria Components and Tailwind v4 per vendor pages (e.g. https://www.untitledui.com/react/components/dashboards/dashboard-05). Licence and commercial terms **not verified**. Mentioned for completeness only.

### Animation dependency
- `motion` 14.6.0 and `framer-motion` 14.6.0, both MIT, peers `react ^18.0.0 || ^19.0.0`. Last activity 2026-10-22. https://registry.npmjs.org/motion, https://registry.npmjs.org/framer-motion
- The app pins framer-motion 10; 14.x is a major jump to check.
- `tailwindcss` 4.3.3, MIT. https://registry.npmjs.org/tailwindcss
- `lucide-react` 1.61.0, **ISC**, peer react `^16.5.1 || ^17 || ^18 || ^19`. https://registry.npmjs.org/lucide-react

---

## Comparison table

| Source | Best for | Licence | Install | React 18 | Tailwind v4 fit | A11y quality | Bundle cost | Local-first risks | Last activity |
|---|---|---|---|---|---|---|---|---|---|
| Morphin | Motion patterns | Pro-gated, free-tier licence not verified | not verified | not verified | not verified | not verified | not verified | not verified | not verified |
| Bencho | Block library + MCP | not stated | copy-paste + MCP | not verified | not verified | not verified | not verified | not verified | not verified |
| Libraries.dev (5 pkgs) | Decorative effects | MIT | npm | yes (peer >=18) | fine (CSS/SVG/WebGL, decorative) | decorative, pointer-events none; reduced motion partial | ~83 KB gz for all five; img-fx needs three | not verified | 2026-09 |
| Aceternity UI | Visual inspiration | custom, not permissive | copy-paste (shadcn CLI) | not stated | yes | not verified | depends on Motion | MCP setup | not verified |
| Magic UI | Copy-paste effects | not stated | copy-paste | not verified | not verified | not verified | not verified | not verified | not verified |
| shadcn/ui | Copy-paste base components | MIT | CLI copy-paste | **v4 path expects React 19** | yes (v4 path) | Radix-based | small | none | 4.22.1 |
| Origin UI | not verified | not verified | not verified | not verified | not verified | not verified | not verified | redirects to coss.com | not verified |
| Radix Themes | Styled kit | MIT | npm + global CSS | yes (peer 18) | conflicting styles | Radix-based | 4.9 MB unpacked | not verified | 2026-01 |
| Radix primitives | Headless base | MIT | npm | yes | yes (unstyled) | good | small | none | 2026 |
| React Aria Components | Headless, a11y-first | Apache-2.0 | npm | yes (peer 18) | yes (unstyled) | strongest claims (vendor) | 6.9 MB unpacked | none | 2026-10 |
| Ark UI | Headless (Zag) | MIT | npm | yes (peer >=18) | yes (headless) | not verified | 3.3 MB unpacked | none | 2026-10 |
| HeroUI | Styled kit | MIT | npm | **no (peer >=19)** | yes | not verified | not verified | not verified | 2026-09 |
| Park UI | Panda-based | MIT | CLI + npm | yes | **no (Panda; plugin v3)** | not verified | not verified | not verified | 2025-11 |
| Untitled UI | Dashboard templates | not verified | CLI / copy | not verified | claims v4 | claims RAC (vendor) | not verified | not verified | not verified |

## Ranked shortlist for this app

1. **Radix primitives (`radix-ui` 1.8.1, MIT, React 18 peer)**: already in the stack; keep the existing components and style them with Tailwind v4 classes; lowest migration risk.
2. **React Aria Components (`react-aria-components` 1.22.1, Apache-2.0, React 18 peer)**: strongest accessibility claims, for complex widgets (combobox, date fields) where Radix is weaker; add only where needed.
3. **Motion (`motion` 14.6.0, MIT, React 18 peer) with libraries.dev `border-beam` (1.4.1, MIT, zero deps)**: motion via Motion's reduced-motion hook; border-beam for decorative accents only, with reduced motion wired manually for its rotate types.
4. **Ark UI (`@ark-ui/react` 5.39.3, MIT, React >=18 peer)**: headless fallback if React Aria Components is ruled out; a state-machine base that works with Tailwind v4 (not Park UI).

Excluded: Aceternity (custom licence), Morphin (Pro-gated, licence unverified), Bencho (licence unverified), HeroUI (requires React 19), Park UI (Panda/Tailwind v3), shadcn/ui (v4 path expects React 19; use only with manual porting).

## Not verified (open items)

- Morphin, Bencho, Magic UI, Origin UI licences and install models.
- Bencho MCP install command and tool list.
- Per-package gzipped sizes for libraries.dev (only the 83 KB total is stated).
- Reduced-motion behaviour of `metal-fx` and `img-fx`.
- Telemetry/CDN/remote-font checks on built output for every library. Method: build a sample and grep for remote URLs and analytics scripts.
- Ark UI's own website claims (its docs URLs returned 404).
- Independent accessibility audits of any library; all a11y statements above are vendor claims.
