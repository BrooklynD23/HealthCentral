# Installer research for after the MVP (INSTALLER-POST-MVP)

**Last Updated:** 2026-10-23
**Owner:** repository owner
**Refresh Trigger:** S-C4-1 to S-C4-5 in the [packaging decision record](../../plans/2026-10-01-packaging-decision.md) are signed; MVP-PACKAGING or CODE-SIGNING gets an owner answer; RAPIDOCR-BUNDLE lands; the `main.py` CORS list, `app_data_path`, `sqlcipher3-binary`, `llama-cpp-python` or the embedding pin changes; Apple or Microsoft rewrites the pages cited in section 3.

> **Point-in-time research (2026-10-23).** Documentation only. No product code changed, no owner gate is answered here, no build is licensed, and no dependency is added. The packaging decision record's S-C4-1 to S-C4-5 boxes stay unticked. Markers as in the [MVP package](../2026-10-22-mvp/00-README.md): **[V]** read by me at the primary page (vendor docs, PyPI/npm/crates/Hugging Face JSON, GitHub API, or a local command) on 2026-10-23; **[A]** taken from an earlier research file or a search summary, not re-opened at the primary page; **[U]** not confirmed at a primary source. Recheck [A] and [U] before citing outside the repo.

## The question

After the 2026-10-31 showcase, what should "download Asclexis and double-click it" look like? Which shell, what ships in the box, what a stakeholder sees when the app is unsigned, and which owner gates must be answered first.

Local-first still holds. Every fetch below is install-time or build-time. None is a product runtime call.

## Code facts (read at `origin/main` 45640d5)

| Fact | Evidence |
|---|---|
| Local mode allows only `http://localhost:3000` and `http://127.0.0.1:3000` as CORS origins. Server mode swaps in `settings.cors_origins`. | `src/backend/main.py:118-122`; `src/backend/core/config.py:37` [V] |
| The backend binds `127.0.0.1` in local mode. | `src/backend/main.py:186` [V] |
| No `StaticFiles` mount and no `app.mount` in `main.py`. | grep of `src/backend/main.py` [V] |
| `app_data_path` returns the relative `Path("data")` in local mode, so data lands under the process working directory. | `src/backend/core/config.py:178-183` [V] |
| Every `Path(__file__)` site outside tests, scripts and migrations (grep, 2026-10-23): `api/feedback.py:66` (`rl_exports`, a **write** path, default for `RL_EXPORT_DIR`); `core/migrations.py:31,46` (`alembic.ini` and `migrations/`); `modules/embeddings.py:37` (`_BACKEND_DIR`); `modules/model_integrity.py:42` (`config/model_manifest.json`, four parents up). A fifth, `modules/agent/eval/scorer.py:80`, points at test golden files and is dev-only. | `src/backend/api/feedback.py:66`; `src/backend/core/migrations.py:31,46`; `src/backend/modules/embeddings.py:37`; `src/backend/modules/model_integrity.py:42` [V] |
| The embedding path default is relative (`models/embeddings/all-MiniLM-L6-v2`). A relative value resolves against `_BACKEND_DIR` (the source tree), not the working directory. An absolute `EMBEDDING_MODEL_PATH` skips that. | `src/backend/core/config.py:127`; `src/backend/modules/embeddings.py:48` [V] |
| An opt-in external runner exists (`external_api_provider`, empty by default). When on, it sends redacted text off the machine (owner decision D12). | `src/backend/core/config.py:159`; `src/backend/core/external_runner.py` [V] |
| Neither launcher fetches any model. | grep of `dev.ps1`, `dev.sh` for `download_models` and `embedding` finds nothing [V] |
| `download_models.py` has `auto`, `list`, `--tier`, `ollama`, `embedding` and `nli` commands. `embedding` fetches `sentence-transformers/all-MiniLM-L6-v2` at one pinned revision and checks a SHA-256 per file. | `src/backend/scripts/download_models.py:332-371`; `src/backend/modules/embeddings.py:19-36` [V] |

## 1. Shell: Tauri v2 sidecar, pywebview, or portable PyInstaller onedir

All three need the same product changes first: an absolute per-user data directory (this must also cover `rl_exports`, the feedback write path), the four source-relative sites in the code-facts table re-pointed or bundled, and the frontend built and served. The shell only changes the origin and the window.

| | Tauri v2 + PyInstaller sidecar | pywebview + PyInstaller | Portable PyInstaller onedir + browser |
|---|---|---|---|
| What the user sees | A native window and a real installer (MSI/NSIS/DMG from the Tauri bundler [A]) | A native window started by a Python launcher | A folder; a launcher opens the default browser |
| Licence | `tauri` crate and `@tauri-apps/cli` 2.12.4: Apache-2.0 OR MIT [V] (crates.io, npm) | pywebview 6.2.1: BSD-3-Clause [V] (PyPI) | PyInstaller 6.22.3: GPLv2-or-later with a special exception [V] (PyPI `license` field, quoted in section 4) |
| Version read | CLI release `tauri-cli-v2.12.4`, 2026-10-21 [V] (GitHub API); crate 2.12.5 [V] | 6.2.1 [V] | 6.22.3 [V] |
| Origin the page runs from | New origin (see below) | Same origin if the window loads the backend URL itself [U, follows from the design; test it] | Same origin: the page is served by the backend |
| C-LOCAL-3 CORS change | **Yes.** Add the webview origin to the local-mode list at `main.py:120` | None expected if the window loads `http://127.0.0.1:<port>` [U] | None. The packaging record says "Same-origin; no CORS change needed" (option A) |
| `StaticFiles` mount | Optional. Tauri can serve the built SPA itself from its bundle [A] | Needed, so the window has a URL to load | Needed |
| Per-user data dir (S-C4-2) | Needed, same as the others. Tauri can pass its app-data path to the sidecar as an argument or env var [U] | Needed | Needed |
| Extra runtime | Rust shell; WebView2 on Windows, WKWebView on macOS [A] | WebView2 on Windows [A] | None |
| Main risk | Two build toolchains (Rust and Python). Sidecar needs a binary per target triple | Python GUI loop plus a server thread; no installer, and I did not find a sidecar-style packaging page for it [U] | Least polished: a console window and a browser tab |

**Tauri facts read [V] at v2.tauri.app on 2026-10-23.**
- Sidecar: list the binary under `bundle.externalBin` in `tauri.conf.json`, for example `"externalBin": ["binaries/my-sidecar"]`. Each binary must also exist with a `-$TARGET_TRIPLE` suffix (for example `my-sidecar-x86_64-unknown-linux-gnu`). Running it from JavaScript needs a `shell:allow-execute` (or `shell:allow-spawn`) permission with `"sidecar": true`. The page mentions PyInstaller only as a common way to build such a binary and gives no steps.
- Origin: on Windows the custom protocol is served as `http://<scheme>.localhost` by default, or `https://<scheme>.localhost` when `useHttpsScheme` is true. macOS and Linux use `<scheme>://localhost`. The config reference says the https choice "will NOT allow mixed content when trying to fetch http endpoints". The sidecar is a plain `http://127.0.0.1` server, so keep the default (`false`) on Windows, or the webview may block the calls. Changing this value later also moves IndexedDB, cookies and localStorage, and old data is lost.
- The `<scheme>` for a default app is `tauri` [U]. The exact `Origin` header the backend sees on each OS was not read from a primary page. Capture it from a real build before editing the allow-list. Allow-list those exact strings. Never use `*` and never loosen the existing two entries.
- A search turned up a Tauri CVE (CVE-2026-42184) in `is_local_url()` on Windows and Android; the sources disagree on the affected range [A]. Pin Tauri at or above the fixed release and read the advisory at build time.

**Names used below.** The owner and the record use different letters, so this file uses names, not letters. "Onedir" is the PyInstaller one-folder build (the packaging record's Option A and MVP Q2's (b) "portable folder"). "Tauri" is the packaging record's Option B and MVP Q2's (c) "installer after MVP". MVP Q2's (a) "source + launcher" is a third thing: no build at all.

**What the owner already answered (not re-asked here).** MVP-PACKAGING (`owner-decisions-2026-09-27.md:396`, answered 2026-10-22) is the free-text reply "Option A then work on C installer", with no option label chosen. The L0 note on that row reads it as Q2 (a) source + launcher for the MVP, then Q2 (c) Tauri + PyInstaller sidecar as the installer after the MVP. CODE-SIGNING (`:398`) is "(a) No signing yet". Per the MVP package these restate S-C4-1 and S-C4-3, but the sign-off boxes in the packaging record stay unticked.

**Two tensions to settle.**
1. Q2 (c) as asked says the Tauri installer is "signed". The CODE-SIGNING answer is unsigned. A Tauri installer built under (a) is unsigned.
2. The CODE-SIGNING answer text promises macOS "right-click then Open". The Apple page I read (section 3) does not mention that route. The card below uses the System Settings path only.

**Recommendation (labelled, not a decision).** The owner's answer already points at Tauri with a PyInstaller sidecar after the MVP. The onedir is that sidecar, so building the onedir plus `StaticFiles` first is not wasted work, and it needs no CORS change. Tauri then adds the new origin and the CORS change. pywebview would skip Rust but gives no installer, so it does not fit the owner's "installer" wording. Signing off the packaging path is **S-C4-1** and belongs to the owner. This file does not choose.

## 2. Bundled or fetched once

D8 licenses shipping "the small embedding model" with the app. It does not license GGUF models. Bundling any other model needs its own owner decision (packaging record, "Not licensed by D8").

| Item | Size | Licence | Proposal | Gate |
|---|---|---|---|---|
| Embedding bundle, `all-MiniLM-L6-v2` at `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | The 11 files the pin fetches: 91,578,415 bytes, of which `model.safetensors` is 90,868,376 [V] (HF API, `?blobs=true` at that revision; sum of `siblings` for the files in `EMBEDDING_FILES`) | Apache-2.0 [V] (HF tag `license:apache-2.0`) | **Bundle** in the installer: D8 says so, it is under 100 MB, and the app needs it on first launch. The build must set an absolute `EMBEDDING_MODEL_PATH`, because a relative one resolves against the frozen `_BACKEND_DIR`. Hash-check at build time with the existing per-file SHA-256 | S-C4-4, S-C4-5, EMB-REV |
| Chat GGUF, default CPU tier | `phi-4-mini-instruct-Q4_K_M` 2,491,874,688 bytes [V] (bartowski repo, HF API). Smaller `low` tier `qwen2.5-0.5b-instruct-q4_k_m.gguf` 491,400,032 bytes [V] | Qwen2.5 0.5B: Apache-2.0 [V] (HF tag). Phi-4-mini: MIT [V] (HF API `microsoft/Phi-4-mini-instruct`, tag `license:mit`, read 2026-10-23). The bartowski repo carries no licence tag [V], so the upstream tag is the evidence | **Fetch once, user-triggered**, as today (`download_models.py auto`, C-LOCAL-1's sanctioned call). Shipping 2.5 GB inside an unsigned installer is a worse first download and needs a new owner decision | none new; a bundling change would need its own |
| RapidOCR models | 3 ONNX files, 31,749,509 bytes installed [A] (from the [RapidOCR research](../2026-10-22-rapidocr/00-README.md), `sha256sum`/`ls` there); the `rapidocr` 3.10.0 wheel is 27,288,134 bytes [V] (PyPI JSON). The full new install is 271.0 MB [A] (from [RapidOCR research](../2026-10-22-rapidocr/00-README.md)) | rapidocr and models: Apache-2.0 [A] (RapidOCR research: the wheel's `MODEL_LICENSES.md`; not re-read here). OpenCV wheel redistributes FFmpeg under LGPL [A] | **Only if RAPIDOCR-BUNDLE lands.** The models ship inside the wheel, so nothing is fetched. Pin `Det/Rec/Cls.model_path`, because a missing or mismatched file turns into a ModelScope download [A] | RAPIDOCR-BUNDLE (blocked on size) |
| NLI model | not measured here | not read here | Out of scope. `download_models.py nli` exists | none |

Sizes of the Python side (torch, SQLCipher, llama-cpp wheels) are in [research 01](../2026-10-22-mvp/01-desktop-packaging.md) [A]. The CPU torch footprint inside a frozen build is still unmeasured.

Install-time rule: the build machine runs `python scripts/download_models.py embedding` from `src/backend` (the script lives there; no repo-root copy exists) and the installer carries the result. The installed app never calls Hugging Face for the embedding model.

## 3. Unsigned delivery (CODE-SIGNING option a)

Under option (a) there is no certificate. What a stakeholder sees is below, with the evidence for each step.

**What the sources say.**
- Windows, unsigned file: the warning reads "Windows protected your PC" and the user "must choose 'Run anyway' before the app can run". Self-signed behaves the same. Enterprise policy can remove the choice. Reputation for unsigned files starts at zero for every new version. [V] (learn.microsoft.com SmartScreen reputation page, `ms.date` 2026-05-04, read 2026-10-23.)
- The "More info" link that reveals the "Run anyway" button is not on that page. It comes from Microsoft Q&A answers, so treat the click path as [A].
- Windows 11 Smart App Control "will block execution of unsigned files unless the file has a positive reputation" and "may supersede SmartScreen" [V] (same page). If Smart App Control is on, there may be no "Run anyway" button at all. Whether a stakeholder laptop has it on is [U].
- macOS: Apple's page "Safely open apps on your Mac" (support.apple.com/en-us/102445, "Published Date: May 27, 2026") [V] says macOS Catalina and later requires notarization by default. For an app that is not notarized it gives one path: try to open the app, then open System Settings, click Privacy & Security, scroll down and click **Open Anyway**, then click **Open** when the warning comes back. After that the app opens by double-click. The page does not state a macOS version range for these steps. It names Catalina only for the notarization default. The page does **not** mention the older right-click (Control-click) then Open route. Whether that route still works on the current macOS release is [U]. Do not put it on the card until someone tests it on a real Mac. The CODE-SIGNING answer text does promise it, so the owner may want it tested. The page also says the settings may be unavailable on a managed Mac.

**Draft card: "How to open Asclexis" (one page, for stakeholders).** Needs a real-machine check before it goes out.

> **Asclexis is a new app that we have not paid to have signed. Your computer will warn you. This is expected. It is safe to continue only if you got the file from the person who sent you this card.**
>
> **Windows**
> 1. Double-click the file. A blue box says "Windows protected your PC".
> 2. Click **More info**.
> 3. Click **Run anyway**.
> 4. If there is no "Run anyway" button, your PC is set to block unsigned apps. Stop and tell us. Do not turn the protection off.
>
> **Mac**
> 1. Double-click the app. A message says it cannot be opened. Click **Done** (do not move it to the Trash).
> 2. Open **System Settings**, then **Privacy & Security**.
> 3. Scroll down. Click **Open Anyway** next to the Asclexis message.
> 4. Click **Open** in the new box. You may need your Mac password.
> 5. Next time, double-click as normal.
>
> **After it opens:** Asclexis runs on your computer, and it does not send your data anywhere unless you turn on the optional cloud model [U: wording pending an owner decision]. It is not medical advice.
>
> **If anything looks different from these steps, stop and contact [owner contact].**

Open items for the card: no encryption claim (SQLCIPHER-WHEEL has not landed), the privacy line above, the exact button labels on each OS release [U], a screenshot per step, and the owner contact line.

## 4. Open owner gates (drafted, not asked)

Two of the five have a related owner answer on file. The sign-off boxes do not. In the [packaging decision record](../../plans/2026-10-01-packaging-decision.md) all five S-C4 boxes are unticked. The [MVP owner questions](../2026-10-22-mvp/07-owner-questions.md) say Q2 and Q3 "do not replace" those lines. This file records no answer to any gate.

**S-C4-1. Which packaging path?**
Plain words: how should people get the app after the showcase? On 2026-10-22 you answered MVP-PACKAGING with "Option A then work on C installer". Do you want that signed as the path?
- Tauri window and installer, with the onedir as its sidecar. Matches your answer. Adds a Rust toolchain, a new origin and a CORS change that needs its own review. Say whether the installer is signed or unsigned (see the tension in section 1).
- Onedir only, as a stop on the way. Smallest change, no CORS change. A console window and a browser tab.
- pywebview window. A window without Rust, but no installer.
Tradeoff: polish against build work and risk. Recommendation here: onedir first, as the Tauri sidecar.

**S-C4-2. Where does the app keep its data?**
Plain words: today it writes next to wherever you launched it. A packaged app needs one fixed home per user.
- (a) The standard per-user app-data folder of each OS.
- (b) A folder beside the app, for a fully portable copy.
Tradeoff: (a) survives updates and is what users expect. (b) is easy to copy but can sit in a read-only place. Either choice touches the vault, backup and delete-sweep paths, and DPAPI-sealed keys stay tied to one user and machine whichever is chosen.

**S-C4-3. Do we sign?**
Plain words: signing costs money and does not remove the Windows warning on day one.
- (a) No signing. Give out the card in section 3. You answered CODE-SIGNING with (a) on 2026-10-22; the record's S-C4-3 box is still open.
- (b) Windows only: Artifact Signing from $9.99/month [V] (Microsoft's page). The warning fades only as downloads build reputation. "Several weeks and hundreds of clean installs" is the page's own estimate.
- (c) Mac only: Apple Developer Program, USD 99/year [A]. A clean double-click on Mac.
Tradeoff: money and an identity check against stakeholder friction. EV certificates no longer bypass SmartScreen [V]. Smart App Control can block unsigned apps outright [V].

**S-C4-4. Which licence notices ship?**
Plain words: when we hand out other people's models and libraries, their licences ask us to say so.
- Ship a notices file listing each bundled item and its licence, for example the embedding model (Apache-2.0 [V]) and, if bundled, RapidOCR models (Apache-2.0 [V], with the OpenCV/FFmpeg LGPL flag [A]).
- PyInstaller's PyPI `license` field [V] reads: "GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones)". Read 2026-10-23.
Tradeoff: a small file against legal risk. The owner decides who signs off on notice wording.

**S-C4-5. Which embedding model and revision?**
Plain words: pick the exact model file set we ship.
- (a) `all-MiniLM-L6-v2` at `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, the current pin (91.6 MB [V]).
- (b) A different model or revision.
Tradeoff: (a) is already wired, hashed and tested offline. (b) means new hashes and tests, and possibly a re-index of stored vectors [U]. The answer must match the revision signed under EMB-REV.

## Sources (read 2026-10-23)

- https://v2.tauri.app/develop/sidecar/ ; https://v2.tauri.app/reference/config/ ; https://crates.io/api/v1/crates/tauri ; https://registry.npmjs.org/@tauri-apps/cli/latest ; https://api.github.com/repos/tauri-apps/tauri/releases/latest
- https://pypi.org/pypi/pywebview/json ; https://pypi.org/pypi/pyinstaller/json ; https://pypi.org/pypi/rapidocr/json
- https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2/revision/1110a243fdf4706b3f48f1d95db1a4f5529b4d41 ; https://huggingface.co/api/models/Qwen/Qwen2.5-0.5B-Instruct-GGUF ; https://huggingface.co/api/models/bartowski/microsoft_Phi-4-mini-instruct-GGUF
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
- https://support.apple.com/en-us/102445
