"""HC-LHH-001/002 — LOCAL-HF-HUB: embeddings never reach the Hugging Face Hub.

Both tests run in a fresh interpreter with HF_HUB_OFFLINE and TRANSFORMERS_OFFLINE
removed from the environment. The suite is normally run under HF_HUB_OFFLINE=1,
and huggingface_hub reads that flag at import: left in place, these tests would
pass on a tree that still resolves the bare model name online (recurring
failure #1/#4). HF_HOME points at an empty directory so no cache can satisfy a
load.

The guard patches socket *methods* and records every non-loopback attempt (a
library may swallow the OSError, so refusing alone is not evidence).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("sentence_transformers")

BACKEND_DIR = Path(__file__).resolve().parents[1]

_GUARD = r'''
import json, socket
attempts = []
_LOOPBACK = {"127.0.0.1", "::1", "localhost", None, ""}

def _record(target):
    host = target[0] if isinstance(target, tuple) and target else target
    if isinstance(host, bytes):
        host = host.decode()
    if isinstance(host, str) and host not in _LOOPBACK and not host.startswith("127."):
        attempts.append(str(host))
        raise OSError("non-loopback network blocked by HC-LHH guard")

_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
_getaddrinfo = socket.getaddrinfo

def _guard_connect(self, address):
    _record(address)
    return _connect(self, address)

def _guard_connect_ex(self, address):
    _record(address)
    return _connect_ex(self, address)

def _guard_getaddrinfo(host, *args, **kwargs):
    _record((host,))
    return _getaddrinfo(host, *args, **kwargs)

socket.socket.connect = _guard_connect
socket.socket.connect_ex = _guard_connect_ex
socket.getaddrinfo = _guard_getaddrinfo
'''

_LOAD = _GUARD + r'''
from modules.embeddings import EmbeddingsModule

try:
    EmbeddingsModule()._ensure_initialized()
    outcome = "initialized"
except Exception as exc:  # fail-closed is fine here; only the network matters
    outcome = type(exc).__name__
print("HC_LHH_RESULT=" + json.dumps({"outcome": outcome, "attempts": attempts}))
'''

_STARTUP = _GUARD + r'''
import main
from fastapi.testclient import TestClient

with TestClient(main.app):
    pass
print("HC_LHH_RESULT=" + json.dumps({"outcome": "started", "attempts": attempts}))
'''


def _run(script: str, tmp_path: Path) -> dict:
    hf_home = tmp_path / "hf-empty"
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("HF_", "TRANSFORMERS_", "SENTENCE_TRANSFORMERS_", "EMBEDDING_MODEL_PATH"))
    }
    env.update(
        HF_HOME=str(hf_home),
        EMBEDDING_MODEL_PATH=str(tmp_path / "absent-model"),
        PYTHONPATH=str(BACKEND_DIR),
        TEST_MODE="1",
        DATABASE_ENCRYPTION_REQUIRED="false",
        APP_MODE="server",
        SQLITE_DATABASE_PATH=str(tmp_path / "data" / "lhh.db"),
    )
    (tmp_path / "data").mkdir()
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("HC_LHH_RESULT=")]
    assert proc.returncode == 0 and lines, f"probe crashed:\n{proc.stderr[-3000:]}"
    return json.loads(lines[-1].split("=", 1)[1])


def test_hc_lhh_001_first_embedding_load_makes_no_hub_request(tmp_path):
    out = _run(_LOAD, tmp_path)
    assert out["attempts"] == [], f"embedding load contacted a non-loopback host: {out['attempts']}"


def test_hc_lhh_002_app_startup_makes_no_hub_request(tmp_path):
    out = _run(_STARTUP, tmp_path)
    assert out["attempts"] == [], f"app startup contacted a non-loopback host: {out['attempts']}"
