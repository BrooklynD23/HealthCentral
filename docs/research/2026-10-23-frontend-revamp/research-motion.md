# Motion library research for the HealthCentral frontend (2026-10-23)

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

Scope: research only, no repo edits. Versions and licences from `npm view` (run 2026-10-23). Every fact cites a URL; anything not reachable is marked **not verified**.

Constraints applied: no runtime CDN or telemetry, permissive licence, prefers-reduced-motion with a calm fallback, transform/opacity only, INP <= 200 ms (web.dev), CLS ~0.

## 1. Motion (successor to framer-motion)

- npm: `motion` 14.6.0, MIT, peers `react ^18.0.0 || ^19.0.0`, unpacked 895 KB (`npm view motion`). `framer-motion` latest on npm is also 14.6.0, MIT, same peers (`npm view framer-motion`). The upgrade guide says to move to `motion`.
- Upgrade path: `npm uninstall framer-motion && npm install motion`, then change imports from `"framer-motion"` to `"motion/react"`. Source: https://motion.dev/docs/react-upgrade-guide
- Breaking changes from v10/v11 per the guide: v11 changed `getVelocity()` timing for same-block value updates and moved the post-mount render to a microtask (Jest tests may need an animation-frame await). v10 removed the `whileInView` IntersectionObserver fallback (needs polyfill for old browsers) and made `AnimatePresence exitBeforeEnter` throw (use `mode="wait"`). v12 and v14 have no breaking changes for Motion for React. v13 made `@emotion/is-prop-valid` required (matters only for styled-components/emotion users). Source: https://motion.dev/docs/react-upgrade-guide
- React 18: the peer range includes 18 (npm). The guide does not list React 18 as a change; it says framer-motion 7 made react@18 the minimum. Source: same guide.
- Bundle: the full `motion` cannot go below ~43 KB; `m` plus `LazyMotion` gives an initial render just over 5 KB. `domAnimation` adds ~24 KB, `domMax` ~38 KB (drag and layout). `LazyMotion strict` throws if a `motion` component is used inside it. Source: https://motion.dev/docs/react-reduce-bundle-size. Note the docs show the `m` import as `motion/react-m`.
- `useReducedMotion()` returns a boolean that updates when the setting changes. It only reports; the component decides what to do. Source: https://motion.dev/docs/react-use-reduced-motion
- `MotionConfig reducedMotion`: `"user"` follows the OS setting, `"always"` forces it on, `"never"` (default) ignores it. When active, transform and layout animations are disabled but opacity and backgroundColor keep running. Source: https://motion.dev/docs/react-motion-config. This is the calm fallback we want: opacity-only motion survives.
- Spring API (https://motion.dev/docs/react-transitions): `type: "spring"`; `stiffness` (default 1), `damping` (10), `mass` (1), `velocity`, `bounce` (0.25, range -1..1), `duration`, `visualDuration` (seconds, overrides `duration`), `restSpeed` (0.1), `restDelta` (0.01). Setting `stiffness`, `damping` or `mass` overrides `bounce` and `duration`. Tween default duration 0.3 s (0.8 s with keyframes). Named eases include `easeOut`, `circOut`, `backOut`, `anticipate`; arrays are cubic-bezier.
- Layout: `layout` prop animates size and position changes caused by a React render, measured and applied with transforms. Layout changes must come from `style` or `className`, not `animate`. `layoutId` shares one element across mounts (wrap with `AnimatePresence` for exits). `LayoutGroup` syncs siblings that did not re-render. Border changes defeat the transform optimisation. Source: https://motion.dev/docs/react-layout-animations. Reduced-motion behaviour of `layout`: **not verified** on that page; `MotionConfig` disables transform and layout animations under "user".
- Tailwind fit: good. Motion sets inline `transform` and `opacity`; Tailwind utilities for layout and colour still work. Avoid animating Tailwind's `transition-*` classes on the same element.
- Risks: large surface; v10 to v14 is a multi-version jump; `layout` re-measures on render, so it can cost CPU on long lists; the docs' React 18 coverage is implicit (peer range only).

## 2. GSAP

- npm: `gsap` 3.15.0 (3.14.2 also exists). Licence string: "Standard 'no charge' license" (https://gsap.com/standard-license). Unpacked ~6.3 MB (includes all plugins; tree-shake by importing only what you use).
- Licence terms (https://gsap.com/standard-license, effective 2025-04-30, last modified 2025-05-30): free for commercial use. Former members-only plugins (SplitText, MorphSVG and others) are included. Permitted use covers any website, web app or digital interface, by any person or company. No attribution is required, but proprietary notices must not be removed. Prohibited: building GSAP into no-code animation tools that compete with Webflow's animation builder without written consent; reverse engineering to build competing products. Webflow keeps IP; GSAP's licence overrides Webflow's ToS where they conflict. The page does not explicitly address internal or SaaS use, but web app use is within Permitted Uses. Not legal advice (the page says so too). ScrollSmoother's inclusion is implied by "all of GSAP", not stated per plugin.
- `@gsap/react` 2.1.2, peers `gsap ^3.12.5`, `react >=17`; licence "SEE LICENSE AT https://gsap.com/standard-license" (npm). This means React 18 is inside the declared peer range. Source for hook: https://gsap.com/resources/React/
- `useGSAP(callback, depsOrConfig)`: config has `dependencies`, `scope` (a ref, so selectors are scoped), `revertOnUpdate`. Uses `gsap.context()` internally to revert on unmount. Animations created later (click handlers, timeouts) need `contextSafe()`. Strict Mode double-runs effects, which the hook handles. Register with `gsap.registerPlugin(useGSAP)`. Source: https://gsap.com/resources/React/
- Reduced motion: GSAP has no built-in policy. Use `gsap.matchMedia()` or check `prefers-reduced-motion` yourself. **Not verified** against docs in this pass.
- Risks: the licence has an unusual redistribution clause (no competing no-code tools) and changes can be made by Webflow. Lots of power (timelines, ScrollTrigger) that a small app does not need. Bundle is larger than needed unless tree-shaken.

## 3. react-spring

- npm: `react-spring` 10.0.4, MIT, peers `react ^16.8 || ^17 || ^18 || ^19`. Unpacked 7 KB (wrapper; the real code is in `@react-spring/*`). Installing the wrapper pulls the web and core packages.
- Docs (https://www.react-spring.dev/) list bundle sizes of 55.1 KB (react-spring), 19.2 KB (web), 15.2 KB (core), gzip not specified. Hooks shown: `useSpring`. `useTransition` and `useSprings` appear in the API but were not confirmed on the landing page. Reduced-motion support: **not verified** (not on the landing page).
- Fit: works with Tailwind (animate inline style values). Physics is similar to Motion springs but Motion is the stronger ecosystem now. Risks: a second physics system alongside Motion would duplicate concepts.

## 4. AutoAnimate (@formkit/auto-animate)

- npm: `@formkit/auto-animate` 0.10.0, MIT, unpacked 59 KB, no peers declared.
- API: `autoAnimate(parent, options?)` returns `{ enable(), disable() }`; React: `useAutoAnimate` from `@formkit/auto-animate/react` returns a ref. Animates immediate children when added, removed or moved. Source: https://auto-animate.formkit.com/
- Reduced motion: respects `prefers-reduced-motion` and disables itself. Source: https://auto-animate.formkit.com/ . Bundle size on the page: not stated (npm unpacked 59 KB is the only number). Which properties it animates: not stated on the page.
- Fit: best for list add/remove/reorder with zero config. Not a timeline tool.

## 5. Rive (@rive-app/react-canvas)

- npm: `@rive-app/react-canvas` 4.37.1, MIT, peers `react ^16.8 || ^17 || ^18 || ^19`, unpacked 49 KB (JS wrapper). `@rive-app/canvas` 2.45.1 MIT, unpacked 5.8 MB (includes the WASM runtime, so runtime size is in the wrapper and the core package). `@rive-app/react-canvas-lite` 4.37.1 MIT also exists.
- Docs (https://rive.app/docs/runtimes/react/react): the page covers `@rive-app/react-webgl2`, not react-canvas. `src` takes a local path or a hosted URL; the docs' examples use a `cdn.rive.app` URL. Whether the runtime fetches WASM from a CDN at runtime: **not verified**. For a local-first app the `.riv` file must be bundled locally, and the WASM must be served locally (check the runtime's `locateFile` option before adopting).
- Reduced motion: state-machine driven; depends on your inputs. **Not verified**.
- Risks: needs a designer to author `.riv` files; a hosted `.riv` URL would violate the no-CDN rule. Good for hero illustrations and stateful micro-interactions, not for data.

## 6. lottie-react / dotLottie

- `lottie-react` 3.1.2, MIT, peers `react ^18.2 || ^19`, unpacked 367 KB (npm). Wraps `lottie-web` 5.13.0, MIT, unpacked 25 MB (includes all builds).
- `@lottiefiles/dotlottie-react` 0.20.0, MIT, peers `react ^17 || ^18 || ^19`, unpacked 530 KB. `@lottiefiles/dotlottie-web` 0.81.0, MIT, unpacked 7.4 MB (WASM-based).
- Lottie JSON files are local assets; check the dotLottie player's WASM loading (locally served by default is typical, **not verified** here). Reduced motion: manual (pause the animation when `prefers-reduced-motion` matches). **Not verified** on docs.
- Fit: good for after-effects-style illustrations (empty states, onboarding). Heavy for micro-interactions. Not for chart entrances.

## 7. Theatre.js

- `@theatre/core` 0.7.2, Apache-2.0, unpacked 903 KB (npm). `@theatre/studio` 0.7.2, **AGPL-3.0-only**, unpacked 22 MB, peers `@theatre/core *` (npm). The studio is a dev-time editor, so it must not ship in the production bundle if the AGPL matters for this app.
- Docs (https://www.theatrejs.com/): a motion design toolset (sequence editor, graph editor, easing presets) that just changes JS variables. The licence text on that page: not stated; the npm licence fields above are the verified source.
- Risks: effectively a timeline authoring tool for 3D or scenes. For a health app's UI it adds nothing a Motion timeline does not. Recommend not adopting.

## 8. anime.js v4

- npm: `animejs` 4.5.0, MIT, peer `three >=0.150` (optional, for Three.js adapter), unpacked 2.1 MB (npm). Earlier 4.4.1 unpacked 1.9 MB.
- Docs (https://animejs.com/documentation/): v4 has `animate`, `createTimeline` (timeline API is listed as `add`, `set`, `sync`, `call`), `stagger`, `spring` easing and a WAAPI section (`waapi.convertEase`). A "Using with React" page exists in the nav; its content was **not verified** (not fetched). Bundle size on the docs: not stated; the docs page returned mostly navigation. Reduced motion: **not verified**.
- Risks: a second library, similar capability to Motion. Not needed.

## 9. Platform APIs

### View Transitions API (same-document)
- Use `document.startViewTransition(() => updateDOM())`, with a guard for unsupported browsers. Browser versions per Chrome docs: Chrome and Edge 111+, Firefox 144, Safari 18. Source: https://developer.chrome.com/docs/web-platform/view-transitions . Release dates per browser: not given there.
- Reduced motion: the React Router guide shows a CSS override that sets `animation: none !important` on `::view-transition-*` under `prefers-reduced-motion: reduce`. Source: https://reactrouter.com/how-to/view-transitions
- React Router 7 support: the legacy `viewTransition` prop on `<Link>`/`<NavLink>` and the `navigate(path, { viewTransition: true })` option are **deprecated** in favour of React's own `<ViewTransition>` component, which requires **React and React DOM 19.3 or later**. The legacy prop still works with older React versions. Do not enable both. Back/forward (popstate) navigations skip transitions. Source: https://reactrouter.com/how-to/view-transitions
- npm: `react-router` 8.5.0 (latest) requires `react >=19.2.7`, so it is not an option on React 18. Use React Router 7.x (latest `7.18.4`, peers `react >=18`) and the legacy `viewTransition` prop on React 18. Verified via `npm view react-router@7` and `npm view react-router@8.5.0`.

### CSS `@starting-style` and `transition-behavior`
- `@starting-style` defines the start values for elements entering the DOM or leaving `display: none`. MDN: Baseline 2024 "Newly available" (works across latest browsers since August 2024; older versions may not). No per-browser versions on the page. Source: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@starting-style
- `transition-behavior: allow-discrete` lets `display` and `overlay` transition. Its support status: **not verified** (MDN compatibility table did not render in the fetch). Check https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transition-behavior before relying on it.
- Use: enter/exit for simple overlays and popovers with no JS. Pair with a fallback (the element just appears when unsupported).

## 10. Recommendation

Primary library: **Motion** (`motion`, `motion/react`, `LazyMotion` + `m`, `MotionConfig reducedMotion="user"`). Same mental model as Framer Motion, small with `m`, MIT, React 18 in its peer range, and it can express all the spring and layout behaviour needed.

Specialist (at most one): **AutoAnimate** for list add/remove/reorder (MIT, 59 KB, reduced-motion aware, zero config). It is optional; skip it if Motion's `layout` covers the list cases.

Do not adopt: GSAP (licence is free but restrictive on redistribution, and it is a second engine), react-spring (duplicates Motion), Theatre.js (AGPL studio), anime.js v4 (duplicates Motion), Rive/Lottie unless a designer supplies assets, and React Router `viewTransition` on React 18 beyond the legacy prop.

Use per job:
- Page transitions: the View Transitions API via the legacy React Router `viewTransition` prop (React 18), with a `prefers-reduced-motion` CSS override. Fall back to a Motion opacity fade when unsupported.
- List and layout animations: Motion `layout` and `layoutId` inside `LayoutGroup`; AutoAnimate only for simple lists.
- Micro-interactions (hover, press, toggle): Motion `whileTap`/`whileHover` gated on `(hover: hover) and (pointer: fine)`, plus CSS `transition` on Tailwind classes for colour changes.
- Number count-ups on lab values: Motion `animate()` on a MotionValue with `useMotionValue` and `useTransform` to a formatted text node (opacity and text only, no layout). Under reduced motion, set the final value immediately (verify `MotionConfig` behaviour in code first, since text tweens are not transforms).
- Chart entrances: CSS or Motion opacity plus a `transform` `scaleY` on bars (origin bottom), one pass on first view via IntersectionObserver. Do not animate SVG `width` or `d` path attributes on the main thread for big datasets.

## 11. Motion tokens (proposal)

Sources for the values: Emil Kowalski's review-animations standards in his public skills repo (verified by fetch of the raw file on GitHub): https://raw.githubusercontent.com/emilkowalski/skills/main/skills/review-animations/STANDARDS.md . Those numbers match the community-published summaries (not independent). Motion defaults and spring options: https://motion.dev/docs/react-transitions . Linear and Vercel-specific tokens: **not verified** (no primary source fetched).

Easing (CSS and Motion):
- `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)` for UI entering or exiting (Motion: `ease: [0.23, 1, 0.32, 1]`).
- `--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1)` for elements moving on screen.
- Never `ease-in` on UI. `linear` only for constant motion (progress, marquee). `ease` for colour and hover changes.

Durations (ms), from the same standards file:
- Press feedback: 100-160
- Tooltips and small popovers: 125-200
- Dropdowns and selects: 150-250
- Modals and drawers: 200-500
- Page transitions: 250-400 (proposal, not in source)
- Default UI ceiling: under 300

Springs (Motion, for physical motion such as drag release and sheet snaps; defaults from the Motion docs):
- `snappy`: `{ type: "spring", visualDuration: 0.25, bounce: 0.15 }`
- `gentle`: `{ type: "spring", visualDuration: 0.4, bounce: 0.1 }`
- `sheet`: `{ type: "spring", stiffness: 380, damping: 36, mass: 1 }` (proposal; tune in review)

Reduced motion:
- Keep opacity and colour changes, remove transform movement. Reduced motion means fewer and gentler animations, not zero.
- Implement with `MotionConfig reducedMotion="user"` and a CSS `@media (prefers-reduced-motion: reduce)` block for View Transitions and Tailwind `motion-safe:`/`motion-reduce:` variants.

Performance rules: animate only `transform` and `opacity`, under INP 200 ms (https://web.dev/articles/inp), and avoid layout-triggering properties (https://web.dev/articles/animations-guide). CLS target: no animation that shifts layout (use transform for entrances, reserve space for count-ups and charts).

## Unverified or failed fetches

- Linear, Vercel motion guidelines: not fetched; no primary source.
- animations.dev (Emil): returned summary only, no numbers; not used.
- Motion: per-API reduced-motion behaviour of `layout`/`layoutId`; React 18 explicit statement (only the peer range).
- GSAP `@gsap/react` React version range (only peer range from npm).
- Rive WASM and CDN behaviour; Rive size beyond npm unpacked numbers.
- Lottie/dotLottie runtime fetch behaviour; reduced motion.
- react-spring reduced motion; AutoAnimate bundle size and animated properties.
- Theatre.js licence text on its site (npm licence fields used instead).
- anime.js v4 React page and bundle size.
- `transition-behavior` browser support.
