# 04 — Self-Improvement Loop

*Version 0.1 · Design spec — feedback capture and export are implemented; fine-tuning and skill-rewriting stages are aspirational.*

---

## 1. Overview

HealthCentral's self-improvement loop lets the local model get better at a specific patient's domains over time — without cloud services and without external data sharing. Fine-tuning and skill-rewriting are manual operator steps today; only feedback capture and export are automated.

The loop runs entirely on the user's hardware:

```
User feedback (thumbs up/down + correction)
        │
        ▼
ResponseFeedback  (per-profile SQLCipher DB)
        │  [export, confirmed=true, PHI redacted]
        ▼
DPO / GRPO / SFT  JSONL files  (rl_exports/profile_<uuid>/)
        │  [offline fine-tuning — trl / axolotl / llama-factory]
        ▼
Fine-tuned GGUF or LoRA adapter
        │  [placed in models/ or via ollama pull]
        ▼
Updated model deployed locally
        │  [hot-reload: PUT /api/v1/settings/model/provider]
        ▼
Model serves improved responses → collects new feedback → loop repeats
```

---

## 2. Stage 1 — Feedback Capture

- Users rate assistant responses with thumbs up (+1) or thumbs down (−1).
- Optional: supply a correction — what the assistant *should* have said.
- Stored in `ResponseFeedback` table inside the **per-profile SQLCipher DB** (never the master DB, never any network).
- See `src/backend/api/feedback.py` and `src/backend/models/response_feedback.py`.

**Privacy invariant:** feedback data never leaves the local machine and never crosses profile boundaries.

---

## 3. Stage 2 — Dataset Export

Trigger via `POST /api/v1/feedback/export` with `confirmed=true` in the request body.

| Format | File | Contents |
|---|---|---|
| DPO | `dpo_pairs.jsonl` | `{prompt, chosen, rejected}` pairs |
| SFT | `sft_positives.jsonl` | `{prompt, completion}` single-sided positives |
| GRPO | `grpo_rewards.jsonl` | `{prompt, response, reward}` one row per rating |
| Metadata | `metadata.json` | counts, date range, model distribution |

**Redaction:** `modules/redaction.RedactionEngine(policy_level="standard")` is applied to every prompt, response, and correction field before any file is written. The `standard` policy strips SSNs, emails, phone numbers, and name-context patterns. Dates of birth and physical addresses require `policy_level="strict"` and are not removed by the default export. Redaction does not guarantee removal of every lab value, date, or biomarker name — do not treat exported JSONL files as fully de-identified.

**Output location:** `rl_exports/profile_<full-profile-uuid>/`

---

## 4. Stage 3 — Offline Fine-Tuning *(external / aspirational)*

⚠️ **PLACEHOLDER:** No in-app trainer exists. This is a manual operator step.

Recommended tooling (all open-source):
- **trl** (`trl.DPOTrainer`) — DPO fine-tuning from Hugging Face
- **axolotl** — flexible fine-tuning with YAML config
- **llama-factory** — GUI + CLI for SFT/DPO/GRPO

Typical workflow:
1. Export JSONL from the app.
2. Run trainer on a GPU machine (can be separate from the patient device).
3. Convert output to GGUF (`llama.cpp/convert_hf_to_gguf.py`) or keep as a LoRA adapter.

**Safety review gate:** Before deploying a fine-tuned model, verify it still passes the `interpret_safety` prohibited-pattern tests (`pytest tests/test_interpret_safety.py`). A model that starts giving medical advice or dosing instructions must not be deployed.

---

## 5. Stage 4 — Local Deployment & Hot-Reload

- Place the GGUF file in `models/` **or** run `ollama pull <tag>`.
- Switch via the API (no restart needed):
  ```http
  PUT /api/v1/settings/model/provider
  { "provider": "llama_cpp", "model": "models/my-finetuned.gguf" }
  ```
- The provider change is logged to the master audit log.
- The new model must remain on localhost only — the `OllamaProvider` refuses non-localhost URLs at construction time.

---

## 6. Skill-Rewriting Extension *(aspirational)*

The RL reward signal (rating +1/−1) can be repurposed as a quality judge to iteratively rewrite Claude skills stored in `~/.claude/skills/`.

Concept:
1. Extract domain-specific conversations from the RL dataset (e.g. all turns tagged `biomarker`).
2. Score the current skill prompt against that subset — does it produce responses that match the `chosen` column of DPO pairs?
3. Use a capable model to rewrite the skill prompt to improve the score.
4. Re-evaluate, accept if improved, discard if not.
5. Repeat on a schedule or when feedback volume crosses a threshold.

**Hard safety constraint:** Skills that touch `interpret_safety`, redaction, faithfulness, or verifier logic must **never** be auto-rewritten. Any change to safety-critical prompts requires explicit human review and approval.

---

## 7. Guardrails & Open Questions

### Invariants that survive every loop iteration

- No medical advice — `interpret_safety` prohibited patterns must keep passing.
- Grounded, cited responses — `[REFERENCE:N]` / `[YOUR_RESULTS:N]` format preserved.
- Per-profile isolation — fine-tuned adapters are associated with the profile whose data trained them.
- Redaction before export — PHI never enters the JSONL files.
- Audit logging — model switch events recorded.

### Open questions

- Reward model: how to handle reward-hacking / feedback poisoning (adversarial inputs rated highly)?
- Eval harness: automated gate before redeploy (beyond interpret_safety tests)?
- Drift detection: how to detect if the fine-tuned model drifts from clinical accuracy?
- Multi-profile adapter isolation: can adapters be safely shared across profiles, or is that a privacy violation?
- Versioning: rollback path if a deployed model degrades quality.

---

## 8. Next Sprint — Backlog (To Explore)

These options will be evaluated in the next sprint cycle. Each represents a different approach to closing the self-improvement loop or improving extraction quality. No implementation decisions have been made; the sprint will research and compare them.

### Option A — Skills as a per-profile DB (plugged into Agents)

Instead of rewriting flat skill files, store skills as versioned rows in the per-profile SQLCipher DB. Each profile gets its own skill variants tuned to its terminology, test panels, and medications. When an agent is invoked, it loads the profile's current skill snapshot rather than a global file.

- **Key question:** How to version and roll back skill rows safely? How to prevent a corrupted skill row from silently degrading all responses for that profile?
- **Dependency:** Requires a skill-scoring harness that evaluates a candidate skill row against the RL dataset before promotion.

### Option B — Lightweight domain classifier (agent routing signal)

Train or fine-tune a small classifier (e.g. distilled BERT or a LoRA on a 0.5B base) to tag incoming queries with a domain label (`biomarker`, `medication`, `imaging`, `general`). Agents use this label to select the most relevant skill variant or tool. The RL dataset can be used to evaluate and improve classifier accuracy over time.

- **Key question:** Can this run in < 50 ms on CPU to avoid chat latency regression?
- **Privacy constraint:** The classifier must run locally; no network calls.

### Option C — Vision / multimodal model for PDF extraction

Current PDF ingestion relies on text-layer extraction and OCR. A vision-capable model (e.g. Gemma 4 multimodal, Phi-3 Vision, or GOT-OCR 2.0) could handle scanned labs, handwritten notes, and complex table layouts that the current pipeline misses.

- **Key question:** Does the model run acceptably on CPU-only hardware (majority of users)? What is the minimum RAM floor?
- **Placeholder:** Gemma 4 E2B/E4B multimodal is listed in `docs/model_tiers/` but HuggingFace repo URLs are unverified — confirm before experimenting.

### Evaluation criteria for next sprint

| Criterion | Weight |
|---|---|
| Privacy — stays local, per-profile isolation | Must-have |
| Latency — no regression on real-time chat path | Must-have |
| Quality improvement (measured on RL dataset) | High |
| Hardware floor (works on 8 GB RAM) | High |
| Implementation complexity | Medium |
