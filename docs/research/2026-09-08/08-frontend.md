# Track 8 — Frontend refactor: motion, agent-trace UI, and design system

**Scope:** repo (`src/frontend/`) + web · **Read-only** — no source file was modified;
this document is the only write. Verified 2026-09-08 against branch
`claude/healthcentral-agentic-research-r1n54x`. See [`00-brief.md`](00-brief.md)
for the shared baseline and constraints this track inherits.

---

## Summary

The frontend is in better shape than "scattered animation library, no agent UI"
suggests, and worse in one specific place than the brief's framing implies it
might be fixed by frontend work alone.

**What's already good and should be built on, not replaced:**
`components/ui/Motion.tsx` already centralizes entrance/stagger/modal variants
and already threads `useReducedMotion()` through them
(`src/frontend/src/hooks/useReducedMotion.ts`) — the reduced-motion policy
this research would otherwise have to invent is already the load-bearing
default in the one shared module. A fully-built, accessible, hover/focus
citation tooltip (`components/lab-interpreter/CitationTooltip.tsx`) already
exists and is unused outside the Interpret page. A shaded reference-range
`ReferenceArea` chart already exists
(`components/lab-interpreter/InterpretedTrendChart.tsx`) — it's just not the
one `TrendsDashboard.tsx` uses.

**What's actually missing, and why it's not purely a frontend problem:**
the agent-trace UI (research question 2) cannot be built from the frontend
alone. `POST /assistant/chat` (`src/backend/api/assistant.py:657`) awaits
`run_agent()` to completion and returns one flat `ChatResponse` — no
`run_id`, no per-step trace, and critically, no `terminal` field: `abstain`
and `escalate` are two distinct, already-computed backend outcomes
(`modules/agent/schemas.py` `AgentTerminal.terminal: Literal["answer",
"abstain", "escalate"]`) that `_agent_terminal_to_response_parts()`
(`api/assistant.py:568-620`) collapses into the same `segment_type:
"uncertainty"` before the wire — the frontend today cannot tell an abstain
from an escalation even if it wanted to. Similarly, `Draft.sentences` runs
parallel to `Draft.citations` internally (`nodes/draft.py:44-46`,
`guardrails/groundedness.py` `map_sentences`) — a per-sentence citation
mapping already exists in the backend and is thrown away at
`guard.py:173`'s `text=" ".join(mapping.surviving)` before it ever reaches
`ChatResponse`. **The single highest-value, lowest-effort move in this whole
track is a backend serialization change** (stop discarding data the agent
already computed), paired with a frontend rendering change that is almost
entirely reuse of an existing component. Flagging this for coordination with
Track 1/3, since `AgentTerminal`, `ChatResponse`, and `graph.py` are backend
files this track cannot touch.

**Stack currency:** nothing here is urgent. `framer-motion` was renamed to
**Motion** (now independent of Framer, v12, import path `motion/react`) —
worth a same-behavior rename eventually, not now. React 19.2 and a stable
React Compiler exist, but React 18→19 buys this codebase almost nothing it
needs today (no Suspense-heavy data fetching, already on React Query for
server state) against real regression risk in Radix + framer-motion
compatibility. Tailwind v3→v4 is a real, quantifiable one-to-two-day job
(92 non-test TS/TSX files, a config with no custom plugins, one `dark:`
usage total) but buys performance the app doesn't need on a localhost build
and forces a `bg-gradient-to-*` → `bg-linear-to-*` rewrite across every
gradient in the design system for no product benefit. None of this is
"worth doing now."

**Accessibility:** the written plan (`docs/02_frontend_accessibility_plan.md`)
sets real WCAG 2.2 AA-shaped targets and cites a specific 2026-02-12 audit
with fixes applied. The trend chart's accessible-alternative requirement
("chart view must include ... data table view") from that same document is
**not met** in `TrendsDashboard.tsx` today — there's a textual summary but
no data table, confirmed by reading the component. There is **no i18n**
anywhere in the app: `index.html` hardcodes `lang="en"`, no `react-intl` /
`next-intl` / `formatjs` dependency exists, and every user-facing string is
inline English in JSX. For a stated user population that includes
non-English speakers, this is a gap worth naming even though fixing it is
out of scope for an incremental pass.

---

## 1. Motion system

### What's there today

`components/ui/Motion.tsx` is a real, if small, motion system, not a grab
bag:

- `fadeVariants` / `slideUpVariants` — the two entrance shapes used
  everywhere.
- `staggerContainerVariants` (`staggerChildren: 0.05`) + `StaggerGroup` /
  `StaggerItem` for list reveals.
- `PageTransition` — wraps route content, picks `fadeVariants` over
  `slideUpVariants` automatically when `useReducedMotion()` is true.
- `modalVariants` / `backdropVariants` for overlays.

`useReducedMotion.ts` is a correct, minimal `matchMedia` hook (listens for
live changes, not just initial state). Global CSS
(`src/frontend/src/styles/globals.css:29-40`) also has an unconditional
`@media (prefers-reduced-motion: reduce)` block collapsing all
`animation-duration`/`transition-duration` to `0.01ms` — so there is
**defense in depth**: even a component that forgets to call the hook still
gets the CSS override. That's the right structure; this section proposes
tokenizing it, not rebuilding it.

**What's inconsistent:** durations and easings are hand-typed at each call
site rather than drawn from a shared scale. `PageTransition` uses
`{ duration: 0.3, ease: 'easeOut' }`; `TrendsDashboard`'s chart line uses
`animationDuration={prefersReducedMotion ? 0 : 800}` (a bare number, no
named token); `BadgeToast` uses a spring (`type: 'spring', damping: 20,
stiffness: 300`) with no shared spring scale to draw from; the sidebar's
active-tab indicator uses a different spring
(`bounce: 0.2, duration: 0.4`) for a conceptually similar "something moved"
motion. Four different animation shapes for what should be two or three
named tiers. `tailwind.config.js` *also* defines a parallel, redundant
animation vocabulary (`animate-fade-in`, `animate-slide-up`, keyframes
`fadeIn`/`slideUp`/`scaleIn`/`shimmer`) that duplicates what Motion.tsx
already expresses in JS — two systems for the same handful of effects,
neither the canonical one.

**One tone note, not a defect:** `BadgeToast.tsx` (medication adherence
gamification) uses `rotate: -5` entrance, a `scale-150 opacity-20`
`animate-ping` halo, and emoji icons (🔥🏆⭐). That's a deliberate register
shift for an achievement toast, and arguably fine in an adherence-coaching
context — but it's the one place in the app that reads as *performing*
rather than informing, which is exactly what CLAUDE.md's "motion should
reduce cognitive load, not perform" flags. Worth a design conversation, not
a rewrite.

### Policy: when is motion allowed at all

For a health app whose brand guidelines already say "restraint with
purpose" and whose users include anxious, unwell, or elderly patients, the
policy should be stricter than "respect `prefers-reduced-motion`" (necessary
but not sufficient):

1. **Motion communicates state change, never decorates.** An element may
   animate only if its motion answers a real question: *did something
   appear, disappear, move, or complete?* No motion whose only job is to
   look polished (no per-character stagger on headings, no autoplaying
   backgrounds beyond the existing 3% noise texture, which is static).
2. **Never animate clinical values.** A number changing (a lab result, a
   trend delta) must render at its final value immediately — no
   count-up/count-down tweening. This directly contradicts the brand
   guidelines' own suggestion ("Smooth number transitions for trend
   changes," `docs/brand/brand-guidelines.md` "Motion &
   Micro-interactions") — flagging that line as a conflict with the
   "reduce cognitive load" principle this research was asked to hold to:
   an animated number is momentarily *wrong*, and for a patient checking
   whether their glucose is dangerously high, a half-second of a wrong
   number is a real cost for zero benefit. Recommend the brand doc be
   corrected in the same pass that ships the token table below.
3. **Reduced motion means zero non-essential motion, not "shorter."**
   Today's implementation is inconsistent on this: `PageTransition`
   swaps to a pure fade (still animates opacity) under reduced motion;
   `TrendsDashboard`'s line-draw goes to `animationDuration={0}` (correct:
   instant); `Sidebar`'s active-tab `layoutId` is set to `undefined` under
   reduced motion (correct: disables the FLIP animation entirely). Pick one
   rule — reduced motion means duration 0 for state changes, not a faster
   version of the same motion — and apply it everywhere `Motion.tsx`
   currently does the softer "reduce to fade" thing.
4. **No motion gates comprehension.** Nothing the user needs to read may be
   mid-transition when they need to read it — this is already true here
   (nothing blocks input during animation) and should stay a hard rule as
   the agent-trace UI (Section 2) adds a live-updating surface.

### Coherent motion system: durations, easing, springs, distance

A token table, meant to live as constants exported from `Motion.tsx`
(extending it, not replacing it) and mirrored into
`tailwind.config.js`'s `transitionDuration`/`transitionTimingFunction` so
both the JS (`framer-motion`/Motion) and CSS-utility paths agree:

| Token | Value | Used for |
|---|---|---|
| `duration.instant` | `0ms` | Reduced-motion override for everything below |
| `duration.fast` | `120ms` | Hover/press feedback, focus ring, tooltip open |
| `duration.base` | `200ms` | Default state change: card expand, toast enter |
| `duration.slow` | `320ms` | Page/route transitions, modal enter |
| `duration.chart` | `600ms` | Chart line draw only — the one place a slower reveal earns its cost, capped well below today's inconsistent `800ms` |
| `ease.standard` | `cubic-bezier(0.2, 0, 0, 1)` | Default for enter/exit — a slightly decelerated ease-out, closer to Material's "standard" curve than the bare `'easeOut'` string used today |
| `ease.exit` | `cubic-bezier(0.4, 0, 1, 1)` | Faster acceleration out — exits should feel quicker than entrances |
| `spring.snap` | `{ type: 'spring', stiffness: 420, damping: 34 }` | Small UI moves: active-tab indicator, toggle switches — replaces the two divergent ad hoc springs in Sidebar/BadgeToast |
| `spring.settle` | `{ type: 'spring', stiffness: 260, damping: 26 }` | Anything larger: modal/panel entrance, badge toast |
| `distance.sm` | `4px` | Micro-shifts: hover lift, focus nudge |
| `distance.md` | `12px` | Standard entrance offset (already used ad hoc as `y: 12` in `Motion.tsx` and `ExplainAssistant.tsx` — just needs naming) |
| `distance.lg` | `24px` | Reserved; not currently needed — don't introduce a use for it speculatively |
| `stagger.tight` | `40ms` | List item reveal (current `0.05`/50ms rounds down slightly for snappier lists) |

This is roughly six numbers and two curves — small enough that adopting it
is a mechanical find-and-replace across the 23 files already touching
`framer-motion`, not a redesign. Each call site keeps its own trigger
logic; only the raw numbers move to named constants.

### Layout animations, shared-element transitions, View Transitions API

- **Layout animations** (`layout` / `layoutId` props): already in use
  correctly and sparingly — `Sidebar.tsx`'s active-item background is the
  only `layoutId` in the app. That's the right amount. Framer/Motion's
  `layout` prop is powerful but expensive (it measures DOM on every
  render); no evidence in this codebase that more of it is needed. Keep it
  rare.
- **Shared-element transitions** (an element visually "becoming" another
  across a route change — e.g., a citation chip growing into the
  Verification Workbench panel it deep-links to) would be a genuinely nice
  touch for `citationTarget()`-style navigation
  (`pages/ExplainAssistant.tsx:59-77`) but is real engineering cost
  (`layoutId` shared across route boundaries needs the outgoing and
  incoming trees mounted simultaneously, which React Router's default
  unmount-on-navigate defeats without extra plumbing). Not recommended now
  — the existing "open in new tab context" navigation is already legible
  and testable; a shared-element transition adds motion-library surface
  area for a cosmetic win.
- **CSS View Transitions API** as a lower-cost alternative for route
  changes: same-document View Transitions are Baseline-supported across
  current Chrome/Edge, Safari 18+, and Firefox 152+ as of 2026
  [[Can I Use / browser support summary](https://www.testmuai.com/learning-hub/view-transitions-api-browser-support/)].
  For a single-page app using client-side routing (react-router-dom, not
  cross-document navigation), the relevant API is
  `document.startViewTransition()` wrapping a state update — genuinely
  usable today without a polyfill, since it degrades to an instant
  (non-animated) transition on any browser that lacks it. **This is worth
  prototyping for route-level `PageTransition` as a framer-motion/Motion
  replacement**: zero added JS bundle weight, and the browser — not
  `framer-motion`'s FLIP measurement pass — owns the diff. The catch: it
  animates a DOM snapshot, so it can't easily do the "slide up with
  staggered children" entrance `Motion.tsx` currently does; it's a good fit
  for a plain crossfade, not for `StaggerGroup`. Recommend it as a later,
  separable experiment (Section on Recommendations), not a blocking
  dependency for the token-table work above.

Sources: [Motion (prev Framer Motion) — official site](https://motion.dev/),
[Framer Motion Becomes Independent](https://fireup.pro/news/framer-motion-becomes-independent-introducing-motion),
[View Transitions API browser support, 2026](https://www.testmuai.com/learning-hub/view-transitions-api-browser-support/),
[Cross-document View Transitions guide, 2026](https://trade-assistance.com/blog/cross-document-view-transitions-mpa-2026/).

---

## 2. The agent-trace UI

### What the backend actually does versus what the frontend shows

Confirmed by reading `graph.py` end to end
(`src/backend/modules/agent/graph.py`): every run walks
`plan → act → reflect → (loop|draft) → guard → terminal`, every node appending a
`RunStep` to `run_log.steps` (`state.py` `RunStep{step_index, node, payload,
timestamp}`) and recording wall-clock duration via
`record_node_timing()` (`metrics.py`) into the same `MetricsCollector` that
serves `/api/v1/monitoring/metrics`. `MAX_STEPS = 5` bounds the loop
(`state.py:19`). None of this — not the steps, not the timings, not the
`run_id` itself — crosses into `ChatResponse`. `POST /assistant/chat`
(`api/assistant.py:657-670`) calls `run_agent()`, gets back one
`AgentTerminal{terminal, text, citations, run_id}`, and
`_agent_terminal_to_response_parts()` throws away `run_id` and the
`terminal` **type** (only its text ends up on the wire, wrapped as one
`ResponseSegment`). The frontend's only signal that something took a while
is a generic three-dot "Searching documents and generating response..."
bubble (`pages/ExplainAssistant.tsx:737-753`) that is identical whether the
agent ran zero tool calls or hit the five-call budget.

This means: **before any frontend component can render a step timeline,
`ChatResponse` needs new fields.** That's a backend contract change
(Track 1/3 territory — this track does not modify `src/backend/`), so
what follows is the frontend design *and* the minimal wire contract it
needs, stated explicitly so it can be handed across the track boundary.

### Minimal wire contract this UI needs

```jsonc
// Additive fields on ChatResponse — nothing existing removed or renamed.
{
  "run_id": "…",                    // already generated (new_run_id()), just not returned
  "terminal": "answer" | "abstain" | "escalate",  // AgentTerminal.terminal, currently discarded
  "steps": [                        // optional: only if Track 1/3 approves exposing RunLog
    { "node": "plan", "tool_name": "compute_trend", "duration_ms": 42 },
    { "node": "act",  "tool_name": "compute_trend", "duration_ms": 118 },
    { "node": "reflect", "decision": "draft", "duration_ms": 6 }
  ],
  "sentences": [                    // Draft.sentences × Draft.citations, already computed,
    { "text": "…", "citation_indices": [0] },   // discarded at guard.py:173's " ".join()
    { "text": "…", "citation_indices": [1, 2] }
  ]
}
```

`run_id` and `terminal` are a one-line addition each (the values already
exist in `AgentTerminal`). `sentences` needs `guard.py` to stop collapsing
`mapping.surviving` into a joined string and instead pass the list through
— `MappingResult.surviving` (list[str]) and `MappingResult.citations`
(parallel list[Citation]) already have the right shape
(`guardrails/groundedness.py:16-18,40-71`); this is exposing existing
data, not computing anything new. `steps` is the only genuinely new
surface (deciding what's safe to show — tool args may contain
question-derived text) and should be scoped conservatively: tool **names**
and timings only, no raw args/results, consistent with `RunStep.payload`'s
own existing contract of "handles, never raw PHI" (`state.py:47`).

### Streaming: design for both cases

`core/llm/` (`src/backend/core/llm/`) confirms the brief's caution is
warranted, but the picture is more specific than "may not exist at all":

- `ollama_provider.py`: `generate_stream()` is real (`stream=True` against
  Ollama's `/api/chat`, async iterator over chunks) — `capabilities.streaming
  = True` (`provider.py:39`).
- `llama_cpp_provider.py`: `capabilities.streaming = False`
  (line 193, comment: *"streaming support requires llama.cpp stream API"*);
  `generate_stream()` exists but its own docstring says *"not yet
  implemented ... yields full response as single chunk"* (line 300).
- **Neither path is wired to `/assistant/chat` today** — the route calls
  `run_agent()` synchronously and returns one JSON body; no
  `StreamingResponse`, no SSE, confirmed by grep (`grep -n "stream\|Stream"
  src/backend/api/assistant.py` returns nothing).

So: streaming may arrive for the Ollama tier before the (probably more
common, given the GGUF/llama.cpp-based tier system in
`docs/model_tiers/`) llama.cpp tier, and may not arrive as token-level
streaming at all in the near term — but **step-level progressive
disclosure does not need token streaming**. The agent loop already has
natural, coarse update points: after each `plan`/`act`/`reflect` node
completes, there's a real, discrete new fact ("just called
`compute_trend`", "decided to loop again"). That can be delivered over a
much simpler mechanism than model-token SSE: either (a) genuine SSE/chunked
response where each chunk is one `RunStep` JSON object as it's appended to
`run_log.steps` (the `graph.py` loop already appends steps synchronously
in order — turning that into a generator is a moderate, not a large,
change to `run_agent`'s call sites), or (b) short-polling a
`GET /assistant/runs/{run_id}` endpoint from the frontend every ~400ms
while `POST /chat` is in flight, backed by nothing more than `RunLog`
already being buildable in-memory during the run. Recommend (b) first: it
requires zero change to `run_agent`'s control flow (no generator
refactor), works identically regardless of which LLM provider is active,
and degrades trivially — if the poll returns nothing new, the UI just
keeps showing the last known step. Revisit (a) once/if Track 1 lands true
token streaming end-to-end, at which point the same UI (Section
"Wireframe" below) upgrades from "step ticks in" to "step ticks in, and
the draft's own text also streams in" without a redesign, because the
component is written against "receive updates over time," not against a
specific transport.

Prior art for this pattern in 2026 agent UX: *"a transparent step list, a
stop-and-edit affordance at every checkpoint, scoped previews of what the
agent is about to touch, and a clear visual separation between 'model is
thinking' and 'agent is doing'"*
[[Agent UX: UI Design for AI Agents in 2026](https://fuselabcreative.com/ui-design-for-ai-agents/)];
progressive-disclosure via a collapsed-by-default "reasoning steps" toggle
that expands into the raw trace only on request
[[Designing Practical Interface Patterns for Agentic AI Transparency](https://mrsinternet.com/designing-practical-interface-patterns-for-agentic-ai-transparency/)];
and the general shift toward agent-observability tooling capturing
"end-to-end reasoning sequences, tool calls, ... from initial prompt to
final action" as a first-class product surface, not just a debug view
[[Agent observability: the complete guide for 2026](https://www.braintrust.dev/articles/agent-observability-complete-guide-2026)].
Asclexis's own `RunLog`/`RunStep` model is already shaped like a
lightweight version of what those tools capture — the gap genuinely is
"exists in the backend, not surfaced," not "needs new instrumentation."

### Rendering ABSTAIN and ESCALATE as first-class, trustworthy outcomes

This is explicitly named as a design problem, and the evidence for why it
matters is in the backend's own comments: `graph.py`'s module docstring
states *"abstain: not enough verified information ... ESCALATE: fixed
'ask your doctor' block ... both are SUCCESSES, never error paths"*
(`graph.py:8`, `schemas.py:31-34`). The templates themselves already do the
hard part — clear, honest, non-alarming copy
(`guardrails/templates.py`):

> **Abstain:** "There isn't enough verified information in your record to
> explain this yet. If the relevant document is imported but not verified,
> verifying it will let Asclexis explain the values it contains."
>
> **Escalate:** "This is a question for your doctor or pharmacist. Asclexis
> can explain what your verified results say, but it can't advise on
> diagnosis, treatment, or medication decisions. Please bring this question
> to your clinician."

Today both render identically — the same amber `status-caution` card with
an `AlertCircle` icon and the label "Limited Context Available"
(`pages/ExplainAssistant.tsx` around the `insufficientContext` branch) —
which actively works against the "first-class success, not a failure"
framing the backend team fought to build: a patient sees the same visual
alarm whether the system correctly declined to speculate (abstain) or
correctly recognized a question needs a clinician (escalate), and that
visual sameness reads as "the app is uncertain" or "something's wrong,"
not as two different, deliberate acts of restraint.

**Design proposal — two distinct terminal cards, both calm, neither styled
as an error:**

- **Abstain** — icon: a document/magnifying glass motif (searched and
  found nothing verified, not "broken"). Color: `ink-secondary` neutral
  tones, not `status-caution` amber (amber implies risk; abstain is an
  absence of data, not a risk signal). Copy: the fixed template, plus one
  concrete next action rendered as a real link — *"Go to Verify"*
  (`/verify`) if there's an unverified document that plausibly bears on
  the question. No retry button that just re-asks the model; retrying
  cannot manufacture verified data that doesn't exist.
- **Escalate** — icon: a person/conversation motif (this is a
  clinician's question, not the app's). Color: `status-info` (the calm
  blue already in the palette, `#6B8CAE`), never `status-attention`/
  `status-caution` — escalate is not a warning about the *app*, it's a
  routing decision, and coloring it like a warning miscommunicates that
  something went wrong when the system is working exactly as designed.
  Copy: the fixed template, with **no** "Ask again" affordance that
  invites rephrasing to route around the classifier — that would
  undermine the exact guarantee (`advice_leakage == 0`,
  `docs/agentic/…`/`eval/scorer.py`) this state exists to protect.
- Both cards get a small `terminal: "abstain"`/`"escalate"` badge in the
  corner, differentiated by more than color per the brand guidelines'
  own rule (`docs/brand/brand-guidelines.md` §6: "colour alone never
  distinguishes them") — an icon plus a one-word label, matching the
  existing `StatusBadge` pattern the brand doc already specifies.

This requires the `terminal` field from the wire-contract addition above;
without it, the frontend is inferring abstain-vs-escalate from string
content, which is what today's crude `content.includes('knowledge base
only')` check already shows is fragile (`ExplainAssistant.tsx` around
line 330).

### Per-sentence citations

The retrieval-time labels `[YOUR_RESULTS:N]` / `[REFERENCE:N]`
(`modules/rag.py:126-134`) are prompt-construction labels the model sees,
not what ships to the client — what ships is `[cite:N]` markers
(`rag.py:819` citation_pattern), converted client-side to plain `[N]`
(`services/assistant.ts` `formatResponseText`). Today's rendering is: the
full response as one prose blob with inert `[N]` markers embedded in the
text, plus a **separate** "Sources:" list of clickable citation chips
below the whole message (`ExplainAssistant.tsx` ~line 570 onward) — a
reader has to manually match a bracketed number in the paragraph to a chip
in the footer list.

The fix is smaller than it sounds, because the component to do it right
already exists and is already used elsewhere in the app:
`components/lab-interpreter/CitationTooltip.tsx` renders a small
numbered, accessible (hover **and** focus, `role="tooltip"`,
`aria-label`) badge that shows the citation's source text inline, used
today in `InterpretedResultCard.tsx` / `PanelInterpretationDashboard.tsx`
but never wired into the chat flow. Given the `sentences` field proposed
above (`{text, citation_indices}[]`), rendering becomes: map sentences to
`<span>{sentence.text}</span>` followed by one `<CitationTooltip>` per
`citation_indices` entry, inline, at the point the sentence ends — replacing
today's single flat text block. The citation tooltip's content should
extend slightly for chat use: alongside the existing `citation.text`
snippet, add the same `citationTarget()`-computed deep link
(`ExplainAssistant.tsx:59-77` already does this work for the footer chips)
so tapping a citation opens `PageImageOverlay` at the right page/bbox — see
Section 3.

### Wireframe sketch — agent-trace surface

```
┌─────────────────────────────────────────────────────────────────┐
│ Explain Assistant                              [Local model ▾]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  You  "Is my LDL cholesterol trending up?"                       │
│                                                                   │
│  ┌─ Asclexis ─────────────────────────────────────── 0:02 ─────┐ │
│  │ ○ plan     chose: compute_trend(ldl_cholesterol)     0.04s  │ │
│  │ ● act      compute_trend → 4 points, rising            0.12s│ │
│  │ ○ reflect  enough grounding → draft                    0.01s│ │
│  │ ○ draft    composing…                          (running)   │ │
│  │ ○ guard    —                                                │ │
│  │                                          [ hide steps ▲ ]   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Asclexis ────────────────────────────────────────────────┐ │
│  │ Your verified LDL cholesterol has risen across your        │ │
│  │ verified results ⓵.  Your most recent value was            │ │
│  │ 142 mg/dL, collected 2026-08-03 ⓶.                          │ │
│  │                                                              │ │
│  │            [⓵ Your Results — trend, 4 points →]             │ │
│  │            [⓶ Your Results — Aug 3 draw, p.2 →]             │ │
│  │                                          [ show steps ▼ ]   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Asclexis · ESCALATE ───────────────────────────────────── ┐ │
│  │  ⚕  This is a question for your doctor or pharmacist.       │ │
│  │     Asclexis can explain what your verified results say,   │ │
│  │     but it can't advise on diagnosis, treatment, or         │ │
│  │     medication decisions. Please bring this question to     │ │
│  │     your clinician.                                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ Asclexis · ABSTAIN ────────────────────────────────────── ┐ │
│  │  🔍  There isn't enough verified information in your        │ │
│  │      record to explain this yet.                            │ │
│  │      [ Go to Verify → 2 documents awaiting review ]          │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

Notes on the sketch:

- The step tray (`○ plan / ● act / ○ reflect / ○ draft / ○ guard`) is
  **collapsed by default after the run completes** — this matches the
  "progressive disclosure" prior art cited above and the app's own
  existing "Progressive disclosure: advanced fields collapsed by default"
  IA principle (`docs/02_frontend_accessibility_plan.md`, Verification
  Workbench section). While the run is *in flight*, it's expanded by
  default (this is the direct replacement for today's static three-dot
  bubble) so the "is it stuck?" anxiety this research was asked to
  design against has a real, truthful answer instead of an ambiguous
  loading animation. Once the answer lands, it collapses to a one-line
  summary ("5 steps · 1.2s") that expands on click — visible for anyone
  who wants to audit it, invisible for anyone who doesn't.
- Node labels (`plan`/`act`/`reflect`/`draft`/`guard`) are technical; the
  patient-facing UI should translate them ("Deciding what to check" /
  "Looking up your results" / "Checking that's enough" / "Writing the
  answer" / "Double-checking sources") — a small copy layer, not a
  redesign, and one that should go through the same brand-voice review as
  any other UI string (no "smart," no implied certainty).
- The escalate/abstain cards use distinct icon glyphs (⚕/🔍 stand in for a
  proper icon-set choice) and explicitly avoid the shared amber card style
  used for `modelUnavailable`/unverified-data banners today, so the three
  don't visually collide.
- `[⓵ Your Results — trend, 4 points →]` citations are inline per-sentence
  (via `CitationTooltip`), not a trailing flat list — this is the "per
  Section 2 sub-finding" fix.

---

## 3. Data-control surfaces

Track 7 is specifying the audit log, data inventory, and provenance-viewer
*data model and API*; this section is how those surfaces should look and
feel, designed against what already exists in the frontend.

**Confirmed today:** zero audit-related frontend code exists
(`grep -rli audit src/frontend/src` returns nothing outside this research),
matching the brief's Gap 7. The only existing "what does the app hold"
surface is `components/settings/BackupCard.tsx` (export/backup) and
`DangerZone.tsx` (delete) — both of which are exemplary *copy* to imitate
(see the brand guidelines' own model: "describe the mechanism, then let the
conclusion follow," `docs/brand/brand-guidelines.md` §4) but neither shows
the user anything about what the *agent* did.

**Provenance viewer — real machinery already exists, reuse it directly.**
`components/PageImageOverlay.tsx` renders a document page image with a
scaled bounding-box highlight from `[x0,y0,x1,y1]` page coordinates,
correctly handling image-load races, revoked object URLs, and a graceful
fallback when no bbox exists. It's currently wired into
`VerificationWorkbench.tsx` for observation/entity provenance. This is
**exactly** the "lineage view from a chart point back to a PDF page" the
brief asks for — it does not need to be built, only *reached* from more
places: a trend chart point (Section 4), an interpreted-result card, and
the new per-sentence citation tooltip (Section 2) should all be able to
open the same `PageImageOverlay` in a consistent panel (a Radix `Dialog`
sheet, most naturally — `@radix-ui/react-dialog` is already a dependency)
rather than each building its own provenance view.

**Audit log — legible to a non-technical patient.** The failure mode to
avoid is what most "activity log" UIs look like: a raw table of
timestamps, route names, and JSON. Design principles for this surface,
informed by the brand voice rules in Section 4 of
`docs/brand/brand-guidelines.md` ("state mechanisms, not reassurances"):

- **Group by conversation/run, not by row.** One agent chat turn produced
  N audit rows (plan/act/reflect/draft/guard) internally; the patient
  should see one entry — "Asked about LDL cholesterol · looked at 4 lab
  results · Aug 15, 2:03pm" — that expands into the same step-tray
  component from Section 2's wireframe. **One component, two entry
  points** (live during a chat, historical in the audit log) — this
  reduces the actual net-new UI work to build for this surface once the
  step-tray exists.
- **Plain-language verbs for each tool**, matching the node-label
  translation from Section 2 ("looked at your lab results," never
  "invoked `query_observations`").
- **Every entry says what it did NOT do**, not just what it did — given
  the read-only invariant (`modules/agent/__init__.py`: agent is read-only
  over clinical data), the audit log gets to make a genuinely reassuring,
  *verifiable* claim: "This only read your records — nothing was changed
  or sent anywhere." That's the same rhetorical move as the
  `DangerZone.tsx` model: state the mechanism (read-only tools, local
  inference) and let the conclusion follow, rather than asserting "your
  data is safe."

**"What do you know about me" inventory.** This is a distinct surface from
the audit log (inventory = current state; audit = history of actions) and
should be structured as categories the patient already recognizes from the
app's own IA (`docs/02_frontend_accessibility_plan.md`'s five nav areas:
documents, observations, medications, care tasks, chat history/memory) —
each with a count and a one-tap path to view/export/delete that category,
rather than a single undifferentiated list. This directly extends the
existing `Export` page pattern rather than inventing a new one.

---

## 4. Charts

### Current state: two divergent implementations of the same chart

`TrendsDashboard.tsx` (the Trends page) and
`components/lab-interpreter/InterpretedTrendChart.tsx` (the Interpret page)
both render a recharts `LineChart` for the same underlying trend data, and
they disagree on the one clinically important detail:

- `TrendsDashboard.tsx` (lines ~464-480): reference range shown as **two
  independent dashed `ReferenceLine`s** at `ref_low`/`ref_high` — no fill,
  no visual "zone."
- `InterpretedTrendChart.tsx` (lines ~127-152): reference range shown as a
  **shaded `ReferenceArea`** between `ref_low` and `ref_high`
  (`fill="#7BA387" fillOpacity={0.08}`) *plus* the same dashed lines with
  "Low"/"High" text labels.

The second is unambiguously the better pattern for a clinical trend — a
shaded band reads instantly as "the normal zone," where two independent
dashed lines require the reader to infer the region between them. The
brand guidelines already name a single canonical `TrendChart` component in
their "Core Components" list (`docs/brand/brand-guidelines.md`
§"Core Components": *"`TrendChart` — Animated line draw on load, interactive
hover states with value callouts"*) — that component doesn't exist yet as
a shared abstraction; two pages independently reimplemented it and drifted.
**Consolidating these into one `components/charts/TrendChart.tsx`** (reused
by both pages, parameterized by height/margin only) is pure risk reduction:
it's not a library change, and it fixes a real inconsistency a patient
could plausibly notice ("why does the same lab value chart differently in
two places").

### Accessible alternative — required by the app's own plan, missing today

`docs/02_frontend_accessibility_plan.md`: *"Chart view must include:
keyboard-navigable legend / data table view / generated textual summary."*
`TrendsDashboard.tsx` has the textual summary (`trendData.summary` +
latest-value line) but **no data table view** and no separate
keyboard-navigable legend (there's only one series per chart, so "legend"
is less critical, but the missing table is a real, testable gap against
the app's own written requirement). Recommend a `<details>`-disclosed
`<table>` beneath each chart — date, value, unit, flag — sourced from the
exact `chartData`/`trendData.data_points` array already in memory, so this
is a rendering addition, not a data-fetching one.

### Export

`ChartExport.test.tsx` and `TrendsDashboard.tsx`'s
`renderSvgToCanvas`/`handleExportPNG`/`handleExportSVG` (lines 51-99,
158-180) already implement PNG/SVG export by serializing the rendered SVG,
drawing it into a canvas, and triggering a download — solid, dependency-free
(no extra library), and tested. No change recommended here beyond moving it
into the consolidated `TrendChart` component alongside the shading fix, so
`InterpretedTrendChart.tsx` gets export for free instead of needing its own
copy.

### Stay-or-move: recharts

**Recommendation: stay.** The alternatives researched for 2026:

- **visx** — low-level D3+React primitives; accessibility and irregular
  time-series handling become entirely the app's own responsibility to
  build (no ARIA out of the box)
  [[React chart libraries 2026 — LogRocket](https://blog.logrocket.com/best-react-chart-libraries-2026/)].
  For a two-chart-implementation app that already has a working, tested
  recharts setup, this is a strictly worse trade: more code to write and
  maintain for the same visual result.
- **Observable Plot** — excellent grammar-of-graphics ergonomics for
  exploratory/ad hoc charting, not built for embedding as interactive
  React components with hover tooltips and export wired to app state the
  way `TrendsDashboard` needs; better suited to a future
  data-science/analyst surface than this patient-facing trend view.
- **ECharts** — canvas-based, built for 100k+-point datasets and real-time
  updates [[same source]]; lab trends here are, per the brief itself,
  *sparse and irregular* (a handful of draws over months/years), which is
  exactly the case recharts's SVG-per-point model handles well and where
  ECharts's canvas/large-N optimizations buy nothing.
- **Accessibility across libraries**: *"Recharts ships first-class ARIA
  roles on series and data points"* versus visx handing you raw SVG to
  annotate yourself
  [[same source]]. Recharts already being the more accessible-by-default
  choice among the alternatives, combined with zero migration cost, makes
  "stay" the actual right call, not just the convenient one — this
  matches CLAUDE.md's instruction that "stay" needs a real argument, and
  the argument is: irregular/sparse time series is recharts's strong
  suit, not its weakness, and every real gap found (shading, table
  fallback, duplication) is a usage problem in this codebase, not a
  library limitation.

Sources: [8 Top React Chart Libraries 2026 — Querio](https://querio.ai/articles/top-react-chart-libraries-data-visualization),
[Best React chart libraries 2026 — LogRocket](https://blog.logrocket.com/best-react-chart-libraries-2026/).

---

## 5. Stack currency

Verified current versions (web search, September 2026) against the
repo's baseline (`package.json`):

| Package | Repo has | Current | Verdict |
|---|---|---|---|
| `framer-motion` | `^10.18.0` | Renamed **Motion**, v12, `motion/react` import [[motion.dev](https://motion.dev/)] | Rename-only migration eventually; not urgent (Section below) |
| `react` / `react-dom` | `^18.2.0` | 19.2.8, React Compiler stable since Oct 2025 [[react.dev changelog](https://react.dev/blog/2025/10/07/react-compiler-1)] | Not now — see below |
| `tailwindcss` | `^3.4.1` | 4.3.3, Rust engine, CSS-native `@theme` [[migration guide 2026](https://www.digitalapplied.com/blog/tailwind-css-v4-migration-new-features-guide)] | Quantified, deferred — see below |
| `@tanstack/react-query` | `^5.17.0` | v5, actively released (5.102.7 in Aug 2026) — same major | No action; already current-generation |
| `zustand` | `^4.4.7` | Zustand ecosystem consensus still favors it for client state alongside TanStack Query for server state [[2026 state-management guidance](https://reactnativerelay.com/article/modern-state-management-react-native-zustand-tanstack-query)] | v4→v5 minor version bump, low-risk, low-priority |
| `@radix-ui/react-*` | individually pinned (`^1.0.5`–`^2.0.6`) | Individual packages now considered legacy-shaped; Radix unified all primitives into one `radix-ui` package as of Feb 2026 [[shadcn/ui changelog](https://ui.shadcn.com/docs/changelog/2026-02-radix-ui)]. `@radix-ui/react-dialog` itself is at 1.1.4 | Version drift on individual packages is real but each is a low-risk, isolated bump — not a coordinated migration |
| `vite` | `^7.3.0` | Current major already | No action |
| `vitest` | `^4.0.16` | Current major already | No action |
| `typescript` | `^5.3.3` | — | Behind by roughly 2 minor releases at most; low priority, verify separately |

### React 18 → 19: not now

**What it buys:** the stable React Compiler (auto-memoization, removing
hand-written `useMemo`/`useCallback` — this codebase has a moderate amount
of that, e.g. `ExplainAssistant.tsx`'s `useMemo` for `suggestedQuestions`
and `activeModelSummary`), the `use()` hook, and Actions/`useActionState` —
none of which this codebase currently needs: data fetching is already
handled by React Query (not raw `use()` + Suspense), and there are no
form-heavy flows crying out for Actions that aren't already served by
React Query mutations.

**What it costs:** framer-motion 10.18 predates React 19 — an upgrade
requires bumping the animation library in the same pass (coupling this to
the Motion rename below) and re-verifying all 23 files that touch it;
Radix's React 19 compatibility work was reported as having "moved slowly"
post-acquisition [[shadcn/ui changelog discussion](https://ui.shadcn.com/docs/changelog/2026-02-radix-ui)],
meaning the four Radix primitives in use (`dialog`, `dropdown-menu`,
`slot`, `tabs`, `tooltip`) each need individual verification, not a
blanket assumption of compatibility; `@testing-library/react` 16.3.2 and
the vitest 4 setup would need a compatibility pass too. This is a
multi-day cross-cutting change with no functional payoff for this specific
app today. **Verdict: worth doing eventually** (React 18 will age out of
security-relevant support windows eventually), **not worth doing now**.

### Tailwind v3 → v4: quantified, still deferred

The migration mechanics for *this specific config* are genuinely simple:
`tailwind.config.js` has no custom plugins (`postcss.config.js` confirms:
just `tailwindcss` + `autoprefixer`, nothing else), and its `extend` block
is entirely declarative — colors, font families, spacing, radii, shadows,
one small `keyframes` block — exactly the shape v4's `@theme` CSS-native
config is designed to absorb via the official `npx @tailwindcss/upgrade`
codemod [[Tailwind v4 migration guide 2026](https://www.digitalapplied.com/blog/tailwind-css-v4-migration-new-features-guide)].
Real, non-automatable costs specific to this repo:

- **92 non-test `.ts`/`.tsx` files** to sweep for any `bg-gradient-to-*`
  usage — v4 renames this family to `bg-linear-to-*`
  [[migration guide, "most common breaking change"](https://www.digitalapplied.com/blog/tailwind-css-v4-migration-new-features-guide)];
  the repo has at least one confirmed use
  (`layout/Sidebar.tsx`: `bg-gradient-to-br from-accent to-accent/80`) and
  likely more across cards/badges given the "layered transparencies for
  depth" brand direction.
- **Dark mode is presently inert** — `tailwind.config.js` defines
  `dark.surface`/`dark.ink` color tokens but there's no `darkMode`
  strategy configured, and only **one** file in the whole app
  (`components/ui/Skeleton.tsx`) uses a `dark:` variant at all. v4 changes
  how dark-mode variants are declared; migrating this now means migrating
  a feature that isn't functionally wired up yet, which is wasted motion
  — recommend deferring the dark-mode question entirely until product
  decides whether dark mode ships, rather than migrating unused
  scaffolding.
- Effort estimate for this codebase specifically: **one to two days**
  (run the codemod, sweep 92 files for the gradient rename and any
  `theme()` function calls in CSS, re-run the full vitest suite + a visual
  spot-check of the ~16 pages) — small, but for zero product-facing
  benefit on a localhost-only build where Tailwind's build-time
  performance gains (its main selling point) don't move any metric this
  app is measured on. **Verdict: worth doing eventually** (v3 will stop
  receiving updates at some point), **not worth doing now** — flag for
  revisit if/when React 19 forces a broader dependency refresh anyway,
  since bundling the two reduces total churn.

### Motion (framer-motion rename): the one "soon, not now" that's nearly free

Because the API is unchanged and only the package name/import path moved
(`framer-motion` → `motion`, `motion/react`)
[[Framer Motion Becomes Independent](https://fireup.pro/news/framer-motion-becomes-independent-introducing-motion)],
this is close to a pure rename across the 23 touching files — genuinely
low-risk relative to the other two. It's still sequenced third here
because doing it *alongside* the token-table work in Section 1 (which
touches the same files) is more efficient than a standalone pass, not
because it's individually risky.

---

## 6. Accessibility

`docs/02_frontend_accessibility_plan.md` targets **WCAG 2.2 AA**-shaped
behaviors. Verified current: **WCAG 2.2 remains the current W3C
Recommendation** used for compliance as of 2026; **WCAG 3.0 is still a
Working Draft**, with a Candidate Recommendation not expected before late
2027 and final Recommendation status "no earlier than 2028/2029"
[[WCAG 3.0 vs 2.2 guide 2026](https://www.webability.io/blog/wcag-3-0-explained)].
So the plan's stated target is still the correct one to hold; no version
update needed there.

### What the plan documents as already fixed (2026-02-12 audit)

Tablist/tab roles on the panel selector, `aria-live="polite"` loading
states, `aria-pressed`/`aria-label`s on export toggles, and framer-motion
animations already respecting `useReducedMotion()` — all confirmed
consistent with what this track independently found reading the same
components (Section 1).

### Gaps found by this track, beyond what the plan's own audit covers

1. **Chart accessible-alternative requirement not met.** Covered in
   Section 4 — the plan requires a data table view; `TrendsDashboard.tsx`
   doesn't have one.
2. **No i18n.** `index.html:2` hardcodes `<html lang="en">`; no
   `react-intl`/`next-intl`/`formatjs`/ICU-message-format dependency
   exists in `package.json`; every user-facing string in the 92 non-test
   source files is inline JSX English. For an app whose stated user
   population explicitly includes non-English speakers
   (`docs/02_frontend_accessibility_plan.md` "UX goals": "optimize for
   ... non-medical users"), this is a real gap, though a large one to
   close — retrofitting i18n onto ~90 files of inline strings is a
   substantial, separate initiative, not an incremental fix, and is
   listed as "worth doing eventually" in Recommendations rather than
   proposed as scoped work here.
3. **Color-only status risk is mostly, not entirely, avoided.** The
   brand guidelines are explicit and correct that `status.*` colors
   "must never be used decoratively" and that `critical`/`attention`
   share the same hex so *"colour alone never distinguishes them —
   always pair a status colour with a label"* (`docs/brand/
   brand-guidelines.md` §6). Spot-checking components against this rule:
   `StatusBadge`-shaped usages generally do pair icon + text (confirmed
   in `ExplainAssistant.tsx`'s error/insufficient-context banners, which
   use `AlertCircle`/`XCircle`/`Info` icons alongside color). The Section
   2 proposal for abstain/escalate cards explicitly follows this same
   rule. No violation found in the files read for this track, but a full
   sweep of every `TrendsDashboard`/`InterpretedResultCard` abnormal-flag
   indicator (`is_abnormal`, `flag`) was outside this track's file budget
   — recommend Track 1 or a dedicated a11y pass grep for `is_abnormal`
   render sites and confirm each pairs an icon/text label, not only a
   color class.
4. **Font scaling / 200% zoom**: the plan's QA checklist requires this be
   verified but the plan doesn't record a result the way the 2026-02-12
   audit table does for other items — this reads as a checklist item
   awaiting its own verification pass, not a known-fixed or known-broken
   state. Flagging as open rather than claiming either outcome.
5. **Keyboard navigation for the agent-trace UI proposed in Section 2**
   needs to be designed in from the start, not retrofitted: the step tray
   must be reachable and expandable via keyboard (a native `<details>`/
   `<summary>` pair, or a properly `aria-expanded`-managed button, not a
   div with an onClick), and the inline `CitationTooltip` badges — already
   correctly keyboard-focusable via `onFocus`/`onBlur` in the existing
   component — set the pattern to follow for any new interactive citation
   markers embedded in flowing text.

### Screen readers, keyboard nav, low vision — what's already right to build on

The existing patterns worth explicitly preserving in every new surface
this track proposes: `role="status"` + `aria-live="polite"` on loading
states (already the house pattern per the 2026-02-12 audit and directly
reusable for the agent-trace step tray's live region), `role="tablist"`/
`role="tab"`/`aria-selected` for panel selectors, `min-h-target`/
`min-w-target` 44px utility classes already defined in `globals.css` for
touch targets, and a real `*:focus-visible` ring tied to the accent color
(`globals.css` `@layer base`). None of these need to be invented for the
agent-trace or data-control surfaces — they need to be *applied* to them,
consistently.

Sources: [WCAG 2.2 current status, 2026](https://accesstive.com/blog/wcag-2-2-vs-wcag-3-0/),
[WCAG 3.0 Explained — timeline](https://www.webability.io/blog/wcag-3-0-explained).

---

## Motion token table (consolidated)

See Section 1 for full derivation and rationale. This is the exportable
constant set:

| Token | Value |
|---|---|
| `duration.instant` | `0ms` |
| `duration.fast` | `120ms` |
| `duration.base` | `200ms` |
| `duration.slow` | `320ms` |
| `duration.chart` | `600ms` |
| `ease.standard` | `cubic-bezier(0.2, 0, 0, 1)` |
| `ease.exit` | `cubic-bezier(0.4, 0, 1, 1)` |
| `spring.snap` | `stiffness 420, damping 34` |
| `spring.settle` | `stiffness 260, damping 26` |
| `distance.sm` | `4px` |
| `distance.md` | `12px` |
| `stagger.tight` | `40ms` |
| **Policy** | Reduced motion = `duration.instant` for all state changes, not a softer/shorter version of the same motion. Clinical values never tween — final value renders immediately, always. |

---

## Recommendations

Ordered by value-per-effort, highest first. **Understand** column marks
whether the change is cosmetic (visual polish only) or changes what a user
can actually understand about their own data/the agent's behavior — per
the brief's explicit ask to keep these distinct.

| # | Change | Files touched | Understand? | Impact | Effort | Risk | Breaks tests? |
|---|---|---|---|---|---|---|---|
| 1 | Return `run_id` + `terminal` on `ChatResponse` (backend, coordinate with Track 1/3); render distinct abstain/escalate cards | `src/backend/api/assistant.py` (backend, out of this track's write scope), `pages/ExplainAssistant.tsx` | **Changes understanding** — patient can now tell "not enough data" from "ask your doctor" | High — directly serves the brief's "highest-value new surface" | Low (1-line backend field additions + one new frontend branch) | Low — additive fields, no existing contract removed | No — additive `ChatResponse` fields are backward compatible; existing tests keep passing unmodified |
| 2 | Wire existing `CitationTooltip` into chat citations, inline per-sentence (needs backend `sentences` field, #1's sibling) | `pages/ExplainAssistant.tsx`, `components/lab-interpreter/CitationTooltip.tsx` (reuse, maybe relocate to `components/ui/` or `components/shared/`), backend `guard.py`/`assistant.py` | **Changes understanding** — a patient can verify which sentence came from which source, not just "somewhere in this list" | High — this is the "per-sentence citation" ask directly | Low-Medium (component exists; wiring + one backend field) | Low | No — new rendering path around existing citation data |
| 3 | Consolidate `TrendsDashboard`'s `ReferenceLine`-only chart and `InterpretedTrendChart`'s `ReferenceArea` version into one shared `components/charts/TrendChart.tsx` with shaded band + export | `pages/TrendsDashboard.tsx`, `components/lab-interpreter/InterpretedTrendChart.tsx` → new `components/charts/TrendChart.tsx` | **Changes understanding** — consistent, clinically-clearer reference-range shading everywhere it appears | Medium-High — fixes a real, visible inconsistency | Medium (careful refactor, both call sites have slightly different data shapes to reconcile) | Low-Medium — must not regress `ChartExport.test.tsx` | Likely yes, intentionally — `ChartExport.test.tsx` and any `InterpretedTrendChart` tests need updating to point at the new shared component; that's expected refactor churn, not a regression |
| 4 | Add accessible data-table fallback under `TrendsDashboard`'s chart, closing the plan's own stated requirement | `pages/TrendsDashboard.tsx` (or the new shared `TrendChart.tsx` from #3 — do together) | **Changes understanding** — screen-reader/low-vision users get real access to the same data sighted users see in the chart | Medium | Low (data already in memory as `chartData`) | Low | No — additive `<details>`/`<table>` |
| 5 | Live step tray during an in-flight chat turn, replacing the static three-dot "Searching..." bubble (needs backend `steps`/polling endpoint from #1's wire contract) | `pages/ExplainAssistant.tsx`, new small polling hook in `services/assistant.ts`; backend: expose `RunLog` during a run (Track 1/3) | **Changes understanding** — this is the core "make the agent legible" ask | High | Medium-High (real backend work to expose in-flight state; frontend polling hook + step-tray component, reusable from #1's terminal card work) | Medium — touches the live chat path; needs careful handling of poll-vs-final-response races | No, if additive; a poll endpoint is new, not a replacement |
| 6 | Motion token table adoption across the 23 `framer-motion`-touching files (Section 1) | `components/ui/Motion.tsx` + 22 call sites, `tailwind.config.js` | Cosmetic (consistency, not new capability) | Medium — reduces visual drift, makes reduced-motion behavior uniform | Medium (mechanical but touches every animated component) | Low | No — same visual outcomes, renamed constants |
| 7 | Reuse the audit-log step-tray component (from #5) as a historical, grouped-by-run audit log entry (Track 7's data model, this track's rendering) | New `pages/`/`components/` surface, depends on Track 7's audit API | **Changes understanding** — first user-facing "what did the agent do with my data" surface | High | Medium (mostly rendering; depends on Track 7 landing the API first) | Low | No — new page |
| 8 | Reuse `PageImageOverlay` as a shared provenance panel reachable from trend-chart points and interpreted-result cards, not just the Verification Workbench | `components/PageImageOverlay.tsx` (wrap in a shared Dialog), `pages/TrendsDashboard.tsx`, `components/lab-interpreter/InterpretedResultCard.tsx` | **Changes understanding** — "where did this number come from" reachable from every place a number appears, not just one page | Medium-High | Low-Medium (component already correct; mostly new entry points + a Radix Dialog wrapper) | Low | No |
| 9 | Correct the brand guidelines' "smooth number transitions for trend changes" line to prohibit animating clinical values (Section 1, policy point 2) | `docs/brand/brand-guidelines.md` (docs, not `src/frontend/`) | N/A — policy correction | Low effort, meaningful correctness fix | Trivial | None | N/A |
| 10 | Prototype CSS View Transitions API for route-level page transitions as a Motion/framer-motion alternative | `components/ui/Motion.tsx` (`PageTransition`), `App.tsx`/router config | Cosmetic | Low-Medium — removes a dependency's runtime cost for one specific transition, no user-facing behavior change | Medium (needs its own spike; interacts with React Router's mount/unmount timing) | Medium — must confirm it doesn't regress on any currently-supported browser; graceful no-op fallback needed and verified | Possibly — `PageTransition`-dependent tests may need updating |
| 11 | Motion (framer-motion) rename to `motion`/`motion/react` | All 23 files currently importing `framer-motion` | Cosmetic (dependency hygiene) | Low | Low-Medium (mechanical rename; sequence with #6 to touch the same files once) | Low-Medium — verify Motion v12's React 18 compatibility before committing (not assumed here; confirm in the PR) | Possibly — any test mocking `'framer-motion'` (e.g. `ChartExport.test.tsx`'s `vi.mock('framer-motion', ...)`) needs its mock path updated to `'motion/react'` too |
| 12 | Tailwind v3 → v4 migration | `tailwind.config.js` → CSS `@theme`, all `bg-gradient-to-*` usages across ~92 files | Cosmetic | Low-Medium — build performance only, no product-facing payoff on a localhost build | Medium (1-2 days per Section 5's estimate) | Low-Medium — codemod-assisted, but full regression pass needed | Possibly — any test asserting exact class names |
| 13 | React 18 → 19 upgrade | Every component (compiler is opt-in but React itself is a full bump), `package.json`, all Radix/framer-motion/testing-library version pins | Cosmetic (Compiler perf, not new user-facing capability today) | Low near-term (buys nothing this app currently needs) | High — coordinated bump across React, Radix, Motion, testing-library | Medium-High — Radix's React 19 work reported as slow post-acquisition; needs a dedicated verification pass, not a routine bump | Likely — full suite re-run required, some tests may need updating for React 19's stricter warnings |

**Not recommended:** shared-element transitions across route boundaries
(Section 1) — real engineering cost for a cosmetic win, when the existing
plain navigation to `/verify?observation=...` is already legible and
tested. **Ask before starting:** none of the above touch
`interpret_safety.py`/`redaction.py`/`faithfulness.py`/`verifier_agent.py`/
auth/encryption directly, but #1, #2, and #5 require backend changes to
`api/assistant.py` and `modules/agent/graph.py`/`guardrails/guard.py` —
those are Track 1/3's files, not this track's to write; this track's job
was to specify the frontend design and the minimal wire contract it needs,
which is what the "Understand?" = yes rows above do.

---

## Sources

- [Motion (prev Framer Motion) — official site](https://motion.dev/)
- [Framer Motion Becomes Independent: Introducing Motion](https://fireup.pro/news/framer-motion-becomes-independent-introducing-motion)
- [React v19 – React blog](https://react.dev/blog/2024/12/05/react-19)
- [React Compiler v1.0 – React blog](https://react.dev/blog/2025/10/07/react-compiler-1)
- [React 19.2 – React blog](https://react.dev/blog/2025/10/01/react-19-2)
- [Tailwind CSS v4 Migration: New Features Guide 2026](https://www.digitalapplied.com/blog/tailwind-css-v4-migration-new-features-guide)
- [WCAG 2.2 vs WCAG 3.0: What Changes & When to Plan in 2026](https://accesstive.com/blog/wcag-2-2-vs-wcag-3-0/)
- [WCAG 3.0 Explained: What Changes & When It's Actually Required (2026)](https://www.webability.io/blog/wcag-3-0-explained)
- [View Transitions API: Browser Support, Features, Limits](https://www.testmuai.com/learning-hub/view-transitions-api-browser-support/)
- [Cross-Document View Transitions Are Finally Cross-Browser: A Practical Guide for 2026](https://trade-assistance.com/blog/cross-document-view-transitions-mpa-2026/)
- [8 Top React Chart Libraries for Data Visualization in 2026 — Querio](https://querio.ai/articles/top-react-chart-libraries-data-visualization)
- [Best React chart libraries in 2026 — LogRocket](https://blog.logrocket.com/best-react-chart-libraries-2026/)
- [Agent UX: UI Design for AI Agents in 2026](https://fuselabcreative.com/ui-design-for-ai-agents/)
- [What Is Agent Observability? A 2026 Developer Guide — MLflow](https://mlflow.org/articles/what-is-agent-observability-a-2026-developer-guide/)
- [Agent observability: the complete guide for 2026 — Braintrust](https://www.braintrust.dev/articles/agent-observability-complete-guide-2026)
- [Designing Practical Interface Patterns for Agentic AI Transparency](https://mrsinternet.com/designing-practical-interface-patterns-for-agentic-ai-transparency/)
- [February 2026 - Unified Radix UI Package — shadcn/ui changelog](https://ui.shadcn.com/docs/changelog/2026-02-radix-ui)
- [Modern State Management: Zustand + TanStack Query, 2026](https://reactnativerelay.com/article/modern-state-management-react-native-zustand-tanstack-query)

### Repo files read for this track (evidence base, not exhaustive)

`src/frontend/package.json`; `src/frontend/tailwind.config.js`,
`postcss.config.js`; `src/frontend/src/styles/globals.css`;
`src/frontend/src/hooks/useReducedMotion.ts`;
`src/frontend/src/components/ui/Motion.tsx`;
`src/frontend/src/components/layout/{AppLayout,Sidebar,TopBar}.tsx`;
`src/frontend/src/components/lab-interpreter/{CitationTooltip,
InterpretedTrendChart,InterpretedResultCard,PanelInterpretationDashboard}.tsx`;
`src/frontend/src/components/medication-coach/BadgeToast.tsx`;
`src/frontend/src/components/PageImageOverlay.tsx`;
`src/frontend/src/components/settings/DangerZone.tsx`;
`src/frontend/src/pages/{ExplainAssistant,TrendsDashboard,
VerificationWorkbench}.tsx`; `src/frontend/src/services/assistant.ts`;
`src/frontend/src/__tests__/ChartExport.test.tsx`;
`docs/02_frontend_accessibility_plan.md`; `docs/brand/brand-guidelines.md`;
`src/backend/modules/agent/{graph,state,schemas,metrics}.py`;
`src/backend/modules/agent/guardrails/{templates,groundedness}.py`;
`src/backend/modules/agent/nodes/draft.py`; `src/backend/api/assistant.py`;
`src/backend/core/llm/{provider,ollama_provider,llama_cpp_provider}.py`.
