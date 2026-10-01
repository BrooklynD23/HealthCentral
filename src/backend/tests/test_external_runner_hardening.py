"""HC-EXT-001…004 — D12 (owner, 2026-09-27): external runner hardening.

"make strict redaction unconditional (remove the dev bypass; keep break-glass
only with audit + UI warning)". See
docs/plans/2026-09-27-W06-external-runner-hardening.md.

No test here touches the network: the provider call is always patched.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.external_runner import ExternalModelRunner
from core.model_runner import InferenceResult

PROFILE = "profile-a"
API_KEY = "test-key-do-not-log"

# Tokens covering every strict rule class that matters here. DOB and MRN are
# strict-ONLY (modules/redaction.py), so they prove the level is strict, not
# merely "some redaction ran".
PHI_PROMPT = (
    "Patient: John Doe DOB: 01/15/1990 MRN: 8834412 SSN 123-45-6789 "
    "takes metformin 500 mg, HbA1c 7.2"
)
REDACTABLE_TOKENS = ("John Doe", "01/15/1990", "8834412", "123-45-6789")


def _runner() -> ExternalModelRunner:
    return ExternalModelRunner(provider="openai", api_key=API_KEY, profile_id=PROFILE)


def _set(mock_settings, *, env: str, enabled: bool, level: str, break_glass: bool) -> None:
    mock_settings.app_env = env
    mock_settings.redaction_enabled = enabled
    mock_settings.redaction_policy_level = level
    mock_settings.external_api_redaction_break_glass = break_glass


def _capturing(sent: list[str], order: list[str] | None = None):
    async def _fake_call(prompt, config):
        if order is not None:
            order.append("dispatch")
        sent.append(prompt)
        return InferenceResult(text="ok", tokens_generated=1, finish_reason="stop", model_name="m")
    return _fake_call


# ---------------------------------------------------------------------------
# HC-EXT-001 — no dev bypass: without break-glass, the prompt is always
# strictly redacted, whatever REDACTION_ENABLED / REDACTION_POLICY_LEVEL say.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled,level",
    [(False, "strict"), (False, "standard"), (True, "standard"), (True, "minimal")],
)
async def test_hc_ext_001_dev_without_break_glass_always_redacts_strictly(enabled, level):
    runner = _runner()
    sent: list[str] = []
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
         patch("core.external_runner.settings") as s:
        _set(s, env="development", enabled=enabled, level=level, break_glass=False)
        result = await runner.generate_async(PHI_PROMPT)

    assert result.finish_reason == "stop"
    assert len(sent) == 1, "provider was not called exactly once"
    for token in REDACTABLE_TOKENS:
        assert token not in sent[0], f"{token!r} left the device (enabled={enabled}, level={level})"

