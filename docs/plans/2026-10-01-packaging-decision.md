# HC-M08a Packaging Decision Record

**Last Updated:** 2026-10-01
**Owner:** repository owner
**Refresh Trigger:** W-8 lands on `main`; S-C4-1…5 are signed; `requirements.txt` native-dependency pins change; `core/config.py` `app_data_path` changes; a `StaticFiles` mount is added.
**Status:** PROPOSED — owner decision pending

This record answers HC-M08a (`feature_list.json:94-96`): "Decision doc exists, passes docs lint, and names a chosen path with rationale." It presents options and measured inputs and makes a labelled recommendation. **It does not choose a path.** The chosen path is owner decision S-C4-1, which carries an empty sign-off line below until the owner signs it. No build is authorized by this record (program stop gate: "a decision doc before any build").

Scope: this is the G-C4 group of [W-11b roadmap items G-C1…G-C4](2026-09-27-W11b-roadmap-items-gc1-gc4.md). It covers packaging approach (HC-M08) and how the embedding model (D8, D8-delivery) reaches a packaged install. It licenses no code, no build, and no model other than "the small embedding model" (D8).

## Background

- Audit §21 Q4 ([Devin-Audit-report.md](../../audit/2026-09-25/Devin-Audit-report.md):334): "**Both** — continue product work AND mine it for research. HC-M08 stays on the roadmap."
- D8 ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md):21): "Ship the small embedding model with the app / installer so no download is ever needed." This was **not** the recommended option.
- D8-delivery ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md):26): "**Script + offline load**" — "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git." This row now exists in the owner-decisions ledger (the W-11b plan's finding F-5, "not yet a row," is stale as of this record).
- Consequence note 4 on D8 ([owner-decisions-2026-09-27.md:62](../capstone-report/owner-decisions-2026-09-27.md)): no installer exists today; interim delivery was an open question, answered by D8-delivery. This record is the next step: the packaging approach that D8-delivery's "installer bundles it later (G-C4)" defers to.
- [W-8 plan](2026-09-27-W08-bundled-embedding-model.md) implements the interim script + offline load. **W-8 has not landed on `main`** (`grep -n embedding_model_path src/backend/core/config.py` on `main@8064244` prints nothing). Every embedding-delivery fact below is therefore labelled **"proposed (W-8, not on main)"**, never as something this repository's runtime does today.

## Options

- **(A) Portable folder plus launcher.** FastAPI serves the built SPA via `StaticFiles`, same-origin. No new native shell dependency.
- **(B) PyInstaller + Tauri.** A Rust-based desktop shell wraps the backend and a separately served frontend.
- **(C) PyInstaller + Electron.** A Chromium-based desktop shell wraps the backend and frontend.

Branch A §13 "Prepared recommendation: portable folder first" is an input to this record, not a conclusion of it.

## Criteria matrix

All facts below measured on `main@8064244` (the start SHA of this worktree, `docs/gc4-packaging-decision`), labelled `@start8064244`.

| Criterion | A: Portable folder | B: PyInstaller + Tauri | C: PyInstaller + Electron | Evidence |
|---|---|---|---|---|
| SQLCipher native bundling | Must bundle `sqlcipher3-binary` wheel as-is | Same bundling need, plus Rust shell | Same bundling need, plus Electron | `src/backend/requirements.txt:32` `sqlcipher3-binary>=0.5.0` @start8064244 |
| llama-cpp native bundling | Must bundle `llama-cpp-python` wheel (CPU build) | Same | Same | `src/backend/requirements.txt:72` `llama-cpp-python==0.3.35` @start8064244 |
| torch footprint | 1.2 GB installed (`sentence-transformers` pulls it in) | Same | Same | Task C4.1 Step 1, this worktree, D9 venv: `du -sh $SP/torch` → `1.2G` |
| WeasyPrint native GTK stack on Windows | Needed if PDF export runs in-process; GTK is not bundled by any of A/B/C automatically | Same | Same | `src/backend/requirements.txt:128` `weasyprint>=60.0` @start8064244 |
| Code signing (SmartScreen; cost; owner) | Needed for any installer/launcher to avoid SmartScreen warnings | Needed | Needed | S-C4-3 (owner, unsigned) |
| Total size | Smallest: no second runtime embedded | Larger: + Rust/WebView2 runtime | Largest: + full Chromium/Electron runtime | qualitative, from component list above |
| Update and uninstall path | Simplest: replace folder contents | Needs platform installer tooling (Tauri bundler) | Needs platform installer tooling (Electron builder) | qualitative |
| **Data directory** | Needs an absolute per-user directory; today `app_data_path` is CWD-relative | Same requirement | Same requirement | `src/backend/core/config.py:159-163` @start8064244: `app_mode == "local"` returns `Path("data")`, relative to the process working directory |
| **Source-relative paths the bundle must carry or re-point** | All three options face the same three paths | same | same | `src/backend/api/feedback.py:66` (`rl_exports` default, relative to `Path(__file__).resolve().parents[1]`); `src/backend/core/migrations.py:31,46` (`alembic.ini` + `migrations/` resolved relative to `Path(__file__).parent.parent`); `src/backend/modules/model_integrity.py:42` (repo-root `config/model_manifest.json`, resolved `Path(__file__).resolve().parent.parent.parent.parent`) — all @start8064244 |
| **Origin / CORS** | Same-origin; no CORS change needed | New origin (Tauri webview); needs a C-LOCAL-3 change | New origin (Electron renderer); needs a C-LOCAL-3 change | `src/backend/main.py:101` @start8064244: local mode allows only `http://localhost:3000` and `http://127.0.0.1:3000` |
| **Bind host** | 127.0.0.1, unchanged | 127.0.0.1, unchanged | 127.0.0.1, unchanged | `src/backend/main.py:166-167` @start8064244: `host = "127.0.0.1" if settings.app_mode == "local" else settings.host`; `dev.ps1:719` @start8064244 passes `--host 127.0.0.1` for local dev |
| **DPAPI portability** | Sealed keys are user- and machine-bound regardless of packaging choice | same | same | `src/backend/core/security.py:314-323` @start8064244 (`is_dpapi_available`, `seal_key_with_dpapi`); "portable" must not promise vault portability across machines beyond the password-sealed copy |
| GGUF delivery | Stays a user-triggered download in all three options | same | same | C-LOCAL-1's sanctioned call; D8 covers only the embedding model, not GGUF tiers |
| No `StaticFiles` mount today | n/a — (A) would add one | n/a | n/a | `docs/capstone-report/architecture-overview.md:21` @start8064244: "No `StaticFiles`/`app.mount` in the backend; no desktop shell"; confirmed empty by `grep -rn "StaticFiles\|app.mount" src/backend/main.py` on this worktree |

### Measured component sizes (Task C4.1 Step 1, D9 venv, this worktree)

```
$ SP=$("$PY" -c "import site; print(site.getsitepackages()[0])")
$ du -sh "$SP"/torch "$SP"/llama_cpp "$SP"/sqlcipher3* "$SP"/sentence_transformers "$SP"/transformers "$SP"
1.2G	.../site-packages/torch
21M	.../site-packages/llama_cpp
2.0M	.../site-packages/sqlcipher3
32K	.../site-packages/sqlcipher3_binary-0.6.0.dist-info
7.0M	.../site-packages/sqlcipher3_binary.libs
5.6M	.../site-packages/sentence_transformers
62M	.../site-packages/transformers
4.7G	.../site-packages                        (whole site-packages tree)

$ "$PY" -c "import torch; print(torch.__version__)"
2.14.0+cu130
```

### Frontend build size (Windows PowerShell, this worktree, `src/frontend`)

```
> npm ci
added 433 packages, and audited 434 packages in 19s
21 vulnerabilities (2 low, 4 moderate, 14 high, 1 critical) — pre-existing npm audit findings, not introduced by this record
> npm run build
✓ 2480 modules transformed.
✓ built in 51.61s
> '{0:N0} bytes' -f (Get-ChildItem dist -Recurse | Measure-Object Length -Sum).Sum
6,339,068 bytes
```
The build emits a warning that `dist/assets/index-CJUCxuZL.js` (540.89 kB) and `dist/assets/LineChart-CboYgZGt.js` (357.79 kB) exceed the 500 kB chunk-size guidance. That is a pre-existing frontend finding, not acted on by this record.

After the build, `git -C <worktree> status --short` showed nothing beyond this record's own files; `src/frontend/node_modules` and `src/frontend/dist` are git-ignored (`.gitignore:58`, `:65`), confirmed with `git check-ignore -v`.

### GGUF tier labels (not measurements)

```
$ python scripts/download_models.py list
Hardware detected: RAM=12.4GB, CPU=6 cores, Disk=102.4GB free, GPU=No, Recommended tier=gemma4-e4b
  low (Qwen2.5 0.5B): RAM 8GB, Disk 1GB
  gemma4-e2b: RAM 8GB, Disk 2GB [PLACEHOLDER URL - verify before use]
  gemma4-e4b: RAM 12GB, Disk 4GB [PLACEHOLDER URL - verify before use]
  mid (Phi-4-mini): RAM 16GB, Disk 3GB
  gemma4-12b: RAM 16GB, Disk 8GB [PLACEHOLDER URL - verify before use]
  high (BioMistral-7B): RAM 32GB, Disk 5GB
```
These are labels in the script (`src/backend/scripts/download_models.py` @start8064244, lines ~77/85/99), not measured download sizes. GGUF tiers stay user-triggered downloads under D8/C-LOCAL-1; they are not part of what the installer bundles.

## How the installer bundles the embedding model (D8 + D8-delivery)

- **Status of the fetch mechanism depends on W-8, which has not landed.** `grep -n "embedding_model_path" src/backend/core/config.py` on this worktree (`main@8064244`) printed nothing. `grep -n "embedding" src/backend/scripts/download_models.py` also printed nothing — the script currently lists only GGUF/Ollama commands. This mechanism is therefore labelled **"proposed (W-8, not on main)"**, exactly as the W-11b plan requires. If W-8 lands before S-C4-1, the build step would run `download_models.py embedding` on the build machine, network used at build time only, never at runtime (per the W-8 plan's own scope) — but that remains proposed, not implemented.
- **Which model: a PROPOSAL, owner-gated as S-C4-5.** D8 approves only "the small embedding model" ([owner-decisions-2026-09-27.md:21](../capstone-report/owner-decisions-2026-09-27.md)). It names no model, revision, hash, or file set. The candidate is the [W-8 plan](2026-09-27-W08-bundled-embedding-model.md)'s own proposal (`:34`, measured facts table): `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 11 files, 91,578,415 bytes, `model.safetensors` sha256 `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`. These values are written here as **"proposed (W-8), pending S-C4-5 / EMB-REV"**, never as the installer's actual contents — EMB-REV (the revision pin) is not signed (`owner-decisions-2026-09-27.md:62`, consequence note 4). If S-C4-5 names a different model or revision, the size and hash are re-measured, never carried over from this record.
- **Licence facts, measured this session (Task C4.1 Step 2, network read, `HF_HUB_OFFLINE` unset for this one command only):**
  ```
  sentence-transformers/all-MiniLM-L6-v2 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 LICENSE/NOTICE files: []
  sentence-transformers/all-MiniLM-L6-v2 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 front matter: ['base_model:', 'license: apache-2.0']
  base_model: UNMEASURED (not declared in the card front matter, or the first read failed)
  ```
  The model card declares `license: apache-2.0` and ships no `LICENSE`/`NOTICE` file in the repo listing. The `base_model:` front-matter key is present but empty, so the base model's own licence is **UNMEASURED** — the card does not name a base model to look up. Which licence and notice files the installer must carry, and on what terms, is **S-C4-4 (owner, unsigned)**. This record does not mandate any.
- The (proposed) launcher would set `EMBEDDING_MODEL_PATH` to an **absolute** path inside the install directory, because the W-8 plan resolves relative paths against `Path(__file__)`, which a PyInstaller one-file build relocates to a temporary extraction directory.
- The (proposed) build step would verify the sha256 of the bundled weights; runtime failure stays fail-closed, per the W-8 plan.
- No weights are committed to git by this record or by W-8's own scope.
- Acceptance for a later HC-M08b/c would be: re-run HC-EMB-002 against the packaged app with the network blocked.
- **Not licensed by D8:** GGUF tiers, and HC-M11's future cross-encoder weights. Branch A §14 d2: "Its model-distribution prerequisite is still unbuilt." D8 covers only "the small embedding model." This record states that bundling either one would need its own owner decision; it does not decide against bundling them, and it does not license HC-M11 code or weights (out of scope per the W-11b plan, G-C5).

## Recommendation

**Recommended: Option (A), portable folder plus launcher**, same-origin `StaticFiles` serving — consistent with branch A §13's prepared recommendation, now cross-checked against this session's measurements.

Rationale:
1. SQLCipher and llama-cpp native bundling is required under every option; (A) adds no second native runtime (no Rust/WebView2, no Chromium) on top of that baseline, keeping total size and update/uninstall surface smallest.
2. (A) needs no CORS change (same-origin), so it does not touch the `main.py:101` localhost allow-list or C-LOCAL-3. (B) and (C) both require widening the origin, which is a C-LOCAL-3 change needing its own review.
3. (A) requires no new desktop-shell toolchain (Tauri or Electron build pipeline) to learn and maintain, lowering the review and maintenance burden for a small team.
4. None of the three criteria that are genuinely option-dependent (native bundling, data directory, source-relative paths) favor (B) or (C) over (A); they are identical across all three options as measured above.

Consequences for a later HC-M08b/c/d, regardless of which option the owner picks:
- `app_data_path` (`core/config.py:159-163`) must change from CWD-relative `Path("data")` to an absolute per-user directory (S-C4-2).
- The three source-relative paths (`api/feedback.py:66`, `core/migrations.py:31,46`, `modules/model_integrity.py:42`) must be re-pointed or carried alongside the executable, since PyInstaller relocates `Path(__file__)` resolution at runtime.
- If (A): add a `StaticFiles` mount serving the built SPA from the backend, same-origin, no CORS change.
- If (B) or (C): add the new desktop-shell origin to the local-mode CORS allow-list (`main.py:101`), which is a C-LOCAL-3 change needing its own review.
- Code signing (S-C4-3) and the embedding-model licence/notice bundling (S-C4-4) are owner decisions independent of which packaging option is chosen.

## What this record does not decide

No build is authorized by this record. HC-M08b (or any packaging code, PyInstaller spec, launcher, or `StaticFiles` wiring) starts only after S-C4-1 is signed. This record does not bundle any model other than "the small embedding model" named by D8, does not commit model weights to git, and does not change `app_data_path`, CORS, or the bind host now — it only names what a later build phase must change.

## Owner decisions (unsigned)

- **S-C4-1** — the chosen packaging path (A, B, or C). ☐ owner: ____ date: ____
- **S-C4-2** — the data-directory location that replaces CWD-relative `app_data_path`. ☐ owner: ____ date: ____
- **S-C4-3** — code signing (yes/no, who pays). ☐ owner: ____ date: ____
- **S-C4-4** — licence notices for redistributed models and libraries (the embedding model's `apache-2.0` licence and any bundled-library notices). ☐ owner: ____ date: ____
- **S-C4-5** — the exact embedding model and revision to bundle. The W-8 candidate is `all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; it must match the revision signed under canonical owner gate EMB-REV (the W-8 plan's own sign-off line). ☐ owner: ____ date: ____

## Traceability

| ID | Location | Note |
|---|---|---|
| HC-M08a | `feature_list.json:94-96` | verification step quoted above |
| Audit §21 Q4 | [Devin-Audit-report.md:334](../../audit/2026-09-25/Devin-Audit-report.md) | "Both — continue product work AND mine it for research" |
| D8 | [owner-decisions-2026-09-27.md:21](../capstone-report/owner-decisions-2026-09-27.md) | "Ship the small embedding model with the app / installer" |
| D8-delivery | [owner-decisions-2026-09-27.md:26](../capstone-report/owner-decisions-2026-09-27.md) | "Script + offline load … Installer bundles it later (G-C4)" |
| Consequence note 4 | [owner-decisions-2026-09-27.md:62](../capstone-report/owner-decisions-2026-09-27.md) | no installer exists; interim delivery open |
| W-8 plan | [2026-09-27-W08-bundled-embedding-model.md](2026-09-27-W08-bundled-embedding-model.md) | embedding model facts, candidate revision, licence gap |
| G-C4 scope | [2026-09-27-W11b-roadmap-items-gc1-gc4.md](2026-09-27-W11b-roadmap-items-gc1-gc4.md) | Approval scope / G-C4, Task C4.2 |
