# 06 — Unresolved questions, owner decisions, go/no-go, task queue

> **Point-in-time research (2026-10-12), updated 2026-10-13.** OD-1 and OD-2
> are resolved by owner direction (rows WEAR-OD1, WEAR-OD2; quoted in
> [00-README.md](00-README.md#owner-direction-applied-2026-10-13)). Every other
> decision below is **open**; recommended options are labelled, none is chosen.
> Back to [00-README.md](00-README.md).

## 1. Owner decisions

| ID | Question | Options | Recommended |
|---|---|---|---|
| OD-1 | Pursue wearables at all, reversing the 2026-07-10 deferral? | (a) defer, (b) evidence gate then decide, (c) build now | **Resolved by owner direction WEAR-OD1:** pursue, Apple and Garmin only ("focus on getting the datas from those to be fully-integrated into HealthCentral"). Code still waits for OM-1/OM-2 real-file evidence. |
| OD-2 | Where does it live? | (a) in HealthCentral, default-off flag, (b) separate plugin repo + versioned `wearable-summary` contract, (c) converter that emits FHIR into the existing importer | **Resolved by owner direction WEAR-OD2:** (a) in-repo ("If it works better internally within this repo, then in-repo"; reasoning in [03 §5.3](03-architecture-contracts.md#53-owner-question-answered-single-repo-or-multi-repo)); (c) rejected on safety ([03 §5](03-architecture-contracts.md#5-separate-repository-option)) |
| OD-3 | Keep the raw export ZIP in the vault? | (a) keep encrypted (re-parse possible, holds clinical records and locations), (b) keep hash + extracted rows only | **(b)** for data minimisation; (a) if re-parse matters more |
| OD-4 | Symptom context | (a) up to 5 dated notes in the visit-prep request, not persisted, (b) new persisted symptom journal | **(a)** for MVP |
| OD-5 | First source and metrics | Apple first, Garmin second; resting HR, sleep duration, steps | **Yes** (Apple-first order recommended; scope set by WEAR-OD1) |
| OD-6 | Minimum data to show a metric | e.g. ≥ 7 days with data in the window | **7 days**, shown with coverage |
| OD-7 | Raise the 50 MB import cap for this type only? | per-type cap vs global | **Per-type**, sized from OM-1 |
| OD-8 | Legal review before distribution (FDA wellness wording, FTC HBNR, FIT licence for Garmin) | yes/no | **Yes** before any public build; the open-source framing does not remove it |

**Top open for L0:** OD-3, OD-4, OD-6, OD-8, and whether OM-4/OM-5 are still required.

## 2. Unresolved questions (need evidence, not opinion)

1. Real Apple export structure: attribute names, offset format, file size for 1-3 years (OM-1).
2. Does `RestingHeartRate` exist per day for typical users, or only with Watch wear at night?
3. How sleep records from multiple sources overlap in one export.
4. Garmin export layout, turnaround, FIT-vs-JSON split, timezone fields (OM-2) — prerequisite for the Garmin slice. Samsung layout (former OM-3) dropped: out of scope.
5. Whether any clinician the owner can reach wants this section at all (OM-4) — open: owner to confirm whether still required under the personal open-source framing.
6. Whether patients will complete a 100 MB+ export-and-move flow (OM-5) — open: same.

## 3. Go / no-go criteria for first implementation

**Go only if all hold:**

1. OM-1 done: a real Apple export inspected; the 3 metrics present with offsets; size known. For the Garmin slice, OM-2 done to the same standard.
2. OM-4/OM-5 — **open, owner to confirm whether still required** under the personal open-source framing. If required: at least 3 of 5 clinicians and 3 of 5 patients say a wearable section would be used, and name at least one of the 3 MVP metrics.
3. OD-3, OD-4, OD-6 signed (OD-1, OD-2 resolved by WEAR-OD1/WEAR-OD2).
4. No current higher-priority safety or audit item is blocked by this work (owner judgement against `docs/features/TASK_LIST.md`).
5. Plan record in `docs/plans/` passes docs lint and the owner's review route (Codex/Fable per memory) before code.

**No-go if any holds:** clinicians call it noise or a liability (if OM-4 runs); the export
lacks offsets or the metrics; the slice needs a mobile app, a vendor API, or an
LLM to be useful.

## 4. Owner and model-machine task queue

None of these need a local model. They need the owner, a phone, or people.

| ID | Task | Who / where | Output |
|---|---|---|---|
| OM-1 | Export Apple Health once; record ZIP size, member list, first 50 `<Record` type names, one record's attributes (redact values), one ECG CSV header. Do not commit the file. | Owner, iPhone | Notes appended to this package |
| OM-2 | Request Garmin Connect "Export Your Data"; record turnaround, folder layout, which files hold stress/HRV/sleep, timezone fields. Do not commit the file. Prerequisite for the Garmin slice. | Owner, Garmin account | Notes |
| ~~OM-3~~ | **Dropped** — Samsung out of scope (WEAR-OD1: owner has only Apple and Garmin watches) | — | — |
| OM-4 | 3-5 short clinician conversations: would you read it, which metrics, max length, liability concerns. **Open — owner to confirm whether still required under the personal open-source framing.** | Owner | Interview notes (no PHI) |
| OM-5 | 3-5 patient conversations: would you export and import, time tolerance. **Open — owner to confirm whether still required under the personal open-source framing.** | Owner | Notes |
| OM-6 | Sign OD-3..OD-8 (OD-1, OD-2 resolved by WEAR-OD1/WEAR-OD2) | Owner | Rows in owner-decisions ledger |
| OM-7 | Legal read: FDA general-wellness wording, FTC HBNR, FIT licence | Owner / counsel | Memo |
| OM-8 | Read full FDA January 2026 general-wellness text ([PDF](https://www.fda.gov/media/90652/download)) and confirm the descriptive-summary position | Owner or a web-capable agent | Quote + page number |

## 5. What this package could not verify

1. Apple export layout and attributes on an Apple page (support page did not render).
2. Garmin export layout, turnaround, FIT wellness messages (support pages 403/404).
3. Samsung export format and metric list (out of scope; reference only).
4. Full text of FDA January 2026 general-wellness and CDS guidance (secondary summaries only).
5. Accuracy figures marked S in [04](04-safety-privacy.md), and any direct study of patients bringing wearable summaries to visits (none found).
6. Any HealthCentral runtime behaviour: no tests or app boot were run (planning-only task; WSL env lacks backend deps).
