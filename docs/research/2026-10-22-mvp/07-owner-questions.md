# 07 — Owner questions from the MVP research pass

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** an owner answer to any question below (record it in `docs/capstone-report/owner-decisions-2026-09-27.md` through L0, then mark it answered here).

> **Point-in-time research (2026-10-22).** None of these is answered. A recommendation appears only where the evidence in files 01-06 supports one. Q2 and Q3 restate S-C4-1 and S-C4-3 from the [packaging decision record](../../plans/2026-10-01-packaging-decision.md) with this pass's evidence; they do not replace those sign-off lines.

## Q1 SQLCIPHER-WHEEL

On Windows and Mac, the app cannot install its encryption library today, so each profile's health data is saved without encryption. A newer package from the same author has the encryption built in for Windows and Mac. Think of a back door that was never fitted with its lock, and a ready-made lock that fits it.

- (a) **Switch to sqlcipher3.** Replace `sqlcipher3-binary` with `sqlcipher3>=0.6.4`. Vaults are encrypted on all three systems; first we test that existing vaults still open. **Recommended:** it closes a privacy claim that is false today, and encryption was confirmed on Linux ([01](01-desktop-packaging.md)).
- (b) **Linux-only demo.** Keep everything as is and show the app only on the GPU box. Stakeholder laptops stay unencrypted.
- (c) **Warn and continue.** Keep everything as is and show a "not encrypted on this computer" banner on Windows and Mac.

Tradeoffs: (a) changes an encryption dependency close to the 2026-10-24 freeze and needs a Windows test run. (b) and (c) keep the privacy claim false on the laptops stakeholders actually use.

## Q2 MVP-PACKAGING (S-C4-1)

How do stakeholders get the app for 2026-10-31? A packaged app needs new build work, and without signing it shows security warnings. Think of handing someone a recipe with a shopping list, versus a boxed meal that isn't ready yet.

- (a) **Source + launcher.** Clone the repo and run `dev.bat` or `dev.sh`, with the first-run fixes. Least new risk; needs Python and Node installed. **Recommended:** the freeze is 2026-10-24 and no packaging row exists.
- (b) **Portable folder.** A PyInstaller one-folder build, with the backend serving the web app. About 3-5 days of work; unsigned warnings.
- (c) **Installer after MVP.** Tauri with a PyInstaller sidecar, signed, built after the showcase.

Tradeoffs: (a) asks the most of a non-developer. (b) risks the freeze, and needs a per-user data folder (S-C4-2) and a same-origin web mount.

## Q3 CODE-SIGNING (S-C4-3)

An unsigned app shows "Windows protected your PC", and on a Mac it is blocked. Signing costs money, and on Windows it does not remove the warning right away. Think of a new shop: a licence on the wall helps, but a reputation still takes time.

- (a) **No signing yet.** Give stakeholders a one-page "how to open it" card.
- (b) **Windows signing.** Azure Artifact Signing, from $9.99/month (Microsoft's page); reputation still builds over weeks.
- (c) **Mac notarization.** Apple Developer Program, $99/year; a clean double-click on Mac.

No recommendation: the right choice depends on budget and on which laptops stakeholders use.

## Q4 SESSION-REENTRY

After an hour, or after the app restarts, the only way back in is the recovery code, and using it replaces the code. Stakeholders who try the app over a day will lock themselves out. Think of a house where the only key that works after dinner is the spare under the mat, and each use swaps the spare for a new one.

- (a) **Password unlock screen.** The start page lists existing profiles and asks for the password; the server side already exists. **Recommended:** only the screen is missing.
- (b) **Longer sessions.** Raise the 60-minute sign-in lifetime. Fewer lockouts, but the vault stays open longer.
- (c) **Keep recovery-only.** Document the recovery route for stakeholders.

Tradeoffs: (a) touches sign-in screens; the server code stays the same unless we also change a "403" to "401" (ask-first). (b) weakens the lock.

## Q5 OCR-FOR-MVP

Scanned or photographed lab reports give no values today unless Tesseract is installed and OCR is switched on. Think of a reader who reads print but not handwriting.

- (a) **Text PDFs only.** OCR stays off, and the app says clearly when a page has no text. **Recommended:** no new dependency before the freeze.
- (b) **Bundle RapidOCR.** Apache-2.0, about 27 MB plus onnxruntime; a new dependency and new code.
- (c) **Tesseract on the demo box.** Install it on the showcase machine only.

Tradeoffs: with (a), stakeholders with scanned reports see no values. (b) adds an untested extraction path.

## Q6 CPU-DEFAULT-MODEL

Most stakeholder laptops have no graphics card, so the chat model must fit in 8-16 GB of memory. Think of choosing an engine: a bigger one is stronger but may not fit the car.

- (a) **Phi-4-mini (MIT).** 2.49 GB, already the "mid" tier. **Recommended:** it is not a "thinking" model, so it avoids the judge problem (2026-10-22 diagnosis item D), where it scored 37 ALLOW / 3 BLOCK on llama.cpp.
- (b) **Qwen3-4B (Apache-2.0).** 2.5 GB; a thinking model, so `think=false` must be handled first.
- (c) **Qwen2.5-1.5B (Apache-2.0).** 1.12 GB, for 8 GB machines; replaces today's 0.5B low tier.

Tradeoffs: there are no primary-source CPU speed figures. Measure with `llama-bench` on one target laptop first.

## Q7 TEST-DEV-DEPS

Two test-only tools would catch extraction and accessibility bugs earlier. Both use MPL-2.0, which covers only their own files, and neither ships inside the app. Think of borrowing a neighbour's tool when the only condition is that you don't repaint it.

- (a) **Add both.** `hypothesis` (backend) and `@axe-core/playwright` (e2e). **Recommended:** both run offline inside the existing CI jobs.
- (b) **Hypothesis only.**
- (c) **Neither for now.**
