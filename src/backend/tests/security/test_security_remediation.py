"""
Tests for Sprint 06 security remediation fixes (SEC-001 through SEC-006).

Each test is tagged with the finding ID it validates.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.backup import _validate_manifest_path


# ---------------------------------------------------------------------------
# Helpers reused from test_input_validator
# ---------------------------------------------------------------------------

def make_scope(
    method: str = "GET",
    path: str = "/api/v1/test",
    query_string: bytes = b"",
    headers: list | None = None,
) -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": headers or [],
    }


class ResponseCapture:
    """Captures ASGI send messages."""
    def __init__(self):
        self.messages: list[dict] = []

    async def __call__(self, message: dict) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int:
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["status"]
        return 0

    @property
    def body_json(self) -> dict:
        for m in self.messages:
            if m["type"] == "http.response.body":
                return json.loads(m["body"])
        return {}


async def passthrough_app(scope, receive, send):
    """Simple ASGI app that returns 200."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b'{"ok": true}'})


async def body_reading_app(scope, receive, send):
    """ASGI app that reads the full body via receive before responding."""
    while True:
        msg = await receive()
        if not msg.get("more_body", False):
            break
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b'{"ok": true}'})


def make_receive(body: bytes = b""):
    """Create a receive callable that returns body."""
    called = False

    async def receive():
        nonlocal called
        if not called:
            called = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


# ===========================================================================
# SEC-001: Metrics endpoint requires auth; /health returns no metrics
# ===========================================================================

class TestSEC001MetricsAuth:
    """GET /monitoring/metrics must require authentication."""

    @pytest.mark.asyncio
    async def test_health_returns_no_metrics_key(self):
        """SEC-001 + SEC-005: /health is a slim liveness probe."""
        from monitoring.health import health_check

        result = await health_check()
        assert result["status"] == "healthy"
        assert "metrics" not in result, "/health should not expose metrics data"
        assert "version" in result

    def test_get_metrics_has_auth_dependency(self):
        """SEC-001: get_metrics endpoint requires RequireAuth dependency."""
        from monitoring.health import get_metrics
        import inspect

        sig = inspect.signature(get_metrics)
        param_names = list(sig.parameters.keys())
        assert "session" in param_names, (
            "get_metrics must declare a 'session: RequireAuth' parameter"
        )


# ===========================================================================
# SEC-002: Import endpoint enforces explicit upload limit
# ===========================================================================

class TestSEC002UploadLimits:
    """Import endpoints enforce the configured upload limit, not unlimited."""

    @pytest.mark.asyncio
    async def test_import_oversized_content_length_rejected(self):
        """SEC-002: Import endpoint with Content-Length > 50 MB → 413."""
        from security.input_validator import InputValidationMiddleware

        mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=100)
        # max_upload_bytes comes from settings (50 MB), but we test by exceeding it
        over_limit = mw.max_upload_bytes + 1
        scope = make_scope(
            method="POST",
            path="/api/v1/documents/import",
            headers=[[b"content-length", str(over_limit).encode()]],
        )
        capture = ResponseCapture()
        await mw(scope, make_receive(), capture)
        assert capture.status == 413

    @pytest.mark.asyncio
    async def test_import_within_upload_limit_passes(self):
        """SEC-002: Import endpoint within upload limit passes."""
        from security.input_validator import InputValidationMiddleware

        mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=100)
        within_limit = mw.max_upload_bytes - 1
        scope = make_scope(
            method="POST",
            path="/api/v1/documents/import",
            headers=[[b"content-length", str(within_limit).encode()]],
        )
        capture = ResponseCapture()
        await mw(scope, make_receive(), capture)
        assert capture.status == 200

    @pytest.mark.asyncio
    async def test_non_import_oversized_rejected(self):
        """SEC-002: Non-import endpoint with Content-Length > 10 MB → 413."""
        from security.input_validator import InputValidationMiddleware

        mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=10_485_760)
        scope = make_scope(
            method="POST",
            path="/api/v1/observations/",
            headers=[[b"content-length", b"20000000"]],
        )
        capture = ResponseCapture()
        await mw(scope, make_receive(), capture)
        assert capture.status == 413

    @pytest.mark.asyncio
    async def test_negative_content_length_rejected(self):
        """SEC-002: Negative Content-Length is rejected as invalid."""
        from security.input_validator import InputValidationMiddleware

        mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=10_485_760)
        scope = make_scope(
            method="POST",
            headers=[[b"content-length", b"-1"]],
        )
        capture = ResponseCapture()
        await mw(scope, make_receive(), capture)
        assert capture.status == 400


# ===========================================================================
# SEC-003: Streaming body exceeding limit returns 413 (not 500)
# ===========================================================================

class TestSEC003StreamingLimit:
    """Streaming bodies that exceed limit produce a clean 413."""

    @pytest.mark.asyncio
    async def test_streaming_body_returns_413_not_500(self):
        """SEC-003: Streaming upload exceeding limit → 413 via _BodyTooLargeError."""
        from security.input_validator import InputValidationMiddleware

        mw = InputValidationMiddleware(body_reading_app, max_request_body_bytes=10)
        scope = make_scope(method="POST")
        capture = ResponseCapture()
        await mw(scope, make_receive(b"x" * 100), capture)
        assert capture.status == 413
        assert "too large" in capture.body_json["detail"].lower()

    @pytest.mark.asyncio
    async def test_streaming_import_also_enforced(self):
        """SEC-003: Streaming import uploads are enforced with upload limit."""
        from unittest.mock import patch
        from security.input_validator import InputValidationMiddleware

        # Patch settings to use a small upload limit for test efficiency
        with patch("security.input_validator.app_settings") as mock_settings:
            mock_settings.max_import_file_size_mb = 1  # 1 MB limit
            mw = InputValidationMiddleware(body_reading_app, max_request_body_bytes=10)

        # Streaming body exceeding the 1 MB upload limit
        over_upload = (1 * 1024 * 1024) + 1
        scope = make_scope(method="POST", path="/api/v1/documents/import")
        capture = ResponseCapture()
        await mw(scope, make_receive(b"x" * over_upload), capture)
        assert capture.status == 413


# ===========================================================================
# SEC-004: Backup manifest path traversal
# ===========================================================================

class TestSEC004PathTraversal:
    """_validate_manifest_path rejects traversal attacks."""

    def test_relative_traversal_rejected(self, tmp_path: Path):
        """SEC-004: Path with '../' is rejected."""
        with pytest.raises(ValueError, match="path traversal"):
            _validate_manifest_path(tmp_path, "../etc/passwd")

    def test_absolute_unix_path_rejected(self, tmp_path: Path):
        """SEC-004: Absolute Unix path is rejected."""
        with pytest.raises(ValueError, match="absolute path"):
            _validate_manifest_path(tmp_path, "/etc/shadow")

    def test_absolute_windows_path_rejected(self, tmp_path: Path):
        """SEC-004: Absolute Windows path is rejected."""
        with pytest.raises(ValueError, match="absolute Windows path"):
            _validate_manifest_path(tmp_path, "C:\\Windows\\System32\\config")

    def test_valid_relative_path_accepted(self, tmp_path: Path):
        """SEC-004: Valid relative path resolves under base_dir."""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file.db").touch()

        result = _validate_manifest_path(tmp_path, "subdir/file.db")
        assert result == (tmp_path / "subdir" / "file.db").resolve()

    def test_simple_filename_accepted(self, tmp_path: Path):
        """SEC-004: Simple filename resolves correctly."""
        (tmp_path / "healthcentral.db").touch()
        result = _validate_manifest_path(tmp_path, "healthcentral.db")
        assert result == (tmp_path / "healthcentral.db").resolve()

    def test_null_byte_in_path_rejected(self, tmp_path: Path):
        """SEC-004: Path with null byte is rejected."""
        with pytest.raises(ValueError, match="null byte"):
            _validate_manifest_path(tmp_path, "file\x00.db")

    def test_restore_returns_error_on_traversal(self, tmp_path: Path):
        """SEC-004: restore() returns RestoreResult(success=False) on malicious paths."""
        from scripts.backup import restore

        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Write a manifest with a path-traversal entry
        manifest = {
            "timestamp": "20260222_120000",
            "created_at": "2026-02-22T12:00:00Z",
            "app_version": "0.1.0",
            "backup_method": "sqlite_backup",
            "files": [{"path": "../etc/passwd", "sha256": "abc", "size_bytes": 0, "method": "sqlite_backup"}],
        }
        (backup_dir / "manifest.json").write_text(json.dumps(manifest))

        result = restore(backup_dir, data_dir)
        assert result.success is False
        assert "path" in result.error.lower()


# ===========================================================================
# SEC-006: Production debug guard
# ===========================================================================

class TestSEC006ProductionDebugGuard:
    """validate_startup() forces debug=False in production."""

    def test_production_debug_forced_off(self):
        """SEC-006: debug=True in production → forced to False."""
        from core.config import Settings

        s = Settings(
            app_env="production",
            debug=True,
            jwt_secret="test-secret-at-least-32-chars-long!!",
        )
        warnings = s.validate_startup()

        assert s.debug is False
        assert any("debug" in w.lower() and "production" in w.lower() for w in warnings)

    def test_development_debug_stays_on(self):
        """SEC-006: debug=True in development is left alone."""
        from core.config import Settings

        s = Settings(app_env="development", debug=True)
        warnings = s.validate_startup()

        assert s.debug is True
        assert not any("debug" in w.lower() and "overridden" in w.lower() for w in warnings)
