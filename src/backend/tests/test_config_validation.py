"""
Tests for STAB-003: Configuration startup validation.

Verifies:
- validate_startup() raises RuntimeError in production with empty jwt_secret
- validate_startup() returns warnings for missing tesseract when ocr_enabled
- validate_startup() returns warnings for missing models path
- is_ocr_available() returns False when tesseract is not installed
- Dev mode starts normally with missing tesseract (warning only)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


def _make_settings(**overrides):
    """Create a fresh Settings instance with test defaults and overrides."""
    from core.config import Settings

    defaults = {
        "app_env": "development",
        "ocr_enabled": False,
        "jwt_secret": "test-secret",
        "models_path": "/tmp/hc_test_models",
    }
    defaults.update(overrides)
    return Settings(**defaults)


class TestValidateStartup:
    """Tests for Settings.validate_startup()."""

    def test_production_empty_jwt_raises(self):
        """Production with empty jwt_secret must raise RuntimeError."""
        s = _make_settings(app_env="production", jwt_secret="")
        with pytest.raises(RuntimeError, match="jwt_secret must be set"):
            s.validate_startup()

    def test_production_with_jwt_succeeds(self):
        """Production with valid jwt_secret should not raise."""
        s = _make_settings(app_env="production", jwt_secret="real-secret-key")
        warnings = s.validate_startup()
        assert isinstance(warnings, list)

    def test_dev_empty_jwt_does_not_raise(self):
        """Development mode should not raise on empty jwt_secret."""
        s = _make_settings(app_env="development", jwt_secret="")
        warnings = s.validate_startup()
        assert isinstance(warnings, list)

    @patch("shutil.which", return_value=None)
    def test_ocr_enabled_no_tesseract_warns_and_disables(self, mock_which):
        """OCR enabled without tesseract should warn and disable OCR."""
        s = _make_settings(ocr_enabled=True)
        warnings = s.validate_startup()
        assert any("tesseract" in w.lower() for w in warnings)
        assert s.ocr_enabled is False

    @patch("shutil.which", return_value="/usr/bin/tesseract")
    def test_ocr_enabled_with_tesseract_no_warning(self, mock_which):
        """OCR enabled with tesseract present should not warn."""
        s = _make_settings(ocr_enabled=True)
        warnings = s.validate_startup()
        assert not any("tesseract" in w.lower() for w in warnings)
        assert s.ocr_enabled is True

    def test_missing_models_path_creates_or_warns(self, tmp_path):
        """Missing models path should attempt creation or warn."""
        models_dir = tmp_path / "nonexistent_models"
        s = _make_settings(models_path=str(models_dir))
        warnings = s.validate_startup()
        # Either directory was created or a warning was emitted
        assert models_dir.exists() or any("models" in w.lower() for w in warnings)


class TestIsOcrAvailable:
    """Tests for the is_ocr_available() standalone function."""

    @patch("shutil.which", return_value=None)
    def test_returns_false_when_no_tesseract(self, mock_which):
        """is_ocr_available() returns False when tesseract is missing."""
        from core.config import is_ocr_available, settings

        original = settings.ocr_enabled
        try:
            settings.ocr_enabled = True
            assert is_ocr_available() is False
        finally:
            settings.ocr_enabled = original

    @patch("shutil.which", return_value="/usr/bin/tesseract")
    def test_returns_true_when_tesseract_present_and_enabled(self, mock_which):
        """is_ocr_available() returns True when tesseract present and enabled."""
        from core.config import is_ocr_available, settings

        original = settings.ocr_enabled
        try:
            settings.ocr_enabled = True
            assert is_ocr_available() is True
        finally:
            settings.ocr_enabled = original

    def test_returns_false_when_ocr_disabled(self):
        """is_ocr_available() returns False when ocr_enabled is False."""
        from core.config import is_ocr_available, settings

        original = settings.ocr_enabled
        try:
            settings.ocr_enabled = False
            assert is_ocr_available() is False
        finally:
            settings.ocr_enabled = original
