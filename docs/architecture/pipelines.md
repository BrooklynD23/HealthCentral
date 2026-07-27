# Pipelines: Documents, Assistant, Safety

**Last Updated:** 2026-07-27
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

    VERIFIED --> TRENDS["trends"]
    VERIFIED --> TL["timeline"]
    VERIFIED --> HL["highlights"]
    VERIFIED --> TASKS["care-task candidates"]
    VERIFIED --> RECON["medication reconciliation"]
    VERIFIED --> EXPORT["exports: doctor summary · visit prep · FHIR · CSV/JSON"]

    style VERIFY fill:#e65100,stroke:#ff9800,color:#fff
    style STORE fill:#1b5e20,stroke:#66bb6a,color:#fff
```

**Everything lands unverified.** That is the load-bearing property of this
diagram: extraction is a suggestion, not a fact, until a human confirms it.
Structured imports are no exception — a FHIR bundle is more accurate than OCR
but still arrives unverified. Downstream surfaces consume the *verified* set;
where they surface unverified rows (the timeline), they label them as pending
rather than presenting them as history.

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

    RAGONLY --> MR
    DRAFT --> MR["ModelRunner"]
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

    GUARD --> SAFE["interpret_safety<br/>faithfulness · verifier_agent"]
    SAFE --> OUT["cited answer<br/>[REFERENCE:N] / [YOUR_RESULTS:N]"]
    SAFE -->|"fails"| ABSTAIN["abstain with reason"]

    style GUARD fill:#4a148c,stroke:#ba68c8,color:#fff
    style FB fill:#e65100,stroke:#ff9800,color:#fff
```

Three things this diagram is asserting:

1. **Tools are read-only.** The agent can query the record; it cannot mutate it.
2. **The no-LLM fallback is a supported path**, not a degraded accident. Every
   surface must work with no model present.
3. **Retrieved text is untrusted input.** Document chunks, entity names and
   memory items are attacker-controlled (a PDF can contain "ignore previous
   instructions"), so they pass through the injection filter before reaching a
   prompt. That is why `redaction_gate` sits inside the loop rather than at the
   end.

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
        EXP["exports · FHIR · visit-prep · RL dataset"]
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

The purple nodes are the mandatory chokepoints. Redaction is unconditional on
the export path — including the RL dataset export, which forces
`policy_level="strict"` with no configuration knob, because an export must not
be made *less* redacted by configuration.
