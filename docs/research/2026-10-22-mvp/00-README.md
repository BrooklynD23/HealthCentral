# MVP readiness research package (2026-10-22)

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** an owner answer to any question in [07-owner-questions.md](07-owner-questions.md); S-C4-1 is signed; `src/backend/requirements.txt` changes `sqlcipher3-binary`, `llama-cpp-python`, `pdfplumber` or `pytesseract`; the showcase date (2026-10-31) moves.

> **Point-in-time research (2026-10-22).** Planning and documentation only. No product code changed, no owner gate is answered here, and no dependency is added. HealthCentral was read at `origin/main` `d2843e8`. Six Haiku 5.5 research agents swept primary sources; Opus 5.5 checked the facts each recommendation rests on. Markers: **[V]** the orchestrator read it at the source (PyPI/npm/Hugging Face JSON, the vendor page, or a local command) on 2026-10-22; **[A]** an agent read it at a primary source and the orchestrator did not re-open it; **[U]** not confirmed at a primary source. Recheck [A] and [U] items before you cite them outside the repo.

## The question

Before the 2026-10-31 showcase, stakeholders who are not developers will download Asclexis and try it: start it, import a lab PDF, see trends, chat, and export. What tools, open-source projects and component libraries would make that safer and quicker, without breaking the local-first rule (no product network calls, everything bundleable and offline)?

## What the repo already decides

These come from [CLAUDE.md](../../../CLAUDE.md) and earlier records. They are constraints here, not open questions.

| Constraint | Consequence for this research |
|---|---|
| Local-first, no network in product paths | A library qualifies only if it runs offline and can be bundled. Install-time downloads (pip, npm, model fetch) are allowed; runtime calls are not. |
| All LLM calls via `ModelRunner`; no new layer over `core/llm/` | Serving options are compared as providers inside `core/llm/`, never as a parallel stack. |
| Ask-first files (CLAUDE.md §1) | Any change touching encryption (SQLCipher packaging) or auth needs an owner yes first. |
| Packaging is undecided | [Packaging decision record](../../plans/2026-10-01-packaging-decision.md): options A (portable folder), B (PyInstaller + Tauri), C (PyInstaller + Electron); S-C4-1 to S-C4-5 are unsigned. [01](01-desktop-packaging.md) adds measurements to that record and does not replace it. |
| Frontend direction | [2026-09-08 frontend research](../2026-09-08/08-frontend.md) chose to stay on recharts and to add `@radix-ui/react-dialog`; [02](02-frontend-components.md) builds on it. |

## Files

| File | Area | Headline |
|---|---|---|
| [01-desktop-packaging.md](01-desktop-packaging.md) | (a) one-click start on Windows/macOS, signing, bundling models | `sqlcipher3` 0.6.4 ships self-contained Windows/macOS wheels, while `sqlcipher3-binary` has never shipped any. Prebuilt llama-cpp CPU wheels exist. For the MVP, demo from source; build the installer afterwards. |
| [02-frontend-components.md](02-frontend-components.md) | (b) component libraries, charts, accessibility | Keep Radix/shadcn and recharts. Add `react-dialog` and use `ReferenceArea` for range bands. Do not adopt a second primitive family before the showcase. |
| [03-pdf-extraction-ocr.md](03-pdf-extraction-ocr.md) | (c) PDF, table and OCR options | Keep pdfplumber. Avoid PyMuPDF (AGPL) and Marker (weights licence). RapidOCR is the lightest post-MVP OCR. |
| [04-local-llm-serving.md](04-local-llm-serving.md) | (d) CPU-only serving and small models | Phi-4-mini (MIT) is the CPU default candidate; Qwen2.5-1.5B (Apache-2.0) is the 8 GB tier. Constrain judge labels with a JSON-schema enum. |
| [05-onboarding-errors-backups.md](05-onboarding-errors-backups.md) | (e) first run, local error reports, crash-safe backups | Keep `VACUUM INTO`. Add temp file + fsync + `os.replace` for the manifest and restore. Report errors locally only (no Sentry). |
| [06-testing-tools.md](06-testing-tools.md) | (f) offline test and quality tools | Add Hypothesis for the extract parsers, `@axe-core/playwright` in e2e, and report-only branch coverage. |
| [07-owner-questions.md](07-owner-questions.md) | decisions | Seven questions in plain language. Recommendations are given only where the evidence supports one. |

## Cross-cutting findings

1. **Encryption on Windows and macOS is a packaging problem, and a cheap fix exists.** Every `sqlcipher3-binary` release (0.5.0 to 0.6.0) ships manylinux x86_64 wheels only **[V]**, so `dev.ps1` installs without it and turns encryption off (`dev.ps1:584-591` sets `DATABASE_ENCRYPTION_REQUIRED=false`). `sqlcipher3` 0.6.4 (uploaded 2026-10-13) ships wheels for win_amd64, win32, win_arm64, macOS arm64, x86_64 and universal2, and Linux **[V]**. Its PyPI description reads "A completely self-contained binary package (wheel) is available starting with version 0.6.2" **[V]**. In a scratch Python 3.11 venv on Linux, `PRAGMA cipher_version` returned `4.19.0 community`, and the database file began with random bytes **[V]**. The import name is the same (`sqlcipher3`). The change touches encryption, so it is owner question Q1.
2. **llama-cpp-python has no wheels on PyPI.** Version 0.3.36 on PyPI is a single sdist **[V]**, so a Windows or macOS install compiles llama.cpp. The project's CPU wheel index lists `llama_cpp_python-0.3.35-py3-none-win_amd64.whl` and `-macosx_11_0_arm64.whl` **[V]**. Pointing the launchers at that index at install time is not a product network call.
3. **sentence-transformers needs torch.** `sentence-transformers` 6.2.0 requires `torch>=2.2` **[V]**, so its `backend="onnx"` option alone does not drop torch from a bundle. Dropping torch would mean calling onnxruntime directly in `modules/embeddings.py`, with a parity test against HC-EMB-002 and the 0.7 threshold left unchanged. That is post-MVP.
4. **Licences to avoid in a distributed build:** PyMuPDF (AGPL-3.0 or Artifex commercial) **[V]**, Nuitka (AGPL-3.0, plus paid add-ons) **[V]**, Marker weights (OpenRAIL-M variant) **[A]**, LM Studio (proprietary terms that bar redistribution) **[A]**, and the Llama 3.2 and Gemma 3 terms (not OSI) **[A]**. Gemma 4 E2B is `apache-2.0` on Hugging Face **[V]**.

The same pass produced a bug list, a readiness checklist and proposed queue rows. They are not part of this PR; L0 sequences them in the build-program queue. Code claims in files 01-06 cite a path, and a `file:line` at `d2843e8` where a line matters, so they can be re-checked without that list. Parser repros (file 03) were run locally on synthetic PDFs; the inputs and outputs are quoted there, and the scripts are not committed.
