# How Asclexis frames itself

> **Copied 2026-10-23** from the L0 scratch directory into this folder, unchanged except for the path rewrites this note describes. Paths that cited the scratch directory now point at this folder where the file was kept (`proto-A.patch`, `proto-B.patch`, `shots/`); anything else marked "L0 scratch" was not committed. Index and provenance: [00-README.md](00-README.md).

Repo: `/mnt/e/Programming/Github Repo/HealthCentral` at `main` 7749744 (clean tree), read 2026-10-23.
Searched CLAUDE.md, AGENT.md, README.md, `docs/capstone-report/**` and wider `docs/**` for
"simulat", "SaaS", "software engineering", "stakeholder", "production", "industry", "agile", "sprint".

## Short answer

**No hand-maintained doc says the project simulates a SaaS product.** "SaaS" shows up only where a doc
tells readers to stay away from SaaS patterns or SaaS dependencies, never as something to aim for. "Simulat*" in the
capstone package only describes someone else's benchmark. Today the docs frame the project in three ways:

1. A **local-first, privacy-first desktop companion for real patients**, education only.
2. A **capstone with two contributions**: the product is the substrate, and the thesis is agentic software engineering.
3. A **UI direction called "Clinical Calm"** ("restraint with purpose"). It asks for a polished, premium feel
   with deliberate motion. It does not ask for an animated, engagement-driven SaaS feel.

The owner's goal ("simulate a real SWE/SaaS product, so the frontend should feel modern, engaging, smooth,
animated") is therefore **a new framing that the docs do not record yet**. It fits the existing
design plan if "SaaS" means SaaS *craft* (fit and finish, responsiveness, real feedback states, coherent
motion). It clashes with the plan if it means SaaS *engagement mechanics* (attention-grabbing animation,
growth loops, telemetry). Before any redesign starts, the owner should write a one-line decision
(say, in `docs/capstone-report/owner-decisions-2026-09-27.md`) that settles which of the two it means.

## Quotes, with file:line

### Product identity (patients, local-first, education only)
- `README.md:3`: "**Local-First Medical Results Companion**"
- `README.md:5`: "A privacy-first desktop application for patients to import medical documents, extract structured information with user verification, visualize trends, and generate grounded explanations with citations."
- `README.md:7`: "**Research and educational open-source project. Not professional medical or legal advice, not a medical device, and not for emergencies.**"
- `README.md:470`: "It is a research study, not a clinical product."
- `AGENT.md:7`: "Local-first, privacy-first desktop app … All data stays on-device … Education only — never diagnosis or treatment advice."
- `CLAUDE.md:22`: "This is a health app for real patients. When in doubt between a clever fix and a conservative one, pick conservative and say why."
- `docs/brand/brand-guidelines.md:7-9`: "This is mostly a safety document. The largest brand risk for this product is not visual inconsistency — it is copy that implies medical advice."

### Capstone / software-engineering framing (the closest thing to "simulate a real product")
- `docs/capstone-report/00-original-goal.md:5`: "Two coupled goals — the product is the substrate; the research is the thesis."
- `docs/capstone-report/00-original-goal.md:27`: "Evidence artifact for the **developer → orchestrator shift** … **harness engineering**, where the environment surrounding the agent … is itself the engineered deliverable."
- `docs/capstone-report/report-outline.md:15`: "Dual contribution: a locally run product (dev launcher; no installer yet, C8) + agentic-SWE methodology study"
- `CS4610_Report_Demo/README.md:4-5`: "CS4610 course deliverable. They describe the harness and the product's development process, and some of what they describe is aspirational".
- `docs/capstone-report/README.md:21`: "Ledger-gated copy of the stakeholder showcase page". Stakeholders are a real audience.
- `docs/capstone-report/owner-decisions-2026-09-27.md:396` (MVP-PACKAGING): "How do stakeholders get the app before 2026-10-31?" The answer was "Option A then work on C installer". The product is meant to ship to real people, the way a product team would ship it.
- `docs/archive/agile/STANDUP.md` (sprints S0–S7, a "PM-orchestrator pass", PRD, phase and sprint docs) shows that the *process* was run like a product team's. That is the SWE-simulation story, and it lives in the process, not in the UI.

### The only "SaaS" mentions (all negative)
- `docs/archive/plans/2026-07-02-fable5-architect-handoff-prompt.md:34`: "…weigh proposals against actual project constraints (local-first, safety-critical modules) instead of generic SaaS-health-app patterns."
- `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md:436`: a gamification library was rejected as a "client for a hosted SaaS API … violates local-first/zero-network constraint outright".
- `docs/prd/PRD_agent_overhaul.md:143` lists a "New cloud/SaaS dependency or telemetry leaving the device" as out of bounds.

### UI direction that already exists (this is what the redesign has to reconcile with)
- `docs/02_frontend_accessibility_plan.md:4`: "Reduce confusion and anxiety via clarity, provenance, and conservative language"
- `docs/02_frontend_accessibility_plan.md:6`: "Optimize for older patients and non-medical users: readable typography, predictable navigation, plain language"
- `docs/02_frontend_accessibility_plan.md:13`: "Target WCAG 2.2 AA behaviors…"
- `docs/02_frontend_accessibility_plan.md:107`: "**\"Clinical Calm\"** aesthetic—refined minimalism with warm, reassuring touches that reduce anxiety while maintaining medical credibility … Think: luxury wellness retreat meets precision lab."
- `docs/02_frontend_accessibility_plan.md:155`: "**Philosophy**: Restraint with purpose. One well-orchestrated moment beats scattered animations."
- `docs/02_frontend_accessibility_plan.md:157-163`: staggered page reveals of 200–300 ms, "gentle lifts", "Smooth number transitions", "Subtle pulse or glow on successful actions", "Respect `prefers-reduced-motion`", "No essential information conveyed via animation alone."
- `docs/02_frontend_accessibility_plan.md:177-185` specifies components that **do not exist** today: `A11yDialog`, `A11yTabs` with an animated underline, `A11yToast` "slide-in … auto-dismiss with progress indicator", `TrendChart` "Animated line draw on load".
- `docs/brand/brand-guidelines.md:151-153`: "Not an icon set, motion spec, or illustration library. Those do not exist yet".
- `src/frontend/src/App.tsx:5`: "Designed for accessibility (WCAG 2.2 AA)."

## Reading for the redesign brief

- The docs already want something that *feels* premium ("luxury wellness retreat meets precision lab").
  That is compatible with "modern SaaS polish". The gap between that intent and the shipped UI is large
  (see `ui-review.md`).
- The docs explicitly rule out *what* SaaS usually brings: remote fonts and CDNs, telemetry or analytics,
  engagement loops, generic SaaS-health patterns. Engagement mechanics are already in tension with the brand
  (gamified "Week Warrior" / "Comeback Kid" badges on the Meds page) and with the brand rule against
  "smart"-style feature names.
- The plan sets "calm" as the ceiling on motion, so the redesign should treat it that way: interruptible, short (≤300 ms),
  reduced-motion-correct, never hiding disclaimers or citations.
