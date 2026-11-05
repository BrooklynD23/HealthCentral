"""HC-UISET-018: a stored pending/downloading download row is only believed while
a task for it is running.

The row in `download_state_json` is written by the running task. When the process
dies, or the profile logs out before the final write, the row stays `pending` or
`downloading` for good, and the Settings page used to lock every Download button
on it. The server is the only place that knows whether a task exists, so GET
reports a stored active row with no running task as `failed`.

These go through `route_client` and the real `ModelSelector.get_download_progress`
against a real row, so the parsing and the Depends graph both run.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.model_settings as model_settings_api
from api.model_settings import _download_model_task, _make_progress_key
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from modules.model_selector import DownloadProgress, ModelSelector
from tests.support.routes import route_client

_DEAD_ERROR = "The download stopped before it finished. Try again."
_PREFIX = "/settings/model"


@pytest.fixture(autouse=True)
def _reset_active_downloads():
    """`_aud_setup` in test_model_settings_api.py installs a task that never clears
    the key, so module state would leak between tests. Reset around every test."""
    def _clear():
        keys = getattr(model_settings_api, "_active_downloads", None)
        if keys is not None:
            with model_settings_api._live_progress_lock:
                keys.clear()
    _clear()
    yield
    _clear()


@pytest_asyncio.fixture
async def make_vault():
    """Factory for real per-profile vaults (in-memory SQLite)."""
    made = []

    async def _make() -> AsyncSession:
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
        session = AsyncSession(engine, expire_on_commit=False)
        made.append((session, engine))
        return session

    yield _make
    for session, engine in made:
        await session.close()
        await engine.dispose()


@pytest.fixture
def selector(tmp_path):
    # Real selector with an empty models dir: is_model_available() is really False.
    return ModelSelector(models_path=str(tmp_path / "models"))


@pytest.fixture
def audit_log(monkeypatch):
    calls: list[dict] = []

    async def spy(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(model_settings_api, "create_audit_log", spy)
    return calls


@pytest.fixture
def started_tasks(monkeypatch, selector):
    """Wire the real selector in; the download task is a stub that records starts and
    never clears the key (it stands for a task that is still running)."""
    started: list[dict] = []

    async def _running_download(**kwargs):
        started.append(kwargs)

    monkeypatch.setattr(model_settings_api, "get_model_selector", lambda: selector)
    monkeypatch.setattr(model_settings_api, "_download_model_task", _running_download)
    return started


def _client(vault, profile_id="profile-a"):
    master = MagicMock()
    master.commit = AsyncMock()
    cm = route_client(
        model_settings_api.router, _PREFIX,
        profile_id=profile_id, master_db=master,
        raise_server_exceptions=False,
    )
    client = cm.__enter__()

    async def _pdb():
        return vault

    client.app.dependency_overrides[get_profile_db_session] = _pdb
    return cm, client


@contextlib.contextmanager
def _http(vault, profile_id="profile-a"):
    cm, client = _client(vault, profile_id)
    try:
        yield client
    finally:
        cm.__exit__(None, None, None)


async def _store(selector, vault, profile_id, tier, status, **fields):
    await selector.update_download_progress(
        profile_id=profile_id,
        tier=tier,
        progress=DownloadProgress(
            tier=tier, status=status, started_at=datetime.now(timezone.utc), **fields
        ),
        db=vault,
    )
    await vault.commit()


def _get(client):
    resp = client.get(f"{_PREFIX}/download-progress")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _post(client, tier="mid"):
    return client.post(f"{_PREFIX}/download", json={"tier": tier})


# --- GET: a stored active row with no running task reads back failed ---------


@pytest.mark.asyncio
async def test_hc_uiset_018_stored_pending_zero_bytes_reads_failed(
    make_vault, selector, started_tasks, audit_log
):
    vault = await make_vault()
    await _store(selector, vault, "profile-a", "mid", "pending")

    with _http(vault) as client:
        row = _get(client)["mid"]

    assert row == {
        "tier": "mid",
        "status": "failed",
        "progress": 0.0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "path": None,
        "error": _DEAD_ERROR,
    }


@pytest.mark.asyncio
async def test_hc_uiset_018_stored_downloading_with_bytes_reads_failed(
    make_vault, selector, started_tasks, audit_log
):
    vault = await make_vault()
    await _store(
        selector, vault, "profile-a", "mid", "downloading",
        progress=0.4, downloaded_bytes=400, total_bytes=1000, path="/models/part",
    )

    with _http(vault) as client:
        row = _get(client)["mid"]

    # The same shape as the task's own failure write: no byte counts, no path.
    assert row["status"] == "failed"
    assert row["error"] == _DEAD_ERROR
    assert (row["progress"], row["downloaded_bytes"], row["total_bytes"]) == (0.0, 0, 0)
    assert row["path"] is None


@pytest.mark.asyncio
async def test_hc_uiset_018_get_does_not_write_the_row(
    make_vault, selector, started_tasks, audit_log
):
    vault = await make_vault()
    await _store(selector, vault, "profile-a", "mid", "pending")

    with _http(vault) as client:
        _get(client)

    stored = (await selector.get_download_progress("profile-a", vault))["mid"]
    assert stored.status == "pending"
    assert stored.error is None


@pytest.mark.asyncio
async def test_hc_uiset_018_terminal_rows_are_untouched(
    make_vault, selector, started_tasks, audit_log
):
    vault = await make_vault()
    await _store(selector, vault, "profile-a", "low", "completed", progress=100.0)
    await _store(selector, vault, "profile-a", "high", "failed", error="disk full")

    with _http(vault) as client:
        rows = _get(client)

    assert rows["low"]["status"] == "completed"
    assert rows["low"]["error"] is None
    assert rows["high"]["status"] == "failed"
    assert rows["high"]["error"] == "disk full"


# --- POST after a dead row ---------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,fields",
    [
        ("pending", {}),
        ("downloading", {"progress": 0.4, "downloaded_bytes": 400, "total_bytes": 1000}),
    ],
)
async def test_hc_uiset_018_new_post_after_dead_row_is_accepted_and_reads_pending(
    status, fields, make_vault, selector, started_tasks, audit_log
):
    vault = await make_vault()
    await _store(selector, vault, "profile-a", "mid", status, **fields)

    with _http(vault) as client:
        assert _get(client)["mid"]["status"] == "failed"
        resp = _post(client)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "pending"
        # The new press overwrote the row and holds the key: it reads as running.
        assert _get(client)["mid"]["status"] == "pending"
    assert len(started_tasks) == 1


# --- a live key keeps the stored row active ----------------------------------


@pytest.mark.asyncio
async def test_hc_uiset_018_row_with_live_key_stays_active(
    make_vault, selector, started_tasks, audit_log
):
    vault = await make_vault()
    with _http(vault) as client:
        assert _post(client).status_code == 200
        # The running task has moved the row on to downloading.
        await _store(
            selector, vault, "profile-a", "mid", "downloading",
            progress=0.4, downloaded_bytes=400, total_bytes=1000,
        )
        row = _get(client)["mid"]

    assert row["status"] == "downloading"
    assert row["error"] is None
    assert row["total_bytes"] == 1000


# --- ordering: the key exists before the pending row is committed ------------


@pytest.mark.asyncio
async def test_hc_uiset_018_key_is_set_when_the_commit_runs(
    make_vault, selector, started_tasks, audit_log, monkeypatch
):
    vault = await make_vault()
    key = _make_progress_key("profile-a", "mid")
    seen: list[bool] = []
    real_commit = vault.commit

    async def spy_commit():
        seen.append(key in model_settings_api._active_downloads)
        await real_commit()

    monkeypatch.setattr(vault, "commit", spy_commit)

    with _http(vault) as client:
        assert _post(client).status_code == 200

    # Key first, then commit: a GET that sees the pending row can never see no key
    # for a task that is about to start.
    assert seen == [True]


# --- the POST itself can raise between adding the key and add_task -----------


@pytest.mark.asyncio
@pytest.mark.parametrize("failing", ["audit", "commit"])
async def test_hc_uiset_018_raise_before_add_task_leaves_no_key(
    failing, make_vault, selector, started_tasks, audit_log, monkeypatch
):
    vault = await make_vault()
    if failing == "audit":
        async def boom(**kwargs):
            raise RuntimeError("audit db down")
        monkeypatch.setattr(model_settings_api, "create_audit_log", boom)
    else:
        async def boom_commit():
            raise RuntimeError("vault locked")
        monkeypatch.setattr(vault, "commit", boom_commit)

    with _http(vault) as client:
        resp = _post(client)
        assert resp.status_code == 500

    assert started_tasks == []
    assert model_settings_api._active_downloads == set()

    if failing == "audit":
        # The pending row was committed but no task exists: it must read failed,
        # not "Preparing..." until the process restarts.
        with _http(vault) as client:
            assert _get(client)["mid"]["status"] == "failed"


@pytest.mark.asyncio
async def test_hc_uiset_018_failed_second_post_keeps_the_first_posts_key(
    make_vault, selector, started_tasks, audit_log, monkeypatch
):
    """The rollback on a raise only undoes a key this POST added."""
    vault = await make_vault()
    key = _make_progress_key("profile-a", "mid")
    with _http(vault) as client:
        assert _post(client).status_code == 200
        assert key in model_settings_api._active_downloads

        async def boom(**kwargs):
            raise RuntimeError("audit db down")

        monkeypatch.setattr(model_settings_api, "create_audit_log", boom)
        assert _post(client).status_code == 500

    assert key in model_settings_api._active_downloads


# --- two profiles never share a key ------------------------------------------


@pytest.mark.asyncio
async def test_hc_uiset_018_one_profiles_live_key_does_not_keep_anothers_row_active(
    make_vault, selector, started_tasks, audit_log
):
    vault_a = await make_vault()
    vault_b = await make_vault()
    await _store(selector, vault_b, "profile-b", "mid", "pending")

    with _http(vault_a, "profile-a") as client_a:
        assert _post(client_a).status_code == 200
        assert _get(client_a)["mid"]["status"] == "pending"

    assert _make_progress_key("profile-a", "mid") in model_settings_api._active_downloads
    with _http(vault_b, "profile-b") as client_b:
        assert _get(client_b)["mid"]["status"] == "failed"

    # And the other way round: b's live key does not revive a stale a-row.
    with _http(vault_b, "profile-b") as client_b:
        assert _post(client_b).status_code == 200
        assert _get(client_b)["mid"]["status"] == "pending"
    assert _make_progress_key("profile-a", "mid") != _make_progress_key("profile-b", "mid")


# --- the real task clears the key on every exit ------------------------------


def _fake_hf(monkeypatch, hf_download):
    monkeypatch.setattr(
        model_settings_api,
        "TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(
            hf_hub_download=hf_download,
            list_repo_files=MagicMock(return_value=["model.gguf"]),
        ),
    )


async def _inline_to_thread(func, *args, **kwargs):
    return func(*args, **kwargs)


def _task_selector():
    sel = MagicMock()
    sel.models_path = "/tmp/models"
    return sel


@pytest.mark.parametrize("outcome", ["success", "exception"])
def test_hc_uiset_018_task_holds_key_while_running_and_clears_it_after_terminal_write(
    outcome, monkeypatch
):
    key = _make_progress_key("profile-a", "low")
    during_download: list[bool] = []
    during_terminal_write: list[tuple[str, bool]] = []

    def hf_download(**kwargs):
        during_download.append(key in model_settings_api._active_downloads)
        if outcome == "exception":
            raise RuntimeError("Download failed")
        return "/tmp/models/model.gguf"

    _fake_hf(monkeypatch, hf_download)

    async def write(profile_id, tier, selector, status, *rest):
        if status in ("completed", "failed"):
            during_terminal_write.append((status, key in model_settings_api._active_downloads))

    model_settings_api._active_downloads.add(key)
    with patch("api.model_settings._write_download_status", side_effect=write):
        with patch("asyncio.to_thread", side_effect=_inline_to_thread):
            asyncio.run(_download_model_task("low", "profile-a", _task_selector()))

    assert during_download == [True]
    # Cleared after the terminal write, not before: between the two a GET would
    # read the old active row with no key and call a finished download failed.
    expected = "completed" if outcome == "success" else "failed"
    assert during_terminal_write == [(expected, True)]
    assert key not in model_settings_api._active_downloads


def test_hc_uiset_018_task_clears_key_when_cancelled(monkeypatch):
    key = _make_progress_key("profile-a", "low")
    _fake_hf(monkeypatch, MagicMock())

    async def scenario():
        in_download = asyncio.Event()

        hf = sys.modules["huggingface_hub"].hf_hub_download

        async def to_thread(func, *args, **kwargs):
            if func is hf:
                in_download.set()
                await asyncio.Event().wait()  # parked until cancelled
            return func(*args, **kwargs)

        model_settings_api._active_downloads.add(key)
        with patch("api.model_settings._write_download_status", new_callable=AsyncMock):
            with patch("asyncio.to_thread", side_effect=to_thread):
                task = asyncio.create_task(
                    _download_model_task("low", "profile-a", _task_selector())
                )
                await asyncio.wait_for(in_download.wait(), timeout=5)
                assert key in model_settings_api._active_downloads
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task

    asyncio.run(scenario())
    assert key not in model_settings_api._active_downloads


def test_hc_uiset_018_task_called_directly_without_a_key_does_not_raise(monkeypatch):
    """Existing tests call the task with no key set: the clear must be a discard."""
    _fake_hf(monkeypatch, MagicMock(return_value="/tmp/models/model.gguf"))
    with patch("api.model_settings._write_download_status", new_callable=AsyncMock):
        with patch("asyncio.to_thread", side_effect=_inline_to_thread):
            asyncio.run(_download_model_task("low", "profile-a", _task_selector()))
    assert model_settings_api._active_downloads == set()
