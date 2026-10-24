# Safety Mode build plan: the stricter-mode toggle (2026-10-24)

**Last Updated:** 2026-10-24
**Owner:** repository owner
**Status:** PROPOSED (Opus L0 planner). Docs only. No owner approval is recorded here; the owner's answer it plans from is recorded in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md) row SAFETY-MODE-BEHAVIOUR (prompt 51).
**Base measured:** `origin/main` @ `29dca22` (2026-10-24). Every `file:line` below was re-read on that tree; they match the [SAFETY-MODE-REAL research](../research/2026-10-23-safety-mode-real/00-README.md), which was read on `fe9581f`.
**Refresh Trigger:** a merge of any `SAFETY-MODE-*` row; PR #264 (B-3) merging or closing; an owner answer to SAFETY-LABEL-WORDING or SAFETY-MODE-DIFF; a new migration in `src/backend/migrations/profile/versions/`; a change to any `file:line` cited below.

## 1. What the owner chose

Owner answer to SAFETY-MODE-BEHAVIOUR (prompt 51, multi-select), verbatim from the owner-decisions row: **"Stricter checks"**, **"Always-on citations view"**, **"Verified-only data"**. "Template-only explanations" was not chosen and is not planned.

The question offered "Stricter checks" with the text "answers need a higher verified share (0.75, not 0.6)". This plan uses **0.75** as that option stated. It is not a measured value; if the owner wants another number above 0.6, only the constant in SAFETY-MODE-STRICT changes.

**L0 reading, not the owner's words:**

- The question asked "Which behaviour should ON mean? You may pick more than one". So the plan has **one switch per profile**, and turning it on turns on all three behaviours together. There are no separate switches.
- The constraint the question stated is kept for every row: **OFF is exactly today's behaviour, and ON is only ever stricter.** Each backend row proves both halves through HTTP.

## 2. Rows and order

| Row | Option | Kind | Depends on | Est h |
|---|---|---|---|---|
| [SAFETY-MODE-SETTING](#safety-mode-setting) | shared | PRODUCT (backend; profile migration) | — | 4.5 |
| [SAFETY-MODE-STRICT](#safety-mode-strict) | A | PRODUCT (backend; safety thresholds, ask-first files read only) | SAFETY-MODE-SETTING | 7 |
| [SAFETY-MODE-VERIFIED](#safety-mode-verified) | D (backend) | PRODUCT (backend; interpretation routes) | SAFETY-MODE-SETTING; after SAFETY-MODE-STRICT (same file) | 9 |
| [SAFETY-MODE-TOGGLE](#safety-mode-toggle) | shared (UI) | PRODUCT (frontend) | SAFETY-MODE-SETTING, UI-SHELL | 2.5 |
| [SAFETY-MODE-CITATIONS](#safety-mode-citations) | C | PRODUCT (frontend; citations display) | SAFETY-MODE-TOGGLE, UI-PG-ASK, UI-PG-RESULTS, UI-PROVENANCE | 4.5 |
| [SAFETY-MODE-VERIFIED-FE](#safety-mode-verified-fe) | D (frontend) | PRODUCT (frontend; lab-value display) | SAFETY-MODE-VERIFIED, SAFETY-MODE-TOGGLE, UI-PG-RESULTS, UI-RIBBON | 3 |

Total 30.5 h. The three backend rows can start now. The frontend rows wait for the UI rows that own their files: UI-SHELL owns `SafetyModeToggle.tsx`, UI-PG-ASK owns `ExplainAssistant.tsx`, and UI-PG-RESULTS replaces `TrendsDashboard.tsx` and `LabInterpreter.tsx` with `ResultsPage.tsx`. Building on today's pages would be rewritten a wave later.

**Shared rules for every row:**

- **No row edits `modules/faithfulness.py`, `modules/verifier_agent.py` or `modules/interpret_safety.py`.** All three are read only. If a build finds it must edit one, it stops and L0 asks SAFETY-MODE-DIFF using the draft wording in the [research](../research/2026-10-23-safety-mode-real/00-README.md#safety-mode-diff-draft-wording-ask-first-files). No row touches auth or encryption code.
- **Route tests go through HTTP** with `tests/support/routes.py::route_client` and a real in-memory profile database (CLAUDE.md §4). Stubs sit below `rag.query`, at the layer `tests/test_safe_interp_grounded.py:83-101` uses. A stub on `rag.query` itself would decide `is_valid` and hide whether a threshold is wired.
- **Every backend row proves both halves:** OFF gives an identical body for the setting absent, set false, and a profile migrated from `015_data_donation`; ON withholds or refuses something that OFF serves, and never the reverse.
- **Agent answer cache:** none of these rows changes the default agent path's output, so the cache key (`modules/agent/cache.py:43-50`) is unchanged. A row that finds it does change agent output must add the mode to that key, or it stops.
- **Audit** on every new route and every refusal, with no question, answer or value text in the row.

## 3. Rows

### SAFETY-MODE-SETTING

**Kind:** PRODUCT (backend; profile migration). **Depends on:** — . **Gate:** SAFETY-MODE-BEHAVIOUR answered (prompt 51). **Ask-first:** none.

**Files.**

- `be/migrations/profile/versions/016_strict_safety_mode.py` (new): `down_revision = "015_data_donation"`, one column `strict_safety_mode` Boolean, `nullable=False`, `server_default="0"`, so every existing profile stays OFF. The downgrade drops the column.
- `be/models/model_settings.py`: the mapped column after `streaks_hidden` (`:141`), with an `# Added by 016_strict_safety_mode.` comment, following that precedent.
- `be/api/assistant.py`: `GET` and `PATCH /assistant/safety-mode`, modelled on `/assistant/memory-settings` (`:548`, `:570`), with the same auth dependencies and `ProfileDbSession`, and an audit row on `PATCH` (action `safety_mode_updated`, the new boolean only). Add one helper, `async def is_strict_safety_mode(profile_db) -> bool`, that the other rows import; it returns `False` when there is no settings row. `api/interpretations.py` already imports from `api.assistant` (`:20`), so no new module is needed.
- `be/tests/test_safety_mode_setting.py` (new): HC-SMS-001…006.

**Tests (RED first, all through `route_client`).**

- HC-SMS-001: a new profile reads `{"strict_safety_mode": false}`.
- HC-SMS-002: a `PATCH` to true persists and is read back.
- HC-SMS-003: the value survives a lock and unlock. Lock through the route, unlock, then `GET`.
- HC-SMS-004: profile isolation. Setting it on profile A leaves profile B false.
- HC-SMS-005: the `PATCH` writes exactly one audit row, which contains no free text.
- HC-SMS-006: a `GET` without auth gets the same status as `/memory-settings` without auth.
- Migration: `test_migration_heads.py` must still show one profile head. Add one upgrade-from-015 case if the existing migration tests have a pattern for it (`test_data_donation.py` or `test_gamification_settings.py` carry the 015 and 014 precedents).

**Acceptance.** `scripts/pyslot.sh env HF_HUB_OFFLINE=1 python -m pytest tests/test_safety_mode_setting.py tests/test_migration_heads.py -q` is green. The collected count rises by the number of new tests, and the PR reports the delta. **Est:** 4.5 h.

### SAFETY-MODE-STRICT

**Kind:** PRODUCT (backend; safety thresholds). **Depends on:** SAFETY-MODE-SETTING. **Never beside:** B-3 (#264 touches `assistant.py`, `interpretations.py`, `rag.py`), RAG-TIMEOUT-ANSWER (#317), SAFETY-MODE-VERIFIED (`interpretations.py`). **Gate:** SAFETY-MODE-BEHAVIOUR answered "Stricter checks" (0.75 as the option stated). **Ask-first:** none edited. `faithfulness.py` and `verifier_agent.py` are read only and are constructed with different arguments.

**Design (research Option A).** When the setting is on, the chat legacy fallback and `interpret-grounded` use a RAG module built with `FaithfulnessConfig(min_overall_score=STRICT_MIN_SCORE)` **and** `VerificationConfig(min_faithfulness_score=STRICT_MIN_SCORE)`, where `STRICT_MIN_SCORE = 0.75` lives in `api/assistant.py` beside `get_rag_module`. Both configs are plain dataclass arguments (`faithfulness.py:55`, `verifier_agent.py:85`). OFF keeps today's module and its 0.6 objects.

**Files.**

| File | Change |
|---|---|
| `be/modules/rag.py:940` (`if verification_metadata.faithfulness_score < 0.6:`) | Compare against `self.faithfulness_scorer.config.min_overall_score` instead of the literal. The default stays 0.6, so OFF is identical. |
| `be/api/assistant.py:217` (`get_rag_module`), `:225`, `:230` | Add `get_strict_rag_module()` (a cached singleton built like `:217`, with the two strict configs). Leave the 0.6 literals alone. |
| `be/api/assistant.py:1055` (`result = await rag.query(`) | Choose the strict module when `is_strict_safety_mode` is true. `_legacy_serve_or_abstain` (`:236`) already turns an invalid result into the abstention. |
| `be/api/interpretations.py:529` (`rag_result = await rag.query(`) | Choose the strict module the same way. |
| `be/api/interpretations.py:598` (`if rag_result.prohibited_advice:` block) | New `elif strict and not rag_result.is_valid:` branch, as an `elif` so the `ESCALATE_TEMPLATE` path always wins with exactly one `prohibited_blocked` audit row. It replaces the segments with `ABSTAIN_TEMPLATE` (`modules/agent/guardrails/templates.py:20`), sets `full_response = ABSTAIN_TEMPLATE` (recurring-failures #2: the withheld text must not ship in `full_response`), clears `verification`, and writes one audit row through `_audit_interpretation` (`:38`) with no text. |
| `be/api/assistant.py:1400` (`"min_faithfulness_score": 0.6,`) | The status route reports the threshold in force for this profile. |
| `be/tests/test_safety_mode_strict.py` (new) | HC-SMA-001…007 |

**Tests (RED first; `route_client`; stubs as in `test_safe_interp_grounded.py:83-101`).**

- HC-SMA-001: chat with the agent disabled and `_run_verification_pipeline` returning `faithfulness_score=0.70`. OFF serves the answer; ON returns `ABSTAIN_TEMPLATE`.
- HC-SMA-002: `interpret-grounded`, same stub with no failed claims. OFF returns the segments with `is_valid` true. ON returns `ABSTAIN_TEMPLATE` as the segment and as `full_response`, empty verification, and one audit row.
- HC-SMA-003: a score of 0.50 on the chat fallback is withheld in both modes. On `interpret-grounded` with OFF it still serves segments with `is_valid` false, which is today's behaviour.
- HC-SMA-004: a prohibited answer under ON still returns `ESCALATE_TEMPLATE` with exactly one `prohibited_blocked` audit row and no strict-abstain row.
- HC-SMA-005: OFF is identical for the setting absent, false, and a 015-migrated profile. Compare the whole response bodies.
- HC-SMA-006: the real verification pipeline, following `_real_verifying_rag` (`test_safe_interp_grounded.py:368`), with only retrieval and generation stubbed. A fixture that scores between 0.6 and 0.75 under the real pipeline passes under OFF and is withheld under ON. This is the test that would notice a strict `FaithfulnessConfig` paired with a 0.6 `VerificationConfig`, or the reverse.
- HC-SMA-007: the default agent chat path returns an identical body under OFF and ON (no reach, as the research says).

**Acceptance.** The new file plus `tests/test_safe_interp_grounded.py` and every existing test that imports `get_rag_module` stay green. `git diff origin/main...HEAD -- src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/modules/interpret_safety.py` is empty and pasted in the PR. **Honest limit for the PR body:** a patient on the default agent path sees no change. **Est:** 7 h.

### SAFETY-MODE-VERIFIED

**Kind:** PRODUCT (backend; interpretation routes). **Depends on:** SAFETY-MODE-SETTING. **Order:** after SAFETY-MODE-STRICT, never beside it (both edit `api/interpretations.py`). **Gate:** SAFETY-MODE-BEHAVIOUR answered "Verified-only data". **Ask-first:** none. `verifier_agent.py` is read only and not called differently.

**Design (research Option D).** When the setting is on, all **six** handlers in `api/interpretations.py` gate on `Observation.user_verified`. Gating only the two observation `POST` routes would let the toggle overclaim (recurring-failures #9).

| Handler (line on `29dca22`) | ON behaviour |
|---|---|
| `generate_interpretation` `:380` | Refuse before `interpret_observation` (`:426`) if the observation is unverified. The refusal must come **before** the stored-row shortcut, because `interpret_observation` returns a stored row when `force_regenerate` is false (`:392`, `:417`). |
| `generate_grounded_interpretation` `:453` | Refuse before `:486` (not only the `:511` question-text branch). |
| `generate_panel_interpretation` `:689` | Refuse before `interpret_panel` (`:715`) if any observation in the panel at `collected_at` is unverified. |
| `batch_generate_interpretations` `:806` | Add each unverified id to `failed` as `{"observation_id": id, "error": "Verify this result first"}` before `:865`. Verified ids still succeed. The response shape (`BatchInterpretResponse`, `:366`) is unchanged. |
| `get_interpretation` `:626` | Refuse when the linked observation is unverified, even if a row stored under OFF exists. |
| `get_recent_interpretations` `:743` | Omit interpretations whose observation is unverified. |

**Refusal contract:** HTTP **409** with `detail = {"code": "observation_unverified", "message": "Verify this result first."}`. It is the same on all four refusing routes so the frontend handles one shape. Each refusal writes one audit row through `_audit_interpretation` with no value text. If Task 0 finds 409 is already used by these routes for another meaning, it picks another status, names it in the PR, and keeps one shape. Use one private helper in `interpretations.py`, used by all six; there is no new module.

**Files.** `be/api/interpretations.py` (the six handlers and one helper), `be/tests/test_safety_mode_verified.py` (new, HC-SMD-001…008).

**Tests (RED first; `route_client`; seed one verified and one unverified observation).**

- HC-SMD-001: OFF, `POST …/interpret` and `…/interpret-grounded` succeed for both observations (today's behaviour).
- HC-SMD-002: ON, both `POST` routes refuse the unverified id with the 409 shape and succeed for the verified one.
- HC-SMD-003: ON with `force_regenerate=false` and a row stored under OFF for the unverified id: the `POST` still refuses and does not return the stored row.
- HC-SMD-004: ON, the `GET …/interpretation` for the unverified id refuses although the row exists; OFF returns it.
- HC-SMD-005: ON, `GET /recent` lists only the verified interpretation; OFF lists both.
- HC-SMD-006: ON, `POST /batch` puts the unverified id in `failed` with the error text and the verified id in `successful`, and the generation stub is never called for the unverified id.
- HC-SMD-007: ON, the panel route with one unverified member is refused; an all-verified panel succeeds.
- HC-SMD-008: every refusal writes exactly one audit row with no value text.

**Acceptance.** The new file plus every existing `tests/test_*interp*` file stay green. In the PR body, list the six handlers with the test that covers each. **Honest limit:** chat sees no change (it is already verified-only, `rag.py:390`, `:609`). Interpretations created under OFF are hidden while ON, not deleted. **Est:** 9 h.

### SAFETY-MODE-TOGGLE

**Kind:** PRODUCT (frontend). **Depends on:** SAFETY-MODE-SETTING, UI-SHELL (which creates `fe/components/layout/SafetyModeToggle.tsx` as the disabled switch of [revamp plan §3.6](2026-10-23-frontend-revamp-plan.md#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real)). **Gate:** SAFETY-MODE-BEHAVIOUR answered. SAFETY-LABEL-WORDING is open and non-blocking: the label stays "Stricter safety mode" unless the owner answers otherwise. **Ask-first:** none.

**Files.** `fe/components/layout/SafetyModeToggle.tsx`, `fe/services/assistant.ts` (`getSafetyMode`, `setSafetyMode`, beside the memory-settings calls), `fe/hooks/useSafetyMode.ts` (new; a React Query hook), `fe/__tests__/safety-mode-toggle.test.tsx` (new, HC-SMT-001…004), `e2e/safety-mode.spec.ts` (new, HC-SMT-005, real backend).

**Behaviour.** The switch is enabled and reflects the server value (`role="switch"`, `aria-checked`). A change sends a `PATCH` and then invalidates the interpretation, recent-interpretation and trend queries so nothing shown under OFF stays on screen under ON. The note under the switch replaces "Not available yet." with L0 wording that the owner can change under SAFETY-LABEL-WORDING: "On: answers need more verified support, sources are always shown, and only values you have checked are interpreted or charted. The standard safety checks always run." The words "Safety Mode ON/OFF" do not return (§3.6). The value is per profile: the lock flow's existing query reset drops it, and it refetches after unlock.

**Tests.** HC-SMT-001: renders the server value. HC-SMT-002: a click sends the `PATCH` and invalidates the three query keys. HC-SMT-003: a failed `PATCH` restores the previous state and shows the error toast. HC-SMT-004: the accessible name and the `aria-checked` value. HC-SMT-005 (e2e): switch on, reload, still on; switch off, reload, still off. The `KNOWN_A11Y` list in `e2e/accessibility.spec.ts` gains no entry. **Est:** 2.5 h.

### SAFETY-MODE-CITATIONS

**Kind:** PRODUCT (frontend; citations display). **Depends on:** SAFETY-MODE-TOGGLE (`useSafetyMode`), UI-PG-ASK (`ExplainAssistant.tsx`), UI-PG-RESULTS (`InterpretedResultCard.tsx`), UI-PROVENANCE (`SourceTrace.tsx`, `CitationTooltip.tsx`). **Gate:** SAFETY-MODE-BEHAVIOUR answered "Always-on citations view". **Ask-first:** none.

**Behaviour (research Option C).** With the mode on, each answer and interpretation shows its sources expanded inline: document name, page, and the quoted text. The content comes from UI-PROVENANCE's components; this row does not duplicate them. With the mode off, today's chips and popovers are unchanged.

**Honesty rule (data gap, research Option C).** On the default agent path the API's `text_snippet` is a locator or id, not a quote (`be/api/assistant.py:853`). The expanded view labels it as a location ("Source: …, page …") and never shows it as a quotation. Quote styling is used only when a real quote is present (the legacy and interpretation paths). Adding real quotes to agent citations is a backend change outside this row.

**Files.** `fe/pages/ExplainAssistant.tsx` (the citation block only; **keep `data-testid="chat-message"` and `data-role`**, which E2E-UIFULL-CI ROUTES-002 depends on), `fe/components/lab-interpreter/InterpretedResultCard.tsx` (citation block), `fe/__tests__/safety-mode-citations.test.tsx` (new, HC-SMC-001…004), `e2e/safety-mode.spec.ts` (HC-SMC-005 appended).

**Tests.** HC-SMC-001: mode on, an answer with two citations renders both expanded with name and page. HC-SMC-002: a locator-only citation is never rendered with quote styling. HC-SMC-003: mode off renders exactly today's chips (snapshot of the role tree, not pixels). HC-SMC-004: an interpretation card under the mode. HC-SMC-005 (e2e): the mode on, ask one question, sources visible without a click; `chat-message` and `data-role` selectors still resolve. **Est:** 4.5 h.

### SAFETY-MODE-VERIFIED-FE

**Kind:** PRODUCT (frontend; lab-value display). **Depends on:** SAFETY-MODE-VERIFIED (the 409 shape), SAFETY-MODE-TOGGLE, UI-PG-RESULTS (`ResultsPage.tsx`), UI-RIBBON (`RangeRibbon.tsx` draws the points). **Gate:** SAFETY-MODE-BEHAVIOUR answered "Verified-only data". **Ask-first:** none.

**Behaviour.** With the mode on, unchecked values are listed under the chart but not plotted, with a one-line note ("2 unchecked values are not plotted. Check them in Review values."). Today's unverified marking, invariant I-13 from W-3 (`contracts.md:33`), stays for the mode off. An interpretation request answered with the 409 `observation_unverified` shape shows a "Verify this result first" state with a link to Review values, not an error toast. With the mode off, today's display is unchanged.

**Files.** `fe/pages/ResultsPage.tsx`, `fe/components/results/RangeRibbon.tsx` (a `hideUnverified` prop), `fe/__tests__/safety-mode-verified.test.tsx` (new, HC-SMV-001…004), `e2e/safety-mode.spec.ts` (HC-SMV-005 appended).

**Tests.** HC-SMV-001: mode on, an unverified point is absent from the plot and present in the list. HC-SMV-002: mode off, both are plotted with today's unverified marker. HC-SMV-003: a 409 `observation_unverified` renders the verify-first state with the Review link. HC-SMV-004: any other error still shows today's error path. HC-SMV-005 (e2e, real backend): seed one unverified value, turn the mode on, and the interpret action shows verify-first. **Est:** 3 h.

## 4. What this plan does not do

- No code, test, threshold or count slot changes, and no gate is signed.
- The 0.75 value comes from the option text the owner chose. It was not measured.
- PR #264 (B-3) is a draft and is not read as main. If it merges before SAFETY-MODE-STRICT, that row rebases onto it and Task 0 re-reads the judge's threshold. If that threshold lives in an ask-first file, SAFETY-MODE-DIFF is needed for it.
