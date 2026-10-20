"""HC-GC5-001..005 - G-C5: HC-M11 NLI cross-encoder behind the default-off flag.

Owner decisions: Q5a (flag stays default off), Q5b (one-time fetch, HF offline,
fail closed), GC5-OL-2 option B (absent model => claim left unverified).
Plan: docs/plans/2026-10-18-GC5-hc-m11-nli-flag-off.md
"""

from __future__ import annotations

import pytest

from modules.rag import RAGModule, RetrievedChunk
from modules.verifier_agent import (
    EntailmentLabel,
    EntailmentResult,
    VerifierAgent,
)

_RESPONSE = """
REPORT FACTS:
Your glucose level is 95 mg/dL, which falls within the normal reference range of 70-100 mg/dL [cite:1].
"""


def _chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id="1",
            source_type="user_document",
            doc_id="doc-1",
            doc_title="Quest Lab Report",
            page=1,
            text="Glucose: 95 mg/dL. Reference range: 70-100 mg/dL. Within normal limits.",
            relevance_score=0.95,
        ),
    ]


def test_hc_gc5_001_flag_reaches_verifier(monkeypatch):
    """USE_LLM_ENTAILMENT reaches VerifierAgent through get_rag_module() and validate_response()."""
    import api.assistant as assistant
    from core.config import settings

    monkeypatch.setattr(settings, "use_llm_entailment", True)
    monkeypatch.setattr(assistant, "_rag_module", None)  # restored by monkeypatch teardown

    rag = assistant.get_rag_module()
    assert rag.verifier.config.use_llm_entailment is True  # H2

    calls: list[tuple[str, str]] = []

    def _spy(self, claim, source):
        calls.append((claim, source.source_id))
        return EntailmentResult(
            source_id=source.source_id,
            label=EntailmentLabel.ENTAILMENT,
            confidence=0.9,
            explanation="spy",
        )

    monkeypatch.setattr(VerifierAgent, "_check_entailment_llm", _spy)
    rag.validate_response(response=_RESPONSE, retrieved_chunks=_chunks())
    assert calls, "use_llm_entailment=True never reached the verifier used by validate_response"  # H1


# ---------------------------------------------------------------------------
# HC-GC5-003: offline load opens zero sockets
# ---------------------------------------------------------------------------

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Copied from tests/test_embedding_bundle.py (HC-EMB probe): socket methods are
# patched on the class; replacing socket.socket breaks a later `import ssl`.
_NLI_PROBE = r'''
import json, logging, socket, sys
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
attempts = []
def _blocked(*args, **kwargs):
    attempts.append("network")
    raise OSError("network blocked by HC-GC5 probe")
socket.socket.connect = _blocked
socket.socket.connect_ex = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked

import modules.model_integrity as mi
from types import SimpleNamespace
# The stand-in cannot match the real pin; the sha gate is covered by HC-GC5-004.
mi.verify_model_file = lambda *a, **k: SimpleNamespace(status=mi.IntegrityStatus.VERIFIED)

from modules.embeddings import load_local_cross_encoder

encoder = load_local_cross_encoder()
scores = encoder.predict([("a", "b")], apply_softmax=True)[0]
out = dict(
    attempts=attempts,
    id2label={str(k): v for k, v in encoder.config.id2label.items()},
    prob_sum=float(sum(float(s) for s in scores)),
    n_scores=len(scores),
)
print("HC_GC5_RESULT=" + json.dumps(out))
'''


def _build_stand_in_nli(directory: Path) -> Path:
    """A ~100 KB 1-layer BERT sequence classifier with NLI labels. No network."""
    from transformers import BertConfig, BertForSequenceClassification, BertTokenizer

    directory.mkdir(parents=True, exist_ok=True)
    words = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "a", "b", "c", "d", "e"]
    (directory / "vocab.txt").write_text("\n".join(words) + "\n", encoding="utf-8")
    BertTokenizer(str(directory / "vocab.txt")).save_pretrained(str(directory))
    cfg = BertConfig(
        vocab_size=len(words), hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
        intermediate_size=32, max_position_embeddings=32, num_labels=3,
        id2label={0: "contradiction", 1: "entailment", 2: "neutral"},
        label2id={"contradiction": 0, "entailment": 1, "neutral": 2},
    )
    BertForSequenceClassification(cfg).save_pretrained(str(directory))
    assert (directory / "model.safetensors").is_file()
    return directory


def _run_nli_probe(tmp_path: Path, model_dir: Path) -> dict:
    hf_home = tmp_path / "hf-empty"
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("HF_", "TRANSFORMERS_", "SENTENCE_TRANSFORMERS_", "NLI_MODEL_PATH"))
    }
    env.update(
        HF_HOME=str(hf_home),
        NLI_MODEL_PATH=str(model_dir),
        PYTHONPATH=str(BACKEND_DIR),
        TEST_MODE="1",
        DATABASE_ENCRYPTION_REQUIRED="false",
    )
    proc = subprocess.run(
        [sys.executable, "-c", _NLI_PROBE],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=300,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("HC_GC5_RESULT=")]
    assert proc.returncode == 0 and lines, f"probe crashed:\n{proc.stderr[-3000:]}"
    out = json.loads(lines[-1].split("=", 1)[1])
    # Native-code fetches that bypass Python sockets would land in the empty cache.
    out["probe_output"] = proc.stdout + proc.stderr
    out["hf_cache_files"] = [str(p) for p in hf_home.rglob("*") if p.is_file()] if hf_home.exists() else []
    return out


def test_hc_gc5_003_offline_load_opens_zero_sockets(tmp_path):
    model_dir = _build_stand_in_nli(tmp_path / "jane-doe-home" / "nli-stand-in")
    out = _run_nli_probe(tmp_path, model_dir)
    assert out["attempts"] == []
    # The library logs the model path at INFO while loading; at DEBUG nothing may carry it.
    for needle in (str(model_dir), "jane-doe-home"):
        assert needle not in out["probe_output"], f"{needle!r} leaked into the probe's stdout/stderr"
    assert out["hf_cache_files"] == []
    assert out["n_scores"] == 3
    assert out["prob_sum"] == pytest.approx(1.0, abs=1e-4)
    assert out["id2label"] == {"0": "contradiction", "1": "entailment", "2": "neutral"}

    # A local directory is never fetched even with local_files_only=False, so the
    # behaviour above cannot see that kwarg flip. Pin it in the source.
    import ast

    tree = ast.parse((BACKEND_DIR / "modules" / "embeddings.py").read_text(encoding="utf-8"))
    loader = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "load_local_cross_encoder")
    calls = [n for n in ast.walk(loader) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "CrossEncoder"]
    assert len(calls) == 1
    kw = {k.arg: k.value for k in calls[0].keywords}
    assert isinstance(kw.get("local_files_only"), ast.Constant) and kw["local_files_only"].value is True


# ---------------------------------------------------------------------------
# HC-GC5-005: `download_models.py nli` fetch rules (mirrors HC-EMB-004a-e)
# ---------------------------------------------------------------------------

import hashlib

sys.path.insert(0, str(BACKEND_DIR / "scripts"))
import download_models  # noqa: E402

from modules import embeddings as emb  # noqa: E402

_NLI_PAYLOAD = b"pinned-nli-weights-stand-in"


def _fake_nli_snapshot(payload: bytes, calls: list):
    def _fake(*, repo_id, revision, local_dir, allow_patterns):
        calls.append({"repo_id": repo_id, "revision": revision, "allow_patterns": list(allow_patterns)})
        root = Path(local_dir)
        for name in allow_patterns:
            (root / name).write_bytes(payload if name == "model.safetensors" else b"{}")
        return str(root)
    return _fake


def _pin_nli_payload(monkeypatch, payload: bytes = _NLI_PAYLOAD) -> dict:
    """Keep the manifest repo/revision, pin the sha of what the fake writes."""
    pin = dict(download_models._nli_pin(), sha256=hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(download_models, "_nli_pin", lambda: pin)
    return pin


def test_hc_gc5_005_cmd_nli_fetch_rules(tmp_path, monkeypatch):
    real_pin = download_models._nli_pin()
    pin = _pin_nli_payload(monkeypatch)
    fetch = "huggingface_hub.snapshot_download"

    # (b) checksum mismatch installs nothing and leaves no directory behind
    monkeypatch.setattr(fetch, _fake_nli_snapshot(b"not the pinned weights", []))
    target = tmp_path / "b" / "nli"
    with pytest.raises(SystemExit) as info:
        download_models.cmd_nli(target)
    assert info.value.code == 1
    assert not target.exists()
    assert not target.with_name("nli.partial").exists()

    # (a) + (d) a correct fetch installs exactly NLI_FETCH_FILES, with the manifest pin
    calls: list = []
    monkeypatch.setattr(fetch, _fake_nli_snapshot(_NLI_PAYLOAD, calls))
    target = tmp_path / "a" / "nli"
    download_models.cmd_nli(target)
    assert calls == [{
        "repo_id": real_pin["repo"],
        "revision": real_pin["revision"],
        "allow_patterns": list(emb.NLI_FETCH_FILES),
    }]
    assert real_pin["revision"] == "a150876415327c80daeff35ca6f68f5ed8cf5c24"
    installed = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert installed == sorted(emb.NLI_FETCH_FILES)
    assert not target.with_name("nli.partial").exists()
    assert pin["sha256"] == hashlib.sha256((target / "model.safetensors").read_bytes()).hexdigest()

    # (c) an existing incomplete target is never deleted; no fetch happens
    calls = []
    monkeypatch.setattr(fetch, _fake_nli_snapshot(b"x", calls))
    target = tmp_path / "c" / "nli"
    target.mkdir(parents=True)
    keep = target / "user-file.txt"
    keep.write_text("do not delete")
    with pytest.raises(SystemExit) as info:
        download_models.cmd_nli(target)
    assert info.value.code == 1
    assert keep.read_text() == "do not delete"
    assert calls == []

    # (c2) a pre-existing .partial is never deleted; no fetch happens
    calls = []
    monkeypatch.setattr(fetch, _fake_nli_snapshot(b"x", calls))
    target = tmp_path / "c2" / "nli"
    partial = target.with_name("nli.partial")
    partial.mkdir(parents=True)
    keep = partial / "someone-elses-file.bin"
    keep.write_bytes(b"do not delete")
    with pytest.raises(SystemExit) as info:
        download_models.cmd_nli(target)
    assert info.value.code == 1
    assert keep.read_bytes() == b"do not delete"
    assert not target.exists()
    assert calls == []

    # (c3) a fetch that fails after writing removes only this run's .partial
    def _failing(*, repo_id, revision, local_dir, allow_patterns):
        (Path(local_dir) / "config.json").write_bytes(b"{}")
        raise OSError("simulated network drop")

    monkeypatch.setattr(fetch, _failing)
    target = tmp_path / "c3" / "nli"
    with pytest.raises(OSError, match="simulated network drop"):
        download_models.cmd_nli(target)
    assert not target.with_name("nli.partial").exists()
    assert not target.exists()


# ---------------------------------------------------------------------------
# HC-GC5-002 / HC-GC5-004: the NLI branch of VerifierAgent._check_entailment_llm
# ---------------------------------------------------------------------------

from modules.verifier_agent import SourceEvidence, VerificationConfig  # noqa: E402

_CLAIM = "Your glucose level is 95 mg/dL, which falls within the normal reference range of 70-100 mg/dL"
_SOURCE = SourceEvidence(
    source_id="1",
    source_text="Glucose: 95 mg/dL. Reference range: 70-100 mg/dL. Within normal limits.",
    source_type="user_document",
)


class _FakeCrossEncoder:
    """Stands in for sentence_transformers.CrossEncoder; mixed-case labels pin .lower()."""

    def __init__(self, probs):
        self._probs = probs
        self.pairs = None
        self.config = type("Cfg", (), {"id2label": {0: "Contradiction", 1: "ENTAILMENT", 2: "Neutral"}})()

    def predict(self, pairs, apply_softmax=False):
        self.pairs = list(pairs)
        assert apply_softmax is True
        return [self._probs]


def _rag(flag: bool) -> RAGModule:
    return RAGModule(
        enable_verification=True,
        verification_config=VerificationConfig(use_llm_entailment=flag),
    )


def test_hc_gc5_002_contradiction_fails_claim(monkeypatch):
    # Precondition (non-vacuous): the rules verify this claim with the flag off.
    off = VerifierAgent(VerificationConfig(use_llm_entailment=False)).verify_claim(_CLAIM, "c1", [_SOURCE])
    assert off.is_verified is True
    assert _rag(False).validate_response(_RESPONSE, _chunks()).verification.failed_claims == 0

    fake = _FakeCrossEncoder([0.9, 0.05, 0.05])
    monkeypatch.setattr("modules.embeddings.load_local_cross_encoder", lambda: fake)

    on = VerifierAgent(VerificationConfig(use_llm_entailment=True)).verify_claim(_CLAIM, "c1", [_SOURCE])
    assert on.is_verified is False
    assert on.contradicting_sources == ["1"]
    assert on.entailment_results[0].label is EntailmentLabel.CONTRADICTION
    assert on.entailment_results[0].confidence == pytest.approx(0.9)
    assert fake.pairs == [(_SOURCE.source_text, _CLAIM)]  # (premise, hypothesis) order

    validated = _rag(True).validate_response(_RESPONSE, _chunks())
    assert validated.verification.failed_claims == 1


def _block_sockets(monkeypatch) -> list:
    import socket

    attempts: list = []

    def _blocked(*args, **kwargs):
        attempts.append("network")
        raise OSError("network blocked by HC-GC5-004")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    return attempts


def _assert_left_unverified(model_dir: Path, monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "nli_model_path", str(model_dir))
    monkeypatch.setattr(emb, "_nli_encoder", None)  # a cached encoder would hide an absent model
    attempts = _block_sockets(monkeypatch)

    result = VerifierAgent(VerificationConfig(use_llm_entailment=True)).verify_claim(_CLAIM, "c1", [_SOURCE])
    assert result.is_verified is False
    assert result.entailment_results[0].label is EntailmentLabel.NEUTRAL
    assert result.entailment_results[0].confidence == 0.0
    assert emb._nli_encoder is None  # a failure is never cached
    assert _rag(True).validate_response(_RESPONSE, _chunks()).verification.failed_claims == 1
    assert attempts == []


def test_hc_gc5_004_absent_model_behaviour(tmp_path, monkeypatch):
    # OL-2 option B: model absent => claim left unverified (fail closed), no network.
    _assert_left_unverified(tmp_path / "does-not-exist", monkeypatch)

    # Sha gate: real-looking files whose weights do not match the manifest pin.
    stand_in = _build_stand_in_nli(tmp_path / "wrong-sha")
    _assert_left_unverified(stand_in, monkeypatch)


# ---------------------------------------------------------------------------
# HC-GC5-004b/c: no log sink, stdout/stderr or cause chain carries the model path
# (recurring-failures #9; same rule as HC-EMB-010a-c)
# ---------------------------------------------------------------------------

import logging  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from tests.test_embedding_fail_closed_paths import _assert_no_path, _leak_surfaces  # noqa: E402


def test_hc_gc5_004b_failures_leak_no_model_path(tmp_path, monkeypatch, caplog, capfd):
    import modules.model_integrity as mi
    from core.config import settings
    from modules.embeddings import EmbeddingModelUnavailableError, load_local_cross_encoder

    home = tmp_path / "jane-doe-home"

    def _load_fails(model_dir: Path) -> EmbeddingModelUnavailableError:
        monkeypatch.setattr(settings, "nli_model_path", str(model_dir))
        monkeypatch.setattr(emb, "_nli_encoder", None)
        with pytest.raises(EmbeddingModelUnavailableError) as failed:
            load_local_cross_encoder()
        return failed.value

    with caplog.at_level(logging.DEBUG):
        absent = _load_fails(home / "absent")
        wrong_sha = _load_fails(_build_stand_in_nli(home / "wrong-sha"))
        # Sha gate satisfied, package cannot load the files: the real failure path.
        corrupt_dir = home / "corrupt"
        corrupt_dir.mkdir(parents=True)
        (corrupt_dir / "config.json").write_text("{}", encoding="utf-8")
        (corrupt_dir / "model.safetensors").write_bytes(b"not a model")
        monkeypatch.setattr(
            mi, "verify_model_file",
            lambda *a, **k: SimpleNamespace(status=mi.IntegrityStatus.VERIFIED),
        )
        corrupt = _load_fails(corrupt_dir)
        # Through the verifier: the WARNING it logs must be path-free too.
        monkeypatch.setattr(settings, "nli_model_path", str(home / "absent"))
        monkeypatch.setattr(emb, "_nli_encoder", None)
        VerifierAgent(VerificationConfig(use_llm_entailment=True)).verify_claim(_CLAIM, "c1", [_SOURCE])

    assert "failed to load" in str(corrupt), "the real package did not fail on the corrupt files"
    for err in (absent, wrong_sha, corrupt):
        assert str(home) not in str(err) and "jane-doe-home" not in str(err)
        assert err.__cause__ is None
    assert corrupt.__suppress_context__ is True  # raised inside `except`: `from None` drops the chain
    _assert_no_path(_leak_surfaces(caplog, capfd), str(home), "jane-doe-home", str(tmp_path))


def test_hc_gc5_004c_load_restores_library_logger_levels(tmp_path, monkeypatch):
    import modules.model_integrity as mi
    import sentence_transformers
    from core.config import settings
    from modules.embeddings import EmbeddingModelUnavailableError, load_local_cross_encoder

    model_dir = tmp_path / "corrupt"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model.safetensors").write_bytes(b"x")
    monkeypatch.setattr(settings, "nli_model_path", str(model_dir))
    monkeypatch.setattr(emb, "_nli_encoder", None)
    monkeypatch.setattr(mi, "verify_model_file", lambda *a, **k: SimpleNamespace(status=mi.IntegrityStatus.VERIFIED))
    loggers = {n: logging.getLogger(n) for n in ("sentence_transformers", "transformers")}
    before = {n: lg.level for n, lg in loggers.items()}
    seen: dict = {}

    def _stub(path, **kwargs):
        seen.update({n: lg.getEffectiveLevel() for n, lg in loggers.items()})
        raise RuntimeError("stop")

    for lg in loggers.values():
        lg.setLevel(logging.INFO)
    monkeypatch.setattr(sentence_transformers, "CrossEncoder", _stub)
    try:
        with pytest.raises(EmbeddingModelUnavailableError):
            load_local_cross_encoder()
        assert seen and all(level >= logging.WARNING for level in seen.values()), seen
        assert all(lg.level == logging.INFO for lg in loggers.values())
    finally:
        for n, lg in loggers.items():
            lg.setLevel(before[n])
