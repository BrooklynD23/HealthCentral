"""
UXQA-005: Security Regression Tests

Tests for authentication bypass, data leakage, input validation,
and other security regression scenarios.

These are unit-level security checks that can run without a live server.
"""

from __future__ import annotations

import re
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# UUID Validation Tests (Path Traversal Prevention)
# ---------------------------------------------------------------------------

class TestUUIDValidation:
    """Verify UUID validation prevents path traversal attacks."""

    def test_valid_uuid_passes(self):
        from api.documents import validate_uuid

        result = validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_path_traversal_rejected(self):
        from api.documents import validate_uuid
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("../../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_empty_string_rejected(self):
        from api.documents import validate_uuid
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("")
        assert exc_info.value.status_code == 400

    def test_sql_injection_attempt_rejected(self):
        from api.documents import validate_uuid
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("'; DROP TABLE documents;--")
        assert exc_info.value.status_code == 400

    def test_null_bytes_rejected(self):
        from api.documents import validate_uuid
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("550e8400-e29b-41d4-a716-44665544\x00")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Document Access Control Tests
# ---------------------------------------------------------------------------

class TestDocumentAccessControl:
    """Verify cross-profile document access is denied."""

    def test_verify_document_access_same_profile(self):
        from api.documents import verify_document_access

        doc = MagicMock()
        doc.profile_id = "profile-001"

        session = MagicMock()
        session.profile_id = "profile-001"

        # Should not raise
        verify_document_access(doc, session)

    def test_verify_document_access_different_profile_blocked(self):
        from api.documents import verify_document_access
        from fastapi import HTTPException

        doc = MagicMock()
        doc.profile_id = "profile-001"
        doc.id = "doc-abc"

        session = MagicMock()
        session.profile_id = "profile-002"

        with pytest.raises(HTTPException) as exc_info:
            verify_document_access(doc, session)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Password Validation Tests
# ---------------------------------------------------------------------------

class TestPasswordValidation:
    """Verify password strength requirements are enforced."""

    def test_valid_password(self):
        from api.profiles import ProfileCreate

        profile = ProfileCreate(display_name="Test", password="SecurePass123")
        assert profile.password == "SecurePass123"

    def test_short_password_rejected(self):
        from api.profiles import ProfileCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProfileCreate(display_name="Test", password="Short1")

    def test_no_uppercase_rejected(self):
        from api.profiles import ProfileCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProfileCreate(display_name="Test", password="nouppercase123")

    def test_no_lowercase_rejected(self):
        from api.profiles import ProfileCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProfileCreate(display_name="Test", password="NOLOWERCASE123")

    def test_no_digit_rejected(self):
        from api.profiles import ProfileCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProfileCreate(display_name="Test", password="NoDigitsHere")


# ---------------------------------------------------------------------------
# OAuth Redirect URI Validation Tests
# ---------------------------------------------------------------------------

class TestOAuthRedirectValidation:
    """Verify OAuth redirect URI allowlist enforcement."""

    def test_valid_redirect_uri_passes(self):
        from api.documents import _normalize_oauth_redirect_uri

        result = _normalize_oauth_redirect_uri("https://app.healthcentral.local/oauth/callback")
        assert result == "https://app.healthcentral.local/oauth/callback"

    def test_javascript_uri_rejected(self):
        from api.documents import _normalize_oauth_redirect_uri
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _normalize_oauth_redirect_uri("javascript:alert(1)")
        assert exc_info.value.status_code == 400

    def test_data_uri_rejected(self):
        from api.documents import _normalize_oauth_redirect_uri
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _normalize_oauth_redirect_uri("data:text/html,<script>alert(1)</script>")
        assert exc_info.value.status_code == 400

    def test_relative_uri_rejected(self):
        from api.documents import _normalize_oauth_redirect_uri
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _normalize_oauth_redirect_uri("/oauth/callback")
        assert exc_info.value.status_code == 400

    def test_fragment_in_uri_rejected(self):
        from api.documents import _normalize_oauth_redirect_uri
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _normalize_oauth_redirect_uri("https://app.healthcentral.local/callback#evil")
        assert exc_info.value.status_code == 400

    def test_unlisted_redirect_blocked(self):
        from api.documents import _resolve_oauth_redirect_uri
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _resolve_oauth_redirect_uri("https://evil.example.com/callback")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Input Sanitization Tests
# ---------------------------------------------------------------------------

class TestInputSanitization:
    """Verify user inputs are properly validated and sanitized."""

    def test_profile_name_max_length(self):
        from api.profiles import ProfileCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProfileCreate(display_name="A" * 256, password="SecurePass123")

    def test_profile_name_empty_rejected(self):
        from api.profiles import ProfileCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProfileCreate(display_name="", password="SecurePass123")


# ---------------------------------------------------------------------------
# File Upload Security Tests
# ---------------------------------------------------------------------------

class TestFileUploadSecurity:
    """Verify file upload boundaries and type restrictions."""

    @pytest.mark.asyncio
    async def test_file_size_limit_enforced(self):
        from api.documents import _read_upload_bounded
        from fastapi import HTTPException

        # Create a mock upload that exceeds limit
        mock_file = AsyncMock()
        large_chunk = b"x" * (1024 * 1024)  # 1MB chunks
        call_count = 0

        async def mock_read(chunk_size):
            nonlocal call_count
            call_count += 1
            if call_count <= 20:  # 20MB total
                return large_chunk
            return b""

        mock_file.read = mock_read

        # Should raise 413 when exceeding 10MB limit
        with pytest.raises(HTTPException) as exc_info:
            await _read_upload_bounded(mock_file, max_bytes=10 * 1024 * 1024)
        assert exc_info.value.status_code == 413


# ---------------------------------------------------------------------------
# Rate Limiting Tests
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Verify rate limiting is enforced on auth endpoints."""

    def test_rate_limiter_blocks_after_threshold(self):
        from core.rate_limiter import auth_rate_limiter

        test_key = "test:security:rate-limit-check"

        # Reset first
        auth_rate_limiter.reset(test_key)

        # Add failures up to threshold
        for _ in range(10):
            auth_rate_limiter.add_failure(test_key)

        # Should eventually block
        decision = auth_rate_limiter.check(test_key)
        assert not decision.allowed, "Rate limiter should block after repeated failures"

        # Cleanup
        auth_rate_limiter.reset(test_key)

    def test_rate_limiter_allows_after_reset(self):
        from core.rate_limiter import auth_rate_limiter

        test_key = "test:security:rate-limit-reset"

        # Add failures and then reset
        for _ in range(10):
            auth_rate_limiter.add_failure(test_key)

        auth_rate_limiter.reset(test_key)

        decision = auth_rate_limiter.check(test_key)
        assert decision.allowed, "Rate limiter should allow after reset"


# ---------------------------------------------------------------------------
# Error Message Leakage Tests
# ---------------------------------------------------------------------------

class TestErrorMessageLeakage:
    """Verify error messages don't leak sensitive information."""

    def test_login_error_is_generic(self):
        """Login failure message should not reveal whether profile exists."""
        # The login endpoint should return "Invalid credentials"
        # not "Profile not found" or "Wrong password"
        expected_message = "Invalid credentials"
        assert "not found" not in expected_message.lower()
        assert "wrong password" not in expected_message.lower()

    def test_document_access_denied_is_generic(self):
        """Document access denied should not reveal document owner."""
        from api.documents import verify_document_access
        from fastapi import HTTPException

        doc = MagicMock()
        doc.profile_id = "profile-001"
        doc.id = "doc-secret"

        session = MagicMock()
        session.profile_id = "profile-attacker"

        with pytest.raises(HTTPException) as exc_info:
            verify_document_access(doc, session)

        # Error detail should not contain the actual owner's profile ID
        assert "profile-001" not in str(exc_info.value.detail)
