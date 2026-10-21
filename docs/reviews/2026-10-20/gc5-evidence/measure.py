"""G-C5 Task 7 measurements. Run from src/backend: python measure.py <load|latency|contradiction|gate|block>.
Sockets are blocked and HF is offline. Scripts only; the model is fetched by scripts/download_models.py nli."""
import asyncio, json, os, resource, socket, statistics, sys, time
from pathlib import Path

BACKEND = Path(os.getcwd())
sys.path.insert(0, str(BACKEND))
os.environ["TEST_MODE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
SOCK_ATTEMPTS = []


def _block(*a, **k):
    SOCK_ATTEMPTS.append(a[:2])
    raise OSError("sockets blocked by measure.py")


for name in ("connect", "connect_ex", "bind", "sendto"):
    setattr(socket.socket, name, _block)
socket.create_connection = _block
socket.getaddrinfo = _block


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def enable_flag(on: bool):
    import api.assistant as A
    from core.config import settings
    settings.use_llm_entailment = on
    A._rag_module = None  # in-process only; get_rag_module() rebuilds with the flag


def build_pairs():
    """(claim, SourceEvidence, tag): legacy golden outputs x glucose chunks, plus synthetic claims per agent-golden vault observation."""
    import re
    from modules.verifier_agent import SourceEvidence
    from tests.legacy_eval.harness import CHUNK_SETS, load_cases
    pairs = []
    srcs = [SourceEvidence(source_id=c["chunk_id"], source_text=c["text"], source_type=c["source_type"]) for c in CHUNK_SETS["glucose"]]
    for case in load_cases():
        for line in case["model_output"].splitlines():
            line = re.sub(r"\[cite:\d+\]", "", line).strip()
            if line and not line.endswith(":") and len(line) > 15:
                for s in srcs:
                    pairs.append((line, s, f"legacy:{case['id']}"))
    for f in sorted((BACKEND / "tests/agent/golden").glob("grounded-*.json")):
        d = json.loads(f.read_text())
        for o in d["vault"]["observations"]:
            v, u, n = o["value"], o.get("unit") or "", o["name"]
            src = SourceEvidence(source_id="1", source_text=f"{n}: {v} {u} (collected {o['collected_at']}).", source_type="user_observation")
            pairs.append((f"Your {n} was {v} {u}.", src, f"agent:{d['id']}:true"))
            pairs.append((f"Your {n} was {round(float(v) * 1.9 + 3, 1)} {u}.", src, f"agent:{d['id']}:wrongvalue"))
            pairs.append((f"Your {n} result is high.", src, f"agent:{d['id']}:high"))
            pairs.append((f"Your {n} result is normal.", src, f"agent:{d['id']}:normal"))
    return pairs


def mode_load():
    import modules.model_integrity as MI
    t = {}
    orig = MI.verify_model_file

    def timed(*a, **k):
        s = time.perf_counter(); r = orig(*a, **k); t["sha256_s"] = time.perf_counter() - s; return r

    MI.verify_model_file = timed
    try:
        import sentencepiece  # noqa
        print("sentencepiece importable: yes")
    except Exception as e:
        print("sentencepiece importable: no ->", type(e).__name__)
    print("rss_before_MB", round(rss_mb(), 1))
    from modules.embeddings import load_local_cross_encoder
    s = time.perf_counter(); enc = load_local_cross_encoder(); total = time.perf_counter() - s
    print("first_call_total_s", round(total, 3), "sha256_s", round(t["sha256_s"], 3), "load_only_s", round(total - t["sha256_s"], 3))
    print("rss_after_load_MB", round(rss_mb(), 1))
    print("id2label", enc.config.id2label)
    print("tokenizer", type(enc.tokenizer).__name__, "is_fast", getattr(enc.tokenizer, "is_fast", None))
    print("sentencepiece loaded in sys.modules after load:", "sentencepiece" in sys.modules)
    print("socket attempts", len(SOCK_ATTEMPTS))


def mode_latency():
    from collections import Counter
    from modules.embeddings import load_local_cross_encoder
    from modules.verifier_agent import VerifierAgent, VerificationConfig
    va = VerifierAgent(VerificationConfig(use_llm_entailment=True))
    pairs = build_pairs()
    print("pairs", len(pairs))
    s = time.perf_counter(); va._check_entailment_llm(pairs[0][0], pairs[0][1]); print("first_call_s", round(time.perf_counter() - s, 3))
    lat, labels = [], []
    for _ in range(3):
        for claim, src, _tag in pairs:
            s = time.perf_counter(); va._check_entailment_llm(claim, src); lat.append((time.perf_counter() - s) * 1000)
    for claim, src, _tag in pairs:
        labels.append(va._check_entailment_llm(claim, src).label.value)
    print("n_calls", len(lat), "distinct_pairs", len(pairs))
    print("predict_ms median", round(statistics.median(lat), 1), "p95", round(pct(lat, 95), 1), "max", round(max(lat), 1), "mean", round(statistics.mean(lat), 1))
    print("labels", dict(Counter(labels)))
    print("peak_rss_MB", round(rss_mb(), 1))
    print("max_length", load_local_cross_encoder().max_length)
    print("socket attempts", len(SOCK_ATTEMPTS))


def mode_contradiction():
    from modules.verifier_agent import VerifierAgent, VerificationConfig
    off = VerifierAgent(VerificationConfig(use_llm_entailment=False))
    on = VerifierAgent(VerificationConfig(use_llm_entailment=True))
    rows = []
    for i, (claim, src, tag) in enumerate(build_pairs()):
        a = off.verify_claim(claim, f"c{i}", [src]); b = on.verify_claim(claim, f"c{i}", [src])
        er = b.entailment_results[0]
        rows.append(dict(tag=tag, claim=claim, rules_ok=a.is_verified, nli_ok=b.is_verified, nli_label=er.label.value, nli_conf=round(er.confidence, 3)))
    both = [r for r in rows if r["rules_ok"]]
    flips = [r for r in both if not r["nli_ok"]]
    contra = [r for r in flips if r["nli_label"] == "contradiction"]
    lowc = [r for r in contra if r["nli_conf"] < 0.7]
    print("claim/source pairs", len(rows), "rules_verified", len(both), "rules_ok->nli_fail", len(flips), "of which CONTRADICTION", len(contra), "of which conf<0.7", len(lowc))
    print("nli_ok->rules_fail (NLI rescues)", len([r for r in rows if r["nli_ok"] and not r["rules_ok"]]))
    for r in rows:
        if r["nli_label"] == "contradiction" and r["nli_conf"] < 0.7:
            print("  lowconf-contradiction:", r)
    print("all low-confidence (<0.7) contradiction rows (any rules result):", len([r for r in rows if r["nli_label"] == "contradiction" and r["nli_conf"] < 0.7]))


def run_gate(flag: bool):
    from fastapi.testclient import TestClient
    from tests.legacy_eval import harness
    from modules.rag import RAGModule
    from modules.verifier_agent import VerifierAgent
    enable_flag(flag)
    bodies, ver, calls = [], [], []
    orig_req, orig_val, orig_chk = TestClient.request, RAGModule.validate_response, VerifierAgent._check_entailment_llm

    def req(self, *a, **k):
        r = orig_req(self, *a, **k); bodies.append(r.json()); return r

    def val(self, response, retrieved_chunks, *a, **k):
        res = orig_val(self, response, retrieved_chunks, *a, **k); v = res.verification
        ver.append(dict(verified=v.verified_claims, failed=v.failed_claims, total=v.total_claims, issues=list(v.claims_with_issues or [])))
        return res

    def chk(self, claim, source):
        r = orig_chk(self, claim, source); calls.append((claim, source.source_id, r.label.value, round(r.confidence, 3))); return r

    TestClient.request, RAGModule.validate_response, VerifierAgent._check_entailment_llm = req, val, chk
    try:
        report = harness.score_cases(harness.load_cases())
    finally:
        TestClient.request, RAGModule.validate_response, VerifierAgent._check_entailment_llm = orig_req, orig_val, orig_chk
    return report, bodies, ver, calls


def mode_gate():
    from tests.legacy_eval.harness import load_cases
    out = {}
    for flag in (False, True):
        t0 = time.perf_counter()
        report, bodies, ver, calls = run_gate(flag)
        print(f"\n=== flag={flag} elapsed {time.perf_counter() - t0:.2f}s, nli calls {len(calls)} ===")
        print(report.render())
        print("Legacy eval gate:", "PASS" if report.passed else "FAIL " + "; ".join(report.failure_reasons()))
        out[flag] = (report, bodies, ver, calls)
    off, on = out[False], out[True]
    print("\n=== per-case (off -> on) ===")
    for i, c in enumerate(load_cases()):
        ro, rn, vo, vn = off[0].results[i], on[0].results[i], off[2][i], on[2][i]
        print(f"{c['id']}: abstained {ro.abstained}->{rn.abstained} valid {ro.is_valid}->{rn.is_valid} "
              f"text_same={off[1][i].get('full_response') == on[1][i].get('full_response')} "
              f"claims(v,f,t) {(vo['verified'], vo['failed'], vo['total'])}->{(vn['verified'], vn['failed'], vn['total'])}")
        if vo["issues"] != vn["issues"]:
            print("   issues_off", vo["issues"]); print("   issues_on ", vn["issues"])
    print("\nNLI calls flag on (claim, src, label, conf):")
    for c in on[3]:
        print("  ", c)
    print("peak_rss_MB", round(rss_mb(), 1), "socket attempts", len(SOCK_ATTEMPTS))


def mode_block():
    from unittest.mock import AsyncMock
    from tests.legacy_eval import harness
    import api.assistant as A
    cases = [c for c in harness.load_cases() if c["expect"] in ("answer", "abstain") and c.get("finish_reason", "stop") == "stop"] * 3

    async def timed(rag, case):
        rag.retrieve_context = AsyncMock(return_value=harness.build_chunks(case["chunk_set"]))
        gaps, state = [], {"stop": False}

        async def beat():
            last = time.perf_counter()
            while not state["stop"]:
                await asyncio.sleep(0.001); n = time.perf_counter(); gaps.append(n - last); last = n

        task = asyncio.create_task(beat()); await asyncio.sleep(0.01)
        s = time.perf_counter()
        await rag.query(question=case["question"], profile_id="p", model_runner=harness.FakeRunner(case["model_output"]), use_memory=False)
        total = time.perf_counter() - s
        state["stop"] = True; await task
        return total, max(gaps)

    async def main():
        enable_flag(True); rag = A.get_rag_module(); res = []
        for i, c in enumerate(cases):
            total, gap = await timed(rag, c); res.append(gap)
            print(f"{'COLD ' if i == 0 else 'warm '}{c['id']}: query {total*1000:.0f} ms, max event-loop stall {gap*1000:.0f} ms")
        print("cold stall ms", round(res[0] * 1000), "| warm stall median/max ms", round(statistics.median(res[1:]) * 1000), round(max(res[1:]) * 1000))
        enable_flag(False); rag2 = A.get_rag_module(); off = []
        for c in cases:
            off.append((await timed(rag2, c))[1])
        print("flag-off max stall ms median/max", round(statistics.median(off) * 1000), round(max(off) * 1000))

    asyncio.run(main())
    print("peak_rss_MB", round(rss_mb(), 1))


if __name__ == "__main__":
    globals()["mode_" + sys.argv[1]]()
