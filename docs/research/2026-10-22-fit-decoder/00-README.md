# FIT decoder research: which decoder may WEAR-11b use (2026-10-22)

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** an owner answer to WEAR-FIT-LIC; a new release of `fitdecode`, `fitparse`, `fit-tool` or `garmin-fit-sdk`; a change to Garmin's FIT Protocol License (the text says "Last updated: October 12, 2022" and Garmin may amend it, section 11g); OM-2 (= OW-W3) shows which metrics the real Garmin export holds.

> **Point-in-time research (2026-10-22). Not legal advice.** Planning and documentation only. No product code, dependency or `requirements*.txt` changed, and no owner gate is answered here. HealthCentral was read at `origin/main` `0e2799b`. Sources were read on 2026-10-22 unless a row says otherwise. Markers: **[V]** read in a primary source or in command output on the read date; **[I]** inferred from what was read; **[U]** could not be checked (used only where a source was unreachable or silent). Where a licence text is ambiguous this note says so and stops; it infers no reading.

## The question

Owner decision OW-W7 (`docs/capstone-report/owner-decisions-2026-09-27.md:385`, prompt 35), verbatim:

> "OW-W7, re-asked with the distinction above. Garmin's licence restricts USE to 'internal business purposes' and forbids DISTRIBUTING its SDK; being non-commercial does not change that. A pip dependency (each user downloads Garmin's SDK themselves) is lower risk than bundling it into an installer (HC-M08), which would be distribution. Which path for reading Garmin .FIT files?"

The owner picked "Research MIT FIT decoder": "A planner checks an independent MIT decoder (e.g. fitdecode/fitparse) and whether Garmin's FIT protocol licence still applies; the dependency choice comes back to you. Avoids Garmin's SDK terms if it holds." This note is that research. It feeds the new gate WEAR-FIT-LIC (draft at the end).

## Headline findings

1. **Q1 is ambiguous in the text, so no reading is inferred.** The Garmin licence defines the "Licensed Technology" as Garmin's FIT SDK "that includes documentation describing the FIT protocol and related source code files". It never says that the file format itself, or an independent implementation of it, is licensed. It also never says the format is free to implement. Section 1 grants a licence "to use the FIT protocol in any software created by Licensee". Garmin publishes no statement on third-party decoders on any page read. See Q1.
2. **Every decoder embeds a profile generated from Garmin's SDK profile.** `fitdecode`, `fitparse` and `fit-tool` each ship a generated profile module stamped with a Garmin SDK version (21.171, 20.8, 21.212/21.213). Garmin ships `Profile.xlsx` in the `garmin/fit-sdk-tools` repo, whose `LICENSE.txt` is word-for-word the same agreement. Whether that makes the MIT decoders subject to Garmin's terms is a legal question this research does not answer. See Q2.
3. **`fit-tool` is BSD-3-Clause, not MIT, and is a community fork** of a package its author removed from PyPI. The plan's "licence field empty on PyPI" is a metadata artefact: the wheel carries `License-Expression: BSD-3-Clause` (Stages Cycling, 2021). `garmin-fit-sdk` carries `LicenseRef-FIT-Protocol-License-Agreement`.
4. **Robustness differs a lot.** On a 6.3 MB synthetic file (900,000 records) `fit-tool` hit a 2 GiB address-space cap and raised `MemoryError`; `fitdecode` stayed at 17 MiB. `fitdecode` only warns on a bad CRC by default; it must be called with `check_crc=CrcCheck.RAISE`. No decoder hung in 1,500 mutated files each. See Q3.
5. **`fitparse` cannot name three message types WEAR-11b may need** (`monitoring_hr_data` 211, `sleep_level` 275, `hrv_value` 371): its bundled profile is SDK 20.8 (2019), so they decode as `unknown_NNN` with raw field numbers. The other three decode all of them. See Q5.
6. **The plan's metric list and the brief differ.** The wearables-11 plan puts resting HR, steps and sleep intervals in scope and lists stress, HRV, SpO2 as non-goals (`docs/plans/2026-10-13-wearables-11-garmin-parser.md:32-37`, `docs/plans/2026-10-13-wearables-00-program.md:26`). Q5 tests both lists. This does not change the WEAR-FIT-LIC options.

## Method

1. Re-read the Garmin licence from `garmin/fit-python-sdk` and the same text in `garmin/fit-sdk-tools`; diffed the sdist `LICENSE.txt` against both (whitespace-normalised: identical).
2. Read Garmin's FIT SDK pages (overview, get-the-sdk, protocol, FIT CSV Tool) as served on 2026-10-22.
3. Downloaded each package's sdist from PyPI into its own empty directory outside the repo; read licence files, READMEs, history, and grepped source for `urllib`, `requests`, `socket`, `subprocess`, `http.client`.
4. Built a scratch Python 3.11.17 venv (`/tmp/claude-1000/fitdec/venv`, outside the repo, never the repo or `asclexis-311` venv) with the four packages at the pinned versions below. Scripts lived in a separate directory and were run with `python -I`.
5. Hand-encoded synthetic `.fit` files with `struct` (no decoder library used to write them), so no decoder produced its own test input. Decoded them in all four decoders with sockets and `subprocess.Popen` patched to raise and a 2 GiB address-space cap.
6. Real Garmin example files were **not** used: the only public ones found (`Activity.fit` in `garmin/fit-sdk-tools/examples`) sit under the same agreement. No real Garmin export exists (OW-W3 is open).

Versions tested (all installed in the scratch venv): `fitdecode 0.11.0`, `fitparse 1.2.0`, `fit-tool 0.9.16`, `garmin-fit-sdk 21.218.0`.

## Q1. Protocol vs SDK: what does the Garmin licence govern?

Source: `https://github.com/garmin/fit-python-sdk/blob/main/LICENSE.txt` (raw copy fetched and quoted below; read 2026-10-22). The same text is in `https://github.com/garmin/fit-sdk-tools/blob/main/LICENSE.txt` and in the `garmin-fit-sdk` 21.218.0 sdist (read 2026-10-22; all three identical after whitespace normalisation) [V].

**Definitions (verbatim, preamble):**

> "This Flexible and Interoperable Data Transfer (FIT) Protocol License Agreement (this "Agreement") is a binding agreement between Garmin International, Inc. and its affiliates (collectively, "Garmin") and the person or entity using the Licensed Technology (each, a "Licensee" or "you"). As used in this Agreement, the "Licensed Technology" means Garmin's Flexible and Interoperable Data Transfer ("FIT") software development kit ("SDK") that includes documentation describing the FIT protocol and related source code files."

**Grant (section 1, verbatim):**

> "Subject to and conditioned upon Licensee's strict compliance with all terms and conditions set forth in this Agreement, Garmin hereby grants to Licensee a non-exclusive, royalty-free, non-transferable, non-sublicensable, limited license to use the Licensed Technology for Licensee's internal business purposes, including to use the FIT protocol in any software created by Licensee and to create modifications of the Licensed Technology ("Modifications") subject to the restrictions in Section 3."

**Restrictions that matter here (section 2, verbatim):**

> "c. except as set forth herein, rent, lease, lend, sell, sublicense, assign, distribute, publish, transfer or otherwise make available the Licensed Technology, or any features or functionality of the Licensed Technology, to any third party for any reason;"
>
> "d. distribute the Licensed Technology or any derivatives thereof so that any part of it becomes subject to any license that requires that the Licensed Technology or any of Garmin's other intellectual property be disclosed or distributed in source code form, or that others have the right to modify it;"
>
> "h. fail to comply with all definitions and provisions in the FIT protocol or deviate from the standards as defined in the FIT protocol and related documentation."

Also: section 4 "Without limiting the foregoing, the Licensed Technology is Confidential Information of Garmin."; section 7 "Licensee is responsible and liable for all uses of the Licensed Technology through access thereto provided or enabled by Licensee, directly or indirectly."; section 11g "This Agreement may be amended from time to time by Garmin in its sole discretion."; section 11i "No Third-Party Beneficiaries"; footer "Last updated: October 12, 2022." [V]

**Garmin statements on third-party decoders.** None found. The licence has no section on independent implementations. Garmin's pages read (`https://developer.garmin.com/fit/overview/`, `/fit/get-the-sdk/`, `/fit/articles/fit-protocol/fit_protocol.html`, `/fit/fitcsvtool/`) describe the format and the Garmin SDKs and say nothing about third-party decoders or about licensing of the format [V, absence on those pages]. Garmin's developer forum, terms-of-use page and any FIT SDK licence page elsewhere were not read: `developer.garmin.com/fit/terms` returned 404, and `thisisant.com/resources/fit` redirected to an ANT programme page with no FIT licence text. Those are **[U]**.

Two Garmin statements bear on what is "the SDK":

- The overview page lists `Profile.xlsx` as "The FIT Profile (Profile.xls) lists all of the predefined FIT messages and FIT data types found in the FIT SDK ... Profile.xlsx is located at /path/to/fit/sdk/Profile.xlsx." [V]
- The protocol page (global profile): "Users should not modify existing definitions found in the global profile." Its revision history has "1.4 February 2013 ... Updated agreement; Clarified global profile usage" (the clarified text itself is not in the page). [V]

**What the text does and does not say [V], no inference drawn:**

- The Licensed Technology is defined as an SDK that includes protocol documentation and source code. The definition does not mention the file format as such.
- Section 1 treats "use the FIT protocol in any software created by Licensee" as something the licence grants within the Licensed Technology; it does not say that using the protocol without the SDK needs this licence, or that it does not.
- Section 2c reaches "any features or functionality of the Licensed Technology"; section 2h refers to "the FIT protocol and related documentation". Whether an independent decoder is covered by either phrase is not stated.

**Conclusion: ambiguous. This note stops here and infers no reading.** Whether the licence reaches an independent implementation of the format, and whether decoders built from the public profile are covered, needs a legal read (option 4 in WEAR-FIT-LIC).

## Q2. Each decoder

Read dates are 2026-10-22 for every cell. "Licence file" means the file inside the sdist, not the PyPI field.

| | `fitdecode` 0.11.0 | `fitparse` 1.2.0 | `fit-tool` 0.9.16 | `garmin-fit-sdk` 21.218.0 |
|---|---|---|---|---|
| Licence file text | MIT (`LICENSE.txt`) | MIT (`LICENSE`) | BSD-3-Clause, 3 clauses (`LICENSE`); wheel `License-Expression: BSD-3-Clause` | Garmin FIT Protocol License Agreement (`LICENSE.txt`, as quoted in Q1); wheel `License-Expression: LicenseRef-FIT-Protocol-License-Agreement` |
| Holder | "Copyright (c) 2018-present Jean-Charles Lefebvre" | "Copyright (c) 2011-2020, David Cooper; Copyright (c) 2017-2020, Carey Metcalfe" | "Copyright 2021 Stages Cycling"; `AUTHORS`: Matt Tucker (Stages Cycling) | Garmin International, Inc. |
| Written from | Generic approach of `fitparse` ("largely based on the generic approach adopted by fitparse ... `profile.py` and ... `generate_profile.py`", README Credits). Its `profile.py` header: "EXPORTED PROFILE FROM SDK VERSION 21.171 ON 2025-08-04". HISTORY v0.11.0: "FIT SDK profile upgraded to v21.171.0"; `generate_profile` reads the "FIT SDK Zip archive" and `Profile.xlsx`. | `profile.py` header: "EXPORTED PROFILE FROM SDK VERSION 20.8 ON 2019-03-05". README: update by downloading "the latest ANT FIT SDK" and running `scripts/generate_profile.py /path/to/fit_sdk.zip`. | Generator `fit_tool/gen/component_registry.py` "Extract main-field component definitions from Profile.xlsx for code generation"; README "Profile in use: 21.212.0 (`fit_tool.SDK_VERSION`)"; upstream commit 2026-08-14 "upgrade garmin fit sdk profile version 21.213.0". README: "community-maintained fork. The original package was removed from PyPI by its author". | Garmin's own SDK. Decode only ("The Python SDK supports decoding of FIT files only", Garmin get-the-sdk page). |
| Terms the profile ships on | `Profile.xlsx` ships in `garmin/fit-sdk-tools` (and the SDK zip) under the same Garmin agreement as Q1 (`LICENSE.txt` identical). None of the three MIT/BSD packages' files states which terms their generated profile is under. **[U]** whether generated output is covered by Garmin's agreement. | same | same | same agreement |
| Last release | 2025-08-06 (upstream last commit 2025-08-06, "release v0.11.0"); 16 open issues | 2020-09-07 (upstream last commit 2025-01-28, a datetime fix, unreleased); 48 open issues | 2026-08-05 (upstream last commit 2026-08-14; 1 open issue; 7 stars) | 2026-10-06 (upstream commit 2026-10-06 "Garmin FIT SDK 21.218.0") |
| Pure Python or native | Pure Python, wheel tag `py3-none-any`; no `.so`/`.c` files | sdist only, no wheel; pure Python (6 `.py`), no native | Pure Python, `py3-none-any` | Pure Python, `py3-none-any` |
| Transitive deps (runtime) | none (all `Requires-Dist` are `extra == "dev"`) | none (`setup.py`: `requires = None` on Python 3) | none (`dependencies = []`; `gen` extra not needed) | none on 3.11 (`typing_extensions` only for Python < 3.8) |
| `requires_python` | `>=3.6` | not declared | `>=3.9` | `>=3.6` |
| Network/subprocess in source | none: grep for `urllib`, `requests`, `socket`, `subprocess`, `http.client`, `urlopen` finds only `import os` / `os.path` | none (only `import os`) | none (only `import os`; 207 `.py` files incl. generator) | none (only `import os` in `stream.py`) |

**Python 3.11 import and decode of one synthetic `.fit`** (scratch venv, Python 3.11.17, `python -I`, sockets and `subprocess.Popen` patched to raise, file `synth.fit`, 155 bytes, hand-encoded). Output pasted:

```
##### fitdecode
OK {'file_id': 1, 'monitoring_hr_data': 1, 'monitoring': 1, 'stress_level': 2, 'hrv_value': 1, 'sleep_level': 2}
   monitoring_hr_data {'timestamp': datetime.datetime(2025, 10, 21, 16, 53, 20, tzinfo=datetime.timezone.utc), 'resting_heart_rate': 52, 'current_day_resting_heart_rate': 53}
   monitoring {'timestamp': ..., 'activity_type': 'walking', 'steps': 2400}
   stress_level {'stress_level_value': 37, 'stress_level_time': ...}
   hrv_value {'timestamp': ..., 'value': 40.0}
   sleep_level {'timestamp': ..., 'sleep_level': 'deep'}
t=0.07s maxrss=41MiB
##### fitparse
OK {'file_id': 1, 'unknown_211': 1, 'monitoring': 1, 'stress_level': 2, 'unknown_371': 1, 'unknown_275': 2}
   monitoring {'timestamp': datetime.datetime(2025, 10, 21, 16, 54, 20), 'activity_type': 'walking', 'steps': 2400}
   stress_level {'stress_level_value': 37, 'stress_level_time': datetime.datetime(2025, 10, 21, 16, 55, 20)}
t=0.05s maxrss=34MiB
##### fit-tool
OK {'file_id': 1, 'monitoring_hr_data': 1, 'monitoring': 1, 'stress_level': 2, 'hrv_value': 1, 'sleep_level': 2}
   monitoring_hr_data {'timestamp': 1761065600000, 'resting_heart_rate': 52, 'current_day_resting_heart_rate': 53}
   monitoring {'timestamp': 1761065660000, 'cycles': 1200.0, 'activity_type': 6}
   stress_level {'stress_level_value': 37, 'stress_level_time': 1761065720000}
   hrv_value {'timestamp': 1761065840000, 'value': 40.0}
   sleep_level {'timestamp': 1761065900000, 'sleep_level': 3}
t=0.07s maxrss=22MiB
##### garmin-fit-sdk
is_fit True check_integrity True
errors []
OK {'file_id_mesgs': 1, 'monitoring_hr_data_mesgs': 1, 'monitoring_mesgs': 1, 'stress_level_mesgs': 2, 'hrv_value_mesgs': 1, 'sleep_level_mesgs': 2}
   monitoring_hr_data_mesgs {'timestamp': ..., 'resting_heart_rate': 52, 'current_day_resting_heart_rate': 53}
   monitoring_mesgs {'timestamp': ..., 'activity_type': 'walking', 'cycles': 1200.0, 'steps': 2400}
   stress_level_mesgs {'stress_level_value': 37, 'stress_level_time': ...}
   hrv_value_mesgs {'timestamp': ..., 'value': 40.0}
   sleep_level_mesgs {'timestamp': ..., 'sleep_level': 'deep'}
t=0.01s maxrss=18MiB
```

(`...` abbreviates a `datetime` already shown in full for the first row. The raw timestamps differ in type: `fit-tool` returns Unix milliseconds; the others return `datetime`, UTC-aware in `fitdecode` and `garmin-fit-sdk`, naive in `fitparse`.) The synthetic file is a test input only, not a claim about what Garmin writes.

No network or subprocess call was triggered by import or decode in any of the four (the patched functions would have raised `RuntimeError`).

## Q3. Robustness on untrusted files

Harness: one process per file, 2 GiB address-space cap (`RLIMIT_AS`), `timeout 90`. Seed files hand-encoded. "Raises" = a library exception. All values measured 2026-10-22 on this box (WSL2).

**CRC check and malformed input** (default call as a caller would write it; `fitdecode` and `fitparse` shown both ways where they differ):

| Case | `fitdecode` | `fitparse` | `fit-tool` | `garmin-fit-sdk` |
|---|---|---|---|---|
| Wrong file CRC | Default `check_crc=WARN`: **decodes everything, only emits a `warnings.warn`**. With `check_crc=CrcCheck.RAISE`: raises `FitCRCError` | Raises `FitCRCError` by default | Raises `FitCRCError` by default | `check_integrity()` returns `False`; `read()` still returns all the data **plus** an `errors` list (`RuntimeError ... CRC Error`): the caller must check `errors` or `check_integrity()` |
| Truncated (30 bytes cut) | Raises `FitEOFError` | Raises `FitEOFError` | Raises `FitHeaderError` ("truncated before the declared records and file CRC") | Returns the messages decoded so far plus an `errors` entry |
| Header claims 4 GiB of data, file is 155 bytes | Raises `FitEOFError` | Raises `FitEOFError` | Raises `FitHeaderError` | Returns data plus an `errors` entry (`TypeError`) |
| Garbage definition (255 fields declared) | `FitEOFError` | `FitParseError` | `FitRecordError` | `errors` entry, no data |
| Random 5000 bytes | `FitHeaderError` | `FitHeaderError` | `FitHeaderError` | `is_fit()` False, `errors` entry |
| Two FIT files concatenated | decodes both | decodes both | decodes both | decodes both |

**Developer-data fields** (`synth_dev.fit`: `developer_data_id`, `field_description`, then a `stress_level` message carrying one developer field `mydev=99`): all four decode the file without error and surface the developer field (`fitdecode` as a normal field `mydev`; `fitparse` as `mydev`; `fit-tool` in `developer_fields`; `garmin-fit-sdk` under `developer_fields: {0: 99}`) [V, command output].

**Oversized / unbounded allocation** (stress-level records, 7 bytes each):

| File | `fitdecode` | `fitparse` | `fit-tool` | `garmin-fit-sdk` |
|---|---|---|---|---|
| 2.1 MB, 300,000 records | 5.3 s, 17 MiB | 8.8 s, 152 MiB | 17.3 s, **765 MiB** | 5.6 s, 89 MiB |
| 6.3 MB, 900,000 records | 16.2 s, 17 MiB | 27.5 s, 423 MiB | **`MemoryError` at the 2 GiB cap** after 44.9 s | 15.3 s, 238 MiB |

Reading: `fitdecode` streams (flat memory). `fitparse` and `garmin-fit-sdk` hold every message and grow linearly (about 65 and 38 bytes per input byte). `fit-tool` grew about 360 bytes per input byte and exhausted 2 GiB on a 6.3 MB file. At the planned per-member FIT cap of 64 MiB (`docs/plans/2026-10-13-wearables-11-garmin-parser.md` line 20), the same ratios would give about 2.4 GiB for `garmin-fit-sdk`, 4.3 GiB for `fitparse` and over 20 GiB for `fit-tool` [I]; this extrapolation is untested. A small cap on decoded bytes, or `fitdecode`'s streaming, bounds memory. **`fit-tool` allocates without a practical bound relative to input size and is listed as such.**

**Hang check:** 1,500 byte-mutated copies of `synth_dev.fit` per decoder (1 to 8 random byte changes inside the body, CRC check off, 5 s alarm, 1 GiB cap). No timeouts and no `MemoryError` in any decoder; none took over 1 s. Outcomes: `fitdecode` 534 ok / 966 raised (`FitParseError`, `FitEOFError`, and also `TypeError` 173, `KeyError` 18, `AssertionError` 6, `ValueError` 4); `fitparse` 520 ok / 980 raised (also `KeyError` 32, `TypeError` 91); `fit-tool` 356 ok / 1,144 raised (`FitRecordError`, `ValueError` 173); `garmin-fit-sdk` 1,500 ok (errors collected, never raised). So **a caller must catch `Exception`, not only the library's error classes, for `fitdecode` and `fitparse`**. This is a small sample, not a proof of absence of hangs; no decoder is listed as hanging.

## Q4. Distribution shapes

"Pip dependency" = a line in `requirements.txt`; each user's machine downloads the package. "Bundled" = the installer (HC-M08) carries the package's files. What each licence text says (not a legal conclusion):

| Decoder | Pip dependency | Bundled in an installer |
|---|---|---|
| `fitdecode` (MIT) | Allowed: MIT grants use, copy, distribute "without restriction" | Allowed; the copyright and licence notice must stay with copies |
| `fitparse` (MIT) | Same | Same |
| `fit-tool` (BSD-3-Clause) | Allowed | Allowed; binary redistribution "must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials"; no endorsement use of "Stages Cycling" |
| `garmin-fit-sdk` | Text restricts use to "internal business purposes" (section 1) and bars to "distribute, publish, transfer or otherwise make available" (2c). Whether a user's own `pip install` makes that user the licensee, and whether a private individual's use is "internal business purposes", is not stated. **Ambiguous; no reading inferred.** | Bundling is "distribute ... to any third party" under the plain wording of 2c; the owner's own OW-W7 text treats it as distribution. Section 2d adds a restriction against distributing under a licence that requires disclosure of source or lets others modify; the HealthCentral repository licence was not checked here. |

The MIT and BSD rows say nothing about the Garmin-derived profile data inside them (Q2); that remains the open legal point.

## Q5. Metric coverage

The wearables-11 plan puts **resting heart rate, steps and sleep** in scope and **stress, HRV, SpO2** out of scope (non-goals). WEAR-11b is built only for in-scope metrics that OM-2 shows only in FIT. Both lists were tested. Input: the synthetic `synth.fit` from Q2 (no real export exists; OW-W3 is open; Garmin's public example file is under the Garmin agreement and was not used). The synthetic file proves what each decoder can name, not what Garmin devices actually write.

| Message (global number) | Metric | `fitdecode` | `fitparse` | `fit-tool` | `garmin-fit-sdk` |
|---|---|---|---|---|---|
| `monitoring_hr_data` (211): `resting_heart_rate` | resting HR (in scope) | named | **`unknown_211`**, raw `unknown_0: 52` | named | named |
| `monitoring` (55): `steps` | steps (in scope) | named, `steps: 2400` | named, `steps: 2400` | named; returns `cycles: 1200.0` and `activity_type: 6`; no `steps` key shown | named, `cycles` and `steps` |
| `sleep_level` (275): `sleep_level` | sleep stages (in scope as sleep) | named, `'deep'` | **`unknown_275`**, raw `unknown_0: 3` | named, integer `3` | named, `'deep'` |
| `stress_level` (227) | stress (non-goal) | named | named | named | named |
| `hrv_value` (371) | HRV (non-goal) | named, `40.0` | **`unknown_371`**, raw `unknown_0: 5120` (unscaled) | named, `40.0` | named, `40.0` |

`fitparse` keeps the raw bytes, so a caller could map field numbers by hand, but its profile is SDK 20.8 (2019) and it is not maintained as a release since 2020. Message numbers and field layouts come from `garmin_fit_sdk.profile` in the scratch venv (a Garmin-licensed source, read only to build the test file) [V].

## Findings table

Every row has a source and the date read. Read date for all rows: 2026-10-22.

| # | Claim | Marker | Source URL |
|---|---|---|---|
| F1 | Licensed Technology is defined as Garmin's FIT SDK "that includes documentation describing the FIT protocol and related source code files" | V | https://github.com/garmin/fit-python-sdk/blob/main/LICENSE.txt |
| F2 | Grant: "use the Licensed Technology for Licensee's internal business purposes, including to use the FIT protocol in any software created by Licensee"; 2c bars distributing or making available the technology "or any features or functionality" | V | same |
| F3 | The licence has no section on independent decoders or on the file format outside the SDK; whether it reaches them is ambiguous | V (text), no inference | same |
| F4 | The same agreement governs `Profile.xlsx` and example files in the tools repo | V | https://github.com/garmin/fit-sdk-tools/blob/main/LICENSE.txt ; https://github.com/garmin/fit-sdk-tools/blob/main/README.md |
| F5 | The `garmin-fit-sdk` 21.218.0 sdist carries the same licence text and `LicenseRef-FIT-Protocol-License-Agreement` | V | https://pypi.org/project/garmin-fit-sdk/21.218.0/ (sdist `LICENSE.txt`, wheel `METADATA`) |
| F6 | Garmin's pages read contain no statement on third-party decoders | V (absence on those pages) | https://developer.garmin.com/fit/overview/ ; https://developer.garmin.com/fit/articles/get-the-sdk/get_the_sdk.html ; https://developer.garmin.com/fit/articles/fit-protocol/fit_protocol.html ; https://developer.garmin.com/fit/fitcsvtool/ |
| F7 | Garmin's forum, terms of use and any other FIT licence page | U (not read; `/fit/terms` 404; `thisisant.com/resources/fit` redirects to an ANT programme page) | https://developer.garmin.com/fit/terms ; https://www.thisisant.com/resources/fit |
| F8 | Python SDK is decode-only | V | https://developer.garmin.com/fit/articles/get-the-sdk/get_the_sdk.html |
| F9 | `fitdecode` 0.11.0: MIT, holder Jean-Charles Lefebvre, released 2025-08-06, profile SDK 21.171, credits `fitparse`'s approach | V | https://pypi.org/project/fitdecode/0.11.0/ (sdist `LICENSE.txt`, `README.rst`, `HISTORY.rst`, `profile.py`) ; https://github.com/polyvertex/fitdecode |
| F10 | `fitparse` 1.2.0: MIT, holders David Cooper and Carey Metcalfe, released 2020-09-07, profile SDK 20.8 (2019-03-05); repo last commit 2025-01-28 | V | https://pypi.org/project/fitparse/1.2.0/ (sdist `LICENSE`, `README.md`, `profile.py`) ; https://github.com/dtcooper/python-fitparse |
| F11 | `fit-tool` 0.9.16: BSD-3-Clause, "Copyright 2021 Stages Cycling", released 2026-08-05, community fork of a package removed from PyPI, generator reads `Profile.xlsx` | V | https://pypi.org/project/fit-tool/0.9.16/ (sdist `LICENSE`, `AUTHORS`, `README.md`, `gen/component_registry.py`) ; https://github.com/shaonianche/python_fit_tool |
| F12 | The plan's "licence field empty on PyPI" for `fit-tool` and `garmin-fit-sdk` is a metadata artefact: both carry `License-Expression` in the wheel | V | https://pypi.org/pypi/fit-tool/json ; https://pypi.org/pypi/garmin-fit-sdk/json |
| F13 | All four are pure Python, with no runtime dependencies on Python 3.11 | V | the four sdists/wheels above (`METADATA`, `pyproject.toml`, `setup.py`) |
| F14 | No `urllib`, `requests`, `socket`, `subprocess` or `http.client` import in any of the four packages; no network/subprocess call during import or decode in the scratch run | V | grep of the four sdists above; `scripts/dec.py` run (scratch, not committed) |
| F15 | All four import and decode a synthetic `.fit` on Python 3.11.17 | V | scratch venv run, output pasted in Q2 |
| F16 | `fitdecode` default `check_crc` is `WARN` (decodes and warns on a wrong CRC); `RAISE` needs an explicit argument | V | `fitdecode/reader.py` line 153 in the 0.11.0 sdist ; https://github.com/polyvertex/fitdecode |
| F17 | `fit-tool` raised `MemoryError` at a 2 GiB cap on a 6.3 MB file; `fitdecode` stayed at 17 MiB | V | scratch run, table in Q3 |
| F18 | No hang or timeout in 1,500 mutated files per decoder; `fitdecode` and `fitparse` also raise `TypeError`/`KeyError`/`AssertionError` | V | scratch run, Q3 |
| F19 | `fitparse` decodes `monitoring_hr_data`, `sleep_level` and `hrv_value` only as `unknown_NNN` | V | scratch run, Q5 |
| F20 | Whether a profile generated from Garmin's `Profile.xlsx` is subject to Garmin's agreement | U (legal question, not answered by any source read) | n/a |
| F21 | wearables-11 in-scope metrics are resting HR, steps, sleep; stress, HRV, SpO2 are non-goals | V | `docs/plans/2026-10-13-wearables-11-garmin-parser.md:32-37` ; `docs/plans/2026-10-13-wearables-00-program.md:26` (repo, `origin/main` `0e2799b`) |
| F22 | Owner's WEAR-D5 answer: "(b) garmin-fit-sdk after licence read" | V | `docs/plans/2026-10-13-wearables-00-program.md:163` |

## Open points

1. **Q1 stays open.** The licence text does not say whether it reaches the format or independent decoders; only a legal read (OD-8 / OM-7) can settle it.
2. **Profile provenance (F20).** All three non-Garmin decoders embed a profile generated from a Garmin SDK profile. Nothing read says which terms such generated output carries. This is the strongest reason the "MIT decoder avoids Garmin's terms" idea is not yet established.
3. **Garmin's forum and other statements (F7)** were not read; a Garmin statement on third-party decoders may exist outside the pages reachable here.
4. **Real files.** OW-W3 (OM-2) is still open. Message coverage in Q5 is for what each decoder can name, not for what a Garmin export contains. If every in-scope metric is in the JSON, WEAR-11b is not built.
5. **Wording gap in the brief vs the plan (F21):** stress and HRV are non-goals in the wearables plan. If the owner wants them in scope, the program non-goals list changes; that is not decided here.
6. **`fit-tool` maintenance risk:** one maintainer, 7 stars, a fork of a removed package.
7. **Pin policy:** the 11b-0 rule wants a pinned version at least two weeks old. On 2026-10-22 every version tested meets it (the newest, `garmin-fit-sdk` 21.218.0, is 16 days old); a pin chosen later must be re-checked.
8. **Caller duties if a decoder is chosen:** with `fitdecode`, pass `check_crc=CrcCheck.RAISE` explicitly; with `fitdecode` or `fitparse`, catch `Exception`, not only the library's error classes (Q3).

## WEAR-FIT-LIC: draft owner question (no recommendation)

Draft, from `docs/plans/2026-10-15-build-program/lane-F-docs-owner-wearables.md` section 2.16 with the summary filled from the findings above. Asked only after this research lands.

> "WEAR-11b reads Garmin metrics that exist only in .FIT files. The research found that Garmin's licence text defines its 'Licensed Technology' as Garmin's FIT SDK including protocol documentation and source code, and does not say whether it reaches the FIT file format itself or independent decoders (the text is ambiguous, so no reading was inferred). Independent decoders exist under MIT (fitdecode, fitparse) and BSD-3-Clause (fit-tool), but each embeds a profile generated from Garmin's SDK profile, and nothing read says on what terms that profile may be used. fitdecode is maintained and streams files in flat memory; fitparse has had no release since 2020 and cannot name three of the message types WEAR-11b may need; fit-tool allocated without bound on a 6.3 MB file. (Not legal advice.) Which decoder may WEAR-11b use?"

| Option (5 words or fewer) | Description |
|---|---|
| **MIT decoder (fitdecode)** | Pin the independent MIT decoder as a pip dependency; changes your WEAR-D5 choice from Garmin's SDK. Only sensible if the research shows Garmin's licence does not cover the format. |
| **Garmin SDK, pip only** | Pin `garmin-fit-sdk` as a pip dependency, never bundled in an installer (HC-M08). Keeps WEAR-D5 as answered; residual risk on "internal business purposes". |
| **No FIT: JSON only** | Drop WEAR-11b; FIT-only Garmin metrics stay unsupported. No licence risk. |
| **Get a legal read** | WEAR-11b waits for the OD-8 / OM-7 legal read. |

**Tradeoffs.** The MIT decoder avoids Garmin's SDK terms only if the format itself is free to implement; this research found that question unanswered in the text (Q1) and found that the decoder's profile comes from Garmin's SDK profile (Q2), so option 1 does not yet have the support its description requires. An unmaintained decoder (fitparse's last release is 2020) adds bug and security risk on untrusted files. Garmin's SDK is maintained and complete but its licence wording targets internal business use. JSON only is safe and loses some metrics. A legal read is correct but slow.

**Effect on an existing answer.** Option 1 changes the owner's WEAR-D5 answer ("(b) garmin-fit-sdk after licence read", `docs/plans/2026-10-13-wearables-00-program.md:163`). No owner answer to WEAR-FIT-LIC exists.

**Analogy.** Reading a song you want to cover: you may be free to play the tune your own way even if you may not copy the record label's sheet music; the research checks which of the two the licence actually restricts, and finds the text does not say.
