# Safety Mode build plan: the stricter-mode toggle (2026-10-24)

**Last Updated:** 2026-10-28 (SAFETY-MODE-TOGGLE delta after the Task 0 stop on #401: files licensed, header layout, owner answer SAFETY-NOTE-WORDING "Specific, staged")
**Owner:** repository owner
**Status:** PROPOSED (Opus L0 planner). Docs only. No owner approval is recorded here; the owner's answer it plans from is recorded in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md) row SAFETY-MODE-BEHAVIOUR (prompt 51).
**Base measured:** `origin/main` @ `29dca22` (2026-10-24). Every `file:line` below was re-read on that tree; they match the [SAFETY-MODE-REAL research](../research/2026-10-23-safety-mode-real/00-README.md), which was read on `fe9581f`.
**Refresh Trigger:** a merge of any `SAFETY-MODE-*` row; PR #264 (B-3) merging or closing; an owner answer to SAFETY-LABEL-WORDING or SAFETY-MODE-DIFF; a new migration in `src/backend/migrations/profile/versions/`; a change to any `file:line` cited below.

## 1. What the owner chose

Owner answer to SAFETY-MODE-BEHAVIOUR (prompt 51, multi-select), verbatim from the owner-decisions row: **"Stricter checks"**, **"Always-on citations view"**, **"Verified-only data"**. "Template-only explanations" was not chosen and is not planned.

The question offered "Stricter checks" with the text "answers need a higher verified share (0.75, not 0.6)". This plan uses **0.75** as that option stated. It is not a measured value: the research calls it "a proposal, to be set or measured before the build" ([research](../research/2026-10-23-safety-mode-real/00-README.md), Tradeoffs). The owner may still confirm or change it; any number above 0.6 changes only the constant in SAFETY-MODE-STRICT.

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
| [SAFETY-MODE-VERIFIED-FE](#safety-mode-verified-fe) | D (frontend) | PRODUCT (frontend; lab-value display) | SAFETY-MODE-VERIFIED, SAFETY-MODE-TOGGLE, SAFETY-MODE-CITATIONS, UI-PG-RESULTS, UI-RIBBON | 3 |

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
- `be/api/assistant.py`: `GET` and `PATCH /assistant/safety-mode`, modelled on `/assistant/memory-settings` (`:548`, `:570`), with the same auth dependencies and `ProfileDbSession`, and an audit row on both routes: `GET` (a settings read, as AUDIT-READ-SCOPE (a) requires) and `PATCH` (action `safety_mode_updated`, the new boolean only). Add one helper, `async def is_strict_safety_mode(profile_db) -> bool`, that the other rows import; it returns `False` when there is no settings row. `api/interpretations.py` already imports from `api.assistant` (`:20`), so no new module is needed.
- `be/tests/test_safety_mode_setting.py` (new): HC-SMS-001…006.

**Tests (RED first, all through `route_client`).**

- HC-SMS-001: a new profile reads `{"strict_safety_mode": false}`.
- HC-SMS-002: a `PATCH` to true persists and is read back.
- HC-SMS-003: the value survives a lock and unlock. Lock through the route, unlock, then `GET`.
- HC-SMS-004: profile isolation. Setting it on profile A leaves profile B false.
- HC-SMS-005: the `GET` and the `PATCH` each write exactly one audit row, which contains no free text.
- HC-SMS-006: a `GET` without auth gets the same status as `/memory-settings` without auth.
- Migration: `test_migration_heads.py` must still show one profile head. Add one upgrade-from-015 case if the existing migration tests have a pattern for it (`test_data_donation.py` or `test_gamification_settings.py` carry the 015 and 014 precedents).

**Acceptance.** `scripts/pyslot.sh env HF_HUB_OFFLINE=1 python -m pytest tests/test_safety_mode_setting.py tests/test_migration_heads.py -q` is green. The collected count rises by the number of new tests, and the PR reports the delta. **Est:** 4.5 h.

### SAFETY-MODE-STRICT

**Kind:** PRODUCT (backend; safety thresholds). **Depends on:** SAFETY-MODE-SETTING. **Never beside:** RAG-TIMEOUT-ANSWER (#317), SAFETY-MODE-VERIFIED (`interpretations.py`). B-3 (#264 touches `assistant.py`, `interpretations.py`, `rag.py`) is a parked draft waiting on B-4, so it holds no files ([contracts](2026-10-15-build-program/contracts.md) §b rule 2, R-5): this row may build beside it, and #264 rebases onto this row when B-3 resumes. **Gate:** SAFETY-MODE-BEHAVIOUR answered "Stricter checks" (0.75 as the option stated). **Ask-first:** none edited. `faithfulness.py` and `verifier_agent.py` are read only and are constructed with different arguments.

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
| `be/tests/test_safety_mode_strict.py` (new) | HC-SMA-001…008 |

**Tests (RED first; `route_client`; stubs as in `test_safe_interp_grounded.py:83-101`).**

- HC-SMA-001: chat with the agent disabled and `_run_verification_pipeline` returning `faithfulness_score=0.70`. OFF serves the answer; ON returns `ABSTAIN_TEMPLATE`.
- HC-SMA-002: `interpret-grounded`, same stub with no failed claims. OFF returns the segments with `is_valid` true. ON returns `ABSTAIN_TEMPLATE` as the segment and as `full_response`, empty verification, and one audit row.
- HC-SMA-003: a score of 0.50 on the chat fallback is withheld in both modes. On `interpret-grounded` with OFF it still serves segments with `is_valid` false, which is today's behaviour.
- HC-SMA-004: a prohibited answer under ON still returns `ESCALATE_TEMPLATE` with exactly one `prohibited_blocked` audit row and no strict-abstain row.
- HC-SMA-005: OFF is identical for the setting absent, false, and a 015-migrated profile. Compare the whole response bodies.
- HC-SMA-006: the real verification pipeline, following `_real_verifying_rag` (`test_safe_interp_grounded.py:368`), with only retrieval and generation stubbed. A fixture that scores between 0.6 and 0.75 under the real pipeline passes under OFF and is withheld under ON. This is the test that would notice a strict `FaithfulnessConfig` paired with a 0.6 `VerificationConfig`, or the reverse.
- HC-SMA-008: the status route (`assistant.py:1400`) reports 0.6 under OFF and 0.75 under ON.
- HC-SMA-007: the default agent chat path returns an identical body under OFF and ON (no reach, as the research says).

**Acceptance.** The new file plus `tests/test_safe_interp_grounded.py` and every existing test that imports `get_rag_module` stay green. `git diff origin/main...HEAD -- src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/modules/interpret_safety.py` is empty and pasted in the PR. **Honest limit for the PR body:** a patient on the default agent path sees no change. **Est:** 7 h.

### SAFETY-MODE-VERIFIED

**Kind:** PRODUCT (backend; interpretation routes). **Depends on:** SAFETY-MODE-SETTING. **Order:** after SAFETY-MODE-STRICT, never beside it (both edit `api/interpretations.py`). **Gate:** SAFETY-MODE-BEHAVIOUR answered "Verified-only data". **Ask-first:** none. `verifier_agent.py` is read only and not called differently.

**Design (research Option D).** When the setting is on, all **six** handlers in `api/interpretations.py` that generate or return a patient interpretation gate on `Observation.user_verified`. The seventh route, `GET /knowledge/biomarker` (`:769`), reads public master-DB knowledge only and is correctly left out. Gating only the two observation `POST` routes would let the toggle overclaim (recurring-failures #9).

| Handler (line on `29dca22`) | ON behaviour |
|---|---|
| `generate_interpretation` `:380` | Refuse before `interpret_observation` (`:426`) if the observation is unverified. The refusal must come **before** the stored-row shortcut, because `interpret_observation` returns a stored row when `force_regenerate` is false (`:392`, `:417`). |
| `generate_grounded_interpretation` `:453` | Refuse before `:486` (not only the `:511` question-text branch). |
| `generate_panel_interpretation` `:689` | Refuse before `interpret_panel` (`:715`) if any panel member is unverified, where the members are selected **exactly as `interpret_panel` selects them** (`modules/interpret.py:326-335`: same profile, `analyte_canonical` in the panel definition, the whole calendar day of `collected_at`). Matching `collected_at` exactly would let unverified same-day values through. The refusal also comes before the stored `PanelInterpretation` shortcut (`interpret.py:345-358`). |
| `batch_generate_interpretations` `:806` | Add each unverified id to `failed` as `{"observation_id": id, "error": "Verify this result first"}` before `:865`. Verified ids still succeed. The response shape (`BatchInterpretResponse`, `:366`) is unchanged. |
| `get_interpretation` `:626` | Refuse when the linked observation is unverified, even if a row stored under OFF exists. |
| `get_recent_interpretations` `:743` | Omit interpretations whose observation is unverified, by joining `Observation` and filtering on `user_verified` **in the SQL query, before `.limit(limit)`** (`:755-759`); filtering after the limit returns a short page. |

**Refusal contract:** HTTP **409** with `detail = {"code": "observation_unverified", "message": "Verify this result first."}`. It is the same on all four refusing routes so the frontend handles one shape. Each refusal writes one audit row through `_audit_interpretation` with no value text. If Task 0 finds 409 is already used by these routes for another meaning, it picks another status, names it in the PR, and keeps one shape. Use one private helper in `interpretations.py`, used by all six; there is no new module.

**Files.** `be/api/interpretations.py` (the six handlers and one helper), `be/tests/test_safety_mode_verified.py` (new, HC-SMD-001…008).

**Tests (RED first; `route_client`; seed one verified and one unverified observation).**

- HC-SMD-001: OFF, `POST …/interpret` and `…/interpret-grounded` succeed for both observations (today's behaviour).
- HC-SMD-002: ON, both `POST` routes refuse the unverified id with the 409 shape and succeed for the verified one.
- HC-SMD-003: ON with `force_regenerate=false` and a row stored under OFF for the unverified id: both `POST …/interpret` and `POST …/interpret-grounded` still refuse and do not return the stored row.
- HC-SMD-004: ON, the `GET …/interpretation` for the unverified id refuses although the row exists; OFF returns it.
- HC-SMD-005: ON, `GET /recent` lists only the verified interpretation; OFF lists both. With `limit=1` and the unverified interpretation newest, ON still returns the verified one (proves the filter is before the limit).
- HC-SMD-006: ON, `POST /batch` puts the unverified id in `failed` with the error text and the verified id in `successful`, and the generation stub is never called for the unverified id.
- HC-SMD-007: ON, the panel route is refused when one member is unverified **at a different time on the same day** than `collected_at`, and also when a panel row stored under OFF exists with `force_regenerate=false`; an all-verified panel succeeds.
- HC-SMD-008: every refusal writes exactly one audit row with no value text.

**Acceptance.** The new file plus every existing `tests/test_*interp*` file stay green. In the PR body, list the six handlers with the test that covers each. **Honest limit:** chat sees no change (it is already verified-only, `rag.py:390`, `:609`). Interpretations created under OFF are hidden while ON, not deleted. **Est:** 9 h.

### SAFETY-MODE-TOGGLE

**Kind:** PRODUCT (frontend). **Depends on:** SAFETY-MODE-SETTING, UI-SHELL (which creates `fe/components/layout/SafetyModeToggle.tsx` as the disabled switch of [revamp plan §3.6](2026-10-23-frontend-revamp-plan.md#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real)). **Gate:** SAFETY-MODE-BEHAVIOUR answered. SAFETY-LABEL-WORDING was answered 2026-10-26 (**"Keep plan default (Recommended)"**), so the label stays "Stricter safety mode". That question covered only the wording "Until the safety toggle does something". The note for the working switch is set by SAFETY-NOTE-WORDING, answered 2026-10-28 (**"Specific, staged"**; see [Delta 2026-10-28](#delta-2026-10-28-task-0-stop-on-401)). **Waits for:** UI-PG-MEDS (#398), UI-PALETTE (#399) and SESSION-REENTRY Task 3 (#402) must merge. **Never beside:** POPOVER-OPEN-COST (#393; both edit `e2e/ui-shell.spec.ts`). **Ask-first:** none.

**Files.** `fe/components/layout/SafetyModeToggle.tsx`, `fe/services/assistant.ts` (`getSafetyMode`, `setSafetyMode`, beside the memory-settings calls), `fe/hooks/useSafetyMode.ts` (new; a React Query hook), `fe/__tests__/safety-mode-toggle.test.tsx` (new, HC-SMT-001…004), `e2e/safety-mode.spec.ts` (new, HC-SMT-005, real backend). Added 2026-10-28, each limited to the change named in the [delta](#delta-2026-10-28-task-0-stop-on-401): `e2e/ui-shell.spec.ts` (HC-UISH-006 only), `e2e/support/mockApi.ts` (one GET fixture), `fe/__tests__/SearchPage.test.tsx` (one module-level mock, only if still needed at Task 0), `fe/components/layout/TopBar.tsx` (the header's `lg` height class only). Here `e2e/` is `src/frontend/e2e/` and `fe/` is `src/frontend/src/`.

**Behaviour.** The switch is enabled and reflects the server value (`role="switch"`, `aria-checked`). A change sends a `PATCH` and then invalidates the interpretation, recent-interpretation and trend queries so nothing shown under OFF stays on screen under ON. The note under the switch, and the same note at the top of the phone popover, replaces "Not available yet. The standard safety checks always run." with the owner's stage-1 wording (SAFETY-NOTE-WORDING, [delta](#delta-2026-10-28-task-0-stop-on-401) item 7). The header grows to fit it (item 5). The words "Safety Mode ON/OFF" do not return (§3.6). The value is per profile: the lock flow's existing query reset drops it, and it refetches after unlock.

**Tests.** HC-SMT-001: renders the server value. HC-SMT-002: a click sends the `PATCH` and invalidates the three query keys. HC-SMT-003: a failed `PATCH` restores the previous state and shows the error toast. HC-SMT-004: the accessible name and the `aria-checked` value. HC-SMT-006 (delta item 4): in the unknown state, the switch is disabled and a click sends no `PATCH`. HC-SMT-005 (e2e): switch on, reload, still on; switch off, reload, still off; after `document.fonts.ready` at 1024 and 1440 px, the note's `scrollHeight` equals its `clientHeight` (no clipping, delta item 5). The `KNOWN_A11Y` list in `e2e/accessibility.spec.ts` gains no entry. **Est:** 2.5 h.

#### Delta 2026-10-28 (Task 0 stop on #401)

The build stopped at Task 0 ([PR #401 comment 6475047832](https://github.com/BrooklynD23/HealthCentral/pull/401#issuecomment-6475047832)). It needs three files outside the row, and it had two wording gaps. The owner then answered SAFETY-NOTE-WORDING (owner-decisions row SAFETY-NOTE-WORDING), and this delta now builds on that answer. Line numbers are on `origin/main` @ `d993c3d`; re-read them after #398 and #399 merge. Each licence names the only change it allows, so it does not depend on the line numbers.

**1. `e2e/ui-shell.spec.ts`, HC-UISH-006 only (`:491-550`).** These tests assert the disabled switch of [revamp plan §3.6](2026-10-23-frontend-revamp-plan.md#36-the-safety-rail-and-the-safety-toggle-until-safety-mode-real). This row replaces that switch by design, so changing the tests is a spec change, not a weakening. Every `ON`/`OFF` and "Safety Mode" assertion stays.

- Desktop test (`:497-514`): replace `toHaveAttribute('aria-disabled', 'true')` (`:512`) with `toBeEnabled()`. The `aria-checked` `'false'` assertion (`:511`) stays; it now checks the mocked server value. The accessible-description assertion (`:513`, `/standard safety checks always run/i`) stays unchanged. The title may say "enabled" instead of "disabled".
- Click test (`:516-530`, "clicking the disabled switch changes no DOM state"): delete it. Its premise is false once the switch works. HC-SMT-002 and HC-SMT-003 now hold its intent (a click sends one `PATCH`; a failure restores the state), along with HC-SMT-005 (real backend) and HC-SMT-006 (no `PATCH` from an unknown state). The 599 answer fails a test only when that test calls `guard.assertClean()`. The HC-UISH-006 tests do not; only the GATE G tests do (`:1013`, on every shell route, and `:1024`, on `/setup`). So the net that remains is that a `PATCH` sent **on page load** fails GATE G, because item 2 mocks only the `GET`. A `PATCH` sent on a click is covered by the HC-SMT tests, not by the mock harness. The PR body names the deleted test and these replacements.
- Phone test (`:539-549`): `:546` asserts only the sentence every stage keeps, `'The standard safety checks always run.'`, so later rows never edit this file. `:547` asserts the new last sentence of the long text (item 6). `:548` stays.
- The section comments (`:491-493`, `:533-535`) may change to match.
- Nothing else in the file changes:
  - not `PAGE_OVERFLOW` (#398);
  - not HC-UIOV-007 (#393);
  - not UI-PALETTE's licensed lines: `:165` `navigateTo('/search')` and `:635-636` HC-UISH-004 desktop, licensed in [L0 ruling 6475095462 on #399](https://github.com/BrooklynD23/HealthCentral/pull/399#issuecomment-6475095462);
  - not HC-UISH-009, whose stillness probe keeps `TOGGLE_NOTE` in `expected`;
  - not the geometry tests: HC-UISH-006 label clipping (`:557-580`) and HC-UISH-004 rows and overlap (`:645-680`) hold under item 5's layout. If one of them fails under that layout, stop and tell L0; do not edit it.

**2. `e2e/support/mockApi.ts`: one `shellFixtures` entry (`:312-339`).** Add `['/assistant/safety-mode', { strict_safety_mode: false }]`. If this row adds a `SafetyModeResponse` type to `fe/services/assistant.ts`, type the entry with it. The entry is GET only. The `PATCH` stays unmocked, so a `PATCH` sent on load gets 599 and fails GATE G (item 1). No other line changes.

**3. `fe/__tests__/SearchPage.test.tsx`: conditional.** The licence applies only if FE-SRCH-UI-003 still renders `<TopBar />` without a `QueryClient` at Task 0. Two other rows touch this test. UI-PALETTE (#399) changes FE-SRCH-UI-003 when the header search becomes the palette trigger. SESSION-REENTRY (#402) is licensed (L0 ruling on #402) to wrap FE-SRCH-UI-003's render in a `QueryClientProvider`. TOGGLE now waits for #402 to merge (item 8), so normally this file is not edited. The `vi.mock` licence below is a fallback, used only if Task 0 still finds no provider.

- If the licence applies, the only change is one module-level `vi.mock('@/hooks/useSafetyMode', …)` beside the existing `vi.mock('@/services/search', …)` (`:11-13`, the same pattern). It returns the off value and an idle mutation. No render call and no assertion changes.
- Task 0 also runs `grep -rln "TopBar\|AppLayout\|SafetyModeToggle" src/frontend/src/__tests__`. Any other test that renders the toggle without a `QueryClient` is a new stop, not a licence.
- On `d993c3d`, `ui-routes.test.tsx` renders the whole `App`, which has a provider (`App.tsx:197`), and mocks `apiGet` to `[]`. That is the unknown state of item 4.

**4. Unknown state: new test HC-SMT-006.** The value is unknown in three cases: the `GET` is pending, the `GET` has failed, or the body lacks a boolean `strict_safety_mode`.

- In the unknown state the switch is disabled and has `aria-checked="false"` (an ARIA switch has no mixed state). It also has `aria-busy="true"` while the request is pending.
- A click sends no `PATCH`.
- A failed load shows the existing error toast once: "Couldn't load the stricter safety mode setting." The switch stays disabled until a refetch succeeds.
- The note text does not change in the unknown state. The server enforces the stored mode whatever the switch shows, so an unknown state never makes the app less strict.
- HC-SMT-006 covers all three cases. For each, it asserts disabled, `aria-checked="false"` and zero `PATCH` calls after a click, and for the failed load it asserts that the toast appears once.

**5. Header layout for a 3-4 line note (`fe/components/layout/TopBar.tsx`, `fe/components/layout/SafetyModeToggle.tsx`).** The owner's option text says the wording "needs a header layout change for 3-4 lines". At `lg` the header is a fixed `lg:h-16` (`TopBar.tsx:25`), and the note column has a fixed `lg:w-96` (`SafetyModeToggle.tsx:19-23`).

- **Note height is fixed.** At `lg` the note gets a fixed line height and a fixed height of `N` lines (`leading-4` with `h-[calc(N*1rem)]`, or the token equivalents). `N` is the larger of two line counts, both measured at `lg:w-96`: the longest planned note (stage 3, item 7) in Source Sans, and the same note in the fallback face. Measured 2026-10-28, so **`N` = 4** (table below). The note keeps `lg:w-96`. The note's height then does not change across the font swap or between stages, so a later row changes only the text.
- **The header height is fixed too.** `TopBar.tsx:25` replaces `lg:h-16` with one fixed `lg` height that holds the switch row, the gap and the `N`-line note. `--shell-top-h` (`AppLayout.tsx:40`) already tracks the header for scroll-padding, so no other offset changes. Below `lg`, nothing changes: the note stays in the popover.
- **Measurement (2026-10-28, scratch worktree on `origin/main` @ `d993c3d`, nothing committed).** Method: a functional Playwright run of the real app at 1440 px with `installMockApi` and `seedMockSession` on `/inbox`. It set the real `[data-safety-toggle-note]` element's text and gave it `line-height: 16px` (`leading-4`). The note renders at 13 px and is 384 px wide. Lines = height ÷ 16. "Source Sans" means `Source Sans 3 Variable` was loaded. For "Fallback", the `.woff2` requests were aborted, and because this Linux box has neither Arial nor Liberation Sans for the `local()` sources at `globals.css:9-16`, Windows' `arial.ttf` was loaded with the same `size-adjust` and overrides. Arial is the metric twin of Liberation Sans. Not a stillness run.

  | Text | Chars | Source Sans | Fallback |
  |---|---|---|---|
  | Stage 1 (owner, verbatim) | 156 | 3 | 3 |
  | Stage 2 (item 7) | 201 | 3 | 3 |
  | Stage 3 (item 7) | 248 | 4 | 4 |
  | Round 1 stage 2 (dropped) | 222 | 4 | 4 |
  | Round 1 stage 3 (dropped) | 279 | **5** | 4 |

  So `N` = 4: the note box is 64 px at `lg` from this row on. Stage 1 leaves one empty line, which keeps the height still when later rows change only the text. The build re-measures stage 1 and stage 3 the same way at Task 0. If either face gives more than 4 lines, the build stops.
- **The limits.** If `N` > 4, stop and tell L0, because the owner's option said 3-4 lines. The text must never be clipped: HC-SMT-005 asserts that the note's `scrollHeight` equals its `clientHeight` after `document.fonts.ready` at 1024 and 1440 px.
- **Licence.** In `TopBar.tsx`, the header's `lg` height class only. In `SafetyModeToggle.tsx`, the note's `lg` classes and the comment at `:19-21`.
- **Stillness.** HC-UISH-003 and HC-UISH-009 must pass at the effective bounds on a quiet box. Run the precheck, then `/tmp/claude-1000/hold_slots.sh`. If the box is not quiet, stop with "blocked: tell L0 — quiet box" and list the commands.

**6. Wording gap (a): the phone popover's long text.** No owner answer decided it. SAFETY-NOTE-WORDING covers only the short note. Plan-level fix, in L0's wording: the first two sentences stay true, so only the third changes.

- Today (`SafetyModeToggle.tsx:55-57`): "Asclexis checks every answer for medical advice and against your own records. These checks are always on and cannot be turned off. A stricter mode is being designed; this switch will turn it on when it is ready."
- After this row: "Asclexis checks every answer for medical advice and against your own records. These checks are always on and cannot be turned off. This switch turns on a stricter mode for this profile. It never turns the standard checks off."

The new sentences say nothing about what the stricter mode does, so they stay true through every later row and no later row edits them. The owner can change this wording at any time; no gate is needed.

**7. Wording gap (b): the note, staged per the owner's answer.** The owner answered SAFETY-NOTE-WORDING with **"Specific, staged"**. The option text, verbatim:

> "On: AI explanations of a single result need more verified support, and values you haven't checked get no explanation. The standard safety checks always run." Each later update adds a clause. Most precise; needs a header layout change for 3-4 lines.


This replaces the plan's earlier note, "On: answers need more verified support, sources are always shown, and only values you have checked are interpreted or charted.", and this delta's first-draft text. Both overclaimed. One constant in the component feeds both the desktop note and the popover note.

| Stage | Set by | Note text | Status |
|---|---|---|---|
| 1 | SAFETY-MODE-TOGGLE (STRICT and VERIFIED are merged) | "On: AI explanations of a single result need more verified support, and values you haven't checked get no explanation. The standard safety checks always run." | the owner's words, verbatim; do not edit |
| 2 | SAFETY-MODE-CITATIONS | "On: AI explanations of a single result need more verified support, and values you haven't checked get no explanation. Answers and result cards show their sources. The standard safety checks always run." | L0 draft, one added sentence; Task 0 confirms it |
| 3 | SAFETY-MODE-VERIFIED-FE | "On: AI explanations of a single result need more verified support, and values you haven't checked get no explanation. Answers and result cards show their sources. The Results chart leaves out unchecked values. The standard safety checks always run." | L0 draft, one more added sentence; Task 0 confirms it |

Each later stage adds one short sentence before the last sentence, as the owner's option allows ("Each later update adds a clause"). Round 1 drafted longer clauses, but its stage 3 (279 characters) measured 5 lines in Source Sans, so the shorter sentences replace it (item 5). Each stage keeps "The standard safety checks always run." and contains no standalone `ON` or `OFF` (HC-UISH-006 checks this case-sensitively, so "On:" passes). Each later row adds its clause only when the clause is true of every surface it names. That row's Task 0 confirms it:

- **CITATIONS (stage 2).** The row licenses only `ExplainAssistant.tsx` (chat answers) and `InterpretedResultCard.tsx` (result cards). It does not license LabInterpreter's grounded explanation card or the panel dashboard. Task 0 lists every route that shows sources for an answer or an interpretation, and checks whether each one shows them without a click when the mode is on. If a surface the clause names is not covered, or a covered surface needs a different name, narrow the sentence ("Answers and result cards show their sources.") so it names only covered surfaces. If no accurate clause fits, stop and tell L0. Never ship a clause that names an uncovered surface.
- **VERIFIED-FE (stage 3).** The row hides unchecked points only in `ResultsPage.tsx` and `RangeRibbon.tsx`. It does not touch `InterpretedTrendChart` or `TrendsDashboard`. Task 0 lists every route that still plots observation values. If any route the patient can reach still plots unchecked values with the mode on, the sentence must name only the Results chart, as drafted ("The Results chart leaves out unchecked values."). If that route is also called "Results", or the clause cannot be made accurate, stop and tell L0.
- **Files.** Both rows gain `fe/components/layout/SafetyModeToggle.tsx` (the note constant only) and `fe/__tests__/safety-mode-toggle.test.tsx` (the note assertion only). Item 5 reserves the stage-3 height, so neither row changes layout. A sentence that no longer fits the reserved `N` = 4 lines in both faces (re-measure as in item 5) is a stop.

**8. Ordering.** The row waits until UI-PG-MEDS (#398, which holds `ui-shell.spec.ts` for the `PAGE_OVERFLOW` entry) and UI-PALETTE (#399, which holds `ui-shell.spec.ts` `:165` and `:635-636`, plus `SearchPage.test.tsx` FE-SRCH-UI-003) have **merged**. It also waits for SESSION-REENTRY Task 3 (#402, open `[claim:claude]`, which holds `SearchPage.test.tsx` and is licensed by L0 ruling to wrap FE-SRCH-UI-003 in a `QueryClientProvider`) to **merge**, and never runs beside it until then. It never runs beside POPOVER-OPEN-COST (#393, which holds `ui-shell.spec.ts` HC-UIOV-007). #393 is a draft, so RUNBOOK §4 check 5 (non-draft PRs) would not catch it. Task 0 reads #393's state with `gh pr view 393 --json state,isDraft,title`:

- Proceed if #393 is merged or closed, or if it is an open draft whose title starts with `[blocked:`, which means it is parked and its slot is released.
- Stop if its title starts with `[claim:` or it is not a draft.

Resume with `build-item {"id":"SAFETY-MODE-TOGGLE","resume_pr":401}`.

**No new owner question.** SAFETY-NOTE-WORDING settled the note. Gap (a) has a plan-level fix.

### SAFETY-MODE-CITATIONS

**Kind:** PRODUCT (frontend; citations display). **Depends on:** SAFETY-MODE-TOGGLE (`useSafetyMode`), UI-PG-ASK (`ExplainAssistant.tsx`), UI-PG-RESULTS (`InterpretedResultCard.tsx`), UI-PROVENANCE (`SourceTrace.tsx`, `CitationTooltip.tsx`). **Gate:** SAFETY-MODE-BEHAVIOUR answered "Always-on citations view". **Ask-first:** none.

**Behaviour (research Option C).** With the mode on, each answer and interpretation shows its sources expanded inline: document name, page, and the quoted text. The content comes from UI-PROVENANCE's components; this row does not duplicate them. With the mode off, today's chips and popovers are unchanged.

**Honesty rule (data gap, research Option C).** On the default agent path the API's `text_snippet` is a locator or id, not a quote (`be/api/assistant.py:853`). The expanded view labels it as a location ("Source: …, page …") and never shows it as a quotation. Quote styling is used only when a real quote is present (the legacy and interpretation paths). Adding real quotes to agent citations is a backend change outside this row.

**Files.** `fe/pages/ExplainAssistant.tsx` (the citation block only; **keep `data-testid="chat-message"` and `data-role`**, which E2E-UIFULL-CI ROUTES-002 depends on), `fe/components/lab-interpreter/InterpretedResultCard.tsx` (citation block), `fe/__tests__/safety-mode-citations.test.tsx` (new, HC-SMC-001…004), `e2e/safety-mode.spec.ts` (HC-SMC-005 appended), `fe/components/layout/SafetyModeToggle.tsx` and `fe/__tests__/safety-mode-toggle.test.tsx` (the note constant and its assertion only: stage 2 of the [TOGGLE delta](#delta-2026-10-28-task-0-stop-on-401); Task 0 confirms the clause, delta item 7, or stops and tells L0).

**Tests.** HC-SMC-001: mode on, an answer with two citations renders both expanded with name and page. HC-SMC-002: a locator-only citation is never rendered with quote styling. HC-SMC-003: mode off renders exactly today's chips (snapshot of the role tree, not pixels). HC-SMC-004: an interpretation card under the mode. HC-SMC-005 (e2e): the mode on, ask one question, sources visible without a click; `chat-message` and `data-role` selectors still resolve. **Est:** 4.5 h.

### SAFETY-MODE-VERIFIED-FE

**Kind:** PRODUCT (frontend; lab-value display). **Depends on:** SAFETY-MODE-VERIFIED (the 409 shape), SAFETY-MODE-TOGGLE, SAFETY-MODE-CITATIONS (both append to `e2e/safety-mode.spec.ts`; never beside it), UI-PG-RESULTS (`ResultsPage.tsx`), UI-RIBBON (`RangeRibbon.tsx` draws the points). **Gate:** SAFETY-MODE-BEHAVIOUR answered "Verified-only data". **Ask-first:** none.

**Behaviour.** With the mode on, unchecked values are listed under the chart but not plotted, with a one-line note ("2 unchecked values are not plotted. Check them in Review values."). Today's unverified marking, invariant I-13 from W-3 (`contracts.md:33`), stays for the mode off. An interpretation request answered with the 409 `observation_unverified` shape shows a "Verify this result first" state with a link to Review values, not an error toast. With the mode off, today's display is unchanged.

**Files.** `fe/pages/ResultsPage.tsx`, `fe/components/results/RangeRibbon.tsx` (a `hideUnverified` prop), `fe/__tests__/safety-mode-verified.test.tsx` (new, HC-SMV-001…004), `e2e/safety-mode.spec.ts` (HC-SMV-005 appended), `fe/components/layout/SafetyModeToggle.tsx` and `fe/__tests__/safety-mode-toggle.test.tsx` (the note constant and its assertion only: stage 3 of the [TOGGLE delta](#delta-2026-10-28-task-0-stop-on-401); Task 0 confirms the clause, delta item 7, or stops and tells L0).

**Tests.** HC-SMV-001: mode on, an unverified point is absent from the plot and present in the list. HC-SMV-002: mode off, both are plotted with today's unverified marker. HC-SMV-003: a 409 `observation_unverified` renders the verify-first state with the Review link. HC-SMV-004: any other error still shows today's error path. HC-SMV-005 (e2e, real backend): seed one unverified value, turn the mode on, and the interpret action shows verify-first. **Est:** 3 h.

## 4. What this plan does not do

- No code, test, threshold or count slot changes, and no gate is signed.
- The 0.75 value comes from the option text the owner chose. It was not measured.
- PR #264 (B-3) is a draft and is not read as main. If it merges before SAFETY-MODE-STRICT, that row rebases onto it and Task 0 re-reads the judge's threshold. If that threshold lives in an ask-first file, SAFETY-MODE-DIFF is needed for it.
