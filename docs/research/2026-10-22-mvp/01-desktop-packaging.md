# 01 — Desktop packaging and one-click start

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** S-C4-1 to S-C4-5 are signed; `sqlcipher3-binary` or `llama-cpp-python` pins change; a packaging row is added to the build-program queue.

> **Point-in-time research (2026-10-22).** Markers as in [00-README.md](00-README.md). This file adds measurements to the [packaging decision record](../../plans/2026-10-01-packaging-decision.md). It does not choose an option, and it licenses no build.

## Today's first run (code facts at `d2843e8`)

| Fact | Evidence |
|---|---|
| Windows launcher: if pip fails and its log mentions "sqlcipher", reinstall without SQLCipher. The second install's output is discarded and its exit code is not checked. | `dev.ps1:480-500` |
| The Windows backend starts hidden with no log file. Readiness polls only the frontend. A dead backend is restarted every 2 s with no cap (the frontend has a cap of 3). | `dev.ps1:798-802`, `:844-854`, `:901-920` |
| Neither launcher fetches the embedding bundle (no `download_models` call). | grep of `dev.ps1`, `dev.sh` |
| `dev.sh` refuses `/mnt/*`, binds 127.0.0.1, writes logs and exits on failure. There is no macOS double-click path. | `dev.sh:60-71`, `:239-272` |
| Data lives under the backend working directory (`src/backend/data`), because `app_data_path` is CWD-relative. | `core/config.py:174-181` |

## Native wheels: the real blocker

| Package | What PyPI ships | Consequence | Option |
|---|---|---|---|
| `sqlcipher3-binary` (pinned `>=0.5.0`, `requirements.txt:32`) | every release 0.5.0 to 0.6.0: manylinux x86_64 wheels only, no sdist for 0.6.0 **[V]** | no SQLCipher on Windows or macOS; the vault is plaintext | `sqlcipher3` 0.6.4: self-contained wheels for cp310+ on win_amd64/win32/win_arm64, macOS arm64/x86_64/universal2, manylinux and musllinux; cp311 win_amd64 wheel 2,551,236 bytes; uploaded 2026-10-13 **[V]**. Licence: zlib-style (Gerhard Häring copyright in `LICENSE`) **[V]**. Linux scratch test: `PRAGMA cipher_version` = `4.19.0 community`; file header random **[V]**. Not run on Windows; existing-vault compatibility not tested. Owner Q1 |
| `llama-cpp-python==0.3.35` (`requirements.txt:72`) | PyPI 0.3.36: one sdist (`.tar.gz`), uploaded 2026-10-01 **[V]** | Windows/macOS compile llama.cpp; without a C++ toolchain the install fails | CPU index `https://abetlen.github.io/llama-cpp-python/whl/cpu` lists `0.3.35` and `0.3.36` `py3-none-win_amd64` and `py3-none-macosx_11_0_arm64` wheels **[V]**; Metal and CUDA indexes exist (README) **[A]** |
| `torch` (pulled in by `sentence-transformers>=…`, which requires `torch>=2.2` **[V]**) | 2.14.1 (2026-09-30) **[V]**; Windows cp311 wheel 124.1 MB, macOS arm64 127.3 MB, Linux x86_64 554.6 MB with CUDA deps **[A]** | dominates bundle size | Linux CPU-only index `download.pytorch.org/whl/cpu` (CI already uses it) **[A]**. A torch-free embedder would mean calling onnxruntime directly (post-MVP, parity test) |
| `weasyprint` | needs GTK on Windows **[A]** | the doctor-summary PDF may fail on Windows | already tracked in the packaging record |

Measured installed footprint (Linux venv, CPU torch): 1.5 GB total, torch 741 MB **[A]** (agent `du` on `~/venvs/asclexis-311`). Embedding bundle: 88 MB in the HF cache **[A]**; the model card gives 22.7M parameters, Apache-2.0 **[A]**.

## Packaging tools

| Tool | Licence | Latest | Fit | Notes |
|---|---|---|---|---|
| PyInstaller | "GPLv2-or-later with a special exception" **[V]**; the exception allows shipping non-GPL programs **[A]** | 6.22.3, 2026-09-12 **[V]** | best fit for options A and B | onedir recommended: onefile extracts to a temp `_MEI*` folder at every start and leaves it behind on a crash **[A]** (pyinstaller.org/en/stable/operating-mode.html). torch and sentence-transformers will need hidden-import hooks **[U]** |
| python-build-standalone + vendored wheels | MPL-2.0 **[A]** | — | portable folder without a freezer | Ship a relocatable CPython 3.11 and install the pinned wheels offline into it **[A]** |
| PyApp | Apache-2.0 OR MIT **[A]** | — | weak | It installs at first run unless wheels are vendored **[A]** |
| Nuitka | AGPL-3.0 (classifier: AGPLv3+) **[V]**; commercial add-ons EUR 250-1000/yr **[A]** | 4.3.1, 2026-10-17 **[V]** | avoid | licence, plus compile risk with native wheels |
| BeeWare Briefcase | BSD-3-Clause **[V]** | 0.4.6, 2026-10-13 **[V]** | spike only | still needs a webview for the UI |
| pywebview | BSD-3-Clause **[V]** | 6.2.1, 2026-04-15 **[V]** | thin native window over a same-origin backend | WebView2 on Windows: Evergreen is part of Windows 11; some Windows 10 machines lack it; the Standalone installer works offline, and the Fixed Version is over 250 MB **[A]** (learn.microsoft.com/microsoft-edge/webview2/concepts/distribution) |
| Tauri v2 + Python sidecar | Apache-2.0 OR MIT **[A]** | CLI 2.12.4 (21 Oct) **[A]** | post-MVP installer | Sidecar: `bundle.externalBin` with a target-triple suffix, `shell:allow-execute` with `sidecar: true` **[A]** (v2.tauri.app/develop/sidecar, page reachable **[V]**). New origin, so a C-LOCAL-3 CORS change |
| Electron + electron-builder | MIT **[A]** | 26.18.0 (20 Oct) **[A]** | avoid | adds a Chromium runtime of about 100 MB **[U]**; auto-update must stay off |

## Signing

- Windows: "EV certificates no longer bypass SmartScreen", and Artifact Signing (formerly Trusted Signing) "Starts at $9.99/month" **[V]** (learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation). Reputation builds over time, so a new binary still warns for a while **[A]**. Smart App Control on Windows 11 can block unsigned executables **[A]**.
- macOS: Apple Developer Program, USD 99/year **[A]** (developer.apple.com/programs, page reachable **[V]**). Notarization uses `codesign --options runtime`, then `xcrun notarytool submit --wait`, then `xcrun stapler staple` **[A]**. An un-notarized download is quarantined by Gatekeeper; the exact bypass steps on the current macOS release are **[U]**.

## Models in a bundle

- Embedding: D8 says ship it with the app. W-8 fetches it into `models/embeddings/` (88 MB) **[A]**. A bundle must set `EMBEDDING_MODEL_PATH` to an absolute path (packaging record).
- GGUF chat models stay a user-triggered download (D8 covers only the embedding model). Sizes are in [04](04-local-llm-serving.md).

## Recommendation

- **For 2026-10-31 (the freeze is 2026-10-24):** demo from source with the launchers, after the first-run fixes. Use the CPU wheel index for llama-cpp, log the backend and wait for `/health`, cap restarts, fetch the embedding bundle, and (if owner Q1 says yes) switch to `sqlcipher3`. No signing. A one-page "how to start" card per OS. Evidence: no packaging row exists, and the record's open items (S-C4-2 data directory, the `StaticFiles` mount, source-relative paths) are each separate product changes.
- **After the showcase:** option A (PyInstaller onedir, same-origin `StaticFiles`, absolute per-user data directory) first. A Tauri or pywebview window can wrap it later. Signing per owner Q3.

## Sources

- https://pypi.org/project/sqlcipher3/ ; https://github.com/coleifer/sqlcipher3 ; https://pypi.org/project/sqlcipher3-binary/
- https://pypi.org/project/llama-cpp-python/ ; https://abetlen.github.io/llama-cpp-python/whl/cpu/llama-cpp-python/
- https://pypi.org/project/torch/ ; https://download.pytorch.org/whl/cpu/ ; https://pypi.org/project/sentence-transformers/ ; https://sbert.net/docs/sentence_transformer/usage/efficiency.html
- https://pyinstaller.org/en/stable/license.html ; https://pyinstaller.org/en/stable/operating-mode.html
- https://pypi.org/project/Nuitka/ ; https://nuitka.net/doc/commercial.html ; https://pypi.org/project/briefcase/ ; https://pywebview.flowrl.com/
- https://github.com/astral-sh/python-build-standalone ; https://github.com/ofek/pyapp
- https://v2.tauri.app/develop/sidecar/ ; https://github.com/tauri-apps/tauri ; https://www.electron.build/
- https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation ; https://developer.apple.com/programs/ ; https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
