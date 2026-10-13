# 04 — Privacy, security and clinical-safety assessment

> **Point-in-time research (2026-10-12).** Evidence labels as in
> [01](01-vendor-matrix.md): V read on page, S snippet/secondary, U unconfirmed.
> Back to [00-README.md](00-README.md).

## 1. Position

The packet is **patient-recorded context**, not clinical measurement. It
reports what a consumer device recorded, how much it recorded, and where the
data came from. It never interprets, thresholds, alerts, or links a value to a
cause. This keeps it inside the repo's "No medical advice" invariant and, per
secondary summaries, inside FDA general-wellness policy (January 2026
revision; page date V, content S). CDS non-device criteria assume a clinician
user, so a patient-facing tool cannot rely on them (S,
[FDA CDS page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software)).

**Framing does not relax controls.** Per owner direction WEAR-OD1
(2026-10-13), HealthCentral is an open-source, personal, research and
educational tool for individuals curious about their own health and fitness
records — not professional medical or legal advice and not a medical device.
That framing is a disclaimer, not a waiver: every control in §3 and §4
(provenance, strict redaction, `ProfileDbSession` isolation, audit, no
thresholds or alerts, no medical advice, hostile-file guards) applies
unchanged. Scope is Apple and Garmin; Samsung rows below are reference only.

## 2. Measurement limits that shape the MVP metric choice

| Metric | Evidence | MVP? |
|---|---|---|
| Resting heart rate | Wrist PPG is most accurate at rest; error rises with intensity (S, [2024 review](https://doaj.org/article/704da2e5ca484d7bbb8f51d920eed847)); Garmin resting HR error <2% in one n=27 study (S, [CinC 2023](https://cinc.org/2023/Program/accepted/237.html)) | **Yes** |
| Sleep duration | Consumer devices overestimate total sleep; wake specificity poor (S, [Haghayegh 2019](https://jmir.org/2019/11/e16273/PDF)); staging only moderate vs PSG (S, [Schyvens 2024](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11004611/)) | **Yes, duration only, with caveat**; no stages |
| Steps | Multi-source double counting is the main risk (inferred from Apple multi-source export) | **Yes**, one source per day |
| HRV | Agrees with ECG at rest/sleep, weaker during activity (S); Apple reports SDNN, Health Connect RMSSD — not comparable | No (later, single vendor) |
| SpO₂ | Occult hypoxemia ~3× more common in Black patients on pulse oximetry (S, Sjoding NEJM 2020); Apple US availability legally contested (S) | **No** |
| Stress scores | Proprietary, unpublished formulas (V Garmin, V Samsung); near-zero agreement with self-report in one study (S) | **No** |
| ECG | FDA-cleared vendor features with own labelling (S) | No; import vendor PDF as a document instead |

## 3. Failure modes and testable controls

| # | Failure mode | Control | Test (pytest unless noted) |
|---|---|---|---|
| F1 | Misleading summary statistics | Median + IQR + n + days-with-data; no mean, no single "average"; never compare to population norms | Fixture with one outlier day: packet shows median unchanged, contains no "average"/"normal" tokens |
| F2 | Sparse or missing data | Coverage line ("data on 9 of 30 days"); suppress a metric below a minimum-days threshold (OD-6) and say why | 3-of-30-day fixture: metric suppressed with reason text |
| F3 | Timezone misinterpretation | Bucket by record's own offset; `tz_changed` flag; footnote in packet | Records at 23:30 −07:00 and 00:30 +01:00 land on their local dates; DST fixture sets `tz_changed` |
| F4 | Duplicates across platforms / devices | One source per metric/day; upsert on re-import; `duplicate_of_source` | iPhone + Watch steps same day → one row, not the sum; importing the same file twice → row count unchanged |
| F5 | Motion-affected readings | Use device-computed resting HR only, not raw HR samples | Parser ignores `HeartRate` samples; only `RestingHeartRate` contributes |
| F6 | Proprietary stress misread | Stress, Body Battery, SpO₂ not on the metric allowlist | Fixture with stress/SpO₂ records → skipped count, no rows |
| F7 | LLM hallucination / causal claims | Section is template-rendered, no ModelRunner call; symptom notes printed beside, never joined to, metrics; banned-phrase screen ("caused", "due to", "indicates", "diagnos", "normal", "abnormal") | Render test asserts no ModelRunner call and no banned phrase; existing `interpret_safety` prohibited patterns still pass |
| F8 | Unintended disclosure via exports | Section excluded unless metric `include_in_packet` and `patient_reviewed_at` set; strict redaction pass; `confirm=true` | HTTP test via `route_client`: unreviewed metrics absent; `source_name` "Jane's Apple Watch" redacted |
| F9 | Cross-profile leakage | `ProfileDbSession` only; no master-DB query; profile_id from session | HTTP test: profile B cannot list or packet profile A's rows (404/empty); grep guard that the new module imports no `get_db` |
| F10 | Inaccessible source attachments | Packet table is real text (no chart-only content); chart has a data-table twin; WCAG 2.2 AA ([W3C](https://www.w3.org/TR/2023/REC-WCAG22-20231005/), V by URL) | vitest + axe on review screen; packet markdown has a table per metric |
| F11 | Scope creep into diagnosis | Closed metric enum; no thresholds or alerts; banned-phrase screen; flag default-off | Test that the enum is exactly the MVP set; config test that `wearables_enabled` defaults False |
| F12 | Hostile file (zip bomb, XML entity expansion, giant attributes) | Size/member caps, DOCTYPE/ENTITY rejection, `_cap` on strings, streaming parse | Fixtures: nested-entity XML → 400; 1 GB-expanding zip → 400 without OOM |
| F13 | Over-collection (export holds clinical records, locations) | Allowlist parse; OD-3 decides raw-ZIP retention | Fixture with `export_cda.xml` and GPX → nothing stored from them |
| F14 | Audit gap or PHI in audit | `audit_and_commit` on import, review, packet; counts only | `test_audit_phi_minimization`-style test for new keys |

## 4. Privacy and compliance

1. **Local-first holds.** No vendor API, no network; patient moves the file.
2. **Redaction.** The packet path already applies strict redaction
   (`modules/export.py:637`). No change to `modules/redaction.py` is proposed.
3. **Patient export.** A wearable CSV is the patient's own data (D3
   full-fidelity exception) and must carry `schema_version`.
4. **HIPAA / FTC.** A consumer-only app is likely outside HIPAA (S, HHS
   summaries); the FTC Health Breach Notification Rule may apply to a
   multi-source health app (V rule page; 2024 amendment details S). Owner
   task OM-7: legal read before any distribution.
5. **Communication.** Plain language, CDC Clear Communication Index check
   (S, [CDC CCI](https://www.cdc.gov/ccindex/widget.html)); every section
   opens with "Recorded by a consumer device. Not a clinical measurement."
