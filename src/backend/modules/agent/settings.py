"""The ``agent_enabled`` feature flag (Phase 0 / story S0-2; cutover S5-1).

Lives in model settings alongside tier/external-API toggles. Defaulted OFF
through S0-S4; S5-1 flipped the default ON as the documented cutover release
(R2) — ``/assistant/chat`` now serves from the agent by default, with the
legacy single-shot path kept as a one-release fallback (flag explicitly False,
or any agent exception) — verified by flag-OFF and fallback regression tests.
Never hardcode the flag; read it from the per-profile model settings store.
"""

from __future__ import annotations

from typing import Any

# S5 cutover (story S5-1) flipped the default ON: /assistant/chat now serves
# from the agent by default, with the legacy rag.query path kept as a one-
# release fallback (see api/assistant.py). This is the documented cutover
# called for by AGILE_PLAN.md Sprint 5, not a weakening of a safety check.
AGENT_ENABLED_DEFAULT = True


def is_agent_enabled(model_settings: Any) -> bool:
    """Return whether the agent path is active for this profile's settings.

    Defensive on shape: ``model_settings`` may be ``None`` (no settings row
    yet — e.g. a fresh profile, mirroring ``user_ocr_preference_enabled`` in
    core/config.py), a dict-like mapping (``UserModelSettingsUpdate``-style
    payloads / test doubles), or an ORM/Pydantic object exposing
    ``agent_enabled`` as an attribute (``UserModelSettings`` rows from
    api/model_settings.py + modules/model_selector.py). Defaults to
    ``AGENT_ENABLED_DEFAULT`` whenever the key/attribute is absent, so a
    profile that has never saved settings still gets the documented default
    (True post-S5-1) and an explicit ``False`` always wins.
    """
    if model_settings is None:
        return AGENT_ENABLED_DEFAULT

    if isinstance(model_settings, dict):
        return bool(model_settings.get("agent_enabled", AGENT_ENABLED_DEFAULT))

    return bool(getattr(model_settings, "agent_enabled", AGENT_ENABLED_DEFAULT))
