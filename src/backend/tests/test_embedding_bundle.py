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


import hashlib

sys.path.insert(0, str(BACKEND_DIR / "scripts"))
import download_models  # noqa: E402
from modules import embeddings as emb  # noqa: E402


def _fake_snapshot(payload: bytes, calls: list):
    def _fake(*, repo_id, revision, local_dir, allow_patterns):
        calls.append({"repo_id": repo_id, "revision": revision, "allow_patterns": list(allow_patterns)})
        root = Path(local_dir)
        for name in allow_patterns:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload if name == "model.safetensors" else b"{}")
        return str(root)
    return _fake


def test_hc_emb_004a_fetch_rejects_checksum_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(b"not the pinned weights", []))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    with pytest.raises(SystemExit) as info:
        download_models.cmd_embedding(target)
    assert info.value.code == 1
    assert not target.exists()
    assert not target.with_name(target.name + ".partial").exists()


def test_hc_emb_004b_fetch_installs_pinned_files_only(tmp_path, monkeypatch):
    payload = b"pinned-weights-stand-in"
    monkeypatch.setattr(emb, "EMBEDDING_WEIGHTS_SHA256", hashlib.sha256(payload).hexdigest())
    calls: list = []
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(payload, calls))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    download_models.cmd_embedding(target)
    assert calls == [{
        "repo_id": emb.EMBEDDING_REPO_ID,
        "revision": emb.EMBEDDING_REVISION,
        "allow_patterns": list(emb.EMBEDDING_FILES),
    }]
    installed = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert installed == sorted(emb.EMBEDDING_FILES)
    assert not target.with_name(target.name + ".partial").exists()


def test_hc_emb_004c_existing_incomplete_target_is_never_deleted(tmp_path, monkeypatch):
    calls: list = []
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(b"x", calls))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    target.mkdir(parents=True)
    keep = target / "user-file.txt"
    keep.write_text("do not delete")
    with pytest.raises(SystemExit) as info:
        download_models.cmd_embedding(target)
    assert info.value.code == 1
    assert keep.read_text() == "do not delete"
    assert calls == []


def test_hc_emb_004d_existing_partial_is_never_deleted(tmp_path, monkeypatch):
    calls: list = []
    monkeypatch.setattr("huggingface_hub.snapshot_download", _fake_snapshot(b"x", calls))
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    partial = target.with_name(target.name + ".partial")
    partial.mkdir(parents=True)
    keep = partial / "someone-elses-file.bin"
    keep.write_bytes(b"do not delete")
    with pytest.raises(SystemExit) as info:
        download_models.cmd_embedding(target)
    assert info.value.code == 1
    assert keep.read_bytes() == b"do not delete"
    assert not target.exists()
    assert calls == []


def test_hc_emb_004e_failed_fetch_removes_only_this_runs_partial(tmp_path, monkeypatch):
    def _failing_download(*, repo_id, revision, local_dir, allow_patterns):
        (Path(local_dir) / "config.json").write_bytes(b"{}")  # a half-written fetch
        raise OSError("simulated network drop")

    monkeypatch.setattr("huggingface_hub.snapshot_download", _failing_download)
    target = tmp_path / "embeddings" / "all-MiniLM-L6-v2"
    partial = target.with_name(target.name + ".partial")
    with pytest.raises(OSError, match="simulated network drop"):
        download_models.cmd_embedding(target)
    assert not partial.exists(), "a failed fetch left its .partial behind and would block the next run"
    assert not target.exists()
    # The pre-existing-.partial case (never deleted) is HC-EMB-004d.


def test_hc_emb_002_fetched_model_loads_offline(tmp_path):
    from modules.embeddings import EMBEDDING_FILES, resolve_embedding_model_dir

    model_dir = resolve_embedding_model_dir()
    if not all((model_dir / name).is_file() for name in EMBEDDING_FILES):
        pytest.fail(
            f"embedding model not installed at {model_dir}; run: "
            "cd src/backend && python scripts/download_models.py embedding"
        )
    out = _run_probe(tmp_path, model_dir)
    assert out["result"] == "loaded" and out["model_loaded"] is True, out
    assert out["dims"] == 384
    assert out["similarity"] > 0.7  # same bar as test_api_rag_index_002b; never lowered
    assert out["attempts"] == [], f"network attempted: {out['attempts']}"
    assert out["hf_cache_files"] == []
