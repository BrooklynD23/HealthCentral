"""
Tests for HC-REM-003: External runner DB scope fix.

get_runner_for_request() should use the profile database (not master)
since UserModelSettings lives in the per-profile encrypted database.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
async def test_runner_lookup_uses_profile_db():
    """
    HC-REM-003-001: get_runner_for_request() should query profile_db.

    Mock profile_db with UserModelSettings row that has use_external_api=True.
    Assert returns an ExternalModelRunner.
    """
    from core.external_runner import get_runner_for_request, ExternalModelRunner

    # Create mock settings
    mock_settings = MagicMock()
    mock_settings.use_external_api = True
    mock_settings.external_api_provider = "openai"
    mock_settings.external_api_key_encrypted = "sk-test-key"

    # Create mock profile_db
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_settings
    mock_profile_db = AsyncMock()
    mock_profile_db.execute.return_value = mock_result

    runner = await get_runner_for_request("test-profile-id", mock_profile_db)

    assert runner is not None
    assert isinstance(runner, ExternalModelRunner)
    mock_profile_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_runner_returns_none_when_not_opted_in():
    """
    HC-REM-003-002: get_runner_for_request() returns None when use_external_api=False.
    """
    from core.external_runner import get_runner_for_request

    mock_settings = MagicMock()
    mock_settings.use_external_api = False

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_settings
    mock_profile_db = AsyncMock()
    mock_profile_db.execute.return_value = mock_result

    runner = await get_runner_for_request("test-profile-id", mock_profile_db)

    assert runner is None


@pytest.mark.asyncio
async def test_runner_returns_none_when_no_settings():
    """
    HC-REM-003-003: get_runner_for_request() returns None when no settings exist.
    """
    from core.external_runner import get_runner_for_request

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_profile_db = AsyncMock()
    mock_profile_db.execute.return_value = mock_result

    runner = await get_runner_for_request("test-profile-id", mock_profile_db)

    assert runner is None
