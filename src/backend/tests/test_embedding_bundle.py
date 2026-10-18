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
