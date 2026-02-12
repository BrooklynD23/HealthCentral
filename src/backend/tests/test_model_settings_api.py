"""
Tests for HC-REM-002: External API settings persistence.

Tests that:
- PUT /external-api saves settings to profile DB
- PUT without consent returns 400
- GET /external-api masks the API key
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.model_settings import router as model_settings_router
from core.auth import (
    Session,
    require_auth,
    get_profile_db_session,
    get_profile_encryption_manager,
)
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


def _make_app():
    app = FastAPI()
    app.include_router(model_settings_router, prefix="/settings/model")
    return app


def _override_auth(profile_id: str):
    async def _auth():
        return Session(
            profile_id=profile_id,
            profile_name="Test",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    return _auth


async def _override_encryption_manager():
    return EncryptionManager()


def test_put_external_api_requires_consent():
    """
    HC-REM-002-001: PUT /external-api without consent_acknowledged should return 400.
    """
    profile_id = str(uuid.uuid4())
    app = _make_app()
    app.dependency_overrides[require_auth] = _override_auth(profile_id)
    app.dependency_overrides[get_profile_db_session] = lambda: _FakeProfileDb()
    app.dependency_overrides[get_profile_encryption_manager] = _override_encryption_manager

    with TestClient(app) as client:
        response = client.put(
            "/settings/model/external-api",
            json={
                "use_external_api": True,
                "provider": "openai",
                "api_key": "sk-test",
                "consent_acknowledged": False,
            },
        )

    assert response.status_code == 400


def test_put_external_api_persists():
    """
    HC-REM-002-002: PUT /external-api with valid payload saves to profile DB.
    """
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    app = _make_app()
    app.dependency_overrides[require_auth] = _override_auth(profile_id)
    app.dependency_overrides[get_profile_encryption_manager] = _override_encryption_manager

    async def _get_db():
        return profile_db

    app.dependency_overrides[get_profile_db_session] = _get_db

    with TestClient(app) as client:
        response = client.put(
            "/settings/model/external-api",
            json={
                "use_external_api": True,
                "provider": "openai",
                "api_key": "sk-test-key-123",
                "consent_acknowledged": True,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["use_external_api"] is True
    assert data["provider"] == "openai"
    assert data["api_key_configured"] is True
    # Key should never be returned in response
    assert "api_key" not in data or "sk-test" not in str(data.get("api_key", ""))
    # Key must be stored encrypted at rest
    stored = profile_db._existing_settings.external_api_key_encrypted
    assert stored != "sk-test-key-123"
    assert stored.startswith("gAAAAA")


def test_download_task_writes_terminal_status(monkeypatch):
    """
    HC-REM-009-001: Background download task should write completed status to DB.
    """
    import asyncio
    from unittest.mock import MagicMock, AsyncMock, patch
    from api.model_settings import _download_model_task, _write_download_status

    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"
    selector.update_download_progress = AsyncMock()

    # Mock hf_hub_download to succeed
    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock) as mock_write:
        with patch("huggingface_hub.hf_hub_download", return_value="/tmp/models/model.gguf"):
            asyncio.run(_download_model_task("low", profile_id, selector))

        mock_write.assert_called_once_with(profile_id, "low", selector, "completed", 100.0)


def test_download_task_writes_failure_status(monkeypatch):
    """
    HC-REM-009-002: Background download task should write failed status on error.
    """
    import asyncio
    from unittest.mock import MagicMock, AsyncMock, patch
    from api.model_settings import _download_model_task

    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"

    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock) as mock_write:
        with patch("huggingface_hub.hf_hub_download", side_effect=RuntimeError("Download failed")):
            asyncio.run(_download_model_task("low", profile_id, selector))

        mock_write.assert_called_once_with(
            profile_id, "low", selector, "failed", 0.0, "Download failed"
        )


def test_get_external_api_masks_key():
    """
    HC-REM-002-003: GET /external-api should return api_key_configured bool,
    never the raw key.
    """
    from unittest.mock import MagicMock

    profile_id = str(uuid.uuid4())

    mock_settings = MagicMock()
    mock_settings.use_external_api = True
    mock_settings.external_api_provider = "anthropic"
    mock_settings.external_api_key_encrypted = "encrypted-key-data"
    mock_settings.preferred_tier = "low"
    mock_settings.auto_detect_enabled = True

    profile_db = _FakeProfileDb(existing_settings=mock_settings)

    app = _make_app()
    app.dependency_overrides[require_auth] = _override_auth(profile_id)

    async def _get_db():
        return profile_db

    app.dependency_overrides[get_profile_db_session] = _get_db

    with TestClient(app) as client:
        response = client.get("/settings/model/external-api")

    assert response.status_code == 200
    data = response.json()
    assert data["api_key_configured"] is True
    assert "encrypted-key-data" not in str(data)
