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

    SCAFFOLD: implemented in Sprint 0 (story S0-2). Must default to
    ``AGENT_ENABLED_DEFAULT`` when the key is absent.
    """
    raise NotImplementedError("S0-2: read agent_enabled from model settings (default OFF)")
