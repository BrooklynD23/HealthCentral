"""HC-OCR-001..021 -- RAPIDOCR-BUNDLE: scanned pages are read locally by RapidOCR.

Medical data path. Every fixture here is synthetic (PIL ImageFont.load_default,
no real patient data) and drawn on the column and ruled-grid layouts of the
RAPIDOCR-RESEARCH report (docs/research/2026-10-22-rapidocr).

Tests that need the engine call ``pytest.importorskip("rapidocr")`` inside the
test, never at module level, so the collected count is the same in an
environment without the OCR packages. A skip is not a pass: the engine tests
must be run in the OCR venv before claiming them.

The subprocess tests (001-003) follow test_embedding_no_network.py HC-LHH-001:
a fresh interpreter, a guard that patches socket.connect / connect_ex /
getaddrinfo, RECORDS every non-loopback attempt and REFUSES it, and a HOME that
is an empty directory.

The Python guard cannot see a native library that opens its own socket.
onnxruntime 1.31.0 ships a Microsoft telemetry client (static libcurl) that
does exactly that, so 001 also waits and then reads the process's real sockets
from /proc (``_native_remote_peers``). The product opts out with
ORT_DISABLE_TELEMETRY=1 before the first onnxruntime import; 001 and 003 prove
the product sets it (the probe strips any inherited ORT_* variable), and 002
alone passes it in by hand because it builds RapidOCR itself.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import zlib
from contextlib import contextmanager
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import APIRouter
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import modules  # noqa: E402
from api import documents as documents_api  # noqa: E402
from api.documents import router as documents_router  # noqa: E402
from api.model_settings import router as model_settings_router  # noqa: E402
from core import config as cfg  # noqa: E402
from core.auth import get_profile_db_session  # noqa: E402
from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models import Observation, UserModelSettings  # noqa: E402
from modules import extract  # noqa: E402
from modules.extract import ExtractModule  # noqa: E402
from modules.ingest import ImportResult  # noqa: E402
from tests.support.routes import route_client  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]

# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

_FONT = ImageFont.load_default(size=28)  # scalable, no system font needed in CI

# analyte, value text, unit, reference range
_ROWS = [
    ("Glucose", "95", "mg/dL", "70-100"),
    ("Creatinine", "1.1", "mg/dL", "0.6-1.3"),
    ("Sodium", "140", "mmol/L", "136-145"),
    ("Potassium", "4.2", "mmol/L", "3.5-5.1"),
    ("Hemoglobin", "13.5", "g/dL", "12.0-17.0"),
    ("HbA1c", "5.4", "%", "4.0-5.6"),
]
_TRUTH = {(a.lower(), float(v), u) for a, v, u, _ in _ROWS}

# Measured in the OCR venv on the column fixture (RapidOCR 3.10.0, 1 thread):
# 5 of 6 rows found, all 5 correct. Hemoglobin's unit is read "7p/6", so that
# row is missing -- missing, not wrong. NEVER lower this number to make a run
# pass: a drop means the engine or the page reading got worse.
_FOUND_FLOOR = 5


def _column_page(rows=_ROWS) -> Image.Image:
    im = Image.new("L", (1700, 200 + 56 * len(rows) + 100), 255)
    dr = ImageDraw.Draw(im)
    dr.text((100, 50), "Collected: 03/14/2025", font=_FONT, fill=0)
    xs = [100, 600, 800, 1000]
    for x, head in zip(xs, ["Test", "Result", "Units", "Range"]):
        dr.text((x, 120), head, font=_FONT, fill=0)
    for k, row in enumerate(rows):
        for x, text in zip(xs, row):
            dr.text((x, 180 + k * 56), text, font=_FONT, fill=0)
    return im


def _grid_page(rows=_ROWS) -> Image.Image:
    row_h, y0 = 62, 120
    im = Image.new("L", (1700, y0 + (len(rows) + 2) * row_h + 60), 255)
    dr = ImageDraw.Draw(im)
    dr.text((100, 50), "Collected: 03/14/2025", font=_FONT, fill=0)
    cols = [100, 560, 860, 1160, 1600]
    for k in range(len(rows) + 2):
        dr.line([(cols[0], y0 + k * row_h), (cols[-1], y0 + k * row_h)], fill=0, width=2)
    for c in cols:
        dr.line([(c, y0), (c, y0 + (len(rows) + 1) * row_h)], fill=0, width=2)
    for c, head in zip(cols, ["Test", "Result", "Units", "Range"]):
        dr.text((c + 12, y0 + 14), head, font=_FONT, fill=0)
    for k, row in enumerate(rows):
        for c, text in zip(cols, row):
            dr.text((c + 12, y0 + (k + 1) * row_h + 14), text, font=_FONT, fill=0)
    return im


def _png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _build_pdf(pages: list) -> bytes:
    """Raw-bytes PDF. A page is ``("text", lines)`` (a Helvetica text layer on a
    letter page) or ``("image", PIL image)`` (one picture and no text layer,
    lossless Flate pixels, media box sized so a 200 dpi render gives back the
    original pixels)."""

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    n = len(pages)
    kids = " ".join(f"{3 + i} 0 R" for i in range(n))
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
    ]
    first_extra = 3 + n  # page objects are 3..2+n; content/resource objects follow
    extras: list[bytes] = []
    for i, (kind, payload) in enumerate(pages):
        content_no = first_extra + len(extras)
        if kind == "text":
            ops = ["BT", "/F1 11 Tf", "14 TL", "50 740 Td"]
            ops += [f"({esc(line)}) Tj T*" for line in payload]
            ops.append("ET")
            stream = "\n".join(ops).encode("latin-1")
            font_no = content_no + 1
            objs.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_no} 0 R >> >> /Contents {content_no} 0 R >>".encode()
            )
            extras.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
            extras.append(
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
            )
        else:
            # 0.002 pt under the exact size: pypdfium2 rounds a page size up to whole
            # pixels (float32 228.96 -> 637 px for a 636 px image), and that 1 px
            # resample alone turned Glucose 95 into 96 at full confidence. The
            # fixture must be pixel-exact; real scans are not (see the PR).
            width_pt, height_pt = payload.width * 72 / 200 - 0.002, payload.height * 72 / 200 - 0.002
            stream = f"q {width_pt:.4f} 0 0 {height_pt:.4f} 0 0 cm /Im1 Do Q".encode("latin-1")
            pixels = zlib.compress(payload.convert("L").tobytes())
            image_no = content_no + 1
            objs.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width_pt:.4f} {height_pt:.4f}] "
                f"/Resources << /XObject << /Im1 {image_no} 0 R >> >> /Contents {content_no} 0 R >>".encode()
            )
            extras.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
            extras.append(
                f"<< /Type /XObject /Subtype /Image /Width {payload.width} /Height {payload.height} "
                f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
                f"/Length {len(pixels)} >>\nstream\n".encode() + pixels + b"\nendstream"
            )
    objs += extras
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    out.write("".join(f"{o:010d} 00000 n \n" for o in offsets).encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def _image_only_pdf(*images: Image.Image) -> bytes:
    """A PDF whose pages are pictures and have no text layer."""
    return _build_pdf([("image", im) for im in images])


def _text_then_scanned_pdf(text_lines: list[str], page2: Image.Image) -> bytes:
    """Two-page PDF: page 1 has a text layer, page 2 is only ``page2`` as a picture."""
    return _build_pdf([("text", text_lines), ("image", page2)])


_MIXED_TEXT_LINES = [
    "Patient: Jane Test  DOB: 1970-01-01  Collected: 03/02/2026",
    "Glucose: 95 mg/dL (70-100)",
    "Creatinine: 1.1 mg/dL (0.7-1.3)",
    "Sodium: 140 mmol/L (135-145)",
]


def _mixed_pdf() -> bytes:
    """Page 1 has a text layer; page 2 is only a picture holding one HbA1c row."""
    return _text_then_scanned_pdf(
        _MIXED_TEXT_LINES, _column_page([("HbA1c", "9.1", "%", "4.0-5.6")])
    )


def _triples(observations) -> list[tuple[str, float | None, str | None]]:
    return [(o.analyte_raw.strip().lower(), o.value, o.unit) for o in observations]


def _assert_no_wrong_value(observations) -> None:
    wrong = [t for t in _triples(observations) if t not in _TRUTH]
    assert wrong == [], f"OCR produced values that are not in the truth set: {wrong}"


def _no_tesseract(monkeypatch) -> None:
    monkeypatch.setattr(cfg, "is_tesseract_on_path", lambda: False)


def _ocr_on(monkeypatch) -> None:
    monkeypatch.setattr(cfg.settings, "ocr_enabled", True)


async def _patient_opted_in(profile_db) -> None:
    """The patient has switched OCR on (OCR-DEFAULT-ON: a profile now starts with it off)."""
    profile_db.add(UserModelSettings(profile_id="profile-a", ocr_preference_enabled=True))
    await profile_db.commit()


# ---------------------------------------------------------------------------
# Native socket check (the Python guard cannot see libcurl inside a wheel)
# ---------------------------------------------------------------------------

def _socket_inodes() -> set:
    """Inodes of every socket this process holds open, native ones included."""
    found = set()
    for fd in os.listdir("/proc/self/fd"):
        try:
            target = os.readlink("/proc/self/fd/" + fd)
        except OSError:
            continue
        if target.startswith("socket:["):
            found.add(target[len("socket:["):-1])
    return found


def _native_remote_peers(inodes, net_dir="/proc/net") -> list:
    """Non-loopback remote endpoints of the given socket inodes (tcp, tcp6, udp, udp6)."""
    import ipaddress

    peers = []
    for table in ("tcp", "tcp6", "udp", "udp6"):
        try:
            with open(net_dir + "/" + table) as handle:
                lines = handle.read().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            cols = line.split()
            if len(cols) < 10 or cols[9] not in inodes:
                continue
            raw, port = cols[2].split(":")
            data = bytes.fromhex(raw)
            if len(data) == 4:
                data = data[::-1]
            else:
                data = b"".join(data[i:i + 4][::-1] for i in range(0, 16, 4))
            ip = ipaddress.ip_address(data)
            ip = getattr(ip, "ipv4_mapped", None) or ip
            if not ip.is_unspecified and not ip.is_loopback:
                peers.append(table + ":" + str(ip) + ":" + str(int(port, 16)))
    return peers


def _watch_native_peers(stop, seen, interval=0.2, inodes=_socket_inodes, net_dir="/proc/net") -> None:
    """Poll until ``stop`` (a threading.Event) is set, adding every remote peer to ``seen``.

    One /proc snapshot misses a connection that opens and closes between two looks
    (a closed socket keeps no fd and shows as inode 0), so keep the union.
    """
    while True:
        seen.update(_native_remote_peers(inodes(), net_dir))
        if stop.wait(interval):
            return


# ---------------------------------------------------------------------------
# Subprocess guard (HC-LHH-001 pattern)
# ---------------------------------------------------------------------------

_GUARD = r'''
import json, os, shutil, socket
attempts = []
_LOOPBACK = {"127.0.0.1", "::1", "localhost", None, ""}

def _record(target):
    host = target[0] if isinstance(target, tuple) and target else target
    if isinstance(host, bytes):
        host = host.decode()
    if isinstance(host, str) and host not in _LOOPBACK and not host.startswith("127."):
        attempts.append(str(host))
        raise OSError("non-loopback network blocked by HC-OCR guard")

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

# Tesseract absent and OCR switched on, as on a launcher machine without Tesseract.
_OCR_ON_NO_TESSERACT = r'''
shutil.which = lambda *args, **kwargs: None
from core.config import settings
settings.ocr_enabled = True
'''


# The native-socket check (and the probes that share its machinery) read /proc/self/fd,
# which exists on Linux only. Windows ETW and macOS are not covered (RDB-L1/L2).
_NEEDS_PROC_FD = pytest.mark.skipif(
    not Path("/proc/self/fd").exists(),
    reason="reads /proc/self/fd; the native-socket check runs on Linux only",
)


def _run_probe(body: str, tmp_path: Path, **extra_env: str) -> tuple[dict, Path]:
    """Run ``body`` in a fresh interpreter under the guard; return (result, empty HOME)."""
    home = tmp_path / "home-empty"
    home.mkdir()
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("HF_", "TRANSFORMERS_", "XDG_", "HOME", "USERPROFILE", "ORT_"))
    }
    env.update(
        HOME=str(home),
        XDG_CACHE_HOME=str(home / "cache"),
        USERPROFILE=str(home),
        PYTHONPATH=str(BACKEND_DIR),
        PYTHONDONTWRITEBYTECODE="1",
        TEST_MODE="1",
        DATABASE_ENCRYPTION_REQUIRED="false",
        APP_MODE="server",
        SQLITE_DATABASE_PATH=str(tmp_path / "ocr.db"),
        **extra_env,
    )
    proc = subprocess.run(
        [sys.executable, "-c", _GUARD + body],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=600,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("HC_OCR_RESULT=")]
    assert proc.returncode == 0 and lines, f"probe crashed (exit {proc.returncode}):\n{proc.stderr[-3000:]}"
    return json.loads(lines[-1].split("=", 1)[1]), home


# ---------------------------------------------------------------------------
# Route harness (same shape as HC-ISP-002 in test_documents_api.py)
# ---------------------------------------------------------------------------

class _CommitTrackingMasterDb:
    def __init__(self) -> None:
        self.added: list = []
        self.commit_snapshots: list[int] = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commit_snapshots.append(len(self.added))


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _stub_vault(monkeypatch, tmp_path) -> None:
    """Replace the encrypted vault with an in-memory one; extraction and doc-type detection stay real."""
    from modules.ingest import IngestModule as RealIngest

    stored: dict[str, bytes] = {}
    classifier = RealIngest(vault_path=tmp_path / "classify", encryption_key=b"x" * 32)

    class _Ingest:
        def __init__(self, *_args, **_kwargs):
            pass

        async def import_document(self, *, file, filename, **_kwargs):
            payload = file.read()
            doc_id = str(uuid.uuid4())
            stored[doc_id] = payload
            return ImportResult(
                document_id=doc_id,
                path_hash=hashlib.sha256(doc_id.encode()).hexdigest(),
                content_hash=hashlib.sha256(payload).hexdigest(),
                doc_type=classifier.detect_doc_type(filename, payload),
                page_count=1,
                is_duplicate=False,
                metadata={},
                encrypted=True,
            )

    async def _no_classify(**_kwargs):
        return None

    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
    monkeypatch.setattr(modules, "IngestModule", _Ingest)
    monkeypatch.setattr(
        documents_api, "get_decrypted_document", lambda _pid, doc_id: io.BytesIO(stored[doc_id])
    )
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", _no_classify)


def _import_over_http(profile_db, monkeypatch, tmp_path, filename: str, data: bytes):
    """POST ``data`` to /documents/import with the real extractor and real doc-type detection."""
    _stub_vault(monkeypatch, tmp_path)

    master = _CommitTrackingMasterDb()
    with route_client(
        documents_router, "/documents", profile_id="profile-a", master_db=master
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        response = client.post(
            "/documents/import", files={"file": (filename, data, "application/pdf")}
        )
    return response, master


@contextmanager
def _patient_client(profile_db, monkeypatch, tmp_path):
    """One HTTP client for the documents and settings routes of ONE profile, sharing one vault DB."""
    _stub_vault(monkeypatch, tmp_path)
    router = APIRouter()
    router.include_router(documents_router, prefix="/documents")
    router.include_router(model_settings_router, prefix="/settings/model")

    with route_client(
        router, "", profile_id="profile-a", master_db=_CommitTrackingMasterDb()
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        yield client


# ---------------------------------------------------------------------------
# HC-OCR-001 .. 003: nothing leaves the machine
# ---------------------------------------------------------------------------

@_NEEDS_PROC_FD
def test_hc_ocr_001_scanned_image_is_read_with_no_network(tmp_path):
    pytest.importorskip("rapidocr")
    png = tmp_path / "page.png"
    png.write_bytes(_png(_column_page()))
    body = (
        "import inspect, threading, time\n"
        + inspect.getsource(_socket_inodes)
        + inspect.getsource(_native_remote_peers)
        + inspect.getsource(_watch_native_peers)
        + r'''
import asyncio
from pathlib import Path
''' + _OCR_ON_NO_TESSERACT + r'''
from modules import extract
# Watch the real sockets (/proc) from before the first onnxruntime import until well past
# the point where its telemetry client uploads (a native thread, about 9 s after the
# session is created). Polling keeps the union, so a connection that opens and closes
# in between is still seen.
seen, stop = set(), threading.Event()
watcher = threading.Thread(target=_watch_native_peers, args=(stop, seen))
watcher.start()
result = asyncio.run(
    extract.ExtractModule().extract_from_image(Path(os.environ["HC_OCR_PNG"]), "doc", effective_ocr=True)
)
time.sleep(15)
stop.set()
watcher.join()
seen.update(_native_remote_peers(_socket_inodes()))
print("HC_OCR_RESULT=" + json.dumps({
    "n": len(result.observations), "unavailable": result.ocr_unavailable, "attempts": attempts,
    "native_peers": sorted(seen),
    "ort_env": os.environ.get("ORT_DISABLE_TELEMETRY"),
}))
'''
    )
    out, home = _run_probe(body, tmp_path, HC_OCR_PNG=str(png))
    assert out["unavailable"] is False, out
    assert out["n"] >= 1, out
    assert out["attempts"] == [], f"OCR contacted a non-loopback host: {out['attempts']}"
    assert out["native_peers"] == [], f"a native library opened a non-loopback socket: {out['native_peers']}"
    assert out["ort_env"] == "1", "the product must opt out of onnxruntime telemetry itself"
    # The temp home is still empty afterwards (spec row HC-OCR-001): no model download,
    # no cache of page text, and no Microsoft/DeveloperTools telemetry queue or device id.
    written = sorted(str(p.relative_to(home)) for p in home.rglob("*"))
    assert written == [], f"OCR wrote into HOME: {written}"


def test_hc_ocr_002_guard_sees_rapidocr_download_path(tmp_path):
    """Positive control for 001: without the model pins, RapidOCR's own download
    branch is reachable, and this guard records it and refuses it."""
    pytest.importorskip("rapidocr")
    empty_models = tmp_path / "models-empty"
    empty_models.mkdir()
    body = r'''
import numpy as np
from rapidocr import RapidOCR
root = os.environ["HC_OCR_ROOT"]
try:
    RapidOCR(params={"Global.model_root_dir": root})(np.full((64, 200, 3), 255, np.uint8))
    outcome = "ok"
except Exception as exc:
    outcome = type(exc).__name__
print("HC_OCR_RESULT=" + json.dumps({
    "outcome": outcome, "attempts": attempts, "entries": sorted(os.listdir(root)),
}))
'''
    # Builds RapidOCR itself, bypassing the product's telemetry opt-out, so it passes
    # the opt-out by hand; 001 and 003 are the tests that prove the product sets it.
    out, _home = _run_probe(
        body, tmp_path, HC_OCR_ROOT=str(empty_models), ORT_DISABLE_TELEMETRY="1"
    )
    assert any(a.endswith("modelscope.cn") for a in out["attempts"]), out
    assert out["outcome"] != "ok", out
    assert out["entries"] == [], f"a refused download left files behind: {out['entries']}"


def test_hc_ocr_003_bad_model_file_fails_closed(tmp_path):
    rapidocr = pytest.importorskip("rapidocr")
    wheel_models = Path(rapidocr.__file__).parent / "models"
    bad = tmp_path / "models-bad"
    bad.mkdir()
    for model in wheel_models.glob("*.onnx"):
        shutil.copy(model, bad / model.name)
    good = tmp_path / "models-good"  # an intact copy somewhere else: the pins must point here
    shutil.copytree(bad, good)
    rec = bad / "PP-OCRv6_rec_small.onnx"
    raw = bytearray(rec.read_bytes())
    raw[1000] ^= 0xFF  # one flipped byte
    rec.write_bytes(bytes(raw))
    png = tmp_path / "page.png"
    png.write_bytes(_png(_column_page()))

    body = r'''
import asyncio
from pathlib import Path
''' + _OCR_ON_NO_TESSERACT + r'''
from modules import extract
extract._rapidocr_model_dir = lambda: Path(os.environ["HC_OCR_BAD_MODELS"])
ready = extract.rapidocr_ready()
result = asyncio.run(
    extract.ExtractModule().extract_from_image(Path(os.environ["HC_OCR_PNG"]), "doc", effective_ocr=True)
)
# control: same process, intact files in another directory -> ready, and the engine
# is pinned to THOSE files (without the pins RapidOCR would use its own default dir)
extract._rapidocr_engine.cache_clear()
extract._rapidocr_model_dir = lambda: Path(os.environ["HC_OCR_GOOD_MODELS"])
control_ready = extract.rapidocr_ready()
engine = extract._rapidocr_engine()
pinned = [str(engine.cfg.Det.model_path), str(engine.cfg.Rec.model_path), str(engine.cfg.Cls.model_path)]
print("HC_OCR_RESULT=" + json.dumps({
    "ready": ready, "control_ready": control_ready, "unavailable": result.ocr_unavailable,
    "n": len(result.observations), "attempts": attempts, "pinned": pinned,
}))
'''
    out, _home = _run_probe(
        body, tmp_path,
        HC_OCR_BAD_MODELS=str(bad), HC_OCR_GOOD_MODELS=str(good), HC_OCR_PNG=str(png),
    )
    assert out["ready"] is False, out
    assert out["unavailable"] is True and out["n"] == 0, out
    assert out["attempts"] == [], f"a bad model file triggered a network attempt: {out['attempts']}"
    assert out["control_ready"] is True, out
    assert all(Path(p).parent == good for p in out["pinned"]), (
        f"model paths are not pinned to the verified directory: {out['pinned']}"
    )


# ---------------------------------------------------------------------------
# HC-OCR-004 .. 007: reading pages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_ocr_004_image_only_pdf_is_read_without_tesseract(monkeypatch):
    pytest.importorskip("rapidocr")
    _ocr_on(monkeypatch)
    _no_tesseract(monkeypatch)

    def _poppler_must_not_run(*_args, **_kwargs):
        raise AssertionError("pdf2image was used on the RapidOCR path")

    monkeypatch.setattr("pdf2image.convert_from_bytes", _poppler_must_not_run)

    pdf = _image_only_pdf(_column_page())
    result = await ExtractModule().extract_from_scanned_pdf(io.BytesIO(pdf), "doc", effective_ocr=True)

    assert result.ocr_unavailable is False
    _assert_no_wrong_value(result.observations)
    assert len(result.observations) >= _FOUND_FLOOR, _triples(result.observations)
    assert {o.extraction_method for o in result.observations} == {"ocr_pdf"}
    assert all(o.confidence <= 0.7 for o in result.observations)


@pytest.mark.asyncio
async def test_hc_ocr_005_image_is_read_without_tesseract(monkeypatch):
    pytest.importorskip("rapidocr")
    _ocr_on(monkeypatch)
    _no_tesseract(monkeypatch)

    result = await ExtractModule().extract_from_image(
        io.BytesIO(_png(_column_page())), "doc", effective_ocr=True
    )

    assert result.ocr_unavailable is False
    _assert_no_wrong_value(result.observations)
    assert len(result.observations) >= _FOUND_FLOOR, _triples(result.observations)
    assert {o.extraction_method for o in result.observations} == {"ocr_image"}
    assert all(o.confidence <= 0.7 for o in result.observations)


@pytest.mark.asyncio
async def test_hc_ocr_006_scanned_pdf_import_is_parsed_not_pending(profile_db, monkeypatch, tmp_path):
    """Route level: OCR on, Tesseract absent, RapidOCR present -> parsed, rows unverified."""
    pytest.importorskip("rapidocr")
    import json as _json

    await _patient_opted_in(profile_db)
    _ocr_on(monkeypatch)
    _no_tesseract(monkeypatch)

    response, master = _import_over_http(
        profile_db, monkeypatch, tmp_path, "scan.pdf", _image_only_pdf(_column_page())
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["document"]["status"] == "parsed", body["document"]
    assert body["observations_extracted"] >= _FOUND_FLOOR, body

    rows = (await profile_db.execute(select(Observation))).scalars().all()
    assert len(rows) == body["observations_extracted"]
    assert rows and all(r.user_verified is False for r in rows), [r.user_verified for r in rows]

    import_rows = [
        o for o in master.added
        if type(o).__name__ == "AuditLog"
        and o.details_json
        and _json.loads(o.details_json).get("doc_type") == "lab_pdf_scanned"
    ]
    assert len(import_rows) == 1, [type(o).__name__ for o in master.added]
    assert master.commit_snapshots and master.commit_snapshots[-1] >= 1

    # The patient's OCR switch reaches a mixed PDF too: api/documents.py passes
    # ocr_pages=ocr_effective. Only the route can see that kwarg (007 calls the module).
    response, _master = _import_over_http(
        profile_db, monkeypatch, tmp_path, "mixed.pdf", _mixed_pdf()
    )
    assert response.status_code == 201, response.text
    assert response.json()["pages_without_text"] in ([], None), response.json()
    mixed_rows = (
        await profile_db.execute(
            select(Observation).where(Observation.doc_id == response.json()["document"]["id"])
        )
    ).scalars().all()
    page2 = [o for o in mixed_rows if o.source_page == 2]
    assert [(o.analyte_raw.lower(), o.value) for o in page2] == [("hba1c", 9.1)], page2
    assert page2[0].user_verified is False and page2[0].extraction_confidence <= 0.7
    assert len([o for o in mixed_rows if o.source_page == 1]) == 3


@pytest.mark.asyncio
async def test_hc_ocr_007_mixed_pdf_reads_only_the_image_page_when_asked(monkeypatch):
    pytest.importorskip("rapidocr")
    _ocr_on(monkeypatch)
    _no_tesseract(monkeypatch)
    text_lines = _MIXED_TEXT_LINES
    pdf = _mixed_pdf()

    with_ocr = await ExtractModule().extract_from_pdf(io.BytesIO(pdf), "doc", ocr_pages=True)
    page2 = [o for o in with_ocr.observations if o.provenance and o.provenance.page == 2]
    assert [(o.analyte_raw.lower(), o.value) for o in page2] == [("hba1c", 9.1)], _triples(page2)
    assert page2[0].extraction_method == "ocr_pdf" and page2[0].confidence <= 0.7
    assert with_ocr.pages_without_text == []
    page1 = [o for o in with_ocr.observations if o.provenance and o.provenance.page == 1]
    assert len(page1) == 3 and {o.extraction_method for o in page1} == {"pdf_text"}

    default = await ExtractModule().extract_from_pdf(io.BytesIO(pdf), "doc")
    assert default.pages_without_text == [2]
    assert [o for o in default.observations if o.provenance and o.provenance.page == 2] == []

    blank = _text_then_scanned_pdf(text_lines, Image.new("L", (1700, 400), 255))
    unreadable = await ExtractModule().extract_from_pdf(io.BytesIO(blank), "doc", ocr_pages=True)
    assert unreadable.pages_without_text == [2]


# ---------------------------------------------------------------------------
# HC-OCR-008 / 009: configuration
# ---------------------------------------------------------------------------

def test_hc_ocr_008_rapidocr_alone_is_an_ocr_engine(monkeypatch, tmp_path):
    from unittest.mock import patch

    (tmp_path / "models").mkdir()  # so validate_startup has no unrelated warning to make

    monkeypatch.setattr("shutil.which", lambda *_a, **_k: None)

    with patch("modules.extract.rapidocr_ready", return_value=True):
        settings = cfg.Settings(
            app_env="development", ocr_enabled=True, jwt_secret="test-secret",
            models_path=str(tmp_path / "models"),
        )
        warnings = settings.validate_startup()
        assert not any("OCR enabled" in w or "tesseract" in w.lower() for w in warnings), warnings
        assert settings.ocr_enabled is True

        monkeypatch.setattr(cfg.settings, "ocr_enabled", True)
        assert cfg.is_ocr_available() is True
        assert cfg.compute_ocr_effective(True) == (True, [])

    with patch("modules.extract.rapidocr_ready", return_value=False):
        settings = cfg.Settings(
            app_env="development", ocr_enabled=True, jwt_secret="test-secret",
            models_path=str(tmp_path / "models"),
        )
        warnings = settings.validate_startup()
        assert any("tesseract" in w.lower() for w in warnings), warnings
        assert settings.ocr_enabled is False
        monkeypatch.setattr(cfg.settings, "ocr_enabled", True)
        assert cfg.is_ocr_available() is False
        effective, blockers = cfg.compute_ocr_effective(True)
        assert effective is False and "tesseract_missing" in blockers

    # OCR switched off by the admin: nothing is built, "an engine is installed" is judged
    # from the packages alone. rapidocr without onnxruntime (an Intel Mac install) is no engine.
    import importlib.util as util

    real_find_spec = util.find_spec

    def installed(*names):
        return lambda name, *a, **k: object() if name in names else real_find_spec(name, *a, **k)

    monkeypatch.setattr(cfg.settings, "ocr_enabled", False)
    monkeypatch.setattr(util, "find_spec", installed("rapidocr", "onnxruntime"))
    assert "tesseract_missing" not in cfg.compute_ocr_effective(True)[1]
    monkeypatch.setattr(util, "find_spec", lambda name, *a, **k: None if name == "onnxruntime" else installed("rapidocr")(name, *a, **k))
    assert "tesseract_missing" in cfg.compute_ocr_effective(True)[1]


@pytest.mark.asyncio
async def test_hc_ocr_009_default_off_pin(profile_db, monkeypatch, tmp_path):
    """GREEN before and after: shipping an engine does not switch OCR on."""
    from unittest.mock import patch

    assert cfg.Settings.model_fields["ocr_enabled"].default is False
    # The patient has opted in, so only the admin switch can hold the import at pending_ocr.
    await _patient_opted_in(profile_db)
    monkeypatch.setattr(cfg.settings, "ocr_enabled", False)  # the code default
    _no_tesseract(monkeypatch)

    with patch("modules.extract.rapidocr_ready", create=True, return_value=True):
        effective, blockers = cfg.compute_ocr_effective(True)
        assert effective is False and "disabled_by_admin" in blockers, blockers

        response, _master = _import_over_http(
            profile_db, monkeypatch, tmp_path, "scan.pdf", _image_only_pdf(_column_page())
        )
    assert response.status_code == 201, response.text
    assert response.json()["document"]["status"] == "pending_ocr", response.json()["document"]
    assert response.json()["observations_extracted"] == 0

    # Same switch on a mixed PDF: OCR off must leave the picture page unread and say so.
    # The spy would hand back a readable HbA1c row for page 2, so only the OCR call itself
    # can put that row in the database: it must never be made.
    ocr_calls = []

    def spy(pdf_bytes, page_numbers=None):
        ocr_calls.append(page_numbers)
        return {2: "HbA1c 9.1 % 4.0-5.6\nGlucose 95 mg/dL 70-100"}

    monkeypatch.setattr("modules.extract._ocr_pdf_pages", spy)
    with patch("modules.extract.rapidocr_ready", return_value=True):
        response, _master = _import_over_http(
            profile_db, monkeypatch, tmp_path, "mixed.pdf", _mixed_pdf()
        )
    assert response.status_code == 201, response.text
    assert response.json()["pages_without_text"] == [2], response.json()
    mixed_rows = (
        await profile_db.execute(
            select(Observation).where(Observation.doc_id == response.json()["document"]["id"])
        )
    ).scalars().all()
    assert [o for o in mixed_rows if o.source_page == 2] == []
    assert len([o for o in mixed_rows if o.source_page == 1]) == 3
    assert ocr_calls == [], "OCR is off: no page may be sent to the OCR engine"


# ---------------------------------------------------------------------------
# HC-OCR-018 .. 021: OCR is the patient's choice (OCR-DEFAULT-ON)
# ---------------------------------------------------------------------------

_SCAN_TEXT = "Glucose 95 mg/dL 70-100\nCreatinine 1.1 mg/dL 0.6-1.3"


def _engine_present(monkeypatch) -> list:
    """Admin OCR on and an engine 'installed', without needing one. Returns the OCR-reader spy log."""
    _ocr_on(monkeypatch)
    monkeypatch.setattr(cfg, "_ocr_engine_available", lambda: True)
    monkeypatch.setattr(extract, "rapidocr_ready", lambda: True)
    reads: list = []

    def reader(image):
        reads.append(image.size)
        return _SCAN_TEXT

    monkeypatch.setattr(extract, "_ocr_image_text", reader)
    return reads


async def _settings_rows(profile_db) -> list:
    return list((await profile_db.execute(select(UserModelSettings))).scalars().all())


@pytest.mark.asyncio
async def test_hc_ocr_018_a_settings_row_made_by_another_write_does_not_turn_ocr_on(
    profile_db, monkeypatch, tmp_path
):
    """A tier save, a voice toggle or hardware detection creates the row; none of them is an OCR choice."""
    _engine_present(monkeypatch)

    with _patient_client(profile_db, monkeypatch, tmp_path) as client:
        voice = client.patch("/settings/model/voice", json={"voice_modal_seen": True})
        assert voice.status_code == 200, voice.text
        response = client.get("/settings/model")

    assert len(await _settings_rows(profile_db)) == 1
    assert response.status_code == 200, response.text
    assert response.json()["ocr_preference_enabled"] is False, response.json()
    assert response.json()["ocr_effective"] is False
    assert "user_disabled" in response.json()["ocr_blockers"]


@pytest.mark.asyncio
async def test_hc_ocr_019_no_settings_row_means_ocr_off_and_the_scan_waits(
    profile_db, monkeypatch, tmp_path
):
    reads = _engine_present(monkeypatch)

    with _patient_client(profile_db, monkeypatch, tmp_path) as client:
        response = client.get("/settings/model")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ocr_preference_enabled"] is False, body
        assert body["ocr_effective"] is False, body
        assert "user_disabled" in body["ocr_blockers"], body
        assert await _settings_rows(profile_db) == [], "reading the setting must not create a row"

        imported = client.post(
            "/documents/import",
            files={"file": ("scan.pdf", _image_only_pdf(_column_page()), "application/pdf")},
        )

    assert imported.status_code == 201, imported.text
    assert imported.json()["document"]["status"] == "pending_ocr", imported.json()["document"]
    assert imported.json()["observations_extracted"] == 0
    assert reads == [], "OCR was never switched on: no page may reach the OCR reader"
    assert (await profile_db.execute(select(Observation))).scalars().all() == []
    assert await _settings_rows(profile_db) == []


@pytest.mark.asyncio
async def test_hc_ocr_020_the_patient_opts_in_and_the_waiting_scan_is_read(
    profile_db, monkeypatch, tmp_path
):
    reads = _engine_present(monkeypatch)

    with _patient_client(profile_db, monkeypatch, tmp_path) as client:
        imported = client.post(
            "/documents/import",
            files={"file": ("scan.pdf", _image_only_pdf(_column_page()), "application/pdf")},
        )
        assert imported.status_code == 201, imported.text
        assert imported.json()["document"]["status"] == "pending_ocr", imported.json()["document"]
        doc_id = imported.json()["document"]["id"]
        assert reads == []

        opted = client.patch("/settings/model/ocr", json={"ocr_preference_enabled": True})
        assert opted.status_code == 200, opted.text
        assert opted.json()["ocr_preference_enabled"] is True, opted.json()
        assert opted.json()["ocr_effective"] is True, opted.json()
        assert opted.json()["ocr_blockers"] == [], opted.json()

        current = client.get("/settings/model").json()
        assert current["ocr_effective"] is True and current["ocr_blockers"] == [], current

        reprocessed = client.post(f"/documents/{doc_id}/reprocess")

    assert reprocessed.status_code == 200, reprocessed.text
    assert reprocessed.json()["document"]["status"] == "parsed", reprocessed.json()["document"]
    assert reprocessed.json()["observations_extracted"] == 2, reprocessed.json()
    assert reads, "the opted-in patient's scan must reach the OCR reader"

    rows = (await profile_db.execute(select(Observation))).scalars().all()
    assert len(rows) == 2
    assert all(r.user_verified is False for r in rows), [r.user_verified for r in rows]


_DEV_SH = REPO_ROOT / "dev.sh"
_DEV_PS1 = REPO_ROOT / "dev.ps1"


def _block(path: Path, opener: str, closer: str) -> str:
    """The text from the first line starting with ``opener`` to the first line that is exactly ``closer``."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(opener))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == closer)
    return "\n".join(lines[start : end + 1])


def _run_dev_sh_ocr_sync(tmp_path, *, tesseract: bool, probe_exit: int, skip: bool = False) -> dict:
    """Run dev.sh's real OCR sync block under bash with stubbed helpers and a stub venv python."""
    block = _block(_DEV_SH, 'if [ "${HC_SKIP_OCR_SETUP:-}" != "1" ]; then', "fi")
    backend = tmp_path / "backend"
    backend.mkdir(exist_ok=True)
    probe_log = tmp_path / "probe.log"
    calls = tmp_path / "calls.log"
    for log in (probe_log, calls):
        log.unlink(missing_ok=True)
    venv_py = tmp_path / "venv_python"
    venv_py.write_text('#!/bin/bash\npwd -P > "$PROBE_LOG"\nprintf "%s\\n" "$@" >> "$PROBE_LOG"\nexit "$PROBE_EXIT"\n')
    venv_py.chmod(0o755)
    script = (
        "set -euo pipefail\n"
        'ok() { echo "ok:$*" >> "$CALLS"; }\n'
        'warn() { echo "warn:$*" >> "$CALLS"; }\n'
        'set_env_key() { echo "set:$2=$3" >> "$CALLS"; }\n'
        + block
        + '\necho DONE >> "$CALLS"\n'
    )
    env = {
        k: v for k, v in os.environ.items() if k != "HC_SKIP_OCR_SETUP"
    } | {
        "BACKEND_DIR": str(backend),
        "ENV_FILE": str(tmp_path / ".env"),
        "VENV_PY": str(venv_py),
        "TESSERACT_OK": "1" if tesseract else "0",
        "PROBE_EXIT": str(probe_exit),
        "PROBE_LOG": str(probe_log),
        "CALLS": str(calls),
    }
    if skip:
        env["HC_SKIP_OCR_SETUP"] = "1"
    done = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, (done.stdout, done.stderr)
    lines = calls.read_text().splitlines()
    assert lines and lines[-1] == "DONE", lines
    probe = probe_log.read_text().splitlines() if probe_log.exists() else None
    return {"calls": lines[:-1], "probe": probe, "backend": str(backend.resolve())}


@pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="needs bash")
def test_hc_ocr_021_launchers_enable_ocr_when_the_bundled_engine_is_found(tmp_path):
    """dev.sh runs for real; dev.ps1 cannot run here, so only its text is checked."""
    # RapidOCR found, no Tesseract (the case the old launcher got wrong)
    got = _run_dev_sh_ocr_sync(tmp_path, tesseract=False, probe_exit=0)
    assert [c for c in got["calls"] if c.startswith("set:")] == ["set:OCR_ENABLED=true"], got
    assert any(c.startswith("ok:") and "RapidOCR" in c and "Tesseract" not in c for c in got["calls"]), got
    assert got["probe"][0] == got["backend"], "the probe must run from the backend directory"
    assert "rapidocr_ready" in "\n".join(got["probe"][1:]), got["probe"]

    # neither engine
    got = _run_dev_sh_ocr_sync(tmp_path, tesseract=False, probe_exit=1)
    assert [c for c in got["calls"] if c.startswith("set:")] == ["set:OCR_ENABLED=false"], got
    assert any(c.startswith("warn:") for c in got["calls"]), got
    assert got["probe"] is not None, "RapidOCR is checked first, so the probe always runs"

    # Tesseract only (a failing probe must give false, never a crash: bash -e is on)
    got = _run_dev_sh_ocr_sync(tmp_path, tesseract=True, probe_exit=1)
    assert [c for c in got["calls"] if c.startswith("set:")] == ["set:OCR_ENABLED=true"], got
    assert any(c.startswith("ok:") and "Tesseract" in c and "RapidOCR" not in c for c in got["calls"]), got

    # both
    got = _run_dev_sh_ocr_sync(tmp_path, tesseract=True, probe_exit=0)
    assert [c for c in got["calls"] if c.startswith("set:")] == ["set:OCR_ENABLED=true"], got
    assert any(c.startswith("ok:") and "RapidOCR" in c and "Tesseract" in c for c in got["calls"]), got

    # HC_SKIP_OCR_SETUP=1 leaves the .env alone and never runs the probe
    got = _run_dev_sh_ocr_sync(tmp_path, tesseract=True, probe_exit=0, skip=True)
    assert got["calls"] == [], got
    assert got["probe"] is None, got

    # dev.ps1: text only
    ps1 = _block(_DEV_PS1, 'if ($env:HC_SKIP_OCR_SETUP -ne "1") {', "}")
    assert "rapidocr_ready" in ps1, ps1
    assert "Set-DotEnvKey" in ps1, ps1
    assert "$LASTEXITCODE" in ps1 and "Pop-Location" in ps1, ps1


def test_hc_ocr_014_disabled_ocr_loads_no_engine(tmp_path):
    """OCR is off by default. Asking whether it is effective (every Settings GET and
    lab import does) must not import onnxruntime / cv2 or build the engine."""
    body = r'''
import sys
shutil.which = lambda *args, **kwargs: None
from core import config as cfg
cfg.settings.ocr_enabled = False
effective, blockers = cfg.compute_ocr_effective(True)
available = cfg.is_ocr_available()
print("HC_OCR_RESULT=" + json.dumps({
    "effective": effective, "blockers": blockers, "available": available,
    "loaded": sorted(m for m in ("onnxruntime", "cv2", "rapidocr") if m in sys.modules),
}))
'''
    out, _home = _run_probe(body, tmp_path)
    assert out["loaded"] == [], f"a disabled-OCR check imported the engine: {out['loaded']}"
    assert out["effective"] is False and out["available"] is False, out
    assert "disabled_by_admin" in out["blockers"], out


# ---------------------------------------------------------------------------
# HC-OCR-010 .. 012: engine order, ruled grids, event loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_ocr_010_rapidocr_first_tesseract_only_as_fallback(monkeypatch):
    from unittest.mock import MagicMock

    pytest.importorskip("pytesseract")
    pytest.importorskip("pdf2image")
    _ocr_on(monkeypatch)
    monkeypatch.setattr(cfg, "is_tesseract_on_path", lambda: True)  # Tesseract "present"

    tess = MagicMock(return_value="Glucose 95 mg/dL 70-100\nSodium 140 mmol/L 136-145\n")
    monkeypatch.setattr("pytesseract.image_to_string", tess)

    # Part 1: engine ready -> Tesseract is not called.
    pytest.importorskip("rapidocr")
    result = await ExtractModule().extract_from_image(
        io.BytesIO(_png(_column_page())), "doc", effective_ocr=True
    )
    assert result.observations, "RapidOCR should have read the page"
    tess.assert_not_called()

    # Part 2: engine not ready -> Tesseract once per page, pages rasterised by pdf2image.
    monkeypatch.setattr(extract, "_rapidocr_engine", lambda: None)
    pages = [Image.new("L", (300, 100), 255), Image.new("L", (300, 100), 255)]
    convert = MagicMock(return_value=pages)
    monkeypatch.setattr("pdf2image.convert_from_bytes", convert)
    result = await ExtractModule().extract_from_scanned_pdf(
        io.BytesIO(b"%PDF-1.4 fake"), "doc", effective_ocr=True
    )
    convert.assert_called_once()
    assert tess.call_count == 2
    assert {o.extraction_method for o in result.observations} == {"ocr_pdf"}


@pytest.mark.asyncio
async def test_hc_ocr_011_ruled_lines_are_removed_before_reading(monkeypatch):
    pytest.importorskip("rapidocr")
    page = _grid_page()
    module = ExtractModule()

    with_derule = module._extract_from_text(await asyncio.to_thread(extract._ocr_image_text, page), 1, "d")

    monkeypatch.setattr(extract, "_remove_ruled_lines", lambda gray: gray)
    without = module._extract_from_text(await asyncio.to_thread(extract._ocr_image_text, page), 1, "d")

    _assert_no_wrong_value(with_derule)
    names = lambda obs: {n for n, _v, _u in _triples(obs)}  # noqa: E731
    assert names(with_derule) >= names(without), (names(with_derule), names(without))
    assert len(with_derule) >= _FOUND_FLOOR, _triples(with_derule)


@pytest.mark.asyncio
async def test_hc_ocr_012_ocr_does_not_block_the_event_loop(monkeypatch):
    _ocr_on(monkeypatch)
    monkeypatch.setattr(cfg, "is_tesseract_on_path", lambda: True)
    monkeypatch.setattr(extract, "_ocr_image_text", lambda _image: (time.sleep(0.5), "")[1])

    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.05)
            ticks += 1

    task = asyncio.create_task(ticker())
    try:
        await ExtractModule().extract_from_image(
            io.BytesIO(_png(Image.new("L", (200, 80), 255))), "doc", effective_ocr=True
        )
    finally:
        task.cancel()
    assert ticks >= 5, f"event loop advanced only {ticks} ticks during a 0.5 s OCR call"

    # Readiness (importing the engine) is asked on the loop, so ask it only when a page
    # is short of text, never for a PDF that is all text, and only once per document.
    calls = []

    def ready(*, pdf):
        calls.append(pdf)
        return False

    monkeypatch.setattr(extract, "_ocr_backend_ready", ready)
    await ExtractModule().extract_from_pdf(
        io.BytesIO(_build_pdf([("text", _MIXED_TEXT_LINES)])), "doc", ocr_pages=True
    )
    assert calls == [], "a text-only PDF must not probe the OCR engine"
    await ExtractModule().extract_from_pdf(
        io.BytesIO(_build_pdf([("text", _MIXED_TEXT_LINES), ("image", _column_page()), ("image", _column_page())])),
        "doc", ocr_pages=True,
    )
    assert calls == [True], "the engine is probed once, the first time a page needs OCR"


@_NEEDS_PROC_FD
def test_hc_ocr_015_native_socket_check_sees_what_the_python_guard_cannot(tmp_path):
    """Control for 001's /proc check: it must flag a remote peer and ignore loopback."""
    import socket

    def table(name: str, rows: list[tuple[str, str]]) -> None:
        header = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        body = "".join(
            f"   {k}: 00000000:0000 {rem} 01 00000000:00000000 00:00000000 00000000  1000        0 {inode}\n"
            for k, (rem, inode) in enumerate(rows)
        )
        (tmp_path / name).write_text(header + body)

    # 4.150.223.102:443 (little-endian hex), as in the review's ss output
    table("tcp", [("66DF9604:01BB", "1111"), ("0100007F:0050", "2222"), ("00000000:0000", "3333")])
    # ::1, ::ffff:127.0.0.1 (loopback) and ::ffff:74.151.238.100 (remote)
    table("tcp6", [
        ("00000000000000000000000001000000:0050", "4444"),
        ("0000000000000000FFFF00000100007F:0050", "5555"),
        ("0000000000000000FFFF000064EE974A:01BB", "6666"),
    ])
    table("udp", [])
    table("udp6", [])
    peers = _native_remote_peers({"1111", "2222", "3333", "4444", "5555", "6666", "9999"}, str(tmp_path))
    assert peers == ["tcp:4.150.223.102:443", "tcp6:74.151.238.100:443"], peers
    assert _native_remote_peers({"2222"}, str(tmp_path)) == []  # an inode we do not hold is ignored

    # the watcher keeps a peer that was there for one look and gone before the next
    import threading

    table("tcp", [("66DF9604:01BB", "1111")])
    seen, stop = set(), threading.Event()
    watcher = threading.Thread(
        target=_watch_native_peers, args=(stop, seen, 0.01, lambda: {"1111"}, str(tmp_path))
    )
    watcher.start()
    deadline = time.monotonic() + 10
    while not seen and time.monotonic() < deadline:
        time.sleep(0.01)
    table("tcp", [])  # connection closed
    time.sleep(0.1)
    stop.set()
    watcher.join()
    assert seen == {"tcp:4.150.223.102:443"}, seen

    # and the inode lookup sees a real socket that Python's patched connect() never touched
    with socket.socket() as sock:
        inode = os.readlink(f"/proc/self/fd/{sock.fileno()}")[len("socket:["):-1]
        assert inode in _socket_inodes()


@_NEEDS_PROC_FD
def test_hc_ocr_016_pdfium_is_never_entered_by_two_threads(tmp_path):
    """PDFium is not thread-safe (pypdfium2 METADATA). Two threads inside it abort the
    whole process (``free(): invalid pointer``, exit 134; or a segfault, exit 139).

    Two races, one probe, because the failure is a native abort that would kill pytest:
    * four ``asyncio.to_thread`` workers run the real ``_ocr_pdf_pages`` against each other;
    * meanwhile the loop thread runs the REAL ``api.documents.get_page_image`` coroutine
      (pdfplumber ``to_image``, which is PDFium too) over every page, again and again.
    Only the engine, the database, auth, audit and the page cache are stubbed.

    What this still cannot see: a PDFium call from a route other than ``get_page_image``
    or from a thread this test does not start (a grep of ``to_image(`` / ``pypdfium2`` /
    ``PdfDocument`` is the recheck), and a race that needs a different PDF than the fixture.
    """
    pytest.importorskip("pypdfium2")
    pdf = tmp_path / "pages.pdf"
    # Text pages are what make PDFium's shared font state race; a scan of only
    # pictures did not crash it in 30 tries, a mixed document did on every try.
    text_page = ("text", [f"Glucose: {n} mg/dL (70-100)" for n in range(30)])
    pdf.write_bytes(_build_pdf([text_page, ("image", _column_page()), text_page, ("image", _column_page())]))
    body = r'''
import asyncio
import io
import threading
from pathlib import Path
from types import SimpleNamespace
from modules import extract
import api.documents as documents

extract.rapidocr_ready = lambda: True
extract._ocr_image_text = lambda image: "page"
data = Path(os.environ["HC_OCR_PDF"]).read_bytes()
errors = []

def work():
    try:
        for _ in range(12):
            assert len(extract._ocr_pdf_pages(data)) == 4
    except BaseException as exc:
        errors.append(type(exc).__name__)

class _Result:
    def scalar_one_or_none(self):
        return SimpleNamespace(id="doc", profile_id="p", source="pages.pdf")

class _ProfileDb:
    async def execute(self, *args, **kwargs):
        return _Result()

async def _audit(*args, **kwargs):
    return None

documents.validate_uuid = lambda *a, **k: None
documents.verify_document_access = lambda *a, **k: None
documents.get_decrypted_document = lambda *a, **k: io.BytesIO(data)
documents._page_image_cache_get = lambda key: None
documents._page_image_cache_set = lambda key, value: None
documents.audit_and_commit = _audit
session = SimpleNamespace(profile_id="p")

async def render_all():
    rendered = 0
    for number in range(1, 5):
        response = await documents.get_page_image(
            "doc", number, session, profile_db=_ProfileDb(), master_db=None
        )
        assert response.body[:8] == b"\x89PNG\r\n\x1a\n"
        rendered += 1
    return rendered

threads = [threading.Thread(target=work) for _ in range(3)]
for t in threads:
    t.start()
rendered = 0
for _ in range(15):
    rendered += asyncio.run(render_all())
for t in threads:
    t.join()
print("HC_OCR_RESULT=" + json.dumps({"errors": errors, "rendered": rendered}))
'''
    out, _home = _run_probe(body, tmp_path, HC_OCR_PDF=str(pdf))
    assert out == {"errors": [], "rendered": 60}, out


def test_hc_ocr_017_only_the_engine_builder_imports_onnxruntime():
    """ORT_DISABLE_TELEMETRY only works if it is set before the FIRST onnxruntime import
    in the process. ``extract._rapidocr_engine`` sets it. Any other product module that
    imports onnxruntime (sentence-transformers' ONNX backend, a new runner) could import
    it first, and then telemetry starts no matter what 001 sees in a fresh process.
    Local imports count: they run whenever the code path does."""
    import ast

    offenders = []
    for path in sorted(BACKEND_DIR.rglob("*.py")):
        rel = path.relative_to(BACKEND_DIR)
        if rel.parts[0] in {"tests", "scripts", "migrations", "venv", ".venv"} or rel.parts[:2] == (
            "models", "embeddings",
        ) or any(part.startswith(".venv") for part in rel.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, (ast.Name, ast.Attribute))
                and getattr(node.func, "attr", getattr(node.func, "id", "")) in {"import_module", "__import__"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                names = [node.args[0].value]
            if any(n == "onnxruntime" or n.startswith("onnxruntime.") for n in names):
                offenders.append(f"{rel.as_posix()}:{node.lineno}")
    assert [o.split(":")[0] for o in offenders] == ["modules/extract.py"], offenders
    # ...and that one import is inside _rapidocr_engine, after the opt-out line.
    source = (BACKEND_DIR / "modules" / "extract.py").read_text(encoding="utf-8")
    body = source.split("def _rapidocr_engine", 1)[1].split("\ndef ", 1)[0]
    assert body.index('os.environ["ORT_DISABLE_TELEMETRY"] = "1"') < body.index("import onnxruntime")


# ---------------------------------------------------------------------------
# HC-OCR-013: notices
# ---------------------------------------------------------------------------

def _ocr_block_requirements() -> list[tuple[str, str]]:
    """(package, specifier version) for the OCR block of requirements.txt."""
    lines = (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("#") and "OCR" in ln)
    found: list[tuple[str, str]] = []
    for ln in lines[start:]:
        ln = ln.strip()
        if ln.startswith("# ====") and found:
            break
        if not ln or ln.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)\s*(?:==|>=)\s*([0-9][0-9A-Za-z.]*)", ln)
        assert match, f"unparsed OCR requirement line: {ln!r}"
        found.append((match.group(1).lower(), match.group(2)))
    return found


def test_hc_ocr_013_third_party_notices_cover_the_ocr_block():
    notices_path = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    assert notices_path.is_file(), "THIRD_PARTY_NOTICES.md is missing"
    notices = notices_path.read_text(encoding="utf-8")

    packages = _ocr_block_requirements()
    names = {n for n, _ in packages}
    assert {"rapidocr", "onnxruntime", "opencv-python-headless", "pypdfium2"} <= names, names

    licence = re.compile(r"Apache-2\.0|MIT|BSD|HPND")
    rows = [ln for ln in notices.splitlines() if ln.lstrip().startswith("|")]
    for name, version in packages:
        row = next((r for r in rows if re.search(rf"\|\s*`?{re.escape(name)}`?\s*\|", r, re.I)), None)
        assert row, f"no notices table row for {name}"
        assert version in row, f"{name}: pinned version {version} missing from its row: {row}"
        assert licence.search(row), f"{name}: no licence in its row: {row}"

    assert "LGPL" in notices
    for lib in ("libavcodec", "libavformat", "libavutil", "libswscale", "libswresample"):
        assert lib in notices, f"FFmpeg statement does not name {lib}"
    assert "opencv_python_headless.libs" in notices
    assert "PaddleOCR" in notices and "Apache-2.0" in notices
    assert re.search(r"modif", notices, re.I), "PaddleOCR modification notice is missing"
