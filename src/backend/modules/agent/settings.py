"""The ``agent_enabled`` feature flag (Phase 0 / story S0-2).

Lives in model settings alongside tier/external-API toggles. Defaults OFF. When
off, ``/assistant/chat`` MUST behave exactly as the legacy single-shot path —
verified by a flag-OFF regression test (FR-1). Never hardcode the flag; read it
from the per-profile model settings store.
"""

from __future__ import annotations

from typing import Any

AGENT_ENABLED_DEFAULT = False


def is_agent_enabled(model_settings: Any) -> bool:
    """Return whether the agent path is active for this profile's settings.

    Defensive on shape: ``model_settings`` may be ``None`` (no settings row
    yet — e.g. a fresh profile, mirroring ``user_ocr_preference_enabled`` in
    core/config.py), a dict-like mapping (``UserModelSettingsUpdate``-style
    payloads / test doubles), or an ORM/Pydantic object exposing
    ``agent_enabled`` as an attribute (``UserModelSettings`` rows from
    api/model_settings.py + modules/model_selector.py). Defaults to
    ``AGENT_ENABLED_DEFAULT`` (False) whenever the key/attribute is absent,
    so the legacy ``/assistant/`` path is unaffected until a profile opts in.
    """
    if model_settings is None:
        return AGENT_ENABLED_DEFAULT

    if isinstance(model_settings, dict):
        return bool(model_settings.get("agent_enabled", AGENT_ENABLED_DEFAULT))

    return bool(getattr(model_settings, "agent_enabled", AGENT_ENABLED_DEFAULT))
