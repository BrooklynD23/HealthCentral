# Owner direction for the frontend revamp (2026-10-23, verbatim)

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

The owner's message, verbatim:

> continue with the post-merge batch. Then run an opus 5.5 high agent to review the current UI, delegate Haiku 5.5 agents to research new UI component libraries, motion libraries, scroll libraries, animation libraries. PLan a complete update for frontend, make it interactive. The idea is that our program for academic project is to simulate SWE (for report, check docs), or SaaS. Therefore, our frontend should be engaging, modern, active like how SaaS has smooth UI/UX experiences with animations & more enganging UI. Use these "[Component Upgrade Playbook]", "[3D Libraries for Vibecoders]", and that subagent should be running in comparison with another opus 5.5 agent that can compare their findings & opinions of frontend designs/revamped. Be ambitious, both follow skills of awwwwards/impeccable/emily kowalski design skills (research + install) and this guideline "[Ambitious Website Prompt for Claude Code]".

The three pasted guideline documents follow, verbatim.

---

## 1. Component Upgrade Playbook

Component Upgrade Playbook — audit & upgrade every component in your web app
Source: @anaav.y's reel "Ready-made animations that make your website addictive"
The reel tours three sites that ship ready-made animated components for
React, each designed to be consumed by an AI coding agent. This playbook
gives Claude Code the links, a component-by-component upgrade map, and a
master prompt that walks your whole app.
The three sources (verified)
Morphin — https://morphin.dev
   Premium animated React components & motion UI (React + Tailwind, GSAP-
   heavy): 3D bending image carousels, orbiting-glow buttons, page-fold
   navigation menus, stacked scroll cards with 3D tilt, dashboards and
   interactive charts. Each component page has a "Get code" documentation
   panel — the code is Pro-only, so without Pro it's a visual/motion
   reference to reimplement, not a copy source.
Bencho — https://bencho.dev
   130+ interactive React components and micro-interactions, browsable by
   gesture (hover / press / drag / type / loading / loop): image accordion,
   time scrubber, loaders, dynamic islands, magnetic dock, command bar,
   tilt cards, toasts, confetti, UI sounds. Every block shows its full
   source, and there is a Bencho MCP server — connect it and Claude
   Code can find and pull blocks itself.
Libraries.dev — https://libraries.dev
   Five high-craft effect libraries that each "ship as a prompt" (one copy
   packs the install line, usage, and every prop). All MIT, free on npm,
   React 18+, zero runtime dependencies (~83 KB total gzipped):
   border-beam (glow that rides a border), thinking-orbs (AI waiting
   states), liquid-gooey (gooey merging), metal-fx (liquid-metal
   buttons), img-fx (loader that becomes the image; needs three).
Upgrade map — your component → best source
Your app's component
Upgrade from
Primary buttons / CTAs
Morphin "Animated Button with Orbiting Glow" · Libraries.dev metal-fx, border-beam
Image galleries, carousels
Morphin "GSAP 3D Bending Image Carousel" · Bencho Image accordion, Carousel, Orbit cards, Album shelf
Nav bars, menus, docks
Morphin "GSAP Page Fold Navigation Menu" · Bencho Radial menu, Create menu, Magnifying dock, Tab bar, Collapsing sidebar
Scroll sections, feature cards
Morphin "Stacked Scroll Cards with 3D Tilt" · Bencho Card fan, Stacked bars
Loaders & loading states
Bencho Blueprint / Dot / Wave / Bounce / Trace / Morph / Pixel / Blocks loaders, Image shimmer, Shimmer text
AI waiting / thinking states
Libraries.dev thinking-orbs · Bencho Thinking
Image-generation placeholders
Libraries.dev img-fx
Sliders & range inputs
Bencho Time scrubber, Budget slider, Wake slider, Slosh slider, Range, Range dial
Toggles & confirms
Bencho Liquid toggle, Slide to confirm, Inline confirm, Switch-style islands
Form inputs
Bencho AI chat input, One-time code, Password strength, Label input, Form error, Copy field
Toasts & feedback
Bencho Toast stack, Notify, Confetti, Like, Emoji reactions, Feedback bar
Cards
Bencho Tilt card, Card swap, Profile hover card, Billing card, Price flow
Data displays
Bencho Heat map, Network graph, Heart rate · Morphin interactive charts / dashboards
Search & command UI
Bencho Command bar, Search, Palette
Overlays / islands
Bencho Dynamic island, Flight / Music / Call island, Access request
Micro-interactions & sound
Bencho hover/press blocks + its interface sounds (subtle, gesture-started, mutable)
Master prompt — paste into Claude Code inside your web app repo
You are upgrading EVERY component of this web app using three reference
component libraries. Work component by component, never in bulk, and
keep the app building after each step.

SOURCES
- Morphin: https://morphin.dev — premium animated React components
  (carousels, glow buttons, fold menus, scroll cards, charts). Its code
  is Pro-gated: treat its demos as the visual/motion reference and
  reimplement them in our stack, unless I paste Pro code for you.
- Bencho: https://bencho.dev — 130+ interactive React components with
  full source on each block page. If the Bencho MCP server is connected,
  use it to find and pull blocks; otherwise open the block page and use
  its source as the reference implementation to adapt.
- Libraries.dev: https://libraries.dev — five MIT npm packages that ship
  as agent prompts: border-beam, thinking-orbs, liquid-gooey, metal-fx,
  img-fx. Install these properly with npm; do not reimplement them.

PHASE 0 — INVENTORY (do this first, change no code)
Scan the repo and write COMPONENT_AUDIT.md listing every component:
file path, what it does, where it's used, and its pattern class (button,
card, nav, modal, loader, input, slider, accordion, toast, table, …).
Then add an "upgrade candidate" column using this priority: match the
component's pattern to the closest reference in the three sources
(name the specific component/package), or mark it "keep — already good"
or "custom — no match". Show me the audit before upgrading anything.

PHASE 1 — UPGRADE LOOP (one component at a time, in this order)
1) Global primitives: buttons, inputs, toggles, loaders, toasts.
2) Navigation: header/nav, menus, tabs, sidebar, command bar.
3) Content: cards, lists, accordions, galleries, carousels.
4) Data: charts, tables, stat displays.
5) Overlays: modals, drawers, islands, popovers.
6) Micro-interactions last: hovers, press feedback, sounds.

For each component:
a. Read the current implementation and its usages. Note its public
   props/API — preserve them unless I approve a breaking change.
b. Open the reference (Bencho block page / MCP, Libraries.dev package
   docs, or the Morphin demo) and study the interaction: trigger,
   motion curve, states, exit behavior.
c. Implement the upgrade in OUR design system: our color tokens, radii,
   spacing, fonts, and dark/light modes. The reference supplies the
   motion and interaction design, not its colors or branding.
d. Motion rules (non-negotiable): animate transform and opacity only;
   spring physics or expo-style easing, no linear or generic ease;
   press feedback within one frame; respect prefers-reduced-motion
   with a calm fallback; keep INP under 200ms and avoid layout shift.
e. Keep it accessible: focus visible, keyboard operable, aria states
   correct, touch target ≥ 44px. Sound (if any) starts only after a
   user gesture, is subtle, and has a mute that persists.
f. Run the build + typecheck, fix what broke, and screenshot the
   component before/after (or describe the visual diff precisely).
g. Append one line to UPGRADE_LOG.md: component, source used, what
   changed. Then move to the next component.

RULES
- One component per cycle. No drive-by refactors of unrelated code.
- If a reference needs a new dependency, name it and its size first;
  prefer what the project already has (e.g. our existing motion lib)
  when it can reproduce the effect faithfully.
- Never paste Morphin code you don't have rights to — reimplement from
  the demo. Bencho source and Libraries.dev packages are fine to use
  per their licenses; keep license notices where required.
- If an upgrade makes a component heavier without a visible quality
  gain, revert it and note why in the log.

FINISH
When the audit list is exhausted, give me a summary: components
upgraded (by source), components intentionally kept, bundle-size delta,
and any component where the reference couldn't beat what we had.
Verify: production build passes, zero console errors, and walk the
app once at mobile width checking every upgraded component works by
touch and keyboard.
Notes before you run it
Bencho MCP is the force multiplier here: connect it in Claude Code
  first and Phase 1 gets much faster, because Claude Code can search and
  fetch blocks directly instead of you pasting source.
Morphin Pro: if you don't have it, the prompt already tells Claude
  Code to reimplement from the demos — the carousels and scroll cards are
  GSAP patterns it knows well. If you do have Pro, paste the "Get code"
  output per component and it will adapt the real thing.
Run the phases as separate sessions if the app is large — Phase 0's
  audit file is the handoff between them.

---

## 2. 3D Libraries for Vibecoders

3D Libraries for Vibecoders — list for Claude Code
Source: @web_pros carousel "3D Libraries for Vibecoders — 04 tools worth
knowing" (https://www.instagram.com/p/Dd86Z4wlKw4/), posted 2026-10-01.
The list (copy as-is)
Aceternity UI (ui.aceternity.com) — React + Tailwind component library
  with polished motion and 3D effects built in (spotlights, beams, 3D cards,
  text effects). Copy-paste components, no heavy install.
Canvas UI — canvas-powered component/effects library for WebGL and
  WebGPU interfaces; HTML-in-canvas components for shader-style visuals.
VGPU by Vercel Labs — WebGPU library/framework built for modern,
  agent-assisted graphics work; designed to be LLM-friendly, so Claude Code
  can write against it effectively.
Spline (spline.design) — browser design tool for building interactive
  3D scenes visually, then embedding/exporting them to the web via React,
  React Three Fiber, Drei, and Three.js.
Paste-ready prompt version (copy everything below into Claude Code)
Here are 4 3D/motion libraries I want available for my web builds:

1. Aceternity UI (ui.aceternity.com) — React + Tailwind components with
   polished motion and 3D effects.
2. Canvas UI — canvas-powered effects and HTML-in-canvas components for
   WebGL/WebGPU interfaces.
3. VGPU by Vercel Labs — WebGPU library designed for agent-assisted
   graphics (LLM-friendly APIs).
4. Spline (spline.design) — visual 3D scene builder that exports to
   React / React Three Fiber / Drei / Three.js.

For my current project:
- First check the official site/docs and npm registry entry for each
  library before using it — install commands and APIs change, so verify
  against the official source, never guess a package name.
- Recommend which ONE fits this project best based on what I'm building
  (marketing/hero visuals vs. real-time 3D product scenes vs. shader
  backgrounds), and explain the tradeoff in 2–3 lines.
- Install and wire up only the chosen library, add ONE demo usage that
  matches my page (e.g. a hero 3D tilt card from Aceternity, or a Spline
  scene embed), keep animation on transform/opacity or the GPU canvas,
  and confirm the production build passes with no console errors.
- If a library's official docs can't be reached, say so and fall back to
  plain Three.js / CSS 3D instead of inventing an API.

---

## 3. Ambitious Website Prompt for Claude Code

Ambitious Website Prompt for Claude Code
Adapted from Felix Rieseberg's (Anthropic, Claude Code lead) essay
How to be more ambitious: A tutorial for humans with models.
His core idea: don't ask the model for a task ("build me a landing page"). Ask it to
first think like the field's best professional — what they'd do that you didn't ask for,
what raw material they'd start from, what methods/tools they'd use, and what outside
check would prove the result is right — then rewrite your request around that and build it.
This version is specialized for websites that feel like AAA game menus and top-tier
tech sites (Linear/Stripe/Arc-tier): instant, tactile, alive — never janky.

The prompt (paste into Claude Code, then describe your site)
I want the ambitious version of this website, not the default one. Work like an
award-winning interactive studio (the teams behind game UIs and Awwwards-tier product
sites), not like a template generator.

Before writing any code, do this analysis and show it to me:

1. DEPTH — the professional standard:
   - What would a top front-end/motion team do on this site that my request doesn't
     ask for? (Name the specific gaps: motion, feedback, states, polish.)
   - What is the rawest material to start from? Real content/copy and real data shapes
     first — no lorem ipsum, no placeholder boxes surviving to the final build.
   - Name the exact methods and tools: stack, animation library, easing/spring system,
     and why each fits this site.
   - The goal beyond the goal: state the outcome this site must produce (signups,
     sales, wow-factor portfolio piece) in one sentence, and design to that outcome,
     not just to my literal request.

2. RANGE — steal from other fields:
   - From game UI: instant tactile feedback on every interaction, spring-physics
     motion, satisfying micro-interactions, zero dead clicks.
   - From film/motion design: choreographed entrances, staggered reveals, easing
     that makes elements feel weighted and physical.
   - From native apps: buttery 60fps scrolling, no layout shift, optimistic UI.

3. Then rewrite my request as a build brief incorporating all of the above, and
   build to the brief.

SMOOTHNESS SPEC — non-negotiable for anything you build:
- Animate transform and opacity ONLY. Never animate width/height/top/left/margins.
- Every interactive element responds within one frame: hover, press, and focus
  states on everything clickable; buttons scale ~0.97 on press with a spring back.
- Use spring physics or curated cubic-bezier curves (e.g. easeOutExpo-style);
  durations 150–400ms for UI, longer only for hero choreography. No linear easing,
  no default browser easing.
- Scroll: smooth-scroll library (Lenis) or CSS scroll-behavior where appropriate;
  scroll-triggered reveals fire once, staggered 40–80ms apart; parallax only via
  transform and only if it stays at 60fps.
- Performance budget: LCP < 2.5s, CLS ~0, INP < 200ms. Lazy-load heavy media,
  preload the hero asset, use GPU-friendly layers sparingly (no will-change spam).
- Motion must respect prefers-reduced-motion: provide a calm fallback.
- Dark, rich surfaces over flat white; depth via layered gradients, subtle noise,
  and glass where it earns its place — no purple-gradient clichés, no generic
  template look.

VALIDATION — prove it, don't assert it:
- npm run build passes; no console errors.
- Run the dev server and screenshot the result (Playwright or equivalent) at
  desktop and mobile widths; check the screenshots yourself for overlap, overflow,
  and unstyled states before declaring done.
- List what you could NOT verify (e.g. real-device frame rate) instead of claiming
  it's smooth.

Ask me up to 4 questions first ONLY if the site's purpose, audience, or stack is
genuinely unclear. Otherwise start: show me the step 1–2 analysis and the rewritten
brief, then build it.

My site: [DESCRIBE YOUR SITE HERE — what it is, who it's for, pages/sections,
any stack preference (default: React + Vite + Tailwind + Framer Motion + Lenis)]

How to use it
Paste the prompt into Claude Code in your project folder.
Replace the "My site:" block with a one-paragraph description of what you're building.
Claude Code will show you the expert analysis + rewritten brief first — skim it,
   correct anything off-target, then let it build.
The four knobs (from the essay, quick reference)
Speed — same work, less time. (The baseline; least interesting knob.)
Altitude — delegate the outcome, not the task. "A landing page that converts
  visitors into signups" beats "a hero, three features, and a footer."
Depth — expert methods, raw materials, unreasonable targets, and an outside
  judge (build, screenshots, metrics) — never let the model grade its own homework.
Range — import techniques from other fields. For websites, the richest imports
  are game UI (feedback/springs), film (choreography), and native apps (scroll feel).
The original Depth prompt and full tutorial are in Rieseberg's essay:
https://felixrieseberg.com/how-to-be-more-ambitious-a-tutorial-for-humans-with-models/
(Reel that pointed here: @gennaroautomates, https://www.instagram.com/reel/DeskvCRuvtH/)
