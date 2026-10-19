# G-C5 HC-M11 NLI Cross-Encoder Behind a Default-Off Flag Implementation Plan

**Last Updated:** 2026-10-18
**Owner:** repository owner
**Status:** PROPOSED — plan only, not approved for execution
**Refresh Trigger:** any commit to `src/backend/modules/verifier_agent.py`, `modules/rag.py`, `api/assistant.py`, `modules/embeddings.py`, `scripts/download_models.py`, `core/config.py` or `config/model_manifest.json`; any owner answer to an [unsigned line](#unsigned-owner-lines); the model's Hub revision changing.
**Base measured:** `origin/main` @ `e000974` (2026-10-18). W-8 (#168) and W-4 (#72) are both merged. Every `file:line` below was re-read at this base. Lane A's design (`lane-A-rag-assistant.md` §G-C5) was written at `3b2236c`; its line numbers have drifted and are corrected in [Measured anchors](#measured-anchors).
**Item:** `G-C5` in [queue.md](2026-10-15-build-program/queue.md) (this plan is item `G-C5-PLAN`, DOCS, no slot). Design source: [lane A §G-C5](2026-10-15-build-program/lane-A-rag-assistant.md); readiness pack: `audit/2026-09-25/waves/scaffold/G-C5.md`; packet: `audit/2026-09-25/gated-items-decision-packet.md` Brief 5.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, then superpowers:executing-plans. Steps use `- [ ]`. Nothing here is ticked, and nothing below is approved except the five owner lines quoted verbatim in [Owner lines](#owner-lines).

**Goal:** Make the existing flag `use_llm_entailment` reach the verifier, and make `_check_entailment_llm` score `(source, claim)` with a local NLI cross-encoder loaded offline. The flag stays **off by default**. With the flag off, the legacy eval output is byte-identical to before. No threshold changes.

**This plan changes no product code.** It describes one hunk in an ask-first file (`modules/verifier_agent.py`); it does not touch it.

---

## Approved scope (verbatim)

`docs/plans/2026-09-08-backlog-closure-plan.md:403` (§14 row 2):

> "| 2 | `HC-M11` approval (§12) | **Approved, scheduled after band A** | Building the cross-encoder behind a flag that defaults off, in two ask-before-touching files. **Not** changing production scoring behaviour, thresholds, or anything else in those files. Its model-distribution prerequisite is still unbuilt. |"

`:365-368` (§12), the narrow reading:

> "Read the approval narrowly. It licenses *building* the scorer behind a flag that defaults off — it is not authorisation to change what production faithfulness scoring does, to alter a threshold, or to touch anything else in those two files. Any of that is a fresh ask."

This plan uses **one** of the two files (`verifier_agent.py`, one function body). `faithfulness.py` needs no edit (`per_claim_entailment` already exists at `faithfulness.py:366`).

## Owner lines

Quoted from `docs/capstone-report/owner-decisions-2026-09-27.md`. The "answer" is the bold text of the row, copied unchanged. Nothing outside these five lines is recorded as approved.

| Line | Gate | Owner answer (verbatim) |
|---|---|---|
| `:225` | Q5a | **not now: flag stays default off** |
| `:226` | Q5b | **one-time fetch via download_models.py, HF offline, fail closed** |
| `:227` | GC5-PLAN | **wait for W-8** (satisfied: W-8 #168 merged, `26106ee` is an ancestor of `origin/main`) |
| `:228` | GC5-MODEL | **plan measures both; owner confirms** |
| `:238` | GC5-ASKFIRST | **Approve the hunk in advance** — "G-C5 may edit verifier_agent.py:304-317 within its plan. Opus review still runs, and you still merge." The row's last column reads `no (recommended: decide on the real diff)`: the owner chose the option that was not the recommended one. |

What each line does **not** say:
- Q5a: not now. The flag never defaults on in this plan, and NLI scores never change production faithfulness. No criterion for enabling was given.
- Q5b: "fail closed" is two words in a one-line answer. It does not say what the patient sees; see [OL-2](#unsigned-owner-lines).
- GC5-MODEL: "plan measures both" means licence and size (packet `:399-403`). The owner **confirms later**; the model is not yet chosen. See [OL-1](#unsigned-owner-lines).
- GC5-ASKFIRST: covers `verifier_agent.py:304-317` and nothing else. Any other `verifier_agent.py` hunk needs a new gate.

## Dependencies and order

- W-8 #168 merged: the loader pattern (`EmbeddingModelUnavailableError`, per-call `local_files_only=True`, `settings.*_model_path`, the `download_models.py` subcommand) is copied from merged code. Contract I-14.
- W-4 #72 merged: `scripts/legacy_eval_gate.py` exists (contract I-2) and is the byte-identical proof's first command.
- **G-C5 is next in the `rag.py` chain** (queue row: "last on `rag.py`"). Hunk H1 edits `rag.py:1027`. Branch it after every earlier `rag.py` PR merges (W-3, #95 per lane A). Re-run Task 0 at branch time.
- B-3 floats per R-4 (queue): it has no shared file with G-C5; confirm with the Task 0 file-overlap check.
- P5: no shared file (scaffold `G-C5.md` §5 `:76`: its grep covers `faithfulness.py` and `verifier_agent.py` for `utcnow`; G-C5 adds none). Order against W-8, W-4 and P5 is satisfied: the first two are merged, P5 is independent.
- This plan consumes I-2 and I-14 **without changing a signature**. No hunk below changes `EmbeddingModelUnavailableError`, `resolve_embedding_model_dir`, `EmbeddingsModule`, or either gate script.

## Measured anchors

All on `e000974`. "Lane A" is the line number lane A quoted.

| Fact | Anchor now | Lane A |
|---|---|---|
| `verify_all_claims(claims_to_verify)` has no config; inside `_run_verification_pipeline` (`rag.py:952`) | `modules/rag.py:1027` | `:1007` |
| `RAGModule.verifier = VerifierAgent(verification_config)` | `rag.py:191` | `:176` |
| `VerificationConfig(min_faithfulness_score=0.6, fail_on_contradiction=True)` | `api/assistant.py:222-225` | `:210-213` |
| flag defined, read nowhere | `core/config.py:162` | `:157` |
| `embedding_model_path` | `core/config.py:123` | — |
| `use_llm_entailment: bool = False` in `VerificationConfig`; defaults 0.7, 1, True, 0.6, False | `verifier_agent.py:76-88` (0.6 at `:85`) | same |
| dispatch to `_check_entailment_llm` | `verifier_agent.py:223-224` | same |
| `_check_entailment_llm` stub body (calls the rules) | `verifier_agent.py:304-317` | same (matches GC5-ASKFIRST) |
| `verify_all_claims(claims, config=None)` builds `VerifierAgent(config)` | `verifier_agent.py:470` | `:470-484` |
| 0.6 threshold sites | `rag.py:886`, `verifier_agent.py:85`, `api/assistant.py:223,227,1228` | `rag.py:866` |
| `per_claim_entailment` already a parameter | `faithfulness.py:366` | `:362-366` |
| `EmbeddingModelUnavailableError`, `resolve_embedding_model_dir`, `local_files_only=True` | `embeddings.py:37`, `:41`, `:112` | — |
| `cmd_embedding`, subparser, dispatch | `download_models.py:327`, `:409`, `:423-424` | `:317-328` |
| the source text field is `SourceEvidence.source_text` (lane A wrote `source.text`) | `verifier_agent.py:33` | — |

Facts that shape the design:
- **No existing test passes a non-default `VerificationConfig`** (`grep -rn "VerificationConfig\|verification_config" src/backend/tests` finds only imports). Every `RAGModule()` in tests builds `VerifierAgent(None)`, whose config equals the defaults. So H1 (pass `self.verifier.config`) is value-identical for every existing caller, and production's `get_rag_module()` values equal the defaults too.
- `get_rag_module()` caches a module-level singleton (`assistant.py:217`). The flag is read once, at first construction. Changing `USE_LLM_ENTAILMENT` needs a restart. This is the existing behaviour for every field; this plan does not change it.
- `verify_claim` marks a claim unverified when it has a contradicting source (`fail_on_contradiction`) or fewer than `min_supporting_sources` supporting sources (`verifier_agent.py:390-409`). `rag.py:880-889` turns any failed claim into a validation error, and `assistant.py:_legacy_serve_or_abstain` (`:233`) replaces an invalid legacy answer with `ABSTAIN_TEMPLATE`.
- `verifier_agent.py` has no logger and no `logging` import. A hunk limited to `:304-317` can only log through an import inside the function body.
- `config/model_manifest.json` holds tier GGUF entries; W-8 pinned its embedding model as constants in `embeddings.py`, not in the manifest. `test_model_integrity.py::test_hc_mint_011` requires each manifest entry to have `repo` and, if `sha256` is set, a 64-hex value. A new entry fits that test.
- `.gitignore:87-98` ignores `*.safetensors`, `*.bin`, `/models/` and `/src/backend/models/embeddings/`. A new `src/backend/models/nli/` directory would leave the tokenizer and config files untracked-but-visible. See [file list](#file-list).

## Model (GC5-MODEL): measured from metadata only

Candidate: `cross-encoder/nli-deberta-v3-xsmall`. **No weights were downloaded.** Source: the Hugging Face Hub HTTP API and the model card, read on 2026-10-18 with
`curl -sS 'https://huggingface.co/api/models/cross-encoder/nli-deberta-v3-xsmall?blobs=true'` plus `.../resolve/<revision>/config.json` and `README.md`.

| Item | Measured value | Source and caveat |
|---|---|---|
| Licence | **`apache-2.0`** | model card front matter and API `cardData.license`. **This contradicts `feature_list.json:142` ("MIT")**; the packet had marked MIT UNVERIFIED (`:401`). The base model's own licence (`microsoft/deberta-v3-xsmall`) is UNMEASURED. The training sets (`nyu-mll/multi_nli`, `stanfordnlp/snli`) carry their own terms: not reviewed, not a legal opinion. |
| Gated / private | `gated: False`, `private: False` | API |
| Pinned revision | `a150876415327c80daeff35ca6f68f5ed8cf5c24` (last modified 2025-04-11T09:26:22Z) | API `sha`; `refs` shows `main` at the same commit |
| Weights file | `model.safetensors`, 283,353,172 bytes | API `siblings[].size` |
| Weights sha256 | `4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9` | API `siblings[].lfs.sha256`: **advertised by the Hub, not recomputed from bytes.** `cmd_nli` recomputes after the fetch and installs nothing on a mismatch, so a wrong pin fails closed. |
| Files to fetch (8) | `README.md` 2,871 · `added_tokens.json` 26 · `config.json` 1,053 · `model.safetensors` 283,353,172 · `special_tokens_map.json` 301 · `spm.model` 2,464,616 · `tokenizer.json` 8,656,624 · `tokenizer_config.json` 1,346 | API sizes. `README.md` is fetched so the licence declaration stays beside the weights. |
| Total to fetch | **294,480,009 bytes (about 281 MiB)** | sum of the 8 sizes |
| Whole repo, all formats | 2,268,597,330 bytes (about 2.1 GiB) | sum of every sibling (adds `pytorch_model.bin`, 9 ONNX variants). **Never fetched**; the allow-list excludes them. |
| Parameters | 70,831,619 (F32 70,831,107 + I64 512) | API `safetensors`. `feature_list.json:142` says "~22M params"; that figure is not what the file holds. |
| Labels | `{0: contradiction, 1: entailment, 2: neutral}` | `config.json` `id2label` |
| Model card accuracy | SNLI-test 91.64, MNLI-mismatched 87.77 | model card; general-domain English, **not medical text** |
| Inference latency, RAM, accuracy on this app's claims | **UNMEASURED** | needs the weights; the plan forbids a download. Measured on the owner host in [Task 7](#task-7--owner-host-evidence-not-part-of-the-pr). |
| `sentencepiece` in the project venv | **UNMEASURED** (`import sentencepiece` fails in `~/venvs/asclexis-311`) | `tokenizer.json` exists, so a fast tokenizer should load without it. Task 3's tiny-model test cannot prove this for DeBERTa. If the real model needs it, `requirements.txt` becomes a new file: stop and tell L0. |
| Whether `CrossEncoder(<dir>, local_files_only=True)` works on this directory | **UNMEASURED** for the real files (signature checked: `local_files_only` is a keyword of `CrossEncoder.__init__` in sentence-transformers 6.1.0; `CrossEncoder.config` exists) | covered for a tiny stand-in model by HC-GC5-003; for the real model by Task 7 |

## File list

Start: queue row `G-C5` (`queue.md:194`). Hunks use only these files.

| File | In queue row | Hunk | Ask-first |
|---|---|---|---|
| `src/backend/modules/verifier_agent.py` | yes | H3, lines `:304-317` only | **yes** (GC5-ASKFIRST) |
| `src/backend/modules/rag.py` | yes | H1 | no |
| `src/backend/api/assistant.py` | yes | H2 | no |
| `src/backend/modules/embeddings.py` | yes | H4 | no |
| `src/backend/core/config.py` | yes | H5 | no |
| `config/.env.example` | yes | H6 | no |
| `src/backend/scripts/download_models.py` | yes | H7 | no |
| `config/model_manifest.json` | yes | H8 | no |
| `src/backend/tests/test_gc5_nli_flag.py` | yes | new, 5 tests (HC-GC5-001 to 005; 005 added after review, see Task 3) | no |
| `CLAUDE.md` / `AGENT.md` count slots | row says "slots" | **not edited by the G-C5 PR** | n/a |

**Not edited:** `modules/faithfulness.py`, `modules/interpret_safety.py`, `modules/redaction.py`, `modules/verifier_agent.py` outside `:304-317`, `scripts/legacy_eval_gate.py`, `scripts/agent_eval_gate.py`, `requirements.txt`.

**Needs an L0 queue-row change (not added silently):**
1. **`.gitignore`** (one line, `/src/backend/models/nli/`). Without it the 7 non-weight files of a fetched model show as untracked and invite `git add`. Alternative with no extra file: default the path to `models/embeddings/nli-deberta-v3-xsmall` (already ignored). The plan assumes the `.gitignore` line; L0 picks.
2. **Slots wording.** The row lists "slots", but `CLAUDE.md:30-34` says PRs never edit the baseline line and the orchestrator updates it in a post-merge batch (SLOT-RULE-2). The PR reports the measured count and delta only. L0 should drop "slots" from the row or confirm the CLAUDE.md text governs.
3. If the real tokenizer needs `sentencepiece`: `src/backend/requirements.txt`.

## Unsigned owner lines

None of these is signed. The plan states each option and does not choose silently. The orchestrator asks; the executor of G-C5 does not start Tasks 3-4 until OL-1 and OL-2 are answered.

### OL-1 GC5-MODEL: confirm the model, licence and pin

Q: "Confirm `cross-encoder/nli-deberta-v3-xsmall`, licence **Apache-2.0** (not MIT as `feature_list.json` says), revision `a150876415327c80daeff35ca6f68f5ed8cf5c24`, 294,480,009 bytes to fetch." Owner line `:228` says the owner confirms. Until then the pins in H4/H8 are proposals. A different model changes H4, H7, H8 and the byte counts.

### OL-2 Absent model with the flag on: fall back to rules, or fail closed?

Queue row `:194` already lists "absent model with flag on" as an open gate. Lane A's design hunk 3 falls back to rules. Owner line `:226` says "fail closed". They differ.

| | A: fall back to the rules | B: fail closed (claims unverified) |
|---|---|---|
| Code in H3 | `return self._check_entailment_rules(claim, source)` | `return EntailmentResult(..., label=NEUTRAL, confidence=0.0, ...)` |
| Flag on, model absent: patient sees | exactly today's answers (rule-based verification, same abstentions) | **every legacy chat answer with a cited claim is abstained** (`ABSTAIN_TEMPLATE`): no supporting source, so `_determine_verification` is False for every claim |
| Never weaker than today? | yes | yes; stricter |
| Operator signal | none except a log line | a log line, and the patient-visible abstentions |
| Matches the signed `:226` text literally | **no** ("fail closed" is not "fall back") | **yes** |
| Risk | A misconfigured install runs unverified-by-NLI while the operator believes NLI is on. A silent downgrade. | A forgotten fetch silently disables all legacy answers while the flag is on. |

Both options keep flag-off unchanged. The plan's default for the tests and hunk text is **B**, because it matches the signed words. The decision is the owner's; if the owner picks A, only H3's absent branch and HC-GC5-004's assertions change.

### OL-3 ModelRunner applicability

CLAUDE.md §3: all LLM calls go through `ModelRunner`. A cross-encoder is not an LLM; `modules/embeddings.py` already loads `sentence_transformers` directly (the embeddings precedent, W-8). Options: **(A, planned)** load directly in `embeddings.py` beside the embedder, no new layer (CLAUDE.md §2); **(B)** add an NLI method to the `ModelRunner` facade. B adds a layer for a non-generative model. The packet's option C (prompting the local LLM for entailment) is not what Q5b chose. Unsigned: the plan assumes A.

### OL-4 Feed `per_claim_entailment` into faithfulness in v1? (lane A open question 4)

Default in this plan: **no**. With the flag on, only the verifier's claim outcomes change; the faithfulness score (`rag.py:1030-1033`) is unchanged. Yes would add a second `rag.py` hunk and an NLI call per claim outside the verifier, changing the score that decides `faithfulness < 0.6` (`rag.py:886`). That is closer to "changing what production faithfulness scoring does" (backlog `:365-368`): a fresh ask. If the owner says yes, L0 opens a follow-on row; this plan does not draft the hunk.

### OL-5 Anything beyond `verifier_agent.py:304-317`

None is planned. Any other `verifier_agent.py` hunk (a logger import, a new config field) is **unsigned** and needs a new owner gate. Q5a's "flag may later default on" is also unsigned and out of scope.

## Hunks

Each shows Before and After on `e000974`. Indentation is preserved. These are the only product edits G-C5 makes.

### H1 `src/backend/modules/rag.py:1027` (not ask-first)

Before:
```python
        # Run batch verification
        verification_results = verify_all_claims(claims_to_verify)
```
After:
```python
        # Run batch verification
        verification_results = verify_all_claims(claims_to_verify, self.verifier.config)
```
Value-identical today (see [Measured anchors](#measured-anchors)); it makes the config reach `VerifierAgent`.

### H2 `src/backend/api/assistant.py:222-225` (not ask-first)

Before:
```python
    if _rag_module is None:
        _rag_module = RAGModule(
            enable_verification=True,
            verification_config=VerificationConfig(
                min_faithfulness_score=0.6,
                fail_on_contradiction=True,
            ),
```
After:
```python
    if _rag_module is None:
        from core.config import settings as app_settings

        _rag_module = RAGModule(
            enable_verification=True,
            verification_config=VerificationConfig(
                min_faithfulness_score=0.6,
                fail_on_contradiction=True,
                use_llm_entailment=app_settings.use_llm_entailment,
            ),
```
The local import matches `assistant.py:371` and `:522`. `0.6` and `fail_on_contradiction` are untouched. Flag default is False, so the value is the dataclass default today.

### H3 `src/backend/modules/verifier_agent.py:304-317` (ASK-FIRST, GC5-ASKFIRST `:238`)

Before (the whole function, `:304-317`):
```python
    def _check_entailment_llm(
        self,
        claim: str,
        source: SourceEvidence,
    ) -> EntailmentResult:
        """
        LLM-based entailment checking.

        Uses secondary LLM to evaluate claim-source relationship.
        """
        # Optional future enhancement: LLM-based entailment.
        # Current default is rule-based matching (value checks + lexical overlap)
        # and is selected by use_llm_entailment=False in config.
        return self._check_entailment_rules(claim, source)
```
After (**option B**, the planned default, see OL-2):
```python
    def _check_entailment_llm(
        self,
        claim: str,
        source: SourceEvidence,
    ) -> EntailmentResult:
        """
        NLI cross-encoder entailment (HC-M11), reached only when
        use_llm_entailment is on. Loaded from a local directory with Hugging
        Face offline; if the model is unavailable the claim is left unverified
        (fail closed, owner decision Q5b).
        """
        import logging

        from modules.embeddings import EmbeddingModelUnavailableError, load_local_cross_encoder

        try:
            encoder = load_local_cross_encoder()
        except EmbeddingModelUnavailableError as exc:
            logging.getLogger(__name__).warning("NLI model unavailable: %s", exc)
            return EntailmentResult(
                source_id=source.source_id,
                label=EntailmentLabel.NEUTRAL,
                confidence=0.0,
                explanation="NLI model not installed; claim left unverified",
            )
        scores = encoder.predict([(source.source_text, claim)], apply_softmax=True)[0]
        best = max(range(len(scores)), key=lambda i: scores[i])
        label = EntailmentLabel(str(encoder.config.id2label[best]).lower())
        return EntailmentResult(
            source_id=source.source_id,
            label=label,
            confidence=float(scores[best]),
            explanation=f"NLI cross-encoder: {label.value}",
        )
```
After (**option A**): the `except` branch instead reads `return self._check_entailment_rules(claim, source)`; the rest is identical.

Notes:
- The edit stays inside `:304-317`. Imports are inside the body so the flag-off path never imports `embeddings` or torch from this file, and no module-level line changes.
- Premise is `source.source_text`, hypothesis is the claim, matching the model's `(premise, hypothesis)` training order.
- `EntailmentLabel(...)` raises `ValueError` if a model ever returns a label outside the enum; with the pinned model the labels are contradiction/entailment/neutral (measured). Not caught on purpose: an unexpected label must be loud, not neutral.
- Thresholds are unchanged: `verify_claim` still demotes an entailment below `min_entailment_confidence` (0.7) to neutral (`verifier_agent.py:173`).
- **Asymmetry, not changed here.** Only ENTAILMENT has the 0.7 floor. A CONTRADICTION at any confidence fails the claim (`verifier_agent.py:177-178`, with `fail_on_contradiction=True`). With an NLI argmax, a low-confidence contradiction (for example 0.34 against 0.33 and 0.33) therefore abstains the legacy answer. Adding a floor would be a `verify_claim` edit outside `:304-317` and outside GC5-ASKFIRST: unsigned, see OL-5. Task 7 measures how often it happens.
- **Failure scope.** Only `EmbeddingModelUnavailableError` from the load is caught. A failure in `encoder.predict` (out-of-memory, tokenizer error) or the deliberate `ValueError` above propagates through `validate_response` (`rag.py:815`) to the route, uncaught, flag on only. That is loud by design; see risk 10.
- **Cost, flag on only.** `validate_response` is synchronous and `query()` calls it inside an `async` function (`rag.py:1297`), so the first-call sha256 of 283 MB, the model load and every `predict` block the event loop. `predict` runs once per claim x source (one pair per call). With the model absent, `load_local_cross_encoder` runs again for each pair and logs one warning per claim x source (failures are not cached). Both are accepted for a default-off flag and measured in Task 7; moving the work to a thread or batching pairs would touch `rag.py` or `verifier_agent.py` beyond the signed range.

### H4 `src/backend/modules/embeddings.py` (after `resolve_embedding_model_dir`, `:41-46`; not ask-first)

Before: the file ends the helper block at `:46` and `@dataclass class EmbeddingsConfig` starts at `:49`.

After (inserted between them; `EmbeddingModelUnavailableError` and `resolve_embedding_model_dir` are unchanged):
```python
# HC-M11 NLI cross-encoder. Repo, revision and weights sha256 are pinned in
# config/model_manifest.json ("nli-deberta-v3-xsmall"); the runtime below never
# contacts that repo. Fetched once by scripts/download_models.py nli.
NLI_MANIFEST_KEY = "nli-deberta-v3-xsmall"
NLI_FETCH_FILES = (
    "README.md", "added_tokens.json", "config.json", "model.safetensors",
    "special_tokens_map.json", "spm.model", "tokenizer.json", "tokenizer_config.json",
)
NLI_REQUIRED_FILES = ("config.json", "model.safetensors")
_nli_encoder = None


def resolve_nli_model_dir() -> Path:
    """Directory the NLI cross-encoder is loaded from (NLI_MODEL_PATH)."""
    from core.config import settings

    path = Path(settings.nli_model_path)
    return path if path.is_absolute() else _BACKEND_DIR / path


def load_local_cross_encoder():
    """Load the NLI cross-encoder from the local directory only; never the network.

    Fails closed (EmbeddingModelUnavailableError) when files are missing, the
    weights do not match the manifest pin, or the model cannot be loaded. A
    failure is not cached, so fetching the model needs no restart.
    """
    global _nli_encoder
    if _nli_encoder is not None:
        return _nli_encoder
    model_dir = resolve_nli_model_dir()
    missing = [n for n in NLI_REQUIRED_FILES if not (model_dir / n).is_file()]
    if missing:
        raise EmbeddingModelUnavailableError(
            f"NLI model not installed at {model_dir} ({len(missing)} required files missing). "
            "Fetch it once with: cd src/backend && python scripts/download_models.py nli"
        )
    from modules.model_integrity import IntegrityStatus, verify_model_file

    if verify_model_file(model_dir / "model.safetensors", NLI_MANIFEST_KEY).status is not IntegrityStatus.VERIFIED:
        raise EmbeddingModelUnavailableError(f"NLI weights at {model_dir} do not match the pinned sha256")
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise EmbeddingModelUnavailableError("sentence-transformers is not installed") from exc
    try:
        _nli_encoder = CrossEncoder(str(model_dir), local_files_only=True)
    except Exception as exc:  # corrupt or incompatible files: fail closed, never download
        raise EmbeddingModelUnavailableError(
            f"NLI model at {model_dir} failed to load: {type(exc).__name__}"
        ) from exc
    return _nli_encoder
```
The integrity function is `verify_model_file(path, tier, *, manifest_path=None)` at `modules/model_integrity.py:138`, and the sketch above calls it that way. `model_integrity.py` is not edited. A missing manifest yields `UNKNOWN_TIER`, which is not `VERIFIED`, so the load fails closed.

### H5 `src/backend/core/config.py:123` (not ask-first)

Before:
```python
    embedding_model_path: str = "models/embeddings/all-MiniLM-L6-v2"
```
After:
```python
    embedding_model_path: str = "models/embeddings/all-MiniLM-L6-v2"
    # HC-M11 NLI cross-encoder (owner decision Q5b, 2026-10-17). Fetched once by
    # `python scripts/download_models.py nli`; used only when use_llm_entailment
    # is on. Relative paths resolve against src/backend.
    nli_model_path: str = "models/nli/nli-deberta-v3-xsmall"
```
`use_llm_entailment` (`:162`) is not edited; its default stays `False`.

### H6 `config/.env.example` (after the `EMBEDDING_MODEL_PATH` line, `:89`; not ask-first)

Before:
```
EMBEDDING_MODEL_PATH=models/embeddings/all-MiniLM-L6-v2
```
After:
```
EMBEDDING_MODEL_PATH=models/embeddings/all-MiniLM-L6-v2

# NLI cross-encoder, used only when USE_LLM_ENTAILMENT=true (default false).
# Fetch once: cd src/backend && python scripts/download_models.py nli
NLI_MODEL_PATH=models/nli/nli-deberta-v3-xsmall
# USE_LLM_ENTAILMENT=false
```

### H7 `src/backend/scripts/download_models.py` (not ask-first)

`cmd_embedding` (`:327`) and `_embedding_complete` (`:319`) are **not edited** (they are I-14 pattern code). Add beside them (after `cmd_embedding`, before `main` at `:384`) a `cmd_nli` that copies the same structure. The subcommand copy is deliberate: refactoring W-8's merged function belongs to another item (CLAUDE.md §3 surgical edits).

Before: no `nli` subcommand (`:409` registers `embedding`, `:423-424` dispatches it).

After:
```python
def _nli_pin() -> dict:
    from modules.embeddings import NLI_MANIFEST_KEY
    from modules.model_integrity import load_manifest

    return load_manifest()["models"][NLI_MANIFEST_KEY]


def _nli_complete(directory: Path) -> bool:
    from modules.embeddings import NLI_FETCH_FILES

    if not all((directory / name).is_file() for name in NLI_FETCH_FILES):
        return False
    return _sha256(directory / "model.safetensors") == _nli_pin()["sha256"]


def cmd_nli(target: Optional[Path] = None) -> None:
    """Fetch the pinned NLI cross-encoder once. The only network step for it.
    Same rules as cmd_embedding: exclusive .partial dir, sha256 check, never
    deletes a directory it did not create in this run."""
    # Body: copy cmd_embedding (:327-381) line for line, written out in full by the
    # executor, with exactly these substitutions: repo and revision come from
    # _nli_pin(); allow_patterns=list(NLI_FETCH_FILES); the target defaults to
    # resolve_nli_model_dir(); completeness uses _nli_complete(); messages say "NLI".
    # Behaviour pinned by HC-GC5-005: exclusive <target>.partial dir, sha256 check
    # before the rename, nothing installed on mismatch, no deletion of an existing
    # .partial or of any directory this run did not create.
```
Plus, in `main()`: `sub.add_parser("nli", help="Fetch the pinned NLI cross-encoder once (the backend loads it offline)")` after `:409`, and `elif args.command == "nli": cmd_nli()` after `:424`. Also one usage line in the module docstring after `:21`.

### H8 `config/model_manifest.json` (not ask-first)

Before: `"models"` ends with the `"gemma4-12b"` entry (the last key).

After: one added key (and `"updated"` set to the execution date):
```json
    "nli-deberta-v3-xsmall": {
      "repo": "cross-encoder/nli-deberta-v3-xsmall",
      "revision": "a150876415327c80daeff35ca6f68f5ed8cf5c24",
      "filename": "model.safetensors",
      "sha256": "4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9",
      "note": "HC-M11 NLI cross-encoder. Apache-2.0 per the model card (measured 2026-10-18 from Hub metadata). sha256 is the Hub's advertised LFS hash; scripts/download_models.py nli recomputes it after the fetch. Pending owner confirmation GC5-MODEL."
    }
```
Satisfies `test_hc_mint_011` (has `repo`; 64-hex sha). Both H4 and H7 read the pin from here, so there is one copy of it.

## Tasks (test-first)

Interpreter: `~/venvs/asclexis-311/bin/python` written in full. Every pytest run is `"$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest <file> ...` from `src/backend`. Work in a dedicated worktree. Stage explicit paths; never `git add -A`. A break-it edit is made by hand to uncommitted work and undone by hand; confirm with `git diff` that only the intended change remains. Never `git checkout --` in the task worktree.

### Task 0: preconditions

- [ ] `git merge-base --is-ancestor 26106ee30a4d498163a47923b30c05e970a967fd origin/main; echo $?` prints 0 (W-8).
- [ ] `git ls-files src/backend/scripts/legacy_eval_gate.py scripts/legacy_eval_gate.py` lists `scripts/legacy_eval_gate.py` (I-2).
- [ ] Re-grep every anchor in [Measured anchors](#measured-anchors) on the current `origin/main`. Any mismatch other than a line number: STOP and tell L0.
- [ ] File-overlap check against open non-draft PRs (`gh pr diff <n> --name-only`) for every file in the [file list](#file-list).
- [ ] OL-1 and OL-2 answered. If not, do only Tasks 1 and 2 (H1/H2) and report the rest as blocked.
- [ ] `~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1` (through `pyslot.sh`). Record the number: it is the PR's baseline. Measured 1901 on `e000974` on 2026-10-18.

### Task 1: baseline byte-identical capture (flag off, before any hunk)

See [Byte-identical proof](#byte-identical-proof). Save outputs under a scratch directory outside the repo. This is the "before" side; it must be taken on the same base commit the PR branches from, with a clean tree (recurring-failures #5).

### Task 2: H1 and H2 (flag reaches the verifier), test HC-GC5-001

- [ ] **RED first.** Create `tests/test_gc5_nli_flag.py` with `test_hc_gc5_001_flag_reaches_verifier`:
  1. `monkeypatch.setattr(core.config.settings, "use_llm_entailment", True)` and `monkeypatch.setattr(api.assistant, "_rag_module", None)`; `rag = api.assistant.get_rag_module()`.
  2. Assert `rag.verifier.config.use_llm_entailment is True` (H2).
  3. Patch `VerifierAgent._check_entailment_llm` with a spy returning an `ENTAILMENT` result at confidence 0.9. Call `rag.validate_response(...)` on a response with one cited, verifiable claim (reuse the fixture style of `tests/test_rag_pipeline.py` / `test_phase4_ai_safety.py`). Assert the spy was called at least once (H1).
  4. Restore the singleton in a `finally`/fixture so no later test sees the flag-on module.
- [ ] Run it. Expected RED output today: `rag.verifier.config.use_llm_entailment` is `False` (assertion in step 2). Capture the output.
- [ ] Apply H2, re-run: step 2 passes and step 3 still fails (spy not called: `verify_all_claims(claims_to_verify)` builds a default-config agent). Capture this second RED.
- [ ] Apply H1, re-run: GREEN. Capture.
- **Break it:** (a) revert H1 only: step 3 fails. (b) revert H2 only: step 2 fails. Undo by hand.
- **What it would fail to notice:** it calls `get_rag_module()` and `validate_response` directly, not `POST /assistant/chat` through `route_client`, so a broken `Depends(...)` or a route that stops calling `get_rag_module()` is invisible (recurring-failures #1). The flag-off route path is covered by the legacy gate in [the proof](#byte-identical-proof); the flag-on route path is not covered in the PR (it needs the real model; Task 7). It also never loads a real model.

### Task 3: loader, config, script, manifest (H4-H8), tests HC-GC5-003 and HC-GC5-005 (and the sha half of 004)

- [ ] **RED first.** Add `test_hc_gc5_003_offline_load_opens_zero_sockets`, copying the subprocess-probe pattern of `tests/test_embedding_bundle.py:28-77` (socket methods patched on the class, not `socket.socket` replaced; clean env without `HF_*`; empty `HF_HOME`; assert no files appear in it). The probe sets `NLI_MODEL_PATH` to a **tiny stand-in model built by the test in `tmp_path`**: a 1-layer BERT sequence classifier (hidden size 16, `num_labels=3`, `id2label` = contradiction/entailment/neutral) saved with `save_pretrained` plus a 10-word `vocab.txt`/tokenizer. It needs no network and about 100 KB. Inside the probe, after the socket patch and before use, it patches `modules.model_integrity.verify_model_file` to return a `VERIFIED` result (H4 imports it inside the function, so the patch takes effect) (the stand-in cannot match the real pin; the sha gate is covered by HC-GC5-004). The probe calls `load_local_cross_encoder()` then `predict([("a","b")], apply_softmax=True)` and prints a JSON line with `attempts`, the label, and a probability sum.
- [ ] Run. Expected RED: `ImportError: cannot import name 'load_local_cross_encoder' from 'modules.embeddings'`. Capture.
- [ ] Apply H4, H5. Re-run until GREEN: `attempts == []`, three probabilities summing to about 1, `hf_cache_files == []`. Capture.
- [ ] Apply H6, H7, H8. Run `tests/test_model_integrity.py::test_hc_mint_011_shipped_manifest_is_valid_and_honest` and `tests/test_embedding_bundle.py` to prove they still pass (neither is edited).
- [ ] **RED first, 005.** `test_hc_gc5_005_cmd_nli_fetch_rules` (mirror `HC-EMB-004a-e` in `tests/test_embedding_fail_closed_paths.py` and `test_embedding_bundle.py`): patch `huggingface_hub.snapshot_download` with a fake that writes a stand-in file set into the directory it is given (no network). Assert (a) a correct fake (files match `NLI_FETCH_FILES`, weights sha256 equal to a patched `_nli_pin()`) installs the target; (b) a checksum mismatch installs nothing and leaves no target directory; (c) a pre-existing `<target>.partial` is never deleted (the command refuses or aborts and the directory is byte-identical afterwards); (d) the fake is called with the manifest `revision` and `allow_patterns == list(NLI_FETCH_FILES)`. Expected RED: `AttributeError: module 'scripts.download_models' has no attribute 'cmd_nli'`. H7's body is written in full from `cmd_embedding` (`:327-381`) with the substitutions listed in H7.
- [ ] `python scripts/download_models.py --help` lists `nli` (read-only check; **do not run `nli`**).
- **Break it:** (a) in H4 make `load_local_cross_encoder` call `socket.create_connection(("huggingface.co", 443))` once before loading: `attempts` becomes `["network"]` and 003 fails. (b) change `local_files_only=True` to `False` and put a `config.json` in the stand-in dir whose `_name_or_path` is a hub id: any fetch attempt must show in `attempts` or in the empty-`HF_HOME` assertion, and 003 fails. Undo by hand.
- **What it would fail to notice:** a stand-in BERT is not DeBERTa; tokenizer/`sentencepiece` behaviour of the real model, and `CrossEncoder.config.id2label` on the real files, are not exercised (Task 7). Native-code fetches that bypass Python sockets are caught only by the empty-`HF_HOME` assertion. A weights file whose sha matches the manifest but whose bytes are malicious is outside this test (the pin protects only against accidental or Hub-side change).
- **Break it (005):** (a) skip the sha compare in `cmd_nli`: (b) fails. (b) make `cmd_nli` `rmtree` an existing `.partial`: (c) fails. Undo by hand. **What it would fail to notice:** the fake `snapshot_download` never talks to the Hub, so a wrong repo id, a revision the Hub no longer serves, or a real file-name mismatch only show at the owner's first real fetch (Task 7).

### Task 4: H3 (the ask-first hunk), tests HC-GC5-002 and HC-GC5-004

- [ ] **RED first, 002.** `test_hc_gc5_002_contradiction_fails_claim`: build a `VerifierAgent(VerificationConfig(use_llm_entailment=True))`; patch `modules.embeddings.load_local_cross_encoder` to return a fake object with `.predict(pairs, apply_softmax=True)` returning `[[0.9, 0.05, 0.05]]` and `.config.id2label = {0: "contradiction", 1: "entailment", 2: "neutral"}`. Pick a (claim, source) pair for which the **rules** return `ENTAILMENT` at or above 0.7, and first assert that with `use_llm_entailment=False` the claim verifies (`failed_claims == 0`): the precondition that stops this test passing vacuously. Then, flag on, assert the claim is unverified, `contradicting_sources` names the source, and through `RAGModule(...).validate_response` that `verification.failed_claims == 1`.
- [ ] Run. Expected RED today: the stub calls the rules, the claim verifies, the final assertion fails. Capture.
- [ ] **RED first, 004.** `test_hc_gc5_004_absent_model_behaviour`: point `settings.nli_model_path` at an absent `tmp_path` dir; with the flag on, `verify_claim` on the same pair. First `monkeypatch.setattr(modules.embeddings, "_nli_encoder", None)` (and again in the wrong-sha half): the test runs in-process and the module global is never reset, so an encoder cached by an earlier test would hide an absent model (recurring-failures #4). **Assertions follow OL-2.** Option B (planned): the claim is unverified, `entailment_results[0].label is NEUTRAL`, `confidence == 0.0`, and no socket opened. Option A: the claim result equals the flag-off result. Also in this test: place the tiny stand-in model from Task 3 at the path with a **wrong** sha (the real manifest pin does not match it) and assert the same absent-model behaviour (the sha gate). Expected RED today: `load_local_cross_encoder` does not exist before Task 3, and after Task 3 the stub still returns the rule result, so the assertion fails. Capture.
- [ ] Apply H3 (option per OL-2). Re-run both: GREEN. Capture.
- **Break it:** (002) invert the mapping in H3 (take `argmin`): the contradiction test fails; (002) drop the `.lower()`: `ValueError` on the fake's labels only if the fake uses capitalised labels, so make the fake's `id2label` mixed-case once to pin this. (004) in H3 delete the `except`: the test errors with `EmbeddingModelUnavailableError` instead of returning a result.
- **What it would fail to notice:** 002 uses a fake model, so it proves wiring and label mapping, not that the real model ever says "contradiction" on a lab claim. It does not test several sources per claim, long premises (truncation is UNMEASURED), or latency. 004 under option B proves the effect on `verify_claim`/`validate_response`, not that `POST /assistant/chat` shows `ABSTAIN_TEMPLATE`; the route-level abstention is `_legacy_serve_or_abstain`'s existing, already-gated behaviour.

### Task 5: after-capture and diff

Repeat [the proof](#byte-identical-proof) on the finished tree, then diff against Task 1's output.

### Task 6: acceptance, slots, reviews

See [Acceptance](#acceptance-for-the-g-c5-pr) and [Reviews](#reviews). The PR measures `--collect-only` after its final rebase and reports the number and delta. It does not edit `CLAUDE.md:30` or `AGENT.md:76`.

### Task 7: owner-host evidence (not part of the PR)

Q5a says "not now" and the packet's recommended option is to "bring back eval evidence from G-C5". This task needs the weights, so no agent runs it on a build box without the owner. On the owner/model host only: run `python scripts/download_models.py nli`; record the real fetch size and that `sha256` matched; load once with sockets blocked; run the legacy gate **flag on** and record where answers change; measure first-call latency (sha256 plus load), per-claim latency and RAM, and how long the event loop is blocked; count claims where a low-confidence CONTRADICTION fails a claim that the rules verified; force a `predict` failure and record what the route returns; with the model absent, count warning lines per answer; confirm `CrossEncoder.config.id2label` and tokenizer load for the real files. Output is a report, not a flag change. **UNMEASURED until then:** everything in this paragraph.

## Byte-identical proof

"Flag off, output byte-identical" is easy to assert and hard to prove (scaffold risk 1). A test that checks only the flag default cannot see a changed code path (recurring-failures #1), and a cached or contaminated run hides diffs (#5). Run the same four commands on the same base commit, before the first hunk and after the last, flag off, from a clean tree, and record every exit code (GATE-14: the agent gate may not exit on Windows; record the code rather than trusting a PASS line; recurring-failures #6).

```bash
set -o pipefail
R="$(git rev-parse --show-toplevel)"; V=~/venvs/asclexis-311/bin/python
OUT=/tmp/claude-1000/gc5-proof; mkdir -p "$OUT"/{before,after}
S=before   # then: S=after
export USE_LLM_ENTAILMENT=false HF_HUB_OFFLINE=1
cd "$R"; git status --short            # must print nothing but intended hunks at "after"
"$R/scripts/pyslot.sh" "$V" scripts/legacy_eval_gate.py > "$OUT/$S/legacy.txt" 2>&1; echo "legacy_eval_gate exit=$?" | tee -a "$OUT/$S/exit.txt"
"$R/scripts/pyslot.sh" "$V" scripts/agent_eval_gate.py  > "$OUT/$S/agent.txt"  2>&1; echo "agent_eval_gate exit=$?"  | tee -a "$OUT/$S/exit.txt"
cd "$R/src/backend"
"$R/scripts/pyslot.sh" "$V" -m pytest tests/test_phase4_ai_safety.py tests/test_hc_a1_agent_verification.py -q -p no:cacheprovider > "$OUT/$S/pytest.txt" 2>&1; echo "pytest exit=$?" | tee -a "$OUT/$S/exit.txt"
```
Then:
```bash
diff "$OUT/before/legacy.txt" "$OUT/after/legacy.txt"; echo "legacy diff exit=$?"
diff "$OUT/before/agent.txt"  "$OUT/after/agent.txt";  echo "agent diff exit=$?"
diff <(sed -E 's/ in [0-9.]+s.*$//' "$OUT/before/pytest.txt") <(sed -E 's/ in [0-9.]+s.*$//' "$OUT/after/pytest.txt"); echo "pytest diff exit=$?"
diff "$OUT/before/exit.txt" "$OUT/after/exit.txt"; echo "exit-code diff exit=$?"
```
- The only normalisation is stripping pytest's wall-clock suffix. If a gate's raw output differs (timestamps, paths), report the differing lines; do not normalise them away silently.
- **Reach check** (a throwaway script in the scratch directory, not committed): run the legacy gate's `main()` with `VerifierAgent._check_entailment` wrapped by a counter, before and after. Require count greater than 0 and equal. Without it a gate that never reaches the verifier proves nothing about H1.
- **What it would fail to notice:** the golden sets fake retrieval and generation (`tests/legacy_eval/harness.py`), so it proves the flag-off verifier path, not real-model behaviour. It cannot see the flag-on path at all; that is HC-GC5-001/002 and Task 7. `agent_eval_gate.py` did not consume the verifier when last measured (packet Brief 5 table, `scorer.py` row, 2026-10-01; re-check in Task 0), so its identical output is weak evidence for H1-H3. It is listed because the brief names it; the legacy gate and the reach check carry the weight.

## Acceptance for the G-C5 PR

Each command is pasted with its output in the PR. "Predicted" is a prediction; the PR records the measurement.

- [ ] The 5 tests: `... -m pytest tests/test_gc5_nli_flag.py -v` (all five ids: `HC-GC5-001` to `005`; the brief named four, 005 covers the only new network path, `cmd_nli`), RED output captured per test before its hunk.
- [ ] Flag-off diff empty and all exit codes equal ([proof](#byte-identical-proof)).
- [ ] `git diff origin/main -- src/backend/modules/faithfulness.py | wc -l` prints `0`.
- [ ] `git diff origin/main -- src/backend/modules/verifier_agent.py` shows hunks only within the old lines `:304-317` (read the `@@` headers).
- [ ] 0.6 grep unchanged: `git grep -n "0\.6" -- src/backend/modules/rag.py src/backend/modules/verifier_agent.py src/backend/api/assistant.py` equals its output on `origin/main` (compare the two outputs; line numbers in `api/assistant.py` shift by the H2 additions, the values do not; compare the values, not the numbers).
- [ ] `git ls-files | grep -i -E 'safetensors|\.bin$'` prints nothing.
- [ ] `git diff --name-only origin/main...HEAD` lists only [the file list](#file-list) (plus any L0-approved row additions).
- [ ] Full suite through `scripts/pyslot.sh` (run by the Haiku runner, not the implementer): `... -m pytest tests/ -q -p no:cacheprovider`. `test_api_rag_index_002b` may fail without an embedding model; that is environmental and its 0.7 threshold is never lowered.
- [ ] Collected: `... --collect-only -q | tail -1`. **Predicted +5** over the base measured in Task 0 (1901 on `e000974`, so 1906 if nothing else merges). Measured at the PR after the final rebase. `CLAUDE.md:30` and `AGENT.md:76` are not edited by the PR.
- [ ] Docs gates stay green: `docs_lint.py`, `generate_docs_index.py --check`, `harness_drift_check.py`, `repo_hygiene_check.py`.

**Rollback:** revert the PR. With the flag off (default) the path before and after is the same; H1 is value-identical; the model directory is a separate download that can be deleted without touching code. Leaving `USE_LLM_ENTAILMENT` unset is itself the rollback for any deployment.

## Reviews

For the G-C5 build PR (not this plan):
- **Codex adversarial review.** It edits a safety path beside an ask-first file (architectural class, same as W-4).
- **Opus `code-reviewer`**, with the hunk list above as the review checklist. GC5-ASKFIRST (`:238`) says Opus review still runs.
- **Opus `security-reviewer`**: a new model download path beside the Local-first invariant (`CLAUDE.md` Hard invariants). Specific asks: runtime makes no network call (HC-GC5-003); the fetch is user-run and pinned; the sha is checked at fetch and at load; no weights in git; nothing logs claim or source text (H3 logs only the exception text, which names a path and a file count).
- The owner merges (`:238`: "you still merge").

## Risks

| # | Risk | Mitigation or status |
|---|---|---|
| 1 | A green flag-off diff that could not have failed (#1) | reach check; HC-GC5-001 spy; break-it per test |
| 2 | A cached model hides a missing one (#4) | clean env, empty `HF_HOME`, absent-path test (HC-GC5-004) |
| 3 | Figures asserted instead of measured (#3) | licence, size, files, pin measured from Hub metadata; latency/RAM/accuracy UNMEASURED and listed |
| 4 | Licence recorded as MIT in `feature_list.json:142` is Apache-2.0 | OL-1; the ledger text is not edited by this plan |
| 5 | Silent downgrade under option A / silent mass-abstain under option B | OL-2; both effects stated; log line in H3 |
| 6 | Flag read once at first construction (singleton) | existing behaviour; documented in H2; restart required |
| 7 | `cmd_nli` (the only new network path) | covered by HC-GC5-005 (fake fetch; mismatch installs nothing; `.partial` kept); real fetch is Task 7 |
| 8 | Long source chunks truncated by the tokenizer, changing the label | UNMEASURED; Task 7 |
| 9 | A later `rag.py` PR moves `:1027` | Task 0 re-grep; the lane order puts G-C5 last on `rag.py` |
| 10 | Flag on: a `predict` failure or unexpected label propagates uncaught from `validate_response` (`rag.py:815`) to the route | by design (loud, flag-off path unaffected); Task 7 records the route's behaviour on a forced failure; a catch would be a hunk outside `:304-317` (OL-5) |
| 11 | Flag on: sync sha256 (283 MB, first call), model load and each `predict` block the event loop inside async `query()` (`rag.py:1297`); absent model logs one warning per claim x source | accepted for a default-off flag; Task 7 measures first-call and per-claim latency; fixing it needs a hunk outside the signed range |
| 12 | Low-confidence CONTRADICTION fails a claim (no floor, `verifier_agent.py:177-178`) | Task 7 counts flips on the legacy gate flag on; a floor is unsigned (OL-5) |

## Everything UNMEASURED

- Latency, RAM, and accuracy of the model on this app's claims and chunks (needs weights).
- Whether the real files load with `CrossEncoder(<dir>, local_files_only=True)`, and whether `sentencepiece` is needed (`import sentencepiece` fails in the project venv).
- The base model's licence (`microsoft/deberta-v3-xsmall`) and any obligation from the SNLI/MNLI training data.
- That the Hub's advertised weights sha256 equals the bytes (recomputed only by `cmd_nli` at fetch time).
- The flag-on legacy gate result.
- The G-C5 PR's collected count (prediction only).
