"""
Tests for model settings persistence and background download status.
"""

from __future__ import annotations

import asyncio
import sys
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.model_settings import (
    ExternalApiSettingsRequest,
    TimezoneUpdate,
    VoiceSettingsUpdate,
    OcrSettingsUpdate,
    _download_model_task,
    _clear_live_progress,
    _get_live_progress,
    _make_progress_key,
    _set_live_progress,
    get_external_api_settings,
    save_external_api_settings,
    set_timezone,
    update_voice_settings,
    update_ocr_settings,
    _diagnostics_list_response,
)
from core.auth import Session
from core.security import EncryptionManager


class _ScalarResult:
    def __init__(self, one=None):
        self._one = one

    def scalar_one_or_none(self):
        return self._one


class _FakeProfileDb:
    def __init__(self, existing_settings=None):
        self._existing_settings = existing_settings
        self._added = []
        self._committed = False

    async def execute(self, _stmt):
        return _ScalarResult(one=self._existing_settings)

    async def commit(self):
        self._committed = True

    def add(self, obj):
        self._added.append(obj)
        self._existing_settings = obj


def _session(profile_id: str) -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


@pytest.mark.asyncio
async def test_put_external_api_requires_consent():
    profile_id = str(uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await save_external_api_settings(
            request=ExternalApiSettingsRequest(
                use_external_api=True,
                provider="openai",
                api_key="sk-test",
                consent_acknowledged=False,
            ),
            session=_session(profile_id),
            profile_db=_FakeProfileDb(),
            encryption_manager=EncryptionManager(),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_put_external_api_persists():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await save_external_api_settings(
        request=ExternalApiSettingsRequest(
            use_external_api=True,
            provider="openai",
            api_key="sk-test-key-123",
            model="gpt-4o-mini",
            consent_acknowledged=True,
        ),
        session=_session(profile_id),
        profile_db=profile_db,
        encryption_manager=EncryptionManager(),
    )

    assert response.use_external_api is True
    assert response.provider == "openai"
    assert response.model == ""
    assert response.api_key_configured is True
    stored = profile_db._existing_settings.external_api_key_encrypted
    assert stored != "sk-test-key-123"
    assert stored.startswith("gAAAAA")
    assert profile_db._committed is True


def test_download_task_writes_terminal_status(monkeypatch):
    """Task writes 'downloading' at start then 'completed' on success."""
    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"
    selector.update_download_progress = AsyncMock()

    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(
            hf_hub_download=MagicMock(return_value="/tmp/models/model.gguf"),
            list_repo_files=MagicMock(return_value=["model.gguf"]),
        ),
    )

    async def inline_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock) as mock_write:
        with patch("asyncio.to_thread", side_effect=inline_to_thread):
            asyncio.run(_download_model_task("low", profile_id, selector))

        assert mock_write.call_count == 2
        first_call = mock_write.call_args_list[0]
        assert first_call.args == (profile_id, "low", selector, "downloading", 0.0)
        second_call = mock_write.call_args_list[1]
        assert second_call.args == (profile_id, "low", selector, "completed", 100.0)


def test_download_task_writes_failure_status(monkeypatch):
    """Task writes 'downloading' at start then 'failed' with error message on exception."""
    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"

    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(
            hf_hub_download=MagicMock(side_effect=RuntimeError("Download failed")),
            list_repo_files=MagicMock(return_value=["model.gguf"]),
        ),
    )

    async def inline_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock) as mock_write:
        with patch("asyncio.to_thread", side_effect=inline_to_thread):
            asyncio.run(_download_model_task("low", profile_id, selector))

        assert mock_write.call_count == 2
        first_call = mock_write.call_args_list[0]
        assert first_call.args == (profile_id, "low", selector, "downloading", 0.0)
        second_call = mock_write.call_args_list[1]
        assert second_call.args == (profile_id, "low", selector, "failed", 0.0, "Download failed")


def test_download_task_uses_to_thread(monkeypatch):
    """hf_hub_download must run in a thread pool to keep the event loop unblocked."""
    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"

    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(
            hf_hub_download=MagicMock(return_value="/tmp/models/model.gguf"),
            list_repo_files=MagicMock(return_value=["model.gguf"]),
        ),
    )

    to_thread_calls: list = []

    async def tracking_to_thread(func, *args, **kwargs):
        to_thread_calls.append(func)
        return func(*args, **kwargs)

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock):
        with patch("asyncio.to_thread", side_effect=tracking_to_thread):
            asyncio.run(_download_model_task("low", profile_id, selector))

    # The task must offload at least the download itself to a thread pool worker
    assert len(to_thread_calls) >= 1, (
        "Expected asyncio.to_thread to be called at least once for the blocking download"
    )


def test_live_progress_store_lifecycle():
    """Live progress is set, readable, and cleared correctly."""
    profile_id = str(uuid.uuid4())
    key = _make_progress_key(profile_id, "low")

    # Initially absent
    assert _get_live_progress(key) is None

    # Write progress
    _set_live_progress(key, downloaded=512_000_000, total=1_073_741_824)
    result = _get_live_progress(key)
    assert result is not None
    assert result["downloaded_bytes"] == 512_000_000
    assert result["total_bytes"] == 1_073_741_824
    assert abs(result["progress"] - 47.68) < 0.1

    # Clear removes entry
    _clear_live_progress(key)
    assert _get_live_progress(key) is None


@pytest.mark.asyncio
async def test_get_external_api_masks_key():
    profile_id = str(uuid.uuid4())

    mock_settings = MagicMock()
    mock_settings.use_external_api = True
    mock_settings.external_api_provider = "anthropic"
    mock_settings.external_api_key_encrypted = "encrypted-key-data"

    response = await get_external_api_settings(
        session=_session(profile_id),
        profile_db=_FakeProfileDb(existing_settings=mock_settings),
    )

    assert response.api_key_configured is True
    assert "encrypted-key-data" not in str(response)


@pytest.mark.asyncio
async def test_put_timezone_upserts_when_missing():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await set_timezone(
        data=TimezoneUpdate(timezone="America/New_York"),
        session=_session(profile_id),
        profile_db=profile_db,
    )

    assert response.timezone == "America/New_York"
    assert profile_db._existing_settings is not None
    assert profile_db._existing_settings.timezone == "America/New_York"
    assert profile_db._committed is True


@pytest.mark.asyncio
async def test_patch_voice_upserts_when_missing():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await update_voice_settings(
        data=VoiceSettingsUpdate(voice_logging_enabled=True, voice_modal_seen=True),
        session=_session(profile_id),
        profile_db=profile_db,
    )

    assert response.voice_logging_enabled is True
    assert response.voice_modal_seen is True
    assert profile_db._existing_settings is not None
    assert profile_db._existing_settings.voice_logging_enabled is True
    assert profile_db._existing_settings.voice_modal_seen is True
    assert profile_db._committed is True


@pytest.mark.asyncio
async def test_patch_ocr_persists_preference():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await update_ocr_settings(
        data=OcrSettingsUpdate(ocr_preference_enabled=False),
        session=_session(profile_id),
        profile_db=profile_db,
    )

    assert response.ocr_preference_enabled is False
    assert profile_db._existing_settings is not None
    assert profile_db._existing_settings.ocr_preference_enabled is False
    assert profile_db._committed is True


def test_diagnostics_response_has_core_components():
    r = _diagnostics_list_response()
    assert r.checked_at
    ids = {c.id for c in r.components}
    assert "tesseract" in ids
    assert "ocr_python" in ids
