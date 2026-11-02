"""SETTINGS-DETECT-BLOCKING: settings routes must not block the event loop.

HC-SDB-001 GET /settings/model, HC-SDB-002 GET /settings/model/tiers and
HC-SDB-003 GET + POST /settings/model/diagnostics[/recheck] used to run hardware
detection and environment diagnostics synchronously inside async handlers, so
every other request waited behind them. These tests go through HTTP
(route_client) with one shared portal loop, as in HC-LUL
(test_provider_switch_nonblocking.py). A slow call is held open on a
threading.Event; a light probe request must still return within 1 s.
"""

from __future__ import annotations

import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.llm.factory as factory
from api import model_settings
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from tests.support.routes import route_client

PREFIX = "/settings/model"
PROBE = f"{PREFIX}/provider?probe=false"
PROFILE_A = "profile-a"
PINNED_TS = datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
DIAG_CALLS = [
    ("GET", f"{PREFIX}/diagnostics"),
    ("POST", f"{PREFIX}/diagnostics/recheck"),
]


@pytest.fixture(autouse=True)
def _light_provider(monkeypatch):
    """The probe only reads capabilities(); keep it off real provider construction."""
    provider = SimpleNamespace(
        capabilities=lambda: SimpleNamespace(
            context_len=4096,
            multimodal=False,
            function_calling=False,
            streaming=True,
            provider_name="fake",
            model_name="fake-model",
        ),
        is_available=lambda: True,
    )
    monkeypatch.setattr(factory, "get_provider", lambda: provider)


@pytest_asyncio.fixture
async def vault():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _master_db() -> MagicMock:
    db = MagicMock()
    db.commit = AsyncMock(return_value=None)
    return db


def _hardware() -> MagicMock:
    hw = MagicMock()
    hw.ram_total_gb = 8.0
    hw.ram_available_gb = 4.0
    hw.cpu_cores = 4
    hw.cpu_name = "cpu"
    hw.disk_free_gb = 50.0
    hw.gpu_available = False
    hw.gpu_vram_gb = 0.0
    hw.gpu_name = ""
    hw.recommended_tier = "template"
    hw.max_supported_tier = "template"
    hw.detection_timestamp = PINNED_TS
    return hw


def _selector() -> MagicMock:
    selector = MagicMock()
    selector.detect_hardware_tier.return_value = _hardware()
    selector.is_model_available.return_value = False
    selector.get_active_tier = AsyncMock(return_value="template")
    return selector


def _components() -> list[dict]:
    return [{
        "id": "tesseract",
        "label": "Tesseract OCR",
        "status": "ok",
        "detail": "Found at /usr/bin/tesseract",
        "fix_actions": [],
    }]


def _blocking(entered: threading.Event, release: threading.Event, value):
    """Stand-in for a blocking call: signal entry, hold until released or 5 s."""

    def _block(*_args, **_kwargs):
        entered.set()
        release.wait(timeout=5)
        return value

    return _block


@contextmanager
def _settings_client(vault, selector):
    with patch.object(model_settings, "get_model_selector", return_value=selector), \
         route_client(
             model_settings.router, PREFIX,
             profile_id=PROFILE_A, master_db=_master_db(),
         ) as client:
        async def _profile_db():
            return vault

        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        yield client


def _while_blocked(client, method: str, path: str, entered, release):
    """Run the blocked request in a thread, then probe the loop while it is held.

    Returns (blocked response or None, probe response, probe elapsed seconds).
    """
    result: dict = {}

    def run() -> None:
        result["resp"] = client.request(method, path)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    try:
        assert entered.wait(timeout=5), "blocking call never started"
        start = time.monotonic()
        probe = client.get(PROBE)
        elapsed = time.monotonic() - start
    finally:
        release.set()
        t.join(timeout=10)
    return result.get("resp"), probe, elapsed


@pytest.mark.asyncio
async def test_hc_sdb_001_get_model_settings_answers_while_detection_blocks(vault):
    selector = _selector()
    with _settings_client(vault, selector) as client:
        baseline = client.get(PREFIX)
        assert baseline.status_code == 200, baseline.text

        entered, release = threading.Event(), threading.Event()
        selector.detect_hardware_tier.side_effect = _blocking(entered, release, _hardware())
        blocked, probe, elapsed = _while_blocked(client, "GET", PREFIX, entered, release)

    assert probe.status_code == 200, probe.text
    assert elapsed < 1.0, f"event loop blocked {elapsed:.2f}s by hardware detection"
    assert blocked is not None, "blocked request never returned"
    assert blocked.status_code == 200, blocked.text
    assert blocked.json() == baseline.json()


@pytest.mark.asyncio
async def test_hc_sdb_002_list_tiers_answers_while_detection_blocks(vault):
    selector = _selector()
    with _settings_client(vault, selector) as client:
        baseline = client.get(f"{PREFIX}/tiers")
        assert baseline.status_code == 200, baseline.text

        entered, release = threading.Event(), threading.Event()
        selector.detect_hardware_tier.side_effect = _blocking(entered, release, _hardware())
        blocked, probe, elapsed = _while_blocked(
            client, "GET", f"{PREFIX}/tiers", entered, release,
        )

    assert probe.status_code == 200, probe.text
    assert elapsed < 1.0, f"event loop blocked {elapsed:.2f}s by hardware detection"
    assert blocked is not None, "blocked request never returned"
    assert blocked.status_code == 200, blocked.text
    assert blocked.json() == baseline.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", DIAG_CALLS)
async def test_hc_sdb_003_diagnostics_answer_while_checks_block(vault, method, path):
    entered, release = threading.Event(), threading.Event()
    with patch.object(
        model_settings, "build_environment_diagnostics", return_value=_components(),
    ) as checks, _settings_client(vault, _selector()) as client:
        baseline = client.request(method, path)
        assert baseline.status_code == 200, baseline.text

        checks.side_effect = _blocking(entered, release, _components())
        blocked, probe, elapsed = _while_blocked(client, method, path, entered, release)

    assert probe.status_code == 200, probe.text
    assert elapsed < 1.0, f"event loop blocked {elapsed:.2f}s by environment checks"
    assert blocked is not None, "blocked request never returned"
    assert blocked.status_code == 200, blocked.text

    # checked_at is the request time, so it cannot be pinned; it must still parse.
    blocked_body, baseline_body = blocked.json(), baseline.json()
    datetime.fromisoformat(blocked_body.pop("checked_at"))
    datetime.fromisoformat(baseline_body.pop("checked_at"))
    assert blocked_body == baseline_body
