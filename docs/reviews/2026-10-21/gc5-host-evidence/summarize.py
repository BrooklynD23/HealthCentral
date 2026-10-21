"""Recompute every summary figure of the 2026-10-21 report from the committed real_llm_*.json (no model run).
Run from src/backend with TEST_MODE=1 HF_HUB_OFFLINE=1:  python ../../docs/reviews/2026-10-21/gc5-host-evidence/summarize.py [--rederive]
--rederive re-runs the flag-off validate_response on the stored rendered_text (no LLM, no NLI) and writes
off.claims_with_issues_rederived into the JSON for cases whose text was not truncated at 1500 chars."""
import json, statistics, sys
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parent
if "--rederive" in sys.argv:
    sys.path.insert(0, ".")
    from tests.legacy_eval import harness
    import api.assistant as A
    from core.config import settings
    settings.use_llm_entailment = False
    for m in ("llama3.1_8b", "qwen3_8b"):
        p = D / f"real_llm_{m}.json"; d = json.loads(p.read_text(encoding="utf-8"))
        for r in d:
            if len(r["rendered_text"]) >= 1500 or r["id"].startswith("vault:"):
                if r["id"].startswith("vault:"):
                    continue  # vault chunks are rebuilt by real_llm.py; only legacy (harness chunk set) cases are re-derived here
            if r["id"].startswith("legacy:") and len(r["rendered_text"]) < 1500:
                A._rag_module = None
                v = A.get_rag_module().validate_response(r["rendered_text"], harness.build_chunks("glucose"))
                r["off"]["claims_with_issues_rederived"] = list(v.verification.claims_with_issues or [])
                assert v.verification.failed_claims == r["off"]["failed"], r["id"]
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
for m, t in (("llama3.1_8b", "llama3.1:8b"), ("qwen3_8b", "qwen3:8b")):
    d = json.loads((D / f"real_llm_{m}.json").read_text(encoding="utf-8"))
    g = [r["gen_s"] for r in d]
    print(f"{t}: cases={len(d)} served_off={sum(r['off']['status']=='served' for r in d)} served_on={sum(r['on']['status']=='served' for r in d)} "
          f"abstain_off={sum(r['off']['status']=='abstain' for r in d)} abstain_on={sum(r['on']['status']=='abstain' for r in d)} "
          f"escalate_off={sum(r['off']['status']=='escalate' for r in d)} escalate_on={sum(r['on']['status']=='escalate' for r in d)}")
    print(f"  tokens>=1024={sum(1 for r in d if (r['tokens'] or 0) >= 1024)} empty_raw={sum(1 for r in d if not r['raw_text'].strip())} "
          f"gen_s median={statistics.median(g):.3f} total={sum(g):.1f}")
    print(f"  faithfulness identical off/on in {sum(r['on']['faithfulness']==r['off']['faithfulness'] for r in d)} of {len(d)}; "
          f"faith<0.6 (on)={sum(r['on']['faithfulness']<0.6 for r in d)}")
    print(f"  verified-count changed={sum(r['on']['verified']!=r['off']['verified'] for r in d)} up={sum(r['on']['verified']>r['off']['verified'] for r in d)} "
          f"down={sum(r['on']['verified']<r['off']['verified'] for r in d)}")
    c = Counter(x[2] for r in d for x in r["on"]["nli"])
    print(f"  nli calls={sum(c.values())} {dict(c)} entailment<0.7={sum(1 for r in d for x in r['on']['nli'] if x[2]=='entailment' and x[3]<0.7)}")
    print("  served->abstain:", [r["id"] for r in d if r["off"]["status"]=="served" and r["on"]["status"]=="abstain"],
          "abstain->served:", [r["id"] for r in d if r["off"]["status"]=="abstain" and r["on"]["status"]=="served"])
