# 03 — Proposed architecture and data contracts

> **Point-in-time research (2026-10-12).** A proposal, not a licence to build.
> Nothing here changes an existing contract or a safety-critical file. Back to
> [00-README.md](00-README.md).
>
> **Owner direction (2026-10-13):** scope is Apple and Garmin (WEAR-OD1);
> location is in-repo behind a default-off flag (WEAR-OD2, see §5.3). The
> open-source personal-research framing relaxes none of the rules in §3 or §4.

## 1. Current → proposed

| Concern | Current state (see [02](02-implementation-map.md)) | Proposed (MVP) | Reuse |
|---|---|---|---|
| Ingress | `POST /documents/import`; `.csv`/`.json` only; 50 MB | Same route; new `doc_type = "wearable_apple_export"` detected from a `.zip` whose member list contains an `export.xml` member (folder name INFERRED as `apple_health_export/`; OM-1 confirms) | `IngestModule` vault + hash, `_STRUCTURED_IMPORT_DOC_TYPES` dispatch |
| Ingress (Garmin, slice 2) | same | `doc_type = "wearable_garmin_export"` for a Garmin Connect export ZIP; member layout and FIT-vs-JSON split UNVERIFIED until OM-2 | same |
| Parsing | `modules/import_structured.py` pure parsers | `modules/import_wearable.py`: pure, stdlib (`zipfile`, `xml.etree.ElementTree.iterparse`), streaming, allowlisted record types only. Garmin parser added in slice 2; FIT decoding needs either the FIT SDK (licence read, OM-7) or a stdlib decoder — decided after OM-2 | Purity contract, `_cap`, skip-with-reason pattern |
| Storage | `Observation` (lab-shaped, doc_id NOT NULL) | **New per-profile table `wearable_daily_metrics`** (migration `013_*`). Daily aggregates only, no raw samples | `ProfileDatabaseBase`, `Document` as parent for provenance |
| Review | Verification Workbench per observation | One review screen per import: coverage table + "include in packet" per metric; sets `patient_reviewed_at` | Unverified-excluded packet policy (`modules/export.py:521`) |
| Trends | `TrendsDashboard` over observations | Separate "Wearable (patient-recorded)" panel; never on the lab chart | Recharts components |
| Symptoms | none | Up to 5 dated free-text notes in `VisitPrepRequest`; not persisted (owner decision OD-4) | `reason_for_visit` precedent |
| Packet | `compose_visit_prep_packet` sections | New optional section "Wearable measurements (patient-recorded, not clinically verified)", template-rendered, no LLM | Strict redaction at `:637`, `confirm=true`, audit |
| Patient export | CSV/JSON of observations | Add a `wearable_daily_metrics` CSV with schema version column | D3 covers only `GET /export/csv` and `GET /export/json`; a new route needs redaction or an owner decision (corrected, finding ADV-1) |
| Flag | none | `wearables_enabled: bool = False` in `core/config.py` | Existing boolean-flag pattern |

## 2. Data contract — `WearableDailyMetric` v1

One row per (source document, metric, local calendar date).

| Field | Type | Rule |
|---|---|---|
| `id` | String(36) | UUID |
| `profile_id` | String(36) | Indexed; set from session, never from file |
| `doc_id` | String(36) FK documents | Source export; cascade on delete |
| `schema_version` | String(8) | `"wdm-1"` |
| `source_vendor` | String(20) | `apple` (slice 1), `garmin` (slice 2); `samsung` out of scope |
| `source_name` / `source_device` | String(255) capped | From the record (`sourceName`, `device`) — shown in provenance |
| `metric` | String(40) | Closed enum: `resting_heart_rate`, `sleep_asleep_minutes`, `step_count` (MVP) |
| `local_date` | Date | Calendar date in the **record's own UTC offset**, not the PC's |
| `utc_offset_minutes` | Integer | Offset observed for that day; multiple offsets → `tz_changed = true` |
| `tz_changed` | Boolean | Travel/DST day flag; packet footnotes it |
| `n_samples` | Integer | Count of source records contributing |
| `coverage_minutes` | Integer nullable | Wear-time proxy where derivable |
| `value_median`, `value_p25`, `value_p75`, `value_min`, `value_max` | Float | Descriptive only; **no mean** in packet |
| `unit` | String(16) | Canonical: `bpm`, `min`, `count` |
| `method_note` | String(100) | e.g. "wrist optical sensor, device-computed daily value" |
| `duplicate_of_source` | String(20) nullable | Set when another source covered the same metric/day |
| `patient_reviewed_at` | DateTime nullable | Null = excluded from packet |
| `include_in_packet` | Boolean | Patient choice, default False |
| `created_at` | DateTime | `core.time.utcnow` |

**Not stored:** raw samples, ECG waveforms, SpO₂, stress scores, clinical
records from `export_cda.xml`, location (`workout-routes`). The parser skips
them with a counted reason.

## 3. Rules

1. **Validation.** Accept only a ZIP with the expected member; cap
   uncompressed size and member count (zip-bomb guard); refuse XML with a
   `<!DOCTYPE … [` internal subset or `<!ENTITY` (entity-expansion guard; stdlib
   `ElementTree` is not hardened, and `defusedxml` is not a dependency ✓
   `requirements.txt`). Unknown record types are skipped and counted.
2. **Timestamps.** Parse each record's own offset; bucket by its local date;
   store offset; never use the host timezone. Store audit timestamps with
   `utcnow`.
3. **Units.** Closed per-metric unit map; any other unit → skip with reason
   (mirrors `convert_to_canonical` returning `None`).
4. **Dedup.** Same file → existing `content_hash` warning. Same records across
   two imports → upsert on (`profile_id`, `source_vendor`, `metric`,
   `local_date`) keeping the newer import and logging the replacement count.
5. **Multi-device overlap.** Apple export can hold iPhone + Watch + third-party
   apps for steps. MVP rule: per day per metric choose one `sourceName`
   (prefer the Watch; patient can switch), never sum across sources. Record
   the others as `duplicate_of_source`.
6. **Provenance.** Every packet line links metric → source device → import
   file name and date → `doc_id`. Wording always "recorded by", never
   "measured", "diagnosed" or "normal".
7. **Verification.** Wearable rows are **patient-reviewed**, never
   "verified". The term `user_verified` is not reused, so lab logic cannot
   treat them alike.
8. **Isolation.** All reads and writes through `ProfileDbSession`; the table
   lives only in the profile DB.

## 4. Security and compliance implications

| Item | Implication |
|---|---|
| Vault | The full export ZIP (contains every Health record, including clinical records and locations) is stored encrypted like any import. Owner decision OD-3: keep the raw ZIP, or keep only a hash plus the extracted rows. |
| Backups | New table and vault file ride existing unredacted backups (by design). |
| Audit | New events (`wearable.import`, `wearable.review`) need keys added to `core/audit.py:89` `ALLOWED_DETAIL_KEYS`; counts only, no values. |
| Redaction | Packet section goes through the existing strict pass. `source_name` can hold a person's name ("Jane's Apple Watch"), which strict `name_context` (`modules/redaction.py:82-88`) does not match; the packet must not render `source_name` at all (corrected, finding ADV-2). |
| Regulatory | Descriptive, no thresholds, no alerts, no disease words → stays in general-wellness territory per secondary summaries of FDA's January 2026 guidance ([FDA page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices), date V; content S). Legal read is an owner task. |
| FTC HBNR | A consumer health app drawing from multiple sources may be a "vendor of personal health records" ([FTC rule page](https://www.ftc.gov/legal-library/browse/rules/health-breach-notification-rule), V). Local-only storage lowers breach surface but does not remove the question. |

## 5. Separate repository option

### 5.1 Seams a separate repo could use today (no HealthCentral change)

| Seam | How | Problem |
|---|---|---|
| FHIR Bundle file → `parse_fhir_bundle` | External CLI turns `export.xml` into a Bundle of daily `Observation`s; patient imports it | Lands in `observations` → unverified points reach trends and RAG (no `user_verified` filter, [02 §3](02-implementation-map.md)); `device`, `effectivePeriod`, time and offset dropped; aggregates show as "lab" events |
| Lab CSV → `parse_lab_csv` | External CLI writes `Date,Analyte,Value,Unit` | Same problems, plus no provenance at all |

Both are **unsafe** under the brief's rule "do not equate wearable
observations with clinically verified measurements". Neither is recommended.

### 5.2 Seam a plugin would need

A plugin repo would own parsing; HealthCentral would own storage, review,
packet and safety. The contract between them:

| Contract | Owner | Content |
|---|---|---|
| `wearable-summary` file v1 | HealthCentral (versioned, published in `docs/api/`) | JSON: `{"schema": "hc.wearable-summary", "version": "1.0", "generator": {...}, "rows": [WearableDailyMetric fields minus id/profile_id/doc_id/review fields]}` |
| Importer for that file | HealthCentral | Validation, table, review UI, packet section — i.e. everything in §1 except the vendor parser |
| Vendor parsers | Plugin repo | Apple/Garmin → `wearable-summary` v1 |
| Compatibility | Both | HealthCentral rejects unknown major versions; plugin CI validates against a JSON Schema copied from HealthCentral |

**Assessment.** The plugin saves only the parser (one pure module). It adds a
second repo, a release process, a JSON Schema, cross-repo version tests, and a
patient step (run a converter). Prior art: `rl_dataset.SCHEMA_VERSION` is the
only versioned schema today. **Recommendation: build in-repo behind the flag,
keep the parser pure, and emit the same `wearable-summary` v1 shape
internally**, so extracting a plugin later is a move, not a redesign.
Revisit if a second, independent consumer of the parser appears, or if the
Garmin FIT licence requires keeping that parser out of the main distribution.

### 5.3 Owner question answered: single repo or multi-repo?

WEAR-OD1 asked "would multi-repo works, or a single-repo?"; WEAR-OD2 said "If
it works better internally within this repo, then in-repo". **Answer: single
repo — an in-repo module behind `wearables_enabled: bool = False`.**

1. **No plugin mechanism exists** ([02 §6](02-implementation-map.md#6-extension-points-for-an-external-module):
   no entry points, no loader, static router list).
2. **A separate repo first needs a versioned import contract inside
   HealthCentral** (§5.2). The zero-change seams (§5.1) are unsafe. So
   HealthCentral builds the importer, table, review, packet and safety tests
   in both options; the plugin only moves the parser out.
3. **More cost, no safety gain.** A second repo, releases, a JSON Schema,
   cross-repo version tests and a patient converter step, while every safety
   property stays in HealthCentral regardless.

**Seam that would make later extraction cheap** (described, not built now):

- Vendor parsers (`modules/import_wearable.py` and the Garmin parser) stay
  pure: stdlib-only imports, no DB, no HealthCentral imports.
- Parsers emit rows in the `wearable-summary` v1 shape above; the importer
  validates that shape before writing `wearable_daily_metrics`.
- Only once extraction is actually wanted: publish the JSON Schema in
  `docs/api/` and version it.

Extraction triggers stay as above: a second independent consumer of the
parsers, or a FIT licence finding (OM-7) that requires keeping the Garmin
parser out of the main distribution.
