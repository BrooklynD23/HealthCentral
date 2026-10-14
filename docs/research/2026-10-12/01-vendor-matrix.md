# 01 — Vendor/API capability and licensing matrix

> **Point-in-time research (2026-10-12).** Access date for every URL below is
> 2026-10-12. Labels: **V** = read on the cited page; **S** = search snippet or
> third-party source only; **U** = not confirmed. Vendor pages change; recheck
> before building. Back to [00-README.md](00-README.md).
>
> **Scope (owner direction WEAR-OD1, 2026-10-13):** Apple and Garmin only.
> Samsung columns and rows are **out of scope (owner has no device), retained
> for reference**; their labels are unchanged.

## Classification key

| Code | Meaning |
|---|---|
| NE | Native export supported (patient generates a file, no developer relationship) |
| API | API supported (server or SDK, usually approval-gated) |
| NAT | Requires native platform integration (iOS/watchOS/Android app on the phone) |
| R? | Restricted or uncertain |
| NS | Not supported |

## 1. Import feasibility matrix

| Metric | Apple Watch | Garmin | Samsung Galaxy Watch (out of scope, reference) |
|---|---|---|---|
| Heart rate (samples) | NE (S) · NAT (V) | NE (S) · API (V) | NE (U) · NAT via Health Connect (V) |
| Resting heart rate | NE (S) · NAT (V) | NE (S) · API (S) | NE (U) · R? |
| HRV | NE SDNN (S) · NAT (V) | NE JSON (S) · API: not listed in text (U) | NE (U) · NAT: HC has `HeartRateVariabilityRmssdRecord`, Samsung sync U |
| SpO₂ | NE (S) · NAT (V) · R? US feature status (S) | NE (S) · API Pulse Ox (V) | NE (U) · NAT record exists, Samsung sync U |
| Respiratory rate | NE (S) · NAT (V) | NE (S) · API (V) | NE (U) · NAT record exists, Samsung sync U |
| Sleep (duration, stages) | NE (S) · NAT (V) | NE JSON (S) · API (V) | NE (U) · NAT `SleepSessionRecord`, synced (V) |
| Steps / activity | NE (S) · NAT (V) | NE (S) · API (V) | NE (U) · NAT `StepsRecord`, synced (V) |
| Skin / wrist temperature | NE (S) · NAT (V) | U | NE (U) · NAT record exists (V), Samsung sync U |
| Proprietary stress score | NS (Apple has none) | NE JSON (S) · API "stress detail" (V) | NE (U) · NS in Health Connect (V: not on type list) |
| Body Battery / energy | NS | NE JSON (S) · API image label only (U) | NS |
| ECG | NE `electrocardiograms/*.csv` (S) · NAT read-only `HKElectrocardiogram` (V) | PDF share from Connect (S) · NS API | PDF share from Samsung Health Monitor (S) · NS in Health Connect (V) |
| Irregular rhythm / AFib events | NAT category type (V) · NE U | U | R? (IHRN FDA-cleared per press, S) |

**Verdict per vendor**

1. **Apple — in scope, first slice.** One patient-initiated file holds every
   metric; no SDK licence; native app needed only for live sync. Weak point:
   the export layout is confirmed by third parties, not Apple.
2. **Garmin — in scope, second slice.** Account export exists but its layout,
   turnaround and FIT wellness messages are unconfirmed on Garmin pages (OM-2
   settles them). The FIT SDK licence reads "internal business use" (legal read
   needed before distributing, OM-7; the open-source framing does not answer
   it). Health API is business-only with a fee: out of scope for local-first.
3. **Samsung — out of scope (owner has no device); retained for reference.** Personal-data download exists (V) but format and
   metric list are not documented by Samsung. Health Connect needs an Android
   app and only reads 30 days back by default. ECG is PDF only.

## 2. Access paths and licensing

| Path | Vendor | Needs | Licence / terms | Fit for local-first desktop | Source | Label |
|---|---|---|---|---|---|---|
| Health "Export All Health Data" ZIP | Apple | Patient on iPhone; move file to PC | None stated for patient's own file | **Yes** | [macwelt](https://www.macwelt.de/article/2279875/apple-health-daten-exportieren.html), [iGeeksBlog](https://www.igeeksblog.com/how-to-export-import-health-data-in-ios-10), [Apple Community](https://discussions.apple.com/thread/255504486); Apple guide [iph5ede58c3d](https://support.apple.com/guide/iphone/share-your-health-data-iph5ede58c3d/ios) did not render | S |
| HealthKit | Apple | Native iOS/watchOS app, per-type permission sheet | App Review 5.1.3: no ads/data mining, disclose data collected, no PHI in iCloud | No (needs mobile app) | [developer.apple.com/healthkit](https://developer.apple.com/healthkit/), [Review Guidelines](https://developer.apple.com/app-store/review/guidelines/), [HKElectrocardiogram](https://developer.apple.com/documentation/healthkit/hkelectrocardiogram) | V |
| HealthKit on macOS | Apple | — | — | Unclear: `HKHealthStore` lists macOS 13+, marketing page omits Mac | [HKHealthStore](https://developer.apple.com/documentation/healthkit/hkhealthstore) | V (conflict) |
| Garmin Connect "Export Your Data" | Garmin | Account web settings; emailed link | Garmin ToS (not read) | Yes, if layout confirmed | [Gadgetbridge guide](https://gadgetbridge.org/basics/topics/garmin/import-garmin-connect/), [takeoutday](https://takeoutday.org/guides/how-to-export-garmin-connect-data) | S |
| FIT SDK (Python `garmin-fit-sdk`) | Garmin | pip dependency | FIT Protocol License: royalty-free, non-transferable, internal business use | Yes, after legal read | [FIT overview](https://developer.garmin.com/fit/overview/), [LICENSE](https://github.com/garmin/fit-python-sdk/blob/main/LICENSE.txt) | V |
| Garmin Health API | Garmin | Business approval; server endpoint | "Commercial use requires a license fee payment" | No (server, business) | [Health API](https://developer.garmin.com/gc-developer-program/health-api/) | V |
| Garmin Health SDK | Garmin | Enterprise partner | Fee or minimum device order | No | [Health SDK](https://developer.garmin.com/health-sdk/overview/) | V |
| Samsung Health "Download personal data" | Samsung | Patient on phone; files under Downloads/Samsung Health | Not stated | Yes, if format confirmed | [Samsung ANS10001379](https://www.samsung.com/us/support/answer/ANS10001379/) | V (path), U (format) |
| Samsung Health Data SDK | Samsung | Android app; partnership to distribute | Developer terms not read | No | [overview](https://developer.samsung.com/health/data/overview.html), [migration](https://developer.samsung.com/health/data/migration-guide/overview.html), [types](https://developer.samsung.com/health/data/guide/features/data-types.html) | V |
| Health Connect | Android | Android app; per-type permission; 30-day default history | Play policy (not read) | No (needs mobile app) | [read-data](https://developer.android.com/health-and-fitness/health-connect/read-data), [data types](https://developer.android.com/health-and-fitness/health-connect/data-types), [Samsung HC FAQ](https://developer.samsung.com/health/health-connect-faq.html) | V (re-fetched by orchestrator) |

## 3. Proprietary and regulated metrics

| Item | What the vendor says | Implication | Source | Label |
|---|---|---|---|---|
| Garmin Stress (0-100) | Estimate from heart rate and HRV; formula unpublished | Show only as "device-reported score", never as a health measure | [Garmin blog](https://www.garmin.com/en-US/blog/health/top-10-features-to-monitor-your-health/) | V |
| Garmin Pulse Ox | "not considered a medical device … not intended for use in the diagnosis or monitoring of any medical condition" | Carry the disclaimer into the packet | same | V |
| Samsung stress | Wellness feature, accuracy disclaimers, algorithm not disclosed | Same as Garmin | [Samsung ANS10001394](https://www.samsung.com/us/support/answer/ANS10001394/) | V |
| Apple Blood Oxygen (US) | Pulled Jan 2024; redesigned version (iPhone-side processing) restored Aug 2025; ITC closed review Apr 2026 | Availability varies by device/region; exclude from MVP | [9to5Mac 2026-04-17](https://9to5mac.com/2026/04/17/apple-wins-latest-round-in-masimo-fight-as-itc-closes-apple-watch-import-ban-case/), [TidBITS](https://tidbits.com/2025/08/14/blood-oxygen-monitoring-returns-with-ios-18-6-1-and-watchos-11-6-1/) | S |
| ECG apps (Apple, Garmin, Samsung) | FDA-cleared features with own labelling | Do not re-analyse waveforms; a vendor PDF can already be imported as a document today (see [02](02-implementation-map.md)) | [Garmin newsroom](https://garmin.com/en-US/newsroom/?p=4131), [Samsung IHRN](https://news.samsung.com/us/fda-cleared-irregular-heart-rhythm-notification-for-galaxy-watch/), [Apple IRN IFU](https://www.apple.com/legal/ifu/irnf/irn-ifu-2-en_US.pdf) | S |

## 4. Not verified (must be settled with real files — owner tasks OM-1, OM-2)

1. Apple: `export.xml` attribute names, offset format in dates, ECG CSV headers, where AFib history lands, file size for 1-3 years of data.
2. Garmin: export ZIP folder layout, turnaround, whether stress/HRV/SpO₂ are JSON or FIT, timezone fields.
3. Samsung (out of scope, reference only; no owner task): export file format, metric list, `time_offset` semantics.
4. Garmin Health API current intake status (sources conflict).
5. Apple support-page wording for the export (page did not render to tooling).
