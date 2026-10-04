# Pipelines: Documents, Assistant, Safety

**Last Updated:** 2026-10-04
**Owner:** Project Lead
**Refresh Trigger:** An extractor, agent tool, guardrail, or export surface is added or removed

Part of the [architecture diagram set](README.md).

---

## Document → insight

The path a file takes from upload to something the user can act on. Note the
two entry points: OCR-based extraction for PDFs and images, and deterministic
parsing for structured imports (CSV / FHIR bundles, HC-M23).

```mermaid
flowchart TD
    UP["POST /documents<br/>upload"] --> DUP{"duplicate?<br/>hash + date heuristic"}
    DUP -->|warn, don't block| ING["modules/ingest<br/>encrypt to vault docs/"]

    ING --> KIND{"file kind"}
    KIND -->|"PDF / image"| CLS["modules/document_classifier<br/>lab · imaging · pathology · visit_notes"]
    KIND -->|"CSV / FHIR bundle"| STRUCT["modules/import_structured<br/>stdlib json/csv, no new deps"]

    CLS --> EXT{"per-category extractor"}
    EXT --> E1["extract.py — labs"]
    EXT --> E2["extract_visit_notes.py"]
    EXT --> E3["extract_imaging.py"]
    EXT --> E4["extract_pathology.py"]
    E1 & E2 & E3 & E4 --> SPANS["extract_spans.py<br/>char offsets + verbatim quote"]

    SPANS --> NORM["modules/normalize<br/>analyte mapping + unit conversion"]
    STRUCT --> NORM

    NORM --> STORE[("per-profile DB<br/>observations + document_entity<br/><b>all unverified</b>")]

    STORE --> VERIFY["VerificationWorkbench<br/><b>human in the loop</b>"]
    VERIFY --> VERIFIED[("verified data")]

    VERIFIED --> VONLY["verified only: FHIR · visit prep · pinboards · medications (default)<br/>agent answers (values from verified rows only;<br/>pending rows reported as a count)"]
    STORE -.->|"labelled pending"| TL["timeline"]
    STORE -.->|"unreviewed labelled, rejected dropped"| HL["highlights"]
    STORE -.->|"rejected dropped"| TASKS["care-task candidates"]
    STORE -.->|"rejected dropped"| RECON["medication reconciliation"]
    STORE -.->|"unverified included, unlabelled (D4 approved, W-3 pending)"| TRENDS["trends"]
    STORE -.->|"unverified included (outside D4)"| EXPU["exports: doctor summary · CSV/JSON"]

    style VERIFY fill:#e65100,stroke:#ff9800,color:#fff
    style STORE fill:#1b5e20,stroke:#66bb6a,color:#fff
```

**Everything lands unverified.** That is the load-bearing property of this
diagram: extraction is a suggestion, not a fact, until a human confirms it.
Structured imports are no exception — a FHIR bundle is more accurate than OCR
but still arrives unverified. Surfaces differ in what they do with unverified
rows:

- **Verified only:** FHIR export, visit prep, pinboards, and medications
  (unless the caller passes `verified_only=false`).
- **Agent answers:** values come from verified rows only; pending rows are
  reported as a count.
- **Shown with a label:** the timeline (pending) and highlights (unreviewed).
  Rows the user rejected are dropped from highlights, care-task candidates and
  medication reconciliation.
- **Included without a label:** trends and the legacy (non-agent) RAG path.
  Owner decision [D4](../capstone-report/owner-decisions-2026-09-27.md)
  (2026-09-27) approved the change: trends may show unverified points only
  when visibly marked "unverified", and legacy RAG cites verified values only.
  **Approved, not yet implemented** (work item W-3).
- **Included, outside D4:** CSV / JSON exports and the doctor summary.

Reprocessing is rejected for `lab_csv` / `fhir_bundle` documents: there is no
document text to rebuild from, so re-extraction would delete entities and
recreate nothing.

## Assistant & agent graph

```mermaid
flowchart TD
    Q["POST /assistant/chat"] --> SESS["ChatSession / ChatTurn<br/>persisted per profile"]
    SESS --> ENABLED{"agent enabled?"}

    ENABLED -->|no| RAGONLY["modules/rag<br/>retrieve → compose → generate"]
    ENABLED -->|yes| GRAPH

    subgraph GRAPH["modules/agent/graph.py"]
        direction TB
        PLAN["plan<br/>deterministic intent routing"]
        ACT["act<br/>tool dispatch"]
        DRAFT["draft<br/>compose cited answer"]
        REFLECT["reflect<br/>continue or stop"]
        PLAN --> ACT --> DRAFT --> REFLECT
        REFLECT -->|"budget left"| PLAN
    end

    ACT --> TOOLS
    subgraph TOOLS["tools/ — all read-only"]
        T1["query_observations"]
        T2["compute_trend"]
        T3["lookup_reference"]
        T4["check_verification"]
        T5["retrieve_chunks"]
        T6["query_care_tasks"]
        T7["query_medication_changes"]
        T8["query_timeline"]
    end

    RAGONLY --> MR["ModelRunner"]
    MR --> PROV{"provider"}
    PROV -->|default| LC["llama.cpp"]
    PROV -->|configured| OL["Ollama, localhost"]
    PROV -->|"unavailable"| FB["no-LLM fallback<br/><b>must stay functional</b>"]

    DRAFT --> GUARD
    subgraph GUARD["guardrails/"]
        G1["classifier — is this answerable?"]
        G2["groundedness — every claim cited?"]
        G3["redaction_gate — scrub untrusted fields"]
        G4["guard — abstain / template"]
    end

    GUARD --> AOUT["agent answer<br/>template-composed, every sentence cited"]
    GUARD -->|"ungrounded, low confidence, or advice-bait"| ABSTAIN["abstain / escalate<br/>fixed templates"]
    MR --> SAFE["legacy-path checks: validate_response ·<br/>verifier_agent · faithfulness · interpret_safety patterns"]
    SAFE --> OUT["cited answer<br/>[REFERENCE:N] / [YOUR_RESULTS:N]"]
    SAFE -.->|"any check fails (prohibited-advice match, missing citations, faithfulness < 0.6):<br/>is_valid=false, answer still served (W-4 pending)"| OUT

    style GUARD fill:#4a148c,stroke:#ba68c8,color:#fff
    style FB fill:#e65100,stroke:#ff9800,color:#fff
```

Four things this diagram is asserting:

1. **Tools are read-only.** The agent can query the record; it cannot mutate it.
2. **The no-LLM fallback is a supported path**, not a degraded accident. Every
   surface must work with no model present.
3. **Retrieved text is untrusted input.** Document chunks, entity names and
   memory items are attacker-controlled (a PDF can contain "ignore previous
   instructions"), so they pass through the injection filter before reaching a
   prompt. That is why `redaction_gate` sits inside the loop rather than at the
   end.
4. **Only the legacy path calls a model.** The agent's `draft` node composes
   answers from templates over tool output; it makes no LLM call. The legacy
   safety modules (`interpret_safety`, `faithfulness`, `verifier_agent`) run on
   the legacy path only. The agent guard reuses just the 0.6 confidence cutoff
   from `modules/faithfulness.py` and abstains below it.

## Safety & privacy control-flow

Every point where data crosses a trust boundary.

```mermaid
flowchart LR
    subgraph inbound["Untrusted in"]
        DOC["uploaded document text"]
        MEM["memory items"]
        HIST["session history"]
        QUERY["user question"]
    end

    subgraph filters["Neutralize, don't drop"]
        INJ["PROMPT_INJECTION_PATTERNS<br/>→ [UNTRUSTED-INSTRUCTION-REMOVED]"]
    end

    subgraph generate["Generation"]
        PROMPT["compose_prompt"]
        LLM["ModelRunner"]
    end

    subgraph gates["Before anything is shown"]
        CITE["citation required"]
        FAITH["faithfulness"]
        VERIF["verifier_agent"]
        ISAFE["interpret_safety<br/>no diagnosis · no dosing"]
    end

    subgraph outbound["Trusted out"]
        SCREEN["on-screen answer"]
    end

    subgraph files["Anything leaving the app"]
        RED["<b>modules/redaction</b>"]
        EXP["redacted exports:<br/>RL dataset · FHIR · visit prep · pinboards"]
    end

    AUDIT["core/audit<br/>allowlist scrub"]
    MASTER[("unencrypted master DB")]

    DOC & MEM & HIST & QUERY --> INJ --> PROMPT --> LLM --> gates --> SCREEN
    gates -.->|"fails"| ABST["abstain"]
    SCREEN --> RED --> EXP
    generate -.-> AUDIT --> MASTER

    style INJ fill:#4a148c,stroke:#ba68c8,color:#fff
    style RED fill:#4a148c,stroke:#ba68c8,color:#fff
    style AUDIT fill:#4a148c,stroke:#ba68c8,color:#fff
    style MASTER fill:#b71c1c,stroke:#ef5350,color:#fff
```

The purple nodes are the mandatory chokepoints. On the export path, redaction
runs on the RL dataset export (forced `policy_level="strict"` with no
configuration knob, because an export must not be made *less* redacted by
configuration) and on FHIR, visit-prep and pinboard exports. It does **not** run
on CSV / JSON exports, the doctor summary, or backups. Backups are deliberately
unredacted: a redacted backup cannot be restored. For the other three, owner
decision [D3](../capstone-report/owner-decisions-2026-09-27.md) (2026-09-27)
applies: the doctor summary is to be strictly redacted
(**approved, not yet implemented**, work item W-2), and CSV / JSON stay full-fidelity as the
patient's own data, to be named as deliberate exceptions in `CLAUDE.md` and
`docs/compliance/data-privacy.md` (work item W-10).
