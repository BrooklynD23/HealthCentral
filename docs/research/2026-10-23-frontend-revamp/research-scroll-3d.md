# Scroll and 3D/GPU options for the HealthCentral frontend (research, 2026-10-23)

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

Scope: research only, no repo edits. npm data from `npm view` / `npm pack` run on 2026-10-23. Items marked "not verified" could not be confirmed from a primary source in this pass.

## Recommendation

- **Scroll:** Motion (`motion/react`) `useInView` / `useScroll` only, with IntersectionObserver-style triggers for reveals. Do not add Lenis to the app shell. Add native CSS scroll-driven animations only as a progressive enhancement for marketing-style decoration (`@supports`), because Firefox is not shipped.
- **3D:** None in the app. If leadership wants one "wow" moment, use a static illustration or an SVG body map. If a real 3D scene is later required, use plain three.js, lazy-loaded, with a static poster fallback. Do not adopt Spline (see below).
- **Trade-off (scroll):** Motion adds an animation runtime but keeps scroll native, which is better for keyboard, zoom and screen-reader users in a data-dense app. Lenis gives a smoother marketing feel at the cost of hijacking native scroll.
- **Trade-off (3D):** A 3D scene costs GPU, battery and bundle (three.js is roughly 417 KB gzipped for the two main modules), and low-end laptops without a GPU gain nothing a health record needs.
- **Trade-off (Spline):** Easy authoring, but the runtime bundle hard-codes remote CDN hosts, which violates the no-runtime-CDN constraint without patching.

## Scroll

### Lenis (`lenis`, React wrapper at `lenis/react`)
- npm: `lenis@1.3.27`, license MIT, peer `react >=17`. Source: https://www.npmjs.com/package/lenis (npm registry, `npm view lenis`). Repo: https://github.com/darkroomengineering/lenis (MIT © darkroom.engineering, verified by fetch).
- Size (measured from the npm tarball): `dist/lenis.mjs` 8.2 KB gzipped, `dist/lenis-react.mjs` 1.7 KB gzipped.
- Reduced motion: README says "By default, Lenis honors the user's prefers-reduced-motion setting"; smoothing is turned off and programmatic scrolls jump. Opt-out is `respectReducedMotion: false`, which the README says is not recommended (verified: https://github.com/darkroomengineering/lenis). Motion.dev says the default began at 1.3.26 (secondary source: https://motion.dev/docs/lenis).
- Accessibility concern (judgment, not from a cited source): Lenis replaces native wheel/touch scrolling with a JS-driven loop. That can disturb zoom, trackpad momentum, sticky/nested scroll containers and screen-magnifier users. WCAG 2.3.3 (Animation from Interactions, AAA) and 2.2.2 (Pause, Stop, Hide) are the relevant criteria: https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html (URL not fetched in this pass).
- App shell: not recommended. An app shell has nested scroll panes (lists, tables, chat), and Lenis is designed for a single document scroller. Whether it can wrap a nested pane cleanly was not verified.
- Performance: requires either `autoRaf: true` or a manual `lenis.raf(time)` loop (verified: README troubleshooting section). Adds per-frame work on low-end laptops.
- React 18: peer accepts React 17+, so React 18 fits (npm peer data).
- Offline / local-first: pure JS, no network. Fine.

### GSAP ScrollTrigger (`gsap@3.15.0`, `@gsap/react@2.1.2`)
- License: GreenSock "Standard No Charge" license, https://gsap.com/standard-license (verified by fetch). Free for commercial use; covers ScrollTrigger and all plugins (Webflow ownership). Restrictions: no "Prohibited Uses" (visual animation builders that compete with Webflow), no reverse-engineering to build competing products. It does not explicitly address redistribution inside a sold product (verified). Note: the license is not an OSI permissive licence, which may matter for the "permissive licences" constraint. Not decided here.
- npm: `gsap@3.15.0` license string "Standard 'no charge' license"; `@gsap/react@2.1.2` peer `gsap ^3.12.5`, `react >=17` (npm view).
- Size: the npm tarball is 1.7 MB gzipped, but that includes all plugins and sources; the core-only gzipped size was not measured in this pass.
- Reduced motion: GSAP does not handle it automatically; `gsap.matchMedia()` is needed (not verified from a fetched page in this pass).
- Verdict: capable, but adds a second animation system next to Motion. Not needed if Motion covers the app.

### Native CSS scroll-driven animations (`animation-timeline: scroll()` / `view()`)
- MDN (last modified Sep 16 2026, verified by fetch: https://developer.mozilla.org/en-US/docs/Web/CSS/animation-timeline): status "Limited availability. This feature is not Baseline because it does not work in some of the most widely-used browsers." The per-browser table was not in the fetched text (cut at 100k chars); caniuse was not usable through WebFetch.
- Firefox: a Mozilla Connect thread says it is behind a preference and in progress (https://connect.mozilla.org/t5/discussions/why-doesn-t-firefox-support-the-css-animation-timeline/m-p/63761). Secondary guide says Firefox is stable-but-flagged and on the Interop 2026 list (https://www.drweb.de/css-scroll-animationen-ohne-javascript/). Treat Firefox as unsupported until MDN's table is checked.
- Chrome/Edge since 2023; Safari since Sep 2025 (secondary source: drweb guide). Not verified against Apple or caniuse.
- Usage: wrap with `@supports (animation-timeline: scroll())` so unsupported browsers render unanimated content. Use `prefers-reduced-motion: reduce` to disable.
- Local-first / battery: compositor-friendly when animating transform/opacity; no JS.

### Motion `useScroll` / `useInView` (`motion@14.6.0`)
- npm: `motion@14.6.0`, MIT, peers `react ^18.0.0 || ^19.0.0` (verified via `npm view`). `framer-motion@14.6.0` is the same package under the old name.
- `useScroll({container, target, axis, offset, trackContentSize})` returns `scrollX`, `scrollY`, `scrollXProgress`, `scrollYProgress` motion values; motion values bypass React re-renders when used in styles (verified: https://motion.dev/docs/react-use-scroll). Without `trackContentSize`, values update on the next `scroll` event.
- `useInView`: the signature was not fetched (not verified in this pass). Use IntersectionObserver directly if needed; MDN docs for IntersectionObserver not fetched.
- Reduced motion: `useReducedMotion` exists in Motion's React API per my recollection, but not verified in this pass.
- Bundle: `motion` unpacked 895 KB; gzipped size not measured.
- Verdict: fits React 18, MIT, already the "one scroll approach" candidate.

### Aceternity UI (3D card / spotlight)
- Distribution: copy-paste components via the shadcn CLI (`npx shadcn@latest add @aceternity/card-spotlight`), sold in a paid All-Access bundle. Page footer links a "Licence" page whose content was not retrieved. No licence statement on the component page (verified: https://ui.aceternity.com/components/card-spotlight).
- A third-party listing (21st.dev) says Card Spotlight is MIT and the 3D Card Effect's licence is "unknown" (https://21st.dev/@manuarora700/components/card-spotlight, https://21st.dev/@manuarora700/components/3d-card-effect.md). Secondary, unverified.
- Dependencies: Motion for React (per the template note on the page), not separately listed for the card.
- Verdict: do not adopt for a health app. Licence unclear, paid, copy-paste maintenance burden, and the 3D card licence is unknown.

## 3D / GPU

### Canvas UI (DavidHDev)
- What it is: "A library of creative canvas components. Real HTML with WebGL effects running over it. React, Vue, Svelte, vanilla" (verified: https://github.com/DavidHDev/canvas-ui). Creator: David Haz, also known for React Bits (secondary source: https://www.infoq.com/news/2026/09/canvas-ui-webgl/).
- Licence: "MIT + Commons Clause" (verified by fetch). Commons Clause restricts selling the library itself. This fails the permissive-licence constraint on a strict reading.
- Install: source copied via shadcn registry (`npx shadcn@latest add @canvas-ui/liquid-react`), not an npm dependency.
- Browser: html-in-canvas components need Chrome with `chrome://flags/#canvas-draw-element` or an origin trial; other browsers fall back to a GPU overlay (verified).
- Verdict: not suitable (licence and experimental browser API).

### "VGPU by Vercel Labs"
- Real name: `vgpu`, repo https://github.com/vercel-labs/vgpu (verified). MIT. "A TypeScript library for WebGPU: typed shader imports, a tiny gpu-first API." Built on WebGPU; imports `.wgsl` files as typed modules.
- Latest release/version: not confirmed. The GitHub releases section was empty in the fetch; secondary sources conflict (v0.3.1 vs 0.5.0) and are not trusted.
- Local-first / no-GPU: requires WebGPU, so it does nothing on machines without a usable GPU. Not suitable as a baseline.
- Verdict: not relevant to this app. It is a shader toolkit, not a UI effect library.

### Spline (`@splinetool/react-spline@4.1.0`, `@splinetool/runtime@2.0.111`)
- npm: `@splinetool/react-spline@4.1.0` has no `license` field in `npm view`, peers `@splinetool/runtime *`, `next >=14.2.0`, `react *`, `react-dom *`. `@splinetool/runtime@2.0.111` has no licence field in `npm view` (not verified; check the package's LICENSE). Source: `npm view`.
- Size (measured from the tarball): runtime package is 18.9 MB gzipped including all WASM and per-feature chunks; the ESM entry `build/runtime.js` is 37 KB gzipped on its own and loads chunks and WASM at runtime (`hana-ui.wasm` 3.4 MB raw / 1.1 MB `.gz`).
- Self-hosting: Enterprise plan only for the official offline export (https://docs.spline.design/exporting-your-scene/web/exporting-as-self-hosted-project, verified). The open-source route is to download the `.splinecode` file and self-host it (react-spline README via secondary search, not fetched).
- **Network finding (from reading the package, version 2.0.111):** `build/runtime.cjs` contains default base URLs that resolve to remote hosts unless a path is passed: `https://cdn.spline.design/@splinetool/runtime@2.0.111/build`, `https://unpkg.com/@splinetool/runtime@2.0.111/build`, Draco decoder at `https://www.gstatic.com/draco/versioned/decoders/1.5.2/`, plus `apis.spline.design` and `relayserver.spline.design` endpoints. Passing a local base path may avoid the CDN calls; this was not verified at runtime. This violates "no runtime CDN" unless patched.
- Verdict: do not use. It is also the heaviest option measured.

### React Three Fiber, drei, three.js
- `@react-three/fiber` v9 (`9.8.2`, MIT) peers `react >=19 <19.4`, `react-dom >=19 <19.4` (verified: npm view; docs: https://r3f.docs.pmnd.rs/getting-started/introduction says "@react-three/fiber@9 pairs with react@19"). Not compatible with React 18.
- `@react-three/fiber` v8 (`8.18.0`) pairs with React 18 (docs). Use v8 if React 18 stays.
- `@react-three/drei`: `10.7.9` (MIT) peers React ^19 and fiber ^9. `9.122.0` peers React ^18, `three >=0.137`, fiber ^8 (verified: npm view). Use drei 9.x with fiber 8 on React 18.
- `three@0.186.1` (MIT). Gzipped: `build/three.module.js` 131 KB + `three.core.js` 286 KB (about 417 KB, before tree-shaking; measured from tarball). Plain three.js with a lazy-loaded chunk is the lightest real 3D option that stays on React 18.
- Local-first: all bundled from npm, no network. WebGL required; no-GPU laptops fall back to software rendering (slow, battery drain).
- Accessibility: canvas content is invisible to AT; provide text alternatives and `prefers-reduced-motion` handling. Not separately verified in this pass.

### OGL (`ogl@1.0.11`)
- Licence: Unlicense (public domain; verified: `npm view ogl license`). Repo: https://github.com/oframe/ogl. No peer dependencies.
- Size: npm tarball 92 KB gzipped (whole package; ESM core not separately measured). Lighter than three.js; less ecosystem.
- React 18: not needed; plain JS, use in a `useEffect` wrapper.
- Local-first: pure JS, no network. WebGL required.
- Verdict: good if a single tiny effect is ever needed; otherwise not worth the extra dependency.

## Answer: should a health app use 3D?

No, not in the dashboard, documents, lab results or chat. 3D adds GPU load, battery drain and bundle weight for no clinical or comprehension gain, and the target users may have no GPU. If a single moment is wanted (onboarding hero, body-map), prefer a static SVG/illustration with a text alternative; a body map is clearer and more accessible as SVG with keyboard-reachable regions than as a 3D model. If a real 3D scene is later mandated, use plain three.js (lazy-loaded, WebGL-capability check, static poster fallback, reduced-motion stop), not Spline or Canvas UI.

## Sources (all fetched or queried 2026-10-23 unless noted)
- npm registry: `npm view` for lenis, @gsap/react, gsap, motion, framer-motion, @splinetool/react-spline, @splinetool/runtime, @react-three/fiber, @react-three/drei, three, ogl
- https://github.com/darkroomengineering/lenis
- https://gsap.com/standard-license
- https://developer.mozilla.org/en-US/docs/Web/CSS/animation-timeline
- https://github.com/vercel-labs/vgpu
- https://github.com/DavidHDev/canvas-ui
- https://docs.spline.design/exporting-your-scene/web/exporting-as-self-hosted-project
- https://ui.aceternity.com/components/card-spotlight
- https://r3f.docs.pmnd.rs/getting-started/introduction
- https://motion.dev/docs/react-use-scroll
- Secondary (unverified): https://motion.dev/docs/lenis ; https://www.drweb.de/css-scroll-animationen-ohne-javascript/ ; https://connect.mozilla.org/t5/discussions/why-doesn-t-firefox-support-the-css-animation-timeline/m-p/63761 ; https://21st.dev/@manuarora700/components/card-spotlight ; https://www.infoq.com/news/2026/09/canvas-ui-webgl/
- Not fetched: https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html
- Not verified: caniuse table for scroll-driven animations (fetch returned no data); vgpu latest release; Spline runtime behaviour with a local base path.
