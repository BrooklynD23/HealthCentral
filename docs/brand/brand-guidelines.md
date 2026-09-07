# Asclexis — Brand Guidelines

**Owner:** Product
**Last Updated:** 2026-08-01
**Refresh Trigger:** A change to the prohibited patterns in `src/backend/modules/interpret_safety.py`, or to the colour tokens in `src/frontend/tailwind.config.js`.

This is mostly a safety document. The largest brand risk for this product is not
visual inconsistency — it is copy that implies medical advice. That is both a
compliance risk and a violation of an invariant the codebase already enforces.
Read section 3 before writing any user-facing string.

---

## 1. The name

**Asclexis.** Two readings, deliberately:

- *Asclepius* — the Greek god of medicine; the root shared by much of the health
  industry (Asclepius' rod is the profession's own symbol). It places the
  product in health without claiming a clinical role.
- *ask* — the load-bearing reading. This product exists to help someone **ask
  better questions about their own results**, not to answer them
  authoritatively. When the two readings pull against each other in a piece of
  copy, the "ask" reading wins.

The rename replaces "HealthCentral", which collided with the existing
health-media brand healthcentral.com — see
[`../plans/2026-07-07-rename-audit-and-shortlist.md`](../plans/2026-07-07-rename-audit-and-shortlist.md).

## 2. What the product is, in one sentence

> A local-first companion that explains your own medical results, with
> citations, and never diagnoses.

Every word of that sentence is a constraint we already ship: *local-first* (no
network calls in product code paths), *your own* (per-profile encrypted vaults),
*with citations* (`rag.py` labels retrieved context `[YOUR_RESULTS:N]` for the
patient's own measured values and `[REFERENCE:N]` for general medical
knowledge), *never diagnoses* (section 3).

## 3. The hard boundary — explains, never diagnoses

This is not a stylistic preference. `src/backend/modules/interpret_safety.py`
defines `InterpretationSafetyGuard.PROHIBITED_PATTERNS`, a compiled regex list
that fails validation of any interpretation containing:

| Category (as named in code) | What it matches |
|---|---|
| `diagnostic_language` | `you have …`, `you are diagnosed with …`, `diagnosis of …`, `this means/indicates/confirms you have` |
| `certainty_claims` | `definitely/certainly/clearly have/indicates/shows`, `always means`, `never means`, `100%`, `absolutely`, `guaranteed` |
| `dosing_recommendation` | `take <n> mg/mcg/g/ml/units`, `medication dosage`, `dose adjustment`, `increase…dose`, `decrease…dose` |
| `medication_advice` | `prescribe`, `prescription`, `should take`, `must take`, `need to take`, `start taking`, `stop taking`, `discontinue …` |
| `emergency_advice` | `call 911`, `go to the ER`, `emergency room`, `seek immediate`, `medical emergency`, `life-threatening` |

The same class also *requires* two of three disclaimer signals in every
interpretation (`consult`; `healthcare provider|doctor|physician`;
`educational|informational|general information`), and its standard disclaimer
reads: *"This information is for educational purposes only. Please consult your
healthcare provider for personalized medical advice."*

`src/backend/tests/test_interpret_safety_adversarial.py` fails if any of this
regresses — including tests for conditional phrasing, case/dosing obfuscation,
and "doctor voice" role confusion. **Brand copy that implies otherwise puts
writing and code in conflict, and the code wins.** If a slogan needs the guard
relaxed, the slogan is wrong.

## 4. Voice — state mechanisms, not reassurances

The model is the profile-deletion copy in
`src/frontend/src/components/settings/DangerZone.tsx`:

> "This removes your encrypted health record from this device: every document,
> lab result, medication and note, along with any backups this app is holding
> for you. Your encryption key is destroyed, which makes the data unreadable.
> This cannot be undone, and there is no cloud copy to restore from."

Why it works: it never says "don't worry" or "your data is safe". It says *what
happens* — the key is destroyed, therefore the data is unreadable — so the user
can decide for themselves. It also stops exactly where the truth stops: the
file's own header notes we "do not claim the bytes are overwritten, because SSD
wear-levelling makes that claim false."

The same file, on a checkbox the app cannot verify: *"I confirm I have a copy,
or I don't want one"* — with the code comment "the app cannot verify that a copy
was kept, and the wording should not imply otherwise."

Rules that follow:

1. **Describe the mechanism, then let the conclusion follow.** Not "secure" —
   *what* makes it secure.
2. **Never claim what the app cannot verify.** Say who attests to what.
3. **State limits in the same breath as capabilities.** The disclaimer is part
   of the sentence, not a footnote bolted on.
4. **Hedge honestly, not defensively.** "Your result is below the reference
   range your lab printed" is precise. "May possibly potentially indicate" is
   noise.
5. **Second person for the user's data, never for their body.** "Your results",
   "your record" — not "your condition".

## 5. Prohibited constructions

Never write, in UI copy, marketing, docs, or model prompts:

- **Diagnosis:** "you have…", "this indicates…", "this confirms…", "diagnosis
  of…". Write instead: "this value is outside the reference range on your
  report; your healthcare provider can tell you what it means for you."
- **Dosing:** "take…", "increase your…", "you should stop taking…". There is no
  compliant rewrite; drop the claim and point at the clinician.
- **Prognosis:** "this will lead to…", "left untreated this becomes…". The
  product has no basis for a forward-looking claim about a person.
- **Certainty:** "definitely", "guaranteed", "always means", "100%".
- **Feature names containing "wise", "smart", or "doctor"** (and "…Dx",
  "…Diagnosis"). The 2026-07-07 shortlist flagged exactly this when screening
  `Labwise`: *"'wise' mildly implies advice — review against the non-diagnostic
  boundary"*, and the same document says to avoid anything implying
  diagnosis/treatment "per the product's safety boundary". A feature called
  "Smart Insights" makes a claim the guard would reject in prose.

## 6. Palette

The tokens below are what `src/frontend/tailwind.config.js` actually defines.
Document what exists; do not invent new ramps.

| Group | Token | Hex |
|---|---|---|
| `surface` | `DEFAULT` / `elevated` / `muted` / `sunken` | `#FAFAF8` / `#FFFFFF` / `#F5F5F3` / `#EEEDEB` |
| `ink` | `DEFAULT` / `secondary` / `tertiary` / `disabled` | `#1F1F1F` / `#6B6B6B` / `#9A9A9A` / `#BFBFBF` |
| `accent` | `DEFAULT` / `subtle` / `hover` / `pressed` | `#2D7D6F` / `#E8F4F2` / `#256B5F` / `#1E5A50` |
| `status` | `caution` / `caution-subtle` | `#D4A574` / `#FDF6EF` |
| `status` | `attention` / `attention-subtle` | `#C9857A` / `#FDF2F0` |
| `status` | `verified` / `verified-subtle` | `#7BA387` / `#F0F7F2` |
| `status` | `info` / `info-subtle` | `#6B8CAE` / `#F0F4F8` |
| `status` | `critical` / `critical-subtle` | `#C9857A` / `#FDF2F0` (same hex as `attention`) |
| `dark.surface` | `DEFAULT` / `elevated` / `muted` | `#1A1A1A` / `#242424` / `#2E2E2E` |
| `dark.ink` | `DEFAULT` / `secondary` / `tertiary` | `#F5F5F5` / `#A0A0A0` / `#6B6B6B` |

Type: `font-display` Fraunces Variable, `font-body` Source Sans 3 Variable,
`font-mono` JetBrains Mono. Focus ring: `shadow-focus`, derived from the accent.

**`status.*` colours carry meaning and must never be used decoratively.** They
say *attention*, *caution*, *verified*, *info*, *critical* — a reader who has
learned that `status-attention` means "this needs a look" will read it that way
on a marketing page too. `DangerZone` uses `text-status-attention` and
`border-status-attention/40` for exactly this reason. If you want a warm
accent, use `accent.*` or a `surface` tone. Note also that `critical` and
`attention` currently resolve to the same hex, so colour alone never
distinguishes them — always pair a status colour with a label.

## 7. What this document is not

Not a logo specification. Not a marketing-site style guide. Not an icon set,
motion spec, or illustration library. Those do not exist yet, and inventing them
here would create claims nobody is maintaining. When one of them is built, it
gets its own file under `docs/brand/` and this document links to it.
