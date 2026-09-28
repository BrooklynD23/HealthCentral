# W-8 Bundled Embedding Model (D8) Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1, P4 or P5 merges (these change line numbers in the files below); the owner signs Q-FC or Q-HASH; the pinned embedding revision changes; G-C4 (installer) starts.
**Status:** PROPOSED — not executed
**Review status:** 4 Codex rounds; round-4 MAJOR fixed after the last round, not re-reviewed (owner acceptance required).
**Prerequisites:** P0-B and P1 merged to `origin/main`; also P4 and P5 merged (they edit `config/.env.example`, `core/config.py`, `api/documents.py` and `ci.yml` before this plan). Before P1 lands, Task 0's ancestry check fails: that is the intended STOP, not a defect.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load the embedding model only from a local directory, with no network access at runtime. Put it there with a one-time, explicit script fetch. Fail closed when it is absent, and never fall back silently to hash vectors.

**Architecture:**
- `modules/embeddings.py` resolves one configured directory (`EMBEDDING_MODEL_PATH`). It loads that directory with `SentenceTransformer(<dir>, local_files_only=True)`. If the model is missing or unloadable, it raises `EmbeddingModelUnavailableError`. The hash fallback survives only as an explicit `use_fallback=True` for tests.
- `scripts/download_models.py embedding` is the only thing that ever contacts Hugging Face for this model. It fetches a pinned revision and an allow-listed set of 11 files, then checks the weights' sha256.
- Retrieval (`modules/rag.py`) converts the new error into the existing `ModelUnavailableError`. The existing no-model surfaces therefore handle it, and no new UI is added.

**Tech Stack:** Python 3.11, sentence-transformers, huggingface_hub (script only), FastAPI, SQLAlchemy (per-profile SQLCipher vaults), pytest.

## Global Constraints

- The owner's approval text is binding and must not be widened. It is quoted in [Approval scope](#approval-scope).
- **The runtime stays local-only.** No product code path may contact Hugging Face or any other host (`CLAUDE.md` Hard invariants, "Local-first").
- **The one-time fetch is not a product runtime path.** It is a network action in a script that a person runs (or CI runs) explicitly, like the existing GGUF downloads.
- **No model files in git.** No `git add` of anything under `src/backend/models/embeddings/`, and no git-lfs. Vendoring is **not licensed**.
- **"HF offline" is implemented per call, not process-wide.** Never set `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` in product code. The reason: `huggingface_hub` reads the flag into `huggingface_hub.constants.HF_HUB_OFFLINE` at import (measured, hub 0.36.0). Setting it process-wide would also disable the sanctioned, user-triggered GGUF download `hf_hub_download` at `api/model_settings.py:903-937` (B@7b2ff1f).
- **Never lower a threshold.** The 0.7 similarity bar in `test_api_rag_index_002b` (`tests/test_rag_pipeline.py:237-270`, main@40f590e) stays. HC-EMB-002 reuses the same bar.
- The pinned model, from measurements in [Measured facts](#measured-facts):
  - name `all-MiniLM-L6-v2`
  - repo `sentence-transformers/all-MiniLM-L6-v2`
  - revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`
  - `model.safetensors` sha256 `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`
  - 11 files, 91,578,415 bytes
- The model keeps its label `all-MiniLM-L6-v2`. Rows already embedded by the real model therefore stay comparable, because the weights hash is identical across both cached revisions.
- Python 3.11 syntax only. Use `core.time.utcnow` for any timestamp.
- Interpreter for every gate: `~/venvs/asclexis-311/bin/python` (D9), written out in full in every command.
- Worktree root: `/mnt/c/Users/DangT/Documents/GitHub/hc-w08`, a dedicated `git worktree` for this phase (program ground rule 4), written out as an absolute path in every command. No command uses a relative `cd` after another `cd`.
- **Piped exit codes:** every block that pipes a command whose exit code matters (pytest into `tail`) starts with `set -o pipefail` and echoes `${PIPESTATUS[0]}`.
- **Undoing a break-it edit:** every "break it on purpose" edit is made by hand to uncommitted work and **undone by hand**. Confirm with `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 diff` that only the intended change remains. Never use `git checkout --` or `git restore` for this in the phase worktree: it would also discard the task's uncommitted implementation. Files this plan marks read-only are never edited, even temporarily; their behaviour is broken with `monkeypatch` inside the test run.
- **Baseline sentences:** a commit that changes collection updates **only** the collected count. A pass count ("all N pass", "N pass in CI") is written only from a pass count measured in a named environment: interpreter, and embedding model present or absent. Never write a collected number into a pass-count slot. If no such measurement exists, leave the sentence and flag it in the PR.
- **Counts move with collection:** every commit that adds tests also updates the collected count in the `CLAUDE.md` baseline bullet and the `AGENT.md` pytest line, measured just before that commit, and includes both files in its pathspec (CLAUDE.md: "update it in the same commit").
- **Every `path:line` below is labelled with its ref.** Re-verify each one on the post-P1/P4/P5 tree before editing: line numbers will have moved.

---

## Approval scope

**Owner decision D8** ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md), row D8):
- Choice: "**Bundle the model**"
- Option text: "Ship the small embedding model with the app / installer so no download is ever needed."
- This was **not** the recommended option.

**Owner decision D8-delivery**, 2026-09-27, Claude Code chat. It answers Consequence #4 of the same record. The selected option, verbatim:
- "**Script + offline load**" — "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git."

What the two texts license together:
1. A one-time fetch by `src/backend/scripts/download_models.py` into a local models directory.
2. A runtime that loads that directory with Hugging Face offline.
3. A runtime that **fails closed** when the directory is absent.
4. No weights in git.
5. An installer that bundles the model later, as part of G-C4 and not as part of this plan.

**Does NOT license:**
- Committing any model file to git, by plain commit or git-lfs (vendoring).
- Any runtime network call, including a "fetch on first use if missing" convenience.
- Setting `HF_HUB_OFFLINE` process-wide. See Global Constraints; if the owner wants this, stop (Q-OFFLINE).
- Building an installer or packaging (G-C4 / HC-M08 spike).
- Changing the embedding model (for example to `bge-small-en-v1.5`), its dimensions, or the 0.7 bar.
- **The specific patient-visible form of "fails closed".** The text says the runtime fails closed. It does not say what the patient sees: an error, a template, or a skipped step. This plan implements a conservative default that reuses the existing no-model surfaces. The form stays **owner-gated** (Q-FC, unsigned) until signed. See [What the patient sees](#what-the-patient-sees).
- Excluding vectors that the hash fallback stored before this change (Task 7). This changes retrieval for existing vaults and is **owner-gated** (Q-HASH, unsigned).
- Re-embedding existing vaults, new UI, new copy beyond the one error sentence in Task 5, or edits to ask-first files.

**"Bundle" wording vs reality:**
- No installer exists. HC-M08 is a spike, tracked as G-C4 ([implementation-program.md](../capstone-report/implementation-program.md), gap table).
- Until G-C4 lands, "ships with the app" means this: the app's own script fetches the model once, and the app never downloads it itself.
- `EMBEDDING_MODEL_PATH` is the seam the installer will use.
- G-C4 must re-run HC-EMB-002 against the packaged app. A frozen bundle changes what `Path(__file__)` resolves to.

## Traceability

| Kind | ID | Verified text (grep, 2026-09-27) |
|---|---|---|
| Handoff | W-8 ([handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md)) | "The embedding model ships with the app and loads from a local path, with HF offline at runtime. **Open:** delivery before an installer exists." Test: "HC-EMB-001: with the network blocked and an empty HF cache, the embedding module loads from the bundled path or fails closed. It must not silently use the fallback." Acceptance: "test green with the socket blocked" |
| Program | G-A3 ([program](../capstone-report/implementation-program.md), gap table) | "Local-only embedding load (LOCAL-03) · D8 · … the embedding module either loads from the configured local path or fails closed. It must not silently use the fallback." |
| Program | D8 row | "**DECIDED: bundle the model** (not the recommendation; delivery mechanism open)". This plan's Task 0 records the delivery answer |
| Contract | C-LOCAL-2 · PROPOSED ([contract §1](../capstone-report/architecture-engineering-contract.md)) | "The embedding model MUST load from a local path or cache and MUST NOT download implicitly at query time." |
| Contract | C-LOCAL-1 · BINDING | Its "Known exceptions" list includes "the implicit embedding download (C-LOCAL-2)", which this plan removes |
| Contract | C-SAFE-4 · BINDING | Covers "the 0.7 embedding-similarity assertion in `test_api_rag_index_002b`" |
| Matrix | LOCAL-03 ([matrix §1](../capstone-report/specs-compliance-matrix.md)) | "Model fetches happen only through user-triggered downloads … **gap**: implicit HF fetch on first embedding use" |

## Measured facts

The approach is designed from these measurements. Each has its command.

| Fact | Value | Command / evidence |
|---|---|---|
| Model loaded today | `all-MiniLM-L6-v2` by name, from the network or HF cache | `modules/embeddings.py:18,34,56` (main@40f590e = B@7b2ff1f, unchanged by A/B): `SentenceTransformer(self.config.model_name)` |
| Current fallback | SHA-256 token-hash bag-of-words vectors. Chosen silently on *any* load error because `use_fallback=True` is the default. Rows stored with `model_name="hash-fallback"` | `modules/embeddings.py:35,58-69,107,138-218` (main@40f590e) |
| Product callers (both default, so both silently fall back) | `api/documents.py:851` (A@692fdf3; `:850` main) `EmbeddingsModule()`; `modules/rag.py:168` (main@40f590e) `EmbeddingsModule()` | `git grep -n "EmbeddingsModule" origin/claude/healthcentral-agentic-research-r1n54x -- src/backend` |
| Agent path uses embeddings? | **No.** `modules/agent/tools/retrieve_chunks.py` (B) selects rows; the agent cache is exact-match | `git grep -n "embed" <B> -- src/backend/modules/agent` |
| Dead config | `default_embeddings_model = "bge-small-en-v1.5"` at `core/config.py:89` main@40f590e, **removed by B** (`2c98ae6`). `config/.env.example:82-84` still sets `DEFAULT_EMBEDDINGS_MODEL=bge-small-en-v1.5` on B (ignored, `extra="ignore"` at `core/config.py:18-23` B@7b2ff1f) | `git diff main <B> -- src/backend/core/config.py` |
| On-disk size, pinned revision | 11 files, **91,578,415 bytes** (≈87.3 MiB); `model.safetensors` 90,868,376 bytes | `find …/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41 -type f -printf "%s\n" \| awk '{s+=$1} END {print s}'` on `/mnt/c/Users/DangT/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2` |
| HF cache footprint | WSL `~/.cache/huggingface/hub/models--…all-MiniLM-L6-v2`: 88M (1 snapshot `c9745ed1…`, symlinked blobs). Windows cache: 175M (2 snapshot copies, no symlinks) | `du -sh <dir>` |
| Weights identical across revisions | sha256 `53aa51172d142c89…d9db` in both `c9745ed1d9f207416be6d2e6f8de32d1f16199bf` and `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; only `README.md` differs | `sha256sum model.safetensors` in each snapshot |
| Full upstream repo size (onnx/openvino/etc.) | **UNMEASURED**. `allow_patterns` below avoids pulling it | `python -c "from huggingface_hub import HfApi; i=HfApi().model_info('sentence-transformers/all-MiniLM-L6-v2', revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41', files_metadata=True); print(len(i.siblings), sum(s.size or 0 for s in i.siblings))"` (network) |
| License | Model card front matter `license: apache-2.0` (`README.md` in both cached snapshots). The base model's license is **UNMEASURED**, as is whether the repo ships a LICENSE/NOTICE file | `grep -n "^license" <snapshot>/README.md`; for the upstream files, the `list_repo_files` command in Task 4 Step 1 |
| Implicit fetch happened today | Windows cache `refs/main` rewritten `2026-09-27 17:05:28 -0700` to `1110a243…`; the new snapshot dir was created `17:05:33`. Some process on this machine contacted huggingface.co today. The process was not identified | `ls -la --time-style=full-iso /mnt/c/Users/DangT/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/refs` |
| Offline local load works, 0 sockets | `SentenceTransformer(<snapshot dir>, local_files_only=True)` with `HF_HOME` empty and `connect`/`connect_ex`/`create_connection`/`getaddrinfo` blocked: loaded in 0.17 s; dim 384; **similarity 0.9039** on the `002b` sentence pair; **0 socket attempts**. Missing dir → `FileNotFoundError`, 0 attempts. Bare name + `local_files_only=True` + empty cache → `OSError`, 0 attempts | Probe script, Windows Python 3.13.7, sentence-transformers 5.2.0, huggingface_hub 0.36.0, transformers 4.57.3, torch 2.9.1+cpu. **Not** measured in the 3.11 venv; Task 1 re-measures |
| Socket-guard pitfall | Replacing `socket.socket` with a function *before* `ssl` is imported crashes `import ssl` (`TypeError: function() argument 'code' must be code, not str`). `tests/agent/test_s4_phi_gate.py:81-92` (main@40f590e) works only because `ssl` is already imported. The HC-EMB guard patches methods instead | Same probe |
| CI and the embedding model | `backend-tests` installs requirements and runs pytest; there is **no** model step (`.github/workflows/ci.yml:33-51` B@7b2ff1f). CI passes `002b` only through the implicit fetch this plan removes | `git show <B>:.github/workflows/ci.yml` |
| `local_files_only` support | `True` for sentence-transformers 5.2.0. The requirements floor is `sentence-transformers>=2.2.0` (`src/backend/requirements.txt` B@7b2ff1f) | `inspect.signature(SentenceTransformer.__init__)` |

## What the patient sees

Scenario: the model has **not** been fetched. The "after" column shows this plan's default form, which is owner-gated as **Q-FC**.

| Surface | Today (no network and no cache) | After W-8 (default form) |
|---|---|---|
| Assistant chat, agent path (default on, `AGENT_ENABLED_DEFAULT = True` at `modules/agent/settings.py:19` B@7b2ff1f) | unaffected | unaffected (the agent does not embed) |
| Assistant chat, legacy path (agent off, or any agent exception at `api/assistant.py:800-809` B@7b2ff1f) | LLM answer built on hash-vector retrieval, silently | The existing knowledge-fallback answer (`api/assistant.py:904-923,1281+` B@7b2ff1f), with `verification.enabled=false`. Same as a no-LLM install. Only when the profile has document chunks to search |
| Grounded interpretation `POST /interpretations/observations/{id}/interpret-grounded` | answer on hash retrieval | Existing HTTP 501 path (`api/interpretations.py:453-457` B@7b2ff1f), whose `detail` is the fixed sentence "Document search is unavailable because the local embedding model is not installed." No filesystem path |
| Document import | chunks embedded with hash vectors | Import succeeds and observations are extracted. **No chunks are created.** The existing `WARNING` fires (`api/documents.py:684-685` A@692fdf3) |
| Document reprocess | previous chunks deleted, hash chunks written | Previous chunks **kept** (Task 6 fixes delete-before-embed) |
| Documents embedded by the hash fallback earlier | compared against real-model query vectors, which gives meaningless similarity | Task 7 (Q-HASH, gated): excluded from vector search until reprocessed |

If the owner rejects the default form, stop before Task 5. The alternatives are a generic HTTP 500, which is what happens if Task 5 is skipped, or a new explicit message, which needs new copy and UI. Both change Task 5.

## Owned files

| File | Action | Task |
|---|---|---|
| `src/backend/modules/embeddings.py` | modify: constants, `EmbeddingModelUnavailableError`, `resolve_embedding_model_dir`, offline loader, fail-closed default | 2 |
| `src/backend/core/config.py` | modify: add `embedding_model_path` beside `embedding_dimensions` (`:111-112` B@7b2ff1f) | 2 |
| `.gitignore` | modify: ignore `/src/backend/models/embeddings/` (after the `:81-86` block, B@7b2ff1f) | 2 |
| `config/.env.example` | modify: replace dead `DEFAULT_EMBEDDINGS_MODEL` lines (`:82-84` main@40f590e) with `EMBEDDING_MODEL_PATH` | 2 |
| `src/backend/scripts/download_models.py` | modify: `embedding` subcommand | 3 |
| `.github/workflows/ci.yml` | modify: explicit fetch step in `backend-tests` and `e2e-tests` | 4 |
| `src/backend/modules/rag.py` | modify: embed the query only after rows exist, and wrap the error (Task 5); model-name filter (Task 7, gated) | 5, 7 |
| `src/backend/api/documents.py` | modify: embed before deleting chunks on reprocess | 6 |
| `src/backend/tests/test_embedding_bundle.py` | create (HC-EMB-001..004e) | 2, 3, 4 |
| `src/backend/tests/test_embedding_fail_closed_paths.py` | create (HC-EMB-005..008) | 5, 6, 7 |
| `AGENT.md`, `CLAUDE.md` (baseline sentences only), `docs/capstone-report/architecture-engineering-contract.md`, `docs/capstone-report/specs-compliance-matrix.md`, `docs/capstone-report/architecture-overview.md`, `docs/capstone-report/claims-ledger.md`, `docs/architecture/ci-and-quality-gates.md`, `docs/architecture/performance-scalability-review.md` | modify | 8 |

**Read-only (ask-first, must not change):**
- `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`
- `core/auth.py` and anything auth or encryption: `core/security.py`, `core/profile_database.py`

**Read-only (other plans own them):**
- `api/assistant.py` (W-4 legacy abstention)
- `api/interpretations.py` (W-7)
- `modules/model_selector.py` (W-7)
- `src/backend/requirements.txt` (B/P1)
- existing tests, including `tests/test_rag_pipeline.py`

If any of these needs an edit, **stop**.

## Shared-file order

Rule: no two plans edit a shared file at the same time (program, "Shared files are ordered…").

| File | Order |
|---|---|
| `core/config.py` | P1 (B) → S-1 (+4 lines after `debug`, `:28` B@7b2ff1f) → P4 (comment at `:109`) → W-6 (if it edits config) → **W-8**. S-1 shifts W-8's anchors by +4; re-anchor by grep |
| `scripts/download_models.py` | P1 (B) → **W-8** |
| `api/documents.py` | P1 (A) → P5 (Task 2: `utcnow`) → **W-8** |
| `modules/rag.py` | W-5 (`:123-140`) → W-3 (`:323-332`, `:549-553`) → **W-8** (W-4 does not edit rag.py). W-3 and W-8 both edit the `_search_vectors_async` statement (`:549-553` B@7b2ff1f): a real hunk dependency, so serialize |
| `.gitignore` | P1 (B) → P3/W-1 (`!.claude/agents/`) → **W-8** |
| `ci.yml` | P1 → P5 (time lint) → W-4 (eval gate) → W-11a PR-3 (G-B4) → **W-8**, never concurrent (canonical order, 3a B-3) |
| `docs/architecture/ci-and-quality-gates.md` | P4 N6 → W-11a PR-3 (Task 9) → **W-8** (`:58`) → P4 F4 (canonical order, 3a B-3) |
| `config/.env.example` | P1 → S-1 (`:15-19`) → P4 Task 3 (removes `VECTOR_STORE_TYPE`) → **W-8**. S-1 shifts anchors below `:14` by +5; re-anchor by grep |
| `CLAUDE.md` / `AGENT.md` baseline lines | P1 → P4 → W-10 → **W-8** |
| capstone matrix / contract rows | any W, serialized |

**Hard prerequisites:** P1, P4 and P5 merged; also W-3 (shared `_search_vectors_async` statement in `rag.py`) and W-11a PR-3 (`ci.yml`, `ci-and-quality-gates.md`), per 3a B-2/B-3. The other rows are soft: rebase onto whichever of them merged first, and re-verify line numbers.

**Hazard for P5 and later plans:** P5 Task 1 runs `git add src/backend/models/`. The model directory lives inside that package directory (`models_path="models/"` resolves under `src/backend`), so Task 2's `.gitignore` line is what keeps model files out of such directory adds.

## Dependencies

- **Phases:** P1 (B brings `download_models.py`; A brings `documents.py`), P4, P5 (see order above). Downstream: G-C4 consumes `EMBEDDING_MODEL_PATH`.
- **Decisions:** D8 and D8-delivery (approved), D9 (3.11 venv; stop if absent), Q-FC and Q-HASH (this plan, unsigned), EMB-REV (this plan, unsigned), VERIFIED-FALLBACK (Q-FC + W-3 O-1, unsigned).

---

### Task 0: Create the phase worktree, record the owner decisions, open the gates

**Files:** none (PR description plus this plan's sign-off section).

- [ ] **Step 0: Create the worktree and prove it is post-P1.**
  ```bash
  git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin
  git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add /mnt/c/Users/DangT/Documents/GitHub/hc-w08 -b feat/w08-bundled-embedding-model origin/main
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
  ```
  - Prerequisites: P0-B and P1 merged to `origin/main` (plus P4 and P5, checked in Task 1 Step 2).
  - Expected: `post-P1-ok`.
  - Any other output: **STOP**. This is the intended outcome while P1 is unmerged, not a defect. Remove the worktree (`git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/hc-w08 && git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral branch -D feat/w08-bundled-embedding-model`) and wait for P1.
- [ ] **Step 1:** Quote D8 and D8-delivery verbatim in the PR description, from [Approval scope](#approval-scope). Cite D8-delivery as "owner decision D8-delivery, 2026-09-27, Claude Code chat".
- [ ] **Step 2:** Check that the record carries the delivery answer: `grep -n "D8-delivery\|Script + offline load" /mnt/c/Users/DangT/Documents/GitHub/hc-w08/docs/capstone-report/owner-decisions-2026-09-27.md`.
  - Expected today: no hits.
  - If absent, ask the orchestrator to add the row in a `docs:` commit. Do not edit that file from this plan.
- [ ] **Step 3:** Put Q-FC, Q-HASH and Q-OFFLINE to the owner, using the [What the patient sees](#what-the-patient-sees) table. Leave their lines **unsigned** until the owner answers. Task 5 may be *built* before Q-FC is signed, but the PR does not merge without it. Task 7 is not started without Q-HASH.

### Task 1: Phase-start measurement and prerequisites

**Files:** none (record in the PR description, per handoff §6 item 1).

- [ ] **Step 1: Interpreter and libraries.**
  ```bash
  ~/venvs/asclexis-311/bin/python --version
  ~/venvs/asclexis-311/bin/python -c "import inspect, sentence_transformers as st, huggingface_hub as h, transformers, torch; print(st.__version__, h.__version__, transformers.__version__, torch.__version__, 'local_files_only' in inspect.signature(st.SentenceTransformer.__init__).parameters)"
  ```
  - Expected: `Python 3.11.x`, then versions, ending in `True`.
  - If the venv is missing, **stop** (D9 not executed).
  - If the last value is `False`, **stop**: raising the `sentence-transformers` floor edits `requirements.txt`, which another plan owns.
- [ ] **Step 2: Prerequisites landed.**
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08"
  git grep -c default_embeddings_model HEAD -- src/backend/core/config.py     # expect no output (B landed)
  git grep -n "from huggingface_hub import list_repo_files" HEAD -- src/backend/scripts/download_models.py   # expect one hit (B landed)
  git grep -c "datetime.utcnow" HEAD -- src/backend/api/documents.py            # expect no output (P5 landed)
  git grep -c "VECTOR_STORE_TYPE" HEAD -- config/.env.example                   # expect no output (P4 Task 3 landed)
  git ls-files docs/capstone-report/owner-decisions-2026-09-27.md               # expect the path (P0-B landed)
  git grep -n "HC-EMB\|hc_emb" HEAD -- src/backend/tests | wc -l               # expect 0 (no ID collision)
  git grep -n "HC-VER-001" HEAD -- src/backend/tests | head -1                  # expect a hit (W-3 landed)
  ```
  If any expectation fails, **stop**: a prerequisite phase has not landed. W-11a PR-3 has no reliable grep marker: record its merge sha from the PR page, or stop.
- [ ] **Step 3: Re-locate the anchors** on this tree and record them:
  ```bash
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  grep -n "SentenceTransformer(\|use_fallback: bool" src/backend/modules/embeddings.py
  grep -n "query_vector = self._embedder.embed_text(query)\|if not rows:" src/backend/modules/rag.py
  grep -n "embedder = EmbeddingsModule()\|delete(Chunk).where(Chunk.doc_id == doc_id)\|embeddings = embedder.embed_chunks" src/backend/api/documents.py
  grep -n "embedding_dimensions" src/backend/core/config.py
  ```
- [ ] **Step 4: Baseline.**
  ```bash
  set -o pipefail
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && find . -name __pycache__ -prune -exec rm -rf {} +
  ls ~/.cache/huggingface/hub 2>/dev/null | grep -c MiniLM      # record: is the model in this env's HF cache?
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -2; echo "collect exit: ${PIPESTATUS[0]}"   # expect 0
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -20; echo "pytest exit: ${PIPESTATUS[0]}"      # 0, or 1 when START_FAILURES is non-empty
  grep -n "backend tests collected" /mnt/c/Users/DangT/Documents/GitHub/hc-w08/CLAUDE.md
  grep -n "collected;" /mnt/c/Users/DangT/Documents/GitHub/hc-w08/AGENT.md     # record the baseline figures the count-update steps will replace
  ```
  - Record `START_COLLECTED`, the list `START_FAILURES` with each failure named, the interpreter, the OS, and `START_SHA` = `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 rev-parse --short HEAD`.
  - Expect `test_api_rag_index_002b` to pass only if the HF cache holds the model.

### Task 2: Offline local loader that fails closed (HC-EMB-001, HC-EMB-003)

**Files:**
- Modify: `src/backend/modules/embeddings.py` (class docstring, `__init__`, `_ensure_initialized`, new module constants and helpers)
- Modify: `src/backend/core/config.py` (after `embedding_dimensions`)
- Modify: `.gitignore`, `config/.env.example`
- Create: `src/backend/tests/test_embedding_bundle.py`

**Interfaces:**
- Produces, all in `modules.embeddings`:
  - `EMBEDDING_MODEL_NAME: str`, `EMBEDDING_REPO_ID: str`, `EMBEDDING_REVISION: str`, `EMBEDDING_WEIGHTS_SHA256: str`, `EMBEDDING_FILES: tuple[str, ...]`
  - `class EmbeddingModelUnavailableError(RuntimeError)`
  - `resolve_embedding_model_dir() -> Path`: relative paths resolve against `src/backend`, not the working directory
  - `EmbeddingsModule(model_name: str = EMBEDDING_MODEL_NAME, use_fallback: bool = False)`. `embed_text` and `embed_chunks` raise `EmbeddingModelUnavailableError` when the model is absent and `use_fallback` is False. A failure is not cached; the next call retries.
- Produces: `core.config.Settings.embedding_model_path: str = "models/embeddings/all-MiniLM-L6-v2"` (env `EMBEDDING_MODEL_PATH`).

- [ ] **Step 1: Write the failing tests** in `src/backend/tests/test_embedding_bundle.py`:

```python
"""HC-EMB-001..004 — the embedding model loads only from its local directory.

Owner decisions D8 + D8-delivery (2026-09-27): the model is fetched once by
`scripts/download_models.py embedding`; at runtime it loads that path with
Hugging Face offline and fails closed if absent. It must never silently fall
back to hash vectors.

HC-EMB-001/002 run in a fresh interpreter so HF_HOME is read at import (an
in-process monkeypatch of HF_HOME cannot change huggingface_hub's already
computed cache constants). The socket guard patches socket *methods*: replacing
`socket.socket` with a function breaks `import ssl` when ssl is imported later.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

_PROBE = r'''
import json, socket
attempts = []
def _blocked(*args, **kwargs):
    attempts.append("network")
    raise OSError("network blocked by HC-EMB probe")
socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked

from modules.embeddings import EmbeddingModelUnavailableError, EmbeddingsModule

embedder = EmbeddingsModule()
out = {}
try:
    v1 = embedder.embed_text("Blood glucose level is 95 mg/dL which is normal.")
    v2 = embedder.embed_text("The glucose measurement shows 95 mg/dL, within normal range.")
    out.update(result="loaded", model_loaded=embedder._model is not None,
               dims=len(v1), similarity=embedder.cosine_similarity(v1, v2))
except EmbeddingModelUnavailableError as exc:
    out.update(result="failed_closed", error=str(exc))
out["attempts"] = attempts
print("HC_EMB_RESULT=" + json.dumps(out))
'''


def _run_probe(tmp_path: Path, model_dir: Path) -> dict:
    hf_home = tmp_path / "hf-empty"
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("HF_", "TRANSFORMERS_", "SENTENCE_TRANSFORMERS_", "EMBEDDING_MODEL_PATH"))
    }
    env.update(
        HF_HOME=str(hf_home),
        EMBEDDING_MODEL_PATH=str(model_dir),
        PYTHONPATH=str(BACKEND_DIR),
        TEST_MODE="1",
        DATABASE_ENCRYPTION_REQUIRED="false",
    )
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=300,
    )
    lines = [line for line in proc.stdout.splitlines() if line.startswith("HC_EMB_RESULT=")]
    assert proc.returncode == 0 and lines, f"probe crashed:\n{proc.stderr[-3000:]}"
    out = json.loads(lines[-1].split("=", 1)[1])
    # Catches fetches by native code (e.g. the Rust hf_xet client) that bypass
    # Python's socket module: anything downloaded would land in the empty cache.
    out["hf_cache_files"] = [str(p) for p in hf_home.rglob("*") if p.is_file()] if hf_home.exists() else []
    return out


def test_hc_emb_001_absent_model_fails_closed_offline(tmp_path):
    out = _run_probe(tmp_path, tmp_path / "absent-model")
    assert out["result"] == "failed_closed", f"embedder produced vectors without the bundled model: {out}"
    assert out["attempts"] == [], f"network attempted: {out['attempts']}"
    assert out["hf_cache_files"] == []


def test_hc_emb_003_product_code_never_enables_hash_fallback():
    from modules.embeddings import EmbeddingsModule
    from modules.rag import RAGModule

    assert EmbeddingsModule().use_fallback is False
    assert RAGModule(enable_verification=False)._embedder.use_fallback is False

    offenders = []
    for path in BACKEND_DIR.rglob("*.py"):
        rel = path.relative_to(BACKEND_DIR)
        if rel.parts[0] == "tests" or any(p.startswith((".", "venv")) for p in rel.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "EmbeddingsModule":
                continue
            for kw in node.keywords:
                if kw.arg == "use_fallback" and not (
                    isinstance(kw.value, ast.Constant) and kw.value.value is False
                ):
                    offenders.append(f"{rel}:{node.lineno}")
    assert offenders == [], f"product code enables the hash fallback: {offenders}"
```

- [ ] **Step 2: Run them to see RED.**
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_bundle.py -p no:cacheprovider -q -k "test_hc_emb_001 or test_hc_emb_003"
  ```
  Selector note: `hc_emb` has 0 substring hits in `src/backend/tests` on main, A and B (`git grep -i -c "hc_emb\|hc-emb" <ref> -- src/backend/tests`, 2026-09-27). Every `-k` in this plan also uses the full `test_hc_emb_NNN` prefix.
  Expected: 2 failed.
  - 001: `probe crashed: … ImportError: cannot import name 'EmbeddingModelUnavailableError'`
  - 003: `assert True is False`

- [ ] **Step 3: Implement.** In `core/config.py`, directly after `embedding_dimensions: int = 384`:

```python
    # Bundled embedding model (owner decisions D8 + D8-delivery, 2026-09-27).
    # Fetched once by `python scripts/download_models.py embedding`; loaded
    # offline at runtime; retrieval fails closed when it is absent. Relative
    # paths resolve against src/backend, not the working directory.
    embedding_model_path: str = "models/embeddings/all-MiniLM-L6-v2"
```

In `modules/embeddings.py`, add `from pathlib import Path` to the imports, then add these above `EmbeddingsConfig`:

```python
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
# Source for the one-time, user-run fetch only (scripts/download_models.py
# embedding). The runtime below never contacts this repo.
EMBEDDING_REPO_ID = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBEDDING_WEIGHTS_SHA256 = "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"
EMBEDDING_FILES = (
    "1_Pooling/config.json",
    "README.md",
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)
_BACKEND_DIR = Path(__file__).resolve().parents[1]


class EmbeddingModelUnavailableError(RuntimeError):
    """The bundled embedding model is missing or cannot be loaded offline."""


def resolve_embedding_model_dir() -> Path:
    """Directory the embedding model is loaded from (EMBEDDING_MODEL_PATH)."""
    from core.config import settings

    path = Path(settings.embedding_model_path)
    return path if path.is_absolute() else _BACKEND_DIR / path
```

Change `EmbeddingsConfig.model_name` to `EMBEDDING_MODEL_NAME`. Replace the class docstring's fallback sentence, `__init__`'s signature and docstring, and `_ensure_initialized` with:

```python
    """
    Text embedding generation for RAG retrieval.

    Loads the bundled sentence-transformers model from a local directory with
    Hugging Face offline, and fails closed (EmbeddingModelUnavailableError) when
    it is absent. The hash-based fallback exists for tests only
    (use_fallback=True); product code must never enable it (HC-EMB-003).
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        use_fallback: bool = False,
    ):
        """
        Args:
            model_name: Label stored with each vector (Embedding.model_name).
            use_fallback: Tests only. Use hash vectors when the model is absent.
        """
        self.config = EmbeddingsConfig(model_name=model_name)
        self.use_fallback = use_fallback
        self._model = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Load the local model once. A failure is not cached: the next call
        retries, so fetching the model does not need a restart."""
        if self._initialized:
            return
        try:
            self._model = self._load_local_model()
            self.config.dimensions = self._model.get_sentence_embedding_dimension()
        except EmbeddingModelUnavailableError:
            if not self.use_fallback:
                raise
            self._model = None
        self._initialized = True

    def _load_local_model(self):
        """Load from the bundled directory only; never from the network."""
        model_dir = resolve_embedding_model_dir()
        missing = [name for name in EMBEDDING_FILES if not (model_dir / name).is_file()]
        if missing:
            raise EmbeddingModelUnavailableError(
                f"Embedding model not installed at {model_dir} "
                f"({len(missing)} of {len(EMBEDDING_FILES)} files missing). Fetch it once with: "
                "cd src/backend && python scripts/download_models.py embedding"
            )
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingModelUnavailableError("sentence-transformers is not installed") from exc
        try:
            return SentenceTransformer(str(model_dir), local_files_only=True)
        except Exception as exc:  # corrupt or incompatible files: fail closed, never download
            raise EmbeddingModelUnavailableError(
                f"Embedding model at {model_dir} failed to load: {type(exc).__name__}"
            ) from exc
```

`.gitignore`: add after the "Local AI models" block:

```gitignore
# Embedding model fetched by `src/backend/scripts/download_models.py embedding`.
# Owner decision D8-delivery (2026-09-27): no model files in git.
/src/backend/models/embeddings/
```

`config/.env.example`: replace the `# Default embeddings model` comment, its `# Options: bge-small-en-v1.5, e5-small-v2` line and `DEFAULT_EMBEDDINGS_MODEL=bge-small-en-v1.5` (dead since B `2c98ae6`) with:

```dotenv
# Embedding model directory (relative paths resolve against src/backend).
# Fetch once: cd src/backend && python scripts/download_models.py embedding
EMBEDDING_MODEL_PATH=models/embeddings/all-MiniLM-L6-v2
```

- [ ] **Step 4: GREEN.** Run the Step 2 command. Expected: `2 passed`.
- [ ] **Step 5: Break it on purpose** (recurring-failures #1). Undo each break by hand (Global Constraints), then re-run the Step 2 command.
  - (a) Set `use_fallback: bool = True` in `__init__`. Expect 001 red (`result == "loaded"`) and 003 red. Undo it by hand.
  - (b) Replace `SentenceTransformer(str(model_dir), local_files_only=True)` with `SentenceTransformer(self.config.model_name)`, and delete the `missing` check. Expect 001 red on `attempts` (the network was tried). Undo it by hand.
  - (c) Add `use_fallback=True` to `EmbeddingsModule()` in `api/documents.py`. Expect 003 red with that `path:line`. Undo it by hand.
  Record each red line in the PR.
- [ ] **Step 6: What would these tests fail to notice?**
  - 001: network I/O from native code that bypasses Python sockets. Mitigated by the empty-cache assertion, but only if the fetch completes.
  - 003: fallback enabled dynamically, e.g. `**kwargs` or `setattr(obj, "use_fallback", True)`.
  - Neither test covers the route or ingest surfaces; Tasks 5–6 do.
- [ ] **Step 6b: Check that model files stay out of git.** Run `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 check-ignore -v src/backend/models/embeddings/all-MiniLM-L6-v2/tokenizer.json`. Expected: a hit on the new `.gitignore` line.
- [ ] **Step 7: Commit.**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect exit: ${PIPESTATUS[0]}"   # N = the "N tests collected" figure; expect exit 0
  # Count update, same commit: set the collected figure to N in the CLAUDE.md baseline bullet
  # ("**<old> backend tests collected.**" and "if it differs from <old>") and in the AGENT.md pytest line
  # ("(<old> collected; …)"). Pass/env wording is rewritten from measurements in Task 8.
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  git add src/backend/modules/embeddings.py src/backend/core/config.py .gitignore config/.env.example src/backend/tests/test_embedding_bundle.py CLAUDE.md AGENT.md
  git diff --cached --name-only     # expect exactly these 7 paths (incl. CLAUDE.md, AGENT.md)
  git commit -m "feat(embeddings): load the embedding model from a local path offline and fail closed" -- src/backend/modules/embeddings.py src/backend/core/config.py .gitignore config/.env.example src/backend/tests/test_embedding_bundle.py CLAUDE.md AGENT.md
  ```

### Task 3: One-time fetch script (HC-EMB-004a/b/c/d/e)

**Files:**
- Modify: `src/backend/scripts/download_models.py`: usage docstring, new helpers, `cmd_embedding`, argparse `embedding` subparser and dispatch (`:306-342` B@7b2ff1f)
- Test: `src/backend/tests/test_embedding_bundle.py`

**Interfaces:**
- Consumes: the `modules.embeddings` constants and `resolve_embedding_model_dir()` from Task 2. They are imported **inside** the functions so tests can monkeypatch them.
- Produces: `cmd_embedding(target: Optional[Path] = None) -> None`, which exits with code 1 on failure, and CLI `python scripts/download_models.py embedding`.

- [ ] **Step 1: Write the failing tests.** Append to `test_embedding_bundle.py`:

```python
import hashlib

sys.path.insert(0, str(BACKEND_DIR / "scripts"))
import download_models  # noqa: E402
from modules import embeddings as emb  # noqa: E402


def _fake_snapshot(payload: bytes, calls: list):
    def _fake(*, repo_id, revision, local_dir, allow_patterns):
        calls.append({"repo_id": repo_id, "revision": revision, "allow_patterns": list(allow_patterns)})
        root = Path(local_dir)
        for name in allow_patterns:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload if name == "model.safetensors" else b"{}")
        return str(root)
    return _fake


def test_hc_emb_004a_fetch_rejects_checksum_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(b"not the pinned weights", []))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    with pytest.raises(SystemExit) as info:
        download_models.cmd_embedding(target)
    assert info.value.code == 1
    assert not target.exists()
    assert not target.with_name(target.name + ".partial").exists()


def test_hc_emb_004b_fetch_installs_pinned_files_only(tmp_path, monkeypatch):
    payload = b"pinned-weights-stand-in"
    monkeypatch.setattr(emb, "EMBEDDING_WEIGHTS_SHA256", hashlib.sha256(payload).hexdigest())
    calls: list = []
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(payload, calls))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    download_models.cmd_embedding(target)
    assert calls == [{
        "repo_id": emb.EMBEDDING_REPO_ID,
        "revision": emb.EMBEDDING_REVISION,
        "allow_patterns": list(emb.EMBEDDING_FILES),
    }]
    installed = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert installed == sorted(emb.EMBEDDING_FILES)
    assert not target.with_name(target.name + ".partial").exists()


def test_hc_emb_004c_existing_incomplete_target_is_never_deleted(tmp_path, monkeypatch):
    calls: list = []
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(b"x", calls))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    target.mkdir(parents=True)
    keep = target / "user-file.txt"
    keep.write_text("do not delete")
    with pytest.raises(SystemExit) as info:
        download_models.cmd_embedding(target)
    assert info.value.code == 1
    assert keep.read_text() == "do not delete"
    assert calls == []


def test_hc_emb_004d_existing_partial_is_never_deleted(tmp_path, monkeypatch):
    calls: list = []
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(b"x", calls))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    partial = target.with_name(target.name + ".partial")
    partial.mkdir(parents=True)
    keep = partial / "someone-elses-file.bin"
    keep.write_bytes(b"do not delete")
    with pytest.raises(SystemExit) as info:
        download_models.cmd_embedding(target)
    assert info.value.code == 1
    assert keep.read_bytes() == b"do not delete"
    assert not target.exists()
    assert calls == []


def test_hc_emb_004e_failed_fetch_removes_only_this_runs_partial(tmp_path, monkeypatch):
    def _failing_download(*, repo_id, revision, local_dir, allow_patterns):
        (Path(local_dir) / "config.json").write_bytes(b"{}")  # a half-written fetch
        raise OSError("simulated network drop")

    monkeypatch.setattr("huggingface_hub.snapshot_download", _failing_download)
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    partial = target.with_name(target.name + ".partial")
    with pytest.raises(OSError, match="simulated network drop"):
        download_models.cmd_embedding(target)
    assert not partial.exists(), "a failed fetch left its .partial behind and would block the next run"
    assert not target.exists()
    # The pre-existing-.partial case (never deleted) is HC-EMB-004d.
```

- [ ] **Step 2: RED.**
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_bundle.py -p no:cacheprovider -q -k test_hc_emb_004
  ```
  Expected: 5 failed, each with `AttributeError: module 'download_models' has no attribute 'cmd_embedding'`.

- [ ] **Step 3: Implement.**
  - Add `import hashlib` and `import shutil` to the script's imports.
  - Add `python scripts/download_models.py embedding` to the usage docstring, with a one-line note: "one-time fetch of the embedding model; the backend loads it offline".
  - Add the following functions:

```python
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _embedding_complete(directory: Path) -> bool:
    from modules.embeddings import EMBEDDING_FILES, EMBEDDING_WEIGHTS_SHA256

    if not all((directory / name).is_file() for name in EMBEDDING_FILES):
        return False
    return _sha256(directory / "model.safetensors") == EMBEDDING_WEIGHTS_SHA256


def cmd_embedding(target: Optional[Path] = None) -> None:
    """Fetch the pinned embedding model once. The only network step for it.

    The backend never downloads it: modules/embeddings.py loads this directory
    offline and fails closed when it is absent (owner decision D8-delivery,
    2026-09-27). Never deletes a directory it did not create in this run.
    """
    from huggingface_hub import snapshot_download
    from modules.embeddings import (
        EMBEDDING_FILES,
        EMBEDDING_REPO_ID,
        EMBEDDING_REVISION,
        resolve_embedding_model_dir,
    )

    target = Path(target) if target is not None else resolve_embedding_model_dir()
    if target.exists():
        if _embedding_complete(target):
            print(f"Embedding model already installed: {target}")
            return
        print(f"ERROR: {target} exists but is not a complete, verified embedding model.")
        print("Remove it yourself and re-run; this script never deletes an existing directory.")
        sys.exit(1)

    partial = target.with_name(target.name + ".partial")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        partial.mkdir()  # exclusive: this run owns `partial` only if it created it
    except FileExistsError:
        print(f"ERROR: {partial} already exists (an interrupted or concurrent fetch?).")
        print("Remove it yourself and re-run; this script never deletes a directory it did not create.")
        sys.exit(1)
    print(f"Fetching {EMBEDDING_REPO_ID}@{EMBEDDING_REVISION[:12]} ({len(EMBEDDING_FILES)} files) ...")
    try:
        snapshot_download(
            repo_id=EMBEDDING_REPO_ID,
            revision=EMBEDDING_REVISION,
            local_dir=str(partial),
            allow_patterns=list(EMBEDDING_FILES),
        )
    except BaseException:
        # Network error, interrupt, anything: remove only the `partial` this run
        # created (exclusive mkdir above) so the next run is not blocked, then re-raise.
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if not _embedding_complete(partial):
        shutil.rmtree(partial, ignore_errors=True)  # created by this run (exclusive mkdir above)
        print("ERROR: fetched embedding model is incomplete or its weights checksum does not match.")
        print("Nothing was installed.")
        sys.exit(1)

    partial.rename(target)
    print(f"Embedding model installed: {target}")
```

  In `main()`, add the subparser and the dispatch branch:

```python
    sub.add_parser("embedding", help="Fetch the pinned embedding model once (the backend loads it offline)")
```

```python
    elif args.command == "embedding":
        cmd_embedding()
```

- [ ] **Step 4: GREEN.** Run the Step 2 command. Expected: `5 passed`.
- [ ] **Step 5: Break it on purpose.**
  - (a) Delete the `_embedding_complete(partial)` check. Expect 004a red. Undo it by hand.
  - (b) Drop `allow_patterns=`. Expect 004b red. Undo it by hand.
  - (c) Replace the `target.exists()` refusal with `shutil.rmtree(target)`. Expect 004c red. Undo it by hand.
  - (d) Replace the exclusive `partial.mkdir()` block with `shutil.rmtree(partial, ignore_errors=True)`. Expect 004d red. Undo it by hand.
  - (e) Delete the `except BaseException:` cleanup around `snapshot_download`. Expect 004e red (`.partial` left behind). Undo it by hand.
- [ ] **Step 6: What would these tests fail to notice?**
  - They use a fake `snapshot_download`, so they cannot show that the pinned revision still exists on the Hub. Task 4 Step 1 proves that once, and CI proves it on every run.
  - 004d proves a pre-existing `.partial` survives. It cannot prove that two *simultaneous* runs are safe beyond the exclusive `mkdir`: a second run that starts after the first `mkdir` fails cleanly; one that races the `rename` is not tested.
  - Only the weights are hash-checked. A tampered `tokenizer.json` at the pinned revision would pass. Accepted: the revision pin fixes the other files, and `sha256` pins exist only for the weights.
- [ ] **Step 7: Commit.**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect exit: ${PIPESTATUS[0]}"   # N = the "N tests collected" figure; expect exit 0
  # Count update, same commit: set the collected figure to N in the CLAUDE.md baseline bullet
  # ("**<old> backend tests collected.**" and "if it differs from <old>") and in the AGENT.md pytest line
  # ("(<old> collected; …)"). Pass/env wording is rewritten from measurements in Task 8.
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  git add src/backend/scripts/download_models.py src/backend/tests/test_embedding_bundle.py CLAUDE.md AGENT.md
  git diff --cached --name-only     # expect exactly these 4 paths (incl. CLAUDE.md, AGENT.md)
  git commit -m "feat(scripts): fetch the pinned embedding model once with download_models.py embedding" -- src/backend/scripts/download_models.py src/backend/tests/test_embedding_bundle.py CLAUDE.md AGENT.md
  ```

### Task 4: Real one-time fetch, offline-load proof (HC-EMB-002), CI provisioning

**Files:**
- Modify: `.github/workflows/ci.yml`: `backend-tests` after "Install dependencies" (`:47-48` B@7b2ff1f); `e2e-tests` after "Install backend dependencies" (`:197-200` B@7b2ff1f)
- Test: `src/backend/tests/test_embedding_bundle.py`

**Interfaces:**
- Consumes: `cmd_embedding` from Task 3 and `_run_probe` from Task 2.

- [ ] **Step 1: Run the documented command exactly** (recurring-failures #6). This is the only network step in this plan, and it is a script, not the product.
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && ~/venvs/asclexis-311/bin/python scripts/download_models.py embedding
  ```
  - Expected: `Fetching sentence-transformers/all-MiniLM-L6-v2@1110a243fdf4 (11 files) ...`, then `Embedding model installed: …/src/backend/models/embeddings/all-MiniLM-L6-v2`.
  - Record: `du -sb /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend/models/embeddings/all-MiniLM-L6-v2`. Expected ≈ 91,578,415 bytes plus `.cache` metadata.
  - Record: `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 status --short src/backend/models/`. Expected: **empty**.
  - If the revision is not found or the checksum fails, **stop**. Do not change the pin without the owner.
  - Optional, network: record the upstream file list, to measure whether a LICENSE file exists: `~/venvs/asclexis-311/bin/python -c "from huggingface_hub import list_repo_files; print(list_repo_files('sentence-transformers/all-MiniLM-L6-v2', revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'))"`.
- [ ] **Step 2: Write the test.** Append to `test_embedding_bundle.py`:

```python
def test_hc_emb_002_fetched_model_loads_offline(tmp_path):
    from modules.embeddings import EMBEDDING_FILES, resolve_embedding_model_dir

    model_dir = resolve_embedding_model_dir()
    if not all((model_dir / name).is_file() for name in EMBEDDING_FILES):
        pytest.fail(
            f"embedding model not installed at {model_dir}; run: "
            "cd src/backend && python scripts/download_models.py embedding"
        )
    out = _run_probe(tmp_path, model_dir)
    assert out["result"] == "loaded" and out["model_loaded"] is True, out
    assert out["dims"] == 384
    assert out["similarity"] > 0.7  # same bar as test_api_rag_index_002b; never lowered
    assert out["attempts"] == [], f"network attempted: {out['attempts']}"
    assert out["hf_cache_files"] == []
```

- [ ] **Step 3: Run it.**
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_bundle.py -p no:cacheprovider -q -k test_hc_emb_002
  ```
  Expected: `1 passed`. Record the similarity by printing `out` once with `-s` if needed. The Windows 3.13 probe measured 0.9039.
- [ ] **Step 4: Break it on purpose.**
  ```bash
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  EMBEDDING_MODEL_PATH=/nonexistent ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_bundle.py -p no:cacheprovider -q -k test_hc_emb_002; echo "exit: $?"   # expect exit 1, "embedding model not installed at /nonexistent"
  mv /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend/models/embeddings/all-MiniLM-L6-v2 /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend/models/embeddings/all-MiniLM-L6-v2.aside
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_bundle.py -p no:cacheprovider -q -k test_hc_emb_002; echo "exit: $?"   # expect exit 1
  mv /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend/models/embeddings/all-MiniLM-L6-v2.aside /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend/models/embeddings/all-MiniLM-L6-v2
  ```
- [ ] **Step 5: CI provisioning.** Insert this step in both jobs, after the dependency install:

```yaml
      - name: Fetch the embedding model (explicit one-time download; the backend loads it offline)
        working-directory: src/backend
        run: python scripts/download_models.py embedding
```

  - `agent-evals` does not embed. Verify: `cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08" && EMBEDDING_MODEL_PATH=/nonexistent ~/venvs/asclexis-311/bin/python scripts/agent_eval_gate.py; echo $?`. Expected: `0`. If it is not 0, add the step there too and record why.
  - Optional, not required: cache `src/backend/models/embeddings` keyed on the revision.
- [ ] **Step 6: What would HC-EMB-002 fail to notice?**
  - A long-running server that failed before the fetch recovers on the next call, because failure is not cached. HC-EMB-002 only proves a fresh process.
  - Device selection (CPU/GPU) is unchanged and untested.
- [ ] **Step 7: Commit** (two commits, one concern each).
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect exit: ${PIPESTATUS[0]}"   # N = the "N tests collected" figure; expect exit 0
  # Count update, same commit: set the collected figure to N in the CLAUDE.md baseline bullet
  # ("**<old> backend tests collected.**" and "if it differs from <old>") and in the AGENT.md pytest line
  # ("(<old> collected; …)"). Pass/env wording is rewritten from measurements in Task 8.
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  git add src/backend/tests/test_embedding_bundle.py CLAUDE.md AGENT.md
  git diff --cached --name-only     # expect exactly these 3 paths (incl. CLAUDE.md, AGENT.md)
  git commit -m "feat(embeddings): prove the fetched model loads offline with sockets blocked (HC-EMB-002)" -- src/backend/tests/test_embedding_bundle.py CLAUDE.md AGENT.md
  git add .github/workflows/ci.yml
  git diff --cached --name-only     # expect exactly .github/workflows/ci.yml
  git commit -m "fix(ci): fetch the embedding model explicitly before backend and e2e tests" -- .github/workflows/ci.yml
  ```

### Task 5: Legacy retrieval fails closed through existing no-model surfaces (HC-EMB-005, 006a, 006b, 006c) — form owner-gated (Q-FC)

**Files:**
- Modify: `src/backend/modules/rag.py`
  - `:24` import (main@40f590e)
  - move `:546` `query_vector = …` to after `:591-592` `if not rows: return []`
  - add a module constant
- Create: `src/backend/tests/test_embedding_fail_closed_paths.py`

**Interfaces:**
- Consumes: `EmbeddingModelUnavailableError` (Task 2).
- Produces: `modules.rag.EMBEDDING_UNAVAILABLE_MESSAGE: str`. `RAGModule._search_vectors_async` raises `ModelUnavailableError(EMBEDDING_UNAVAILABLE_MESSAGE)` only when rows exist and the model is absent, and returns `[]` for an empty profile without loading the model.

- [ ] **Step 1: Write the failing tests** in `src/backend/tests/test_embedding_fail_closed_paths.py`:

```python
"""HC-EMB-005..008 — what fail-closed means on each retrieval/ingest surface.

Owner decisions D8 + D8-delivery (2026-09-27): runtime "fails closed if
absent". The patient-visible form (existing knowledge-fallback template on
legacy chat; existing 501 on grounded interpretation) is owner-gated as Q-FC in
docs/plans/2026-09-27-W08-bundled-embedding-model.md.
"""

from __future__ import annotations

import struct
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  register every profile table
from core.profile_database import ProfileDatabaseBase
from core.time import utcnow
from models import Chunk, Document, Embedding

UNIT = [1.0] + [0.0] * 383
BLOB = struct.pack("384f", *UNIT)
# Patient-visible 501 detail, copied VERBATIM from the signed Q-FC line in
# docs/plans/2026-09-27-W08-bundled-embedding-model.md. Deliberately a literal,
# not modules.rag.EMBEDDING_UNAVAILABLE_MESSAGE: a wording change in product code
# must fail this test. Change it only when a new Q-FC line is signed.
QFC_APPROVED_DETAIL = "Document search is unavailable because the local embedding model is not installed."


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.fixture
def absent_model(tmp_path, monkeypatch):
    from core.config import settings

    path = tmp_path / "absent-model"
    monkeypatch.setattr(settings, "embedding_model_path", str(path))
    return path


def _document(profile_id: str = "profile-emb") -> Document:
    return Document(
        id=str(uuid.uuid4()), profile_id=profile_id, path_hash="0" * 64, content_hash="1" * 64,
        doc_type="pdf", status="verified", imported_at=utcnow(),
    )


async def _seed_one_chunk(profile_db, profile_id: str = "profile-emb") -> Document:
    doc = _document(profile_id)
    profile_db.add_all([
        doc,
        Chunk(id="chunk-1", doc_id=doc.id, chunk_index=0, text="LDL 128 mg/dL"),
        Embedding(chunk_id="chunk-1", model_name="all-MiniLM-L6-v2", vector_blob=BLOB, dimensions=384),
    ])
    await profile_db.commit()
    return doc


class _SentinelRunner:
    def __init__(self):
        self.calls = 0

    def is_available(self):
        return True

    async def generate_async(self, prompt, config):
        self.calls += 1
        return SimpleNamespace(text="ANSWER-SENTINEL from retrieval", finish_reason="stop")


@pytest.mark.asyncio
async def test_hc_emb_005_legacy_chat_fails_closed_over_http(profile_db, absent_model, monkeypatch):
    import api.assistant as assistant_api
    from api.assistant import router as assistant_router
    from core.auth import get_profile_db_session
    from tests.support.routes import route_client

    profile_id = str(uuid.uuid4())
    await _seed_one_chunk(profile_db, profile_id)
    runner = _SentinelRunner()
    monkeypatch.setattr("core.external_runner.get_runner_for_request", AsyncMock(return_value=runner))
    monkeypatch.setattr(assistant_api, "is_agent_enabled", lambda _settings: False)
    monkeypatch.setattr(assistant_api, "_rag_module", None)

    with route_client(assistant_router, "/assistant", profile_id=profile_id) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post("/assistant/chat", json={"question": "What is my LDL?", "include_references": False})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert runner.calls == 0, "the LLM answered from retrieval that ran without the bundled embedding model"
    assert "ANSWER-SENTINEL" not in body["full_response"]
    assert body["verification"]["enabled"] is False  # existing knowledge-fallback shape


@pytest.mark.asyncio
async def test_hc_emb_006a_retrieval_raises_model_unavailable_without_path(profile_db, absent_model):
    from modules.rag import ModelUnavailableError, RAGModule

    doc = await _seed_one_chunk(profile_db)
    rag = RAGModule(enable_verification=False)
    with pytest.raises(ModelUnavailableError) as info:
        await rag._search_vectors_async(query="LDL", profile_id=doc.profile_id, profile_db=profile_db)
    message = str(info.value)
    assert "embedding model" in message.lower()
    # api/interpretations.py returns this text as a 501 detail to the patient.
    assert str(absent_model) not in message


@pytest.mark.asyncio
async def test_hc_emb_006b_empty_profile_needs_no_embedding(profile_db, absent_model):
    from modules.rag import RAGModule

    rag = RAGModule(enable_verification=False)
    assert await rag._search_vectors_async(query="LDL", profile_id="p", profile_db=profile_db) == []


@pytest.mark.asyncio
async def test_hc_emb_006c_grounded_interpretation_returns_501_over_http(profile_db, absent_model, monkeypatch):
    """POST /interpretations/observations/{id}/interpret-grounded, through HTTP.

    The route maps ModelUnavailableError to 501 and returns str(exc) as the
    detail (api/interpretations.py:453-457 B@7b2ff1f), so the patient sees this
    text. The wording itself is owner-gated (Q-FC). The interpret module is
    stubbed: this test is about retrieval, and interpret.py sits beside the
    ask-first interpret_safety.py.
    """
    import api.assistant as assistant_api
    import api.interpretations as interpretations_api
    from api.interpretations import router as interpretations_router
    from core.auth import get_profile_db_session
    from models import Observation
    from tests.support.routes import route_client

    profile_id = str(uuid.uuid4())
    doc = await _seed_one_chunk(profile_db, profile_id)
    obs_id = str(uuid.uuid4())  # the route validates UUID format
    profile_db.add(Observation(
        id=obs_id, profile_id=profile_id, doc_id=doc.id, analyte_canonical="ldl",
        analyte_raw="LDL", value=128.0, unit="mg/dL", user_verified=True,
    ))
    await profile_db.commit()

    runner = _SentinelRunner()
    monkeypatch.setattr("core.external_runner.get_runner_for_request", AsyncMock(return_value=runner))
    monkeypatch.setattr(assistant_api, "_rag_module", None)  # get_rag_module is shared with the chat route
    stub = SimpleNamespace(interpret_observation=AsyncMock(
        return_value=SimpleNamespace(success=True, interpretation=SimpleNamespace(), error_message=None)
    ))
    monkeypatch.setattr(interpretations_api, "get_interpret_module", lambda: stub)

    with route_client(interpretations_router, "/interpretations", profile_id=profile_id) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.post(f"/interpretations/observations/{obs_id}/interpret-grounded")

    assert resp.status_code == 501, resp.text
    detail = resp.json()["detail"]
    assert detail == QFC_APPROVED_DETAIL  # exact owner-approved wording (Q-FC), not the product constant
    assert str(absent_model) not in detail
    assert runner.calls == 0, "the LLM answered from retrieval that ran without the bundled embedding model"
```

- [ ] **Step 2: RED.**
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_fail_closed_paths.py -p no:cacheprovider -q
  ```
  Expected: 4 failed.
  - 005: `assert 500 == 200` (`Error processing chat request`), because the new error is not a `ModelUnavailableError`.
  - 006a: `EmbeddingModelUnavailableError` raised where `ModelUnavailableError` was expected.
  - 006b: `EmbeddingModelUnavailableError` raised.
  - 006c: `EmbeddingModelUnavailableError` re-raised by `TestClient`, because the interpretations route has no generic handler.

  If 005 or 006c is red for another reason, fix the *test setup* and not the product. Examples: a missing table, or the knowledge fallback needing a real master session (then pass `master_db=` to `route_client`). Record the reason.

- [ ] **Step 3: Implement** in `modules/rag.py`. Change the import to `from .embeddings import EmbeddingModelUnavailableError, EmbeddingsModule`, and add below `class ModelUnavailableError`:

```python
EMBEDDING_UNAVAILABLE_MESSAGE = (
    "Document search is unavailable because the local embedding model is not installed."
)
```

  In `_search_vectors_async`:
  - delete the `# Embed the query` / `query_vector = self._embedder.embed_text(query)` lines near the top;
  - after `if not rows: return []`, insert:

```python
        # Embed only when there is something to compare against. Fail closed:
        # never substitute hash vectors for the bundled model (D8-delivery).
        try:
            query_vector = self._embedder.embed_text(query)
        except EmbeddingModelUnavailableError as exc:
            self._logger.warning("Embedding model unavailable; vector retrieval failed closed: %s", exc)
            raise ModelUnavailableError(EMBEDDING_UNAVAILABLE_MESSAGE) from exc
```

  The log line carries the exception text (a local path). It must never carry `query`, because the question is PHI.
- [ ] **Step 4: GREEN.** Run the Step 2 command. Expected: `4 passed`. Also run `cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend && ~/venvs/asclexis-311/bin/python -m pytest tests/test_rag_pipeline.py tests/test_chat_sessions.py tests/test_memory_integration.py -p no:cacheprovider -q; echo "exit: $?"` and record the result; with the model fetched, expect failures ⊆ START.
- [ ] **Step 5: Break it on purpose.**
  - (a) In `rag.py`, construct `EmbeddingsModule(use_fallback=True)`. Expect 005 red (`runner.calls == 1`) and 003 red. Undo it by hand.
  - (b) Change the wrapper to `raise ModelUnavailableError(str(exc))`. Expect 006a and 006c red (path leak into the 501 detail). Undo it by hand.
  - (c) Wording drift: change one word of `EMBEDDING_UNAVAILABLE_MESSAGE` in `rag.py`. Expect 006c red on `detail == QFC_APPROVED_DETAIL`. Undo it by hand.
  - (d) Route mapping, without editing read-only `api/interpretations.py`: add this line to 006c just before the `with route_client(...)` block, run 006c, then delete the line by hand.
    ```python
    monkeypatch.setattr(interpretations_api, "ModelUnavailableError", type("NotTheMappedError", (Exception,), {}))
    ```
    The route's `except ModelUnavailableError` (`:453-457` B@7b2ff1f) looks the name up in the module at run time, so it no longer matches. Expect 006c red: the exception escapes and `TestClient` re-raises it. Afterwards `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 diff --stat -- src/backend/api/interpretations.py` must print nothing.
- [ ] **Step 6: What would these tests fail to notice?**
  - 006c stubs the interpret module, so it proves the retrieval-to-501 mapping and the detail text, not the interpretation half of the route. A W-7 change that catches `ModelUnavailableError` earlier and returns 201 without the grounded part would trip 006c; a change that alters only the stubbed half would not.
  - 005 proves that the LLM never ran on fallback retrieval. It does not prove that the knowledge-fallback content is good (the existing tests own that).
- [ ] **Step 7: Commit.**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect exit: ${PIPESTATUS[0]}"   # N = the "N tests collected" figure; expect exit 0
  # Count update, same commit: set the collected figure to N in the CLAUDE.md baseline bullet
  # ("**<old> backend tests collected.**" and "if it differs from <old>") and in the AGENT.md pytest line
  # ("(<old> collected; …)"). Pass/env wording is rewritten from measurements in Task 8.
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  git add src/backend/modules/rag.py src/backend/tests/test_embedding_fail_closed_paths.py CLAUDE.md AGENT.md
  git diff --cached --name-only     # expect exactly these 4 paths (incl. CLAUDE.md, AGENT.md)
  git commit -m "fix(rag): fail closed on legacy retrieval when the embedding model is absent" -- src/backend/modules/rag.py src/backend/tests/test_embedding_fail_closed_paths.py CLAUDE.md AGENT.md
  ```

### Task 6: Reprocess keeps existing chunks when embedding fails (HC-EMB-007)

**Files:**
- Modify: `src/backend/api/documents.py`: in `_create_chunks_and_embeddings`, the `if refresh_existing:` delete (`:867-868` A@692fdf3) currently runs **before** `embeddings = embedder.embed_chunks(all_chunks)` (`:871`). The caller swallows the error and commits (`:684-687`), so a failed reprocess commits the deletion. This is recurring-failures #2.
- Test: `src/backend/tests/test_embedding_fail_closed_paths.py`

- [ ] **Step 1: Write the failing test** (append):

```python
@pytest.mark.asyncio
async def test_hc_emb_007_reprocess_keeps_chunks_when_embedding_unavailable(profile_db, absent_model):
    from api import documents as documents_api
    from modules.embeddings import EmbeddingModelUnavailableError

    doc = await _seed_one_chunk(profile_db)
    with pytest.raises(EmbeddingModelUnavailableError):
        await documents_api._create_chunks_and_embeddings(
            profile_db=profile_db, profile_id=doc.profile_id, doc_id=doc.id,
            extracted_text="Glucose 96 mg/dL (70-100)\fLDL 128 mg/dL", refresh_existing=True,
        )
    # Order-of-effects test: the pipeline caller swallows this error and then
    # COMMITS (api/documents.py `except Exception as chunk_error` then
    # `await profile_db.commit()`). Assert on committed state, not on the
    # session's pending state: commit, then read through a fresh query.
    await profile_db.commit()
    profile_db.expunge_all()
    ids = (await profile_db.execute(select(Chunk.id).where(Chunk.doc_id == doc.id))).scalars().all()
    assert ids == ["chunk-1"], "reprocess deleted the previous chunks although no replacement embeddings could be made"
```

- [ ] **Step 2: RED.**
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_fail_closed_paths.py -p no:cacheprovider -q -k test_hc_emb_007
  ```
  Expected: `AssertionError: reprocess deleted the previous chunks …` (`[] == ['chunk-1']`).
- [ ] **Step 3: Implement.** Move the embedding call above the delete. Nothing else changes.

```python
    # Embed before touching existing rows: if the embedding model is
    # unavailable this raises and the document keeps its previous chunks.
    embeddings = embedder.embed_chunks(all_chunks)

    if refresh_existing:
        await profile_db.execute(delete(Chunk).where(Chunk.doc_id == doc_id))
```

  Remove the old `# Generate embeddings` / `embeddings = embedder.embed_chunks(all_chunks)` lines below the delete.
- [ ] **Step 4: GREEN.** Run the Step 2 command, then `cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend && ~/venvs/asclexis-311/bin/python -m pytest tests/test_documents_api.py -p no:cacheprovider -q; echo "exit: $?"`. Expected: `1 passed`, and `test_documents_api.py` failures ⊆ START.
- [ ] **Step 5: Break it on purpose.** Restore the old order. Expect 007 red. Undo it by hand.
- [ ] **Step 6: What would it fail to notice?**
  - The test calls the helper directly and mirrors the caller's commit by hand. If the caller stops committing, the test still passes.
  - The first import of a document is not covered. It creates no chunks, logs a `WARNING`, and the patient sees nothing (see the patient table).
- [ ] **Step 7: Commit.**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect exit: ${PIPESTATUS[0]}"   # N = the "N tests collected" figure; expect exit 0
  # Count update, same commit: set the collected figure to N in the CLAUDE.md baseline bullet
  # ("**<old> backend tests collected.**" and "if it differs from <old>") and in the AGENT.md pytest line
  # ("(<old> collected; …)"). Pass/env wording is rewritten from measurements in Task 8.
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  git add src/backend/api/documents.py src/backend/tests/test_embedding_fail_closed_paths.py CLAUDE.md AGENT.md
  git diff --cached --name-only     # expect exactly these 4 paths (incl. CLAUDE.md, AGENT.md)
  git commit -m "fix(documents): embed before replacing chunks so a failed reprocess keeps the old ones" -- src/backend/api/documents.py src/backend/tests/test_embedding_fail_closed_paths.py CLAUDE.md AGENT.md
  ```

### Task 7 (owner-gated, Q-HASH): Vector search ignores vectors from another model (HC-EMB-008)

**Do not start this task until Q-HASH is signed.**

Patient effect: documents embedded earlier by the hash fallback drop out of legacy vector search until the patient reprocesses them. The number of affected rows in real vaults is **UNMEASURED**. To measure it, the owner runs this on a vault they control, through the app's SQLCipher session and not a raw sqlite3 open: `SELECT model_name, COUNT(*) FROM embeddings GROUP BY model_name;`

**Files:**
- Modify: `src/backend/modules/rag.py` (`_search_vectors_async` statement)
- Test: `src/backend/tests/test_embedding_fail_closed_paths.py`

- [ ] **Step 1: Write the failing test** (append):

```python
@pytest.mark.asyncio
async def test_hc_emb_008_vector_search_ignores_vectors_from_another_model(profile_db):
    from modules.embeddings import EmbeddingsModule
    from modules.rag import RAGModule

    class _FixedEmbedder(EmbeddingsModule):
        def embed_text(self, text):
            return UNIT

    doc = _document()
    profile_db.add_all([
        doc,
        Chunk(id="chunk-real", doc_id=doc.id, chunk_index=0, text="LDL 128 mg/dL"),
        Chunk(id="chunk-hash", doc_id=doc.id, chunk_index=1, text="LDL 128 mg/dL"),
        Embedding(chunk_id="chunk-real", model_name="all-MiniLM-L6-v2", vector_blob=BLOB, dimensions=384),
        Embedding(chunk_id="chunk-hash", model_name="hash-fallback", vector_blob=BLOB, dimensions=384),
    ])
    await profile_db.commit()
    rag = RAGModule(enable_verification=False)
    rag._embedder = _FixedEmbedder()
    results = await rag._search_vectors_async(query="LDL", profile_id=doc.profile_id, profile_db=profile_db)
    assert [chunk["chunk_id"] for chunk, _ in results] == ["chunk-real"]
```

- [ ] **Step 2: RED.** Run `cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && ~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_fail_closed_paths.py -p no:cacheprovider -q -k test_hc_emb_008`. Expected: `['chunk-real', 'chunk-hash'] == ['chunk-real']`, in either order.
- [ ] **Step 3: Implement.** Add to the base `select(Chunk, Embedding, Document)` chain:

```python
            .where(Embedding.model_name == self._embedder.config.model_name)
```

  `Embedding.model_name` is `nullable=False` (`models/embedding.py:50`), so the three-valued-logic trap (recurring-failures #7) does not apply to `==`.
- [ ] **Step 4: GREEN**, then break it by deleting the `.where`. Expect red. Undo it by hand.
- [ ] **Step 5: What would it fail to notice?** Two different models stored under the same label.
- [ ] **Step 6: Commit.**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect exit: ${PIPESTATUS[0]}"   # N = the "N tests collected" figure; expect exit 0
  # Count update, same commit: set the collected figure to N in the CLAUDE.md baseline bullet
  # ("**<old> backend tests collected.**" and "if it differs from <old>") and in the AGENT.md pytest line
  # ("(<old> collected; …)"). Pass/env wording is rewritten from measurements in Task 8.
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08
  git add src/backend/modules/rag.py src/backend/tests/test_embedding_fail_closed_paths.py CLAUDE.md AGENT.md
  git diff --cached --name-only     # expect exactly these 4 paths (incl. CLAUDE.md, AGENT.md)
  git commit -m "fix(rag): exclude vectors made by a different embedding model from vector search" -- src/backend/modules/rag.py src/backend/tests/test_embedding_fail_closed_paths.py CLAUDE.md AGENT.md
  ```

### Task 8: End measurement, whole-flow re-walk, docs

**Files:** the docs listed in [Owned files](#owned-files).

- [ ] **Step 1: End run, model present** (the gate env):
  ```bash
  set -o pipefail
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend" && find . -name __pycache__ -prune -exec rm -rf {} +
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -2; echo "collect exit: ${PIPESTATUS[0]}"   # expect 0
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -20; echo "pytest exit: ${PIPESTATUS[0]}"      # 0, or 1 only if START_FAILURES was non-empty
  ~/venvs/asclexis-311/bin/python -c "from main import app"; echo "import exit: $?"   # expect 0
  ```
  Acceptance:
  - collected = `START_COLLECTED + 13`, or `+ 14` if Task 7 ran. It must equal the figure the last test commit wrote into `CLAUDE.md`/`AGENT.md`;
  - failures ⊆ `START_FAILURES`;
  - the app import succeeds.
- [ ] **Step 2: End run, model absent** (informational; this is what an unfetched install looks like):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend
  EMBEDDING_MODEL_PATH=/nonexistent ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -20; echo "pytest exit: ${PIPESTATUS[0]}"   # expect 1 (model-dependent tests fail)
  ```
  - Record every failure by name.
  - Predicted, **unmeasured**: `test_api_rag_index_002`, `002b`, `002c`, `test_search_vectors_async_calculates_similarity` (all in `tests/test_rag_pipeline.py`), and `test_hc_emb_002…`.
  - If any failure lies outside `tests/test_rag_pipeline.py` and `tests/test_embedding_bundle.py`, **stop**: product behaviour changed on a path this plan did not analyse.
  - Do not edit existing tests to use `use_fallback=True`. That would drop real-model coverage in CI.
- [ ] **Step 3: Invariant greps.**
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08"
  grep -rn "SentenceTransformer(" src/backend --include=*.py | grep -v /tests/          # expect 1 hit, in modules/embeddings.py, with local_files_only=True
  grep -rn "HF_HUB_OFFLINE\|TRANSFORMERS_OFFLINE" src/backend --include=*.py | grep -v /tests/   # expect none
  grep -rnE "import (requests|httpx|aiohttp|socket|urllib\.request|huggingface_hub|sentence_transformers)|from (requests|httpx|aiohttp|huggingface_hub|sentence_transformers)" src/backend --include=*.py | grep -v /tests/ | cut -d: -f1 | sort -u   # expect the same 8 files as on the START tree
  git ls-files | grep -E "\.safetensors$|models/embeddings/"                           # expect none
  git status --short src/backend/models/                                               # expect empty
  ```
- [ ] **Step 4: Re-walk whole flows** (recurring-failures #2), in the running app on Windows (`.\dev.ps1`), model present and then model absent (rename the dir). Record the observed behaviour against the [patient table](#what-the-patient-sees):
  - import a PDF → trends → legacy chat with the agent toggled off → grounded interpretation → reprocess → delete document;
  - `download_models.py embedding` run twice, where the second run must say "already installed".
- [ ] **Step 5: Frontend untouched.** `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 diff --name-only <START_SHA>..HEAD -- src/frontend` (START_SHA recorded in Task 1 Step 4) should print nothing. Then run this on Windows PowerShell and record both exit codes:
  ```powershell
  Set-Location C:\Users\DangT\Documents\GitHub\hc-w08\src\frontend
  npx tsc --noEmit
  "tsc exit: $LASTEXITCODE"          # expect 0
  npx vitest run
  "vitest exit: $LASTEXITCODE"       # expect 0; W-8 changes no frontend file, so any failure is pre-existing — record it by name
  ```
- [ ] **Step 6: Docs** (one `docs:` commit, measured numbers only):
  - `AGENT.md` Commands: add `cd src/backend; python scripts/download_models.py embedding   # one-time fetch of the pinned embedding model; runtime loads it offline and fails closed without it`.
  - `AGENT.md` pytest line and "Known env-only failure" sentence, and the `CLAUDE.md` baseline bullet: the collected figure is already current (each test commit updated it). Rewrite the **pass-count** wording only from measurements in named environments:
    - Task 8 Step 1: `~/venvs/asclexis-311/bin/python` (3.11), model present → "P of N pass";
    - Task 8 Step 2: same interpreter, model absent → the named failure list;
    - CI: only if you read the pass count from the PR's `Backend Tests` log, labelled "CI, ubuntu, Python 3.11, model fetched".

    Label each figure with its environment. Never copy a collected number into a pass slot. If a slot has no measurement, keep the old sentence and flag it in the PR. Name the fetch command. Keep "you must not 'fix' it by lowering the 0.7 threshold" verbatim.
  - Contract C-LOCAL-2:
    - `Enforced at:` `modules/embeddings.py` `_load_local_model`, `modules/rag.py` wrapper, tests HC-EMB-001..007, CI `backend-tests`.
    - `Verify:` the socket-blocked subprocess tests, not a process-wide `HF_HUB_OFFLINE`.
    - Status: per the owner.
  - Contract C-LOCAL-1:
    - remove "the implicit embedding download (C-LOCAL-2)" from the exceptions;
    - add `scripts/download_models.py` to the model-download allow-list;
    - set the file count to the Step 3 result.
  - Matrix LOCAL-03: fill Implementation, Tests and Gate with the paths and HC-EMB IDs. Set Status per the matrix Status table (`enforced` only if the CI job fails on a violation). Do not recount the scorecard line; it belongs to the orchestrator (3a M-2), so tell the orchestrator the row changed.
  - `architecture-overview.md`:
    - `:62`: replace the `ST -. "HTTPS model fetch" .-> HF` edge with a dashed `download_models.py embedding` script edge;
    - `:69`: sentence;
    - `:132`: row.
  - `claims-ledger.md` C10: implicit-download evidence.
  - `docs/architecture/ci-and-quality-gates.md:58` and `performance-scalability-review.md:130`: environment-gap wording.
  ```bash
  cd "/mnt/c/Users/DangT/Documents/GitHub/hc-w08" && python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check
  git add AGENT.md CLAUDE.md docs/capstone-report/architecture-engineering-contract.md docs/capstone-report/specs-compliance-matrix.md docs/capstone-report/architecture-overview.md docs/capstone-report/claims-ledger.md docs/architecture/ci-and-quality-gates.md docs/architecture/performance-scalability-review.md
  git diff --cached --name-only     # expect exactly these 8 paths
  git commit -m "docs: record the offline embedding load, its fetch command and the measured baseline" -- AGENT.md CLAUDE.md docs/capstone-report/architecture-engineering-contract.md docs/capstone-report/specs-compliance-matrix.md docs/capstone-report/architecture-overview.md docs/capstone-report/claims-ledger.md docs/architecture/ci-and-quality-gates.md docs/architecture/performance-scalability-review.md
  ```
  Expected lint output: `Docs lint passed.`, and exit 0 from the index check.

### Task 9: PR and stop

- [ ] **Step 1:** Push the branch and open a PR:
  ```bash
  git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 push -u origin feat/w08-bundled-embedding-model
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08 && gh pr create --base main --head feat/w08-bundled-embedding-model --title "feat(embeddings): load the embedding model offline from a fetched local copy (W-8, D8)" --body-file /mnt/c/Users/DangT/Documents/GitHub/hc-w08-pr-body.md
  ```
  Write the body file outside the worktree, so it is never staged. It follows handoff §6:
  1. START and END measurements (collected, failures, interpreter, command), plus the model-absent run;
  2. each new test with its red line and break-it evidence;
  3. C-LOCAL-2 / C-LOCAL-1 / LOCAL-03 status changes;
  4. the full file list (`git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w08 diff --name-only <START_SHA>..HEAD`);
  5. owner gates reached (Q-FC, Q-HASH, Q-OFFLINE).
- [ ] **Step 2: STOP.** The owner merges. Do not merge while Q-FC is unsigned.

---

## Measured acceptance

| Check | Command | Expected |
|---|---|---|
| New tests | `~/venvs/asclexis-311/bin/python -m pytest tests/test_embedding_bundle.py tests/test_embedding_fail_closed_paths.py -p no:cacheprovider -q` | `13 passed` (`14 passed` with Task 7) |
| Socket blocked + empty HF cache | HC-EMB-001 (absent → `failed_closed`) and HC-EMB-002 (present → `loaded`, similarity > 0.7). Both assert `attempts == []` and an empty `HF_HOME` | green |
| Suite (model present) | Task 8 Step 1 | collected = START + 13 (+1 with Task 7), equal to the `CLAUDE.md`/`AGENT.md` figure; failures ⊆ START |
| Suite (model absent) | Task 8 Step 2 | only `test_rag_pipeline.py` / `test_embedding_bundle.py` names; recorded in `AGENT.md`/`CLAUDE.md` |
| No weights in git | `git ls-files \| grep -E "\.safetensors$\|models/embeddings/"`; `git check-ignore -v src/backend/models/embeddings/all-MiniLM-L6-v2/tokenizer.json` | none; one ignore hit |
| No process-wide offline flag | `grep -rn "HF_HUB_OFFLINE" src/backend --include=*.py \| grep -v /tests/` | none |
| Fetch command works as documented | `cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend && ~/venvs/asclexis-311/bin/python scripts/download_models.py embedding`, run twice | installs; then "already installed" |
| CI | PR checks `Backend Tests`, `E2E Smoke Tests`, `Agent Eval Gate` | green, with the fetch step visible in the logs |
| Offline load in the 3.11 venv | HC-EMB-002 output | **UNMEASURED** until Task 4. The 0.9039 similarity was measured on Windows Py3.13 only |

## Stop gates

1. The D9 venv is missing, or `local_files_only` is absent from the installed sentence-transformers. Stop: fixing it touches `requirements.txt`.
2. A prerequisite phase (P1, P4, P5) has not landed (Task 1 Step 2).
3. The pinned revision does not resolve, or the real fetch fails its checksum. Do not re-pin without the owner.
4. Any edit would touch an ask-first file, `api/assistant.py`, `api/interpretations.py`, `requirements.txt`, or an existing test.
5. Gate-env failures ⊄ START failures, or the model-absent failure list leaves `test_rag_pipeline.py` / `test_embedding_bundle.py`.
6. Anyone proposes committing model files, adding git-lfs, fetching at runtime, or setting `HF_HUB_OFFLINE` process-wide. None of these is licensed.
7. Q-FC, VERIFIED-FALLBACK or EMB-REV unsigned: the PR stays open. Q-HASH unsigned: Task 7 is not started.
8. Any urge to lower the 0.7 bar or skip HC-EMB-002. Neither is allowed (C-SAFE-4).

## Rollback

- **Before the PR is merged:** `cd /mnt/c/Users/DangT/Documents/GitHub/hc-w08 && gh pr close <PR number> --delete-branch`. Then `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/hc-w08`. `main` is untouched.
- **After the merge:** on a new branch from `origin/main`, `git revert` the W-8 commits in reverse order (docs, Task 7, Task 6, Task 5, CI, Task 4, Task 3, Task 2), then open a PR for the owner to merge. Never force-push `main`.
- There is no migration and no schema change.
- After a revert, the runtime again fetches implicitly (the LOCAL-03 gap returns), and CI again relies on that fetch.
- The fetched directory is git-ignored and harmless. If the owner wants it gone, delete only what this plan fetched: `rm -r /mnt/c/Users/DangT/Documents/GitHub/hc-w08/src/backend/models/embeddings/all-MiniLM-L6-v2`. Never delete `src/backend/models/` itself: it is the SQLAlchemy package.
- Task 6's reorder only removes a data-loss path; reverting it restores the old behaviour.
- Task 7's revert re-includes hash-fallback vectors in search.

## Owner sign-offs

- D8 and D8-delivery: **owner-approved** 2026-09-27 (Claude Code chat), quoted in [Approval scope](#approval-scope). Nothing to sign.
- **Q-FC**, the patient-visible form of fail-closed:
  - legacy chat → existing knowledge-fallback answer;
  - grounded interpretation → existing 501 with the text "Document search is unavailable because the local embedding model is not installed.";
  - import → succeeds without document-search chunks;
  - reprocess → keeps previous chunks.

  `[ ] Approved  [ ] Changed to: ________  Owner: ________  Date: ________`

  **Coupled gate VERIFIED-FALLBACK (3a M-8):** decide Q-FC together with W-3 O-1. The legacy-chat row sends the patient to the knowledge fallback, whose `_fetch_latest_obs` has no `user_verified` filter (`api/assistant.py:1329-1347` B@7b2ff1f), so it can cite unverified values, against D4, unless O-1 is signed. Recommended: O-1 = yes, signed before W-8 merges. Per 3a §3 its sign-off line lives in the W-3 plan; this plan only cites it.

  The grounded-interpretation sentence above is copied verbatim into `QFC_APPROVED_DETAIL` in `tests/test_embedding_fail_closed_paths.py`, where HC-EMB-006c asserts it. If the owner changes the wording, update both the product constant and that literal from the signed line, in the same commit. The PR cannot merge until this line is signed.
- **Q-HASH**, Task 7: exclude hash-fallback vectors from legacy vector search until reprocessed.

  `[ ] Approved  [ ] Declined  Owner: ________  Date: ________`
- **Q-OFFLINE**, confirm the interpretation: "HF offline" means a per-call offline load of a local path, not a process-wide `HF_HUB_OFFLINE`, which would disable the sanctioned GGUF download.

  `[ ] Confirmed  Owner: ________  Date: ________`
- **EMB-REV** (3a M-6), the pinned embedding model and revision: `all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (repo `sentence-transformers/all-MiniLM-L6-v2`; see Global Constraints). `owner-decisions-2026-09-27.md:46` leaves the revision pin owner-gated "in the W-8 plan", and W-11b S-C4-5 bundles whatever this line selects. Must be signed before W-8 merges.

  `[ ] Approved  [ ] Changed to: ________  Owner: ________  Date: ________`
- **Merge:** `[ ] Merged  Owner: ________  Date: ________`

## Recurring-failures recheck

| # | Applies | Concrete recheck in this plan |
|---|---|---|
| 1 Green suite that could not fail | yes | A break-it step for every HC-EMB test (Tasks 2–7). The route behaviour goes through HTTP (`route_client`: HC-EMB-005 chat, HC-EMB-006c grounded interpretation, with a break-it on the route's 501 mapping). The socket guard *records* attempts rather than only raising, because libraries swallow `OSError` |
| 2 Fix creates the next bug | yes | Fail-closed exposed the delete-before-embed path in reprocess (Task 6). Task 8 Step 4 re-walks import → chat → interpretation → reprocess → delete |
| 3 Figures asserted | yes | Size, hash, revision and similarity each carry their command. The 3.11-venv figures are UNMEASURED until Task 1 and Task 4 |
| 4 Environment-dependent results | yes | The model-present and model-absent runs are both recorded. CI now fetches explicitly instead of implicitly |
| 5 Contaminated tree | yes | Dedicated worktree. Every commit uses explicit pathspecs. The `.gitignore` line guards P5-style `git add src/backend/models/` |
| 6 Documented commands nobody ran | yes | Task 4 Step 1 runs `python scripts/download_models.py embedding` exactly as `AGENT.md` will list it, from `src/backend` |
| 7 SQL three-valued logic | checked | The Task 7 filter is `==` on a `nullable=False` column; no NULL case |
| 8 Stale guidance | yes | CLAUDE.md "installed (CI)" is false: CI fetches implicitly. `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md:152` says the model is MIT; the card says `apache-2.0` |

## Findings for the orchestrator

1. **CI's embedding "install" is the implicit fetch.** `ci.yml:33-51` (B@7b2ff1f) has no model step. CLAUDE.md:30-31 and AGENT.md:57,64 (main@40f590e) describe CI as having "a real embedding model installed". After W-8, CI must fetch explicitly (Task 4), or `002b` and HC-EMB-002 fail in CI.
2. **Contract C-LOCAL-1's grep allow-list is short one file after P1.** B@7b2ff1f adds `from huggingface_hub import list_repo_files` at `scripts/download_models.py:53` (and `:206`). The grep then returns 8 files, not 7, and `scripts/download_models.py` is not in the allow-list.
3. **Contract C-LOCAL-2's suggested verify (`HF_HUB_OFFLINE=1`) must not become product code.** Process-wide, it would disable `hf_hub_download` at `api/model_settings.py:903-937` (B@7b2ff1f).
4. **Pre-existing data-loss path.** `api/documents.py:867-871` (A@692fdf3) deletes chunks before embedding; the caller at `:684-687` swallows and commits. Fail-closed makes this likely; Task 6 fixes it.
5. **License claim is wrong.** `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md:152` says `all-MiniLM-L6-v2` is MIT; the model card says `license: apache-2.0`. G-C4 (redistribution) inherits the Apache-2.0 obligations; this plan's script does not redistribute.
6. **Live evidence for LOCAL-03.** The Windows HF cache `refs/main` was rewritten on 2026-09-27 at 17:05:28 -0700 to revision `1110a243…`. An implicit Hub contact happened on this machine today.
7. **`models_path="models/"` resolves into the SQLAlchemy package dir `src/backend/models/`**, because the backend runs from `src/backend`. This is an existing wart, not fixed here. The embedding dir is anchored to `src/backend` explicitly and git-ignored.
