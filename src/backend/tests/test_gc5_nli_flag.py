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
import json, socket
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
    out["hf_cache_files"] = [str(p) for p in hf_home.rglob("*") if p.is_file()] if hf_home.exists() else []
    return out


def test_hc_gc5_003_offline_load_opens_zero_sockets(tmp_path):
    model_dir = _build_stand_in_nli(tmp_path / "nli-stand-in")
    out = _run_nli_probe(tmp_path, model_dir)
    assert out["attempts"] == []
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
