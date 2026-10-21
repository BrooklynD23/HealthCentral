"""G-C5 Task 7, model host: real LLM answers through the app's own legacy RAG path.

Run from src/backend:  python real_llm.py gen <ollama-model> | trunc
Hold the three pyslot locks first. HF is offline; sockets: only 127.0.0.1:11434 (Ollama) may connect,
any other connect/getaddrinfo is counted and refused. Flag on only inside this process.
Scripts only; the NLI model is fetched by scripts/download_models.py nli.

Path reused, not invented: RAGModule.compose_prompt -> RAGModule._generate_with_runner (the cite schema and
InferenceConfig the app sends) -> RAGModule.validate_response, via the ModelRunner facade (core/llm Ollama
provider). One generation per case; the SAME text is validated flag off and flag on.
Differences from the app: retrieval is faked (legacy glucose chunk set; observation chunks rebuilt from the
agent golden vaults in the text format of RAGModule._get_observation_chunks); temperature forced to 0.0
(the app sends 0.1) and the Ollama provider has no seed parameter, so no seed is set.
"""
import asyncio, json, os, resource, socket, statistics, sys, time
from dataclasses import replace
from pathlib import Path

BACKEND = Path(os.getcwd())
sys.path.insert(0, str(BACKEND))
MODE = sys.argv[1] if len(sys.argv) > 1 else ""
MODEL = sys.argv[2] if len(sys.argv) > 2 else ""
os.environ["TEST_MODE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
if MODE == "gen":
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["LLM_MODEL"] = MODEL

OTHER_ATTEMPTS, OLLAMA_CONNECTS = [], []
_orig_connect, _orig_connect_ex, _orig_gai = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
_LOCAL = ("127.0.0.1", "::1")


def _ok(addr):
    return isinstance(addr, tuple) and len(addr) >= 2 and addr[0] in _LOCAL and addr[1] == 11434


def _connect(self, addr):
    if _ok(addr):
        OLLAMA_CONNECTS.append(addr[:2]); return _orig_connect(self, addr)
    OTHER_ATTEMPTS.append(("connect", repr(addr)[:80])); raise OSError("blocked by real_llm.py")


def _connect_ex(self, addr):
    if _ok(addr):
        OLLAMA_CONNECTS.append(addr[:2]); return _orig_connect_ex(self, addr)
    OTHER_ATTEMPTS.append(("connect_ex", repr(addr)[:80])); return 111


def _gai(host, *a, **k):
    if host in ("127.0.0.1", "localhost", "::1"):
        return _orig_gai(host, *a, **k)
    OTHER_ATTEMPTS.append(("getaddrinfo", repr(host))); raise OSError("blocked by real_llm.py")


socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = _connect, _connect_ex, _gai


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def enable_flag(on):
    import api.assistant as A
    from core.config import settings
    settings.use_llm_entailment = on
    A._rag_module = None


def vault_chunk(d):
    """Observation summary chunk in the text format of RAGModule._get_observation_chunks (no DB)."""
    from modules.rag import RetrievedChunk
    obs = sorted(d["vault"]["observations"], key=lambda o: o["collected_at"], reverse=True)
    if not obs:
        return []
    latest = obs[0]
    val = f"{latest['value']}" + (f" {latest['unit']}" if latest.get("unit") else "")
    lines = [f"YOUR RESULTS — {latest['name']}", f"Latest value : {val}", f"Collected    : {latest['collected_at']}"]
    vals = [o["value"] for o in obs[:3]]
    if len(vals) >= 2:
        delta = vals[0] - vals[-1]
        pct = abs(delta) / abs(vals[-1]) * 100 if vals[-1] else 0
        arrow = "stable" if pct < 3 else ("decreasing" if delta < 0 else "increasing")
        lines.append(f"Trend (last {len(vals)}): " + " → ".join(str(v) for v in reversed(vals)) + f"  ({arrow})")
    if latest.get("verified"):
        lines.append("(User-verified result)")
    return [RetrievedChunk(chunk_id="obs_1", source_type="user_observation", doc_id="doc-1",
                           doc_title=f"Your {latest['name']} Result", page=None, text="\n".join(lines),
                           relevance_score=0.95, is_user_verified=bool(latest.get("verified")), is_observation_summary=True)]


class TempZeroRunner:
    """ModelRunner (Ollama provider) with temperature forced to 0; records the raw result."""
    def __init__(self, inner):
        self.inner, self.last = inner, None
    def is_available(self):
        return self.inner.is_available()
    async def generate_async(self, prompt, config):
        self.last = await self.inner.generate_async(prompt, replace(config, temperature=0.0))
        return self.last


async def run_gen():
    from core.model_runner import ModelRunner
    from core.llm.factory import get_provider
    from modules.verifier_agent import VerifierAgent
    from tests.legacy_eval import harness
    import api.assistant as A
    prov = get_provider(force_new=True)
    print("provider", type(prov).__name__, "model", getattr(prov, "_model", "?"))
    runner = TempZeroRunner(ModelRunner())
    assert runner.is_available(), "Ollama not available"
    cases = []
    for c in harness.load_cases():
        cases.append(dict(id="legacy:" + c["id"], question=c["question"], chunks=harness.build_chunks(c["chunk_set"]), golden_expect=c["expect"]))
    for f in sorted((BACKEND / "tests/agent/golden").glob("grounded-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        cases.append(dict(id="vault:" + d["id"], question=d["question"], chunks=vault_chunk(d), golden_expect=d["expect"]["terminal"]))
    calls = []
    orig_chk = VerifierAgent._check_entailment_llm
    def chk(self, claim, source):
        r = orig_chk(self, claim, source); calls.append((claim, source.source_id, r.label.value, round(r.confidence, 3))); return r
    VerifierAgent._check_entailment_llm = chk
    out = []
    for c in cases:
        enable_flag(False); rag = A.get_rag_module()
        prompt = rag.compose_prompt(c["question"], c["chunks"])
        t = time.perf_counter()
        text = await rag._generate_with_runner(prompt, runner, n_chunks=len(c["chunks"]))
        gen_s = time.perf_counter() - t
        raw = runner.last
        rec = dict(id=c["id"], question=c["question"], golden_expect=c["golden_expect"], gen_s=round(gen_s, 2),
                   finish=getattr(raw, "finish_reason", None), tokens=getattr(raw, "tokens_generated", None),
                   raw_text=getattr(raw, "text", "")[:1500], rendered_text=text[:1500], chunk_text=c["chunks"][0].text)
        for flag in (False, True):
            enable_flag(flag); rag = A.get_rag_module(); calls.clear()
            s = time.perf_counter(); v = rag.validate_response(text, c["chunks"]); dt = time.perf_counter() - s
            m = v.verification
            status = "escalate" if v.prohibited_advice else ("served" if v.is_valid else "abstain")
            rec["on" if flag else "off"] = dict(status=status, is_valid=v.is_valid, verified=m.verified_claims, failed=m.failed_claims,
                                              total=m.total_claims, faithfulness=round(m.faithfulness_score, 3), errors=list(v.validation_errors),
                                              validate_s=round(dt, 3), nli=[list(x) for x in calls])
        out.append(rec)
        o, n = rec["off"], rec["on"]
        print(f"{rec['id']}: gen {gen_s:.1f}s | off {o['status']} v/f/t {o['verified']}/{o['failed']}/{o['total']} faith {o['faithfulness']} | "
              f"on {n['status']} v/f/t {n['verified']}/{n['failed']}/{n['total']} faith {n['faithfulness']}", flush=True)
        for x in n["nli"]:
            print("     nli:", x)
    safe = MODEL.replace(":", "_")
    Path(os.environ.get("REAL_LLM_OUT", ".")).joinpath(f"real_llm_{safe}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    n_off = sum(r["off"]["status"] == "served" for r in out); n_on = sum(r["on"]["status"] == "served" for r in out)
    print(f"SUMMARY model={MODEL} cases={len(out)} served_off={n_off} served_on={n_on} "
          f"abstain_off={sum(r['off']['status']=='abstain' for r in out)} abstain_on={sum(r['on']['status']=='abstain' for r in out)} "
          f"escalate_off={sum(r['off']['status']=='escalate' for r in out)} escalate_on={sum(r['on']['status']=='escalate' for r in out)}")
    print("ollama connects", len(OLLAMA_CONNECTS), "OTHER socket attempts", len(OTHER_ATTEMPTS), OTHER_ATTEMPTS[:5], "peak_rss_MB", round(rss_mb(), 1))


def run_trunc():
    from modules.embeddings import load_local_cross_encoder
    from modules.verifier_agent import VerifierAgent, VerificationConfig, SourceEvidence
    enc = load_local_cross_encoder()
    va = VerifierAgent(VerificationConfig(use_llm_entailment=True))
    fact = "Glucose: 95 mg/dL (reference range 70-100 mg/dL), collected 2026-01-10."
    claim = "Your glucose was 95 mg/dL."
    filler_unit = ("Fasting glucose tests measure the sugar in blood after at least eight hours without food. "
                   "Laboratories may report results in mg/dL or mmol/L, and reference ranges differ between laboratories. ")
    tok = enc.tokenizer
    print("max_length", enc.max_length)
    def ntok(s): return len(tok(s, add_special_tokens=False)["input_ids"])
    print("fact tokens", ntok(fact), "claim tokens", ntok(claim), "filler_unit tokens", ntok(filler_unit))
    def pad(n):
        t = ""
        while ntok(t) < n:
            t += filler_unit
        return t
    rows = []
    for target in (0, 400, 700, 1500):
        for pos in (("first", "last") if target else ("alone",)):
            f = pad(target)
            text = fact if target == 0 else (fact + " " + f if pos == "first" else f + fact)
            r = va._check_entailment_llm(claim, SourceEvidence(source_id="1", source_text=text, source_type="user_observation"))
            n = ntok(text) + ntok(claim)
            rows.append(dict(filler_tokens=target, fact_position=pos, source_tokens=ntok(text), pair_tokens_approx=n + 3,
                             over_512=(n + 3) > 512, label=r.label.value, conf=round(r.confidence, 3)))
            print(rows[-1], flush=True)
    print("socket: other attempts", len(OTHER_ATTEMPTS))
    Path(os.environ.get("REAL_LLM_OUT", ".")).joinpath("trunc.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    if MODE == "gen":
        asyncio.run(run_gen())
    elif MODE == "trunc":
        run_trunc()
    else:
        sys.exit("usage: real_llm.py gen <model> | trunc")
