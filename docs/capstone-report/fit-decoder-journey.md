# FIT decoder journey: licence ambiguity, measurement, choice (senior project report section)

**Last Updated:** 2026-11-08
**Owner:** repository owner
**Refresh Trigger:** a new release of `fitdecode`, `fitparse`, `fit-tool` or `garmin-fit-sdk`; an owner legal read (the legal question is deferred); the FITDECODER-UPSTREAM work shipping or being dropped; WEAR-11b being re-planned in `docs/plans/` or built.

> **Not legal advice. Decided direction, not done work.** This section records what was measured and what the owner chose. It adds no measurement and no legal reading. Marks follow the folder convention: a claim without a `file:line`, commit hash, owner-decisions row or command output is marked UNVERIFIED. "Research note" below means [`../research/2026-10-22-fit-decoder/00-README.md`](../research/2026-10-22-fit-decoder/00-README.md) (last commits `83ef536a`, `2f6c10f2`, `6de165d1`, read on `origin/main` `d563829d`). "Decisions" means [`owner-decisions-2026-09-27.md`](owner-decisions-2026-09-27.md).

## 1. The goal

- WEAR-11b exists to read Garmin metrics that are present only in `.FIT` files and absent from the JSON export (`docs/plans/2026-10-13-wearables-11-garmin-parser.md:17`). Its in-scope metrics are resting heart rate, steps and sleep intervals (same plan, line 32; research note line 24).
- The plan as written is **PROPOSED, not executed**, and still names the pinned Garmin SDK path (`docs/plans/2026-10-13-wearables-11-garmin-parser.md:1,5`). No `fitdecode` reference exists in that plan on `origin/main` `d563829d` (`grep -n fitdecode` on the plan prints nothing). **UNVERIFIED:** the re-plan onto `fitdecode` is described in a planner draft outside the repo and is not in the repo; do not cite it as landed.

## 2. The setback: the Garmin SDK licence

- Owner decision **WEAR-D5** chose "(b) garmin-fit-sdk after licence read" (Decisions line 166, answered 2026-10-14).
- The licence read raised the wall. Decision **OW-W7** (Decisions line 385) records the owner's question: Garmin's licence restricts use to "internal business purposes" and forbids distributing its SDK, and a pip dependency is lower risk than bundling it in an installer. The owner answered "Research MIT FIT decoder" (prompt 35, 2026-10-22).
- The research note found the licence text **ambiguous**: it defines the "Licensed Technology" as Garmin's FIT SDK, including protocol documentation and source files, and never says whether the file format or independent decoders are covered (research note line 19). No reading was inferred (same line; header, line 7).
- Every decoder embeds a profile generated from Garmin's SDK profile; the note does not answer whether that subjects the MIT decoders to Garmin's terms (research note line 20).

## 3. The measurement

Four decoders, all read and run on 2026-10-22 in a scratch venv with network and subprocess calls patched to raise (research note lines 26-32; no call triggered, line 128). Numbers are from the note; they are synthetic-file measurements, not real Garmin exports (research note line 173: no real export existed).

| Finding | Evidence |
|---|---|
| `fit-tool` is BSD-3-Clause, a community fork; `garmin-fit-sdk` carries Garmin's own licence | research note line 21 |
| `fit-tool` used about 380 B of memory per input byte and hit a 2 GiB cap on a 6.3 MB file; `garmin-fit-sdk` about 40 B/B; `fitdecode` 17 MiB flat | research note lines 22, 151-154 |
| `fitdecode` only warns on a bad CRC unless called with `check_crc=CrcCheck.RAISE` | research note lines 22, 138, 223 |
| `fitdecode` and `fitparse` can raise generic `TypeError`/`KeyError` on corrupt files, so callers must catch `Exception` | research note lines 156, 223 |
| `garmin-fit-sdk` returns data plus an `errors` list on a bad CRC; the caller must check it | research note line 138 |
| No decoder hung or ran out of memory on 1,500 mutated files each | research note lines 22, 156 |
| `fitparse` (SDK 20.8 profile) cannot name `monitoring_hr_data`, `sleep_level`, `hrv_value` | research note lines 23, 177-181, 183 |

## 4. The choice

- Decision **WEAR-FIT-LIC** (Decisions line 405, answered 2026-10-23, prompt 43): the owner picked "MIT decoder (fitdecode)". The option text itself says it "Depends on Garmin's licence not covering the format; the text leaves that open (Q1)".
- The owner's free-text follow-up, verbatim from Decisions line 405: "1. Keep fitcode (improve on the open-source project to be compatible with Garmin's newest version, document our journey, setback, resolution in senior project report). 2. Accepted. 3. Defer anything legal related, provide recommendations." (The word "fitcode" is the owner's; the option chosen is fitdecode.)
- Clarification Q1: "JSON too, plus fitdecode". Clarification Q2: "Upstream-safe (Recommended)", whose option text reads "Ship fitdecode as released (21.171); contribute CRC/error-handling fixes upstream and open an issue asking the maintainer to update the profile; regenerate ourselves only after a legal read (logged as deferred)." (Decisions line 405.)
- Decisions line 405 also records that this answer supersedes WEAR-D5 (b) for WEAR-11b. The "L0 reading" there (WEAR-11a unchanged, WEAR-11b re-planned onto fitdecode) is labelled as L0's reading, not the owner's words.

## 5. Resolution: decided direction, not done work

Nothing in this section is shipped. State on `origin/main` `d563829d`:

- **fitdecode is not integrated.** No FIT decoder code or dependency is added by this row; the wearables plan is still PROPOSED (section 1).
- **Upstream contribution is queued, not done.** FITDECODER-UPSTREAM (`docs/plans/2026-10-15-build-program/queue.md:153`) is "not yet planned": CRC and error-handling fixes to upstream `fitdecode`, plus an issue asking the maintainer to update the profile to SDK 21.218 (the pinned release carries 21.171). No upstream issue or pull request is cited here because none was verified. **UNVERIFIED:** whether any upstream issue or PR exists.
- **Profile regeneration stays deferred.** Regenerating the profile uses Garmin's SDK spreadsheet and waits for a legal read (queue.md:153; Decisions line 405, "logged as deferred").
- **The legal question is deferred, not resolved.** The licence text still leaves open whether it reaches the format or independent decoders (research note line 19), the embedded-profile question is unanswered (line 20), and the owner wrote "Defer anything legal related, provide recommendations." (Decisions line 405). The recommendations are tracked as FIT-LEGAL-RECS (`queue.md:155`, "not yet planned"). Choosing fitdecode reduces exposure to the SDK terms only if Garmin's licence does not cover the format, which is exactly what is not established.
- **Caller duties carry into any build:** `check_crc=CrcCheck.RAISE` and catching `Exception` (research note line 223).
