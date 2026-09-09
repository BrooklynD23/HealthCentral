"""HC-CAP-001..006 — per-tier capability disclosure.

`multimodal` and `function_calling` were computed per-provider and returned by
`/settings/model/provider`, but nothing consumed them and the tier list did not
carry them at all. A user picking the "low" tier had no way to learn that it
will never support the agentic features — the tier list only ever said whether
their hardware could run it.

This is disclosure, not gating: no feature is refused on capability today (the
LLM planner that would need one is not built). The point is that a user
choosing a tier can see what that choice costs them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.model_selector import get_tier_capabilities  # noqa: E402


class TestTierCapabilities:
    def test_hc_cap_001_low_tier_is_not_agentic_capable(self):
        """Qwen2.5-0.5B declares no function calling. 0.5B-class models score
        ~1.4% on BFCL-style multi-turn tool calling, so the tier is a fallback,
        not an agent host — and the UI must be able to say so."""
        caps = get_tier_capabilities("low")
        assert caps["function_calling"] is False
        assert caps["agentic_capable"] is False
        assert caps["context_size"] == 2048

    def test_hc_cap_002_gemma4_tier_reports_its_declared_capabilities(self):
        caps = get_tier_capabilities("gemma4-e2b")
        assert caps["multimodal"] is True
        assert caps["function_calling"] is True
        assert caps["agentic_capable"] is True

    def test_hc_cap_003_mid_tier_context_reflects_the_phi4_swap(self):
        caps = get_tier_capabilities("mid")
        assert caps["context_size"] == 16384, (
            "mid moved to Phi-4-mini for the larger window; disclosure must show it"
        )

    def test_hc_cap_004_template_tier_has_no_model_capabilities(self):
        """The no-LLM fallback path must not claim model capabilities."""
        caps = get_tier_capabilities("template")
        assert caps["context_size"] == 0
        assert caps["multimodal"] is False
        assert caps["function_calling"] is False
        assert caps["agentic_capable"] is False

    def test_hc_cap_005_unknown_tier_degrades_instead_of_raising(self):
        caps = get_tier_capabilities("no-such-tier")
        assert caps["agentic_capable"] is False

    def test_hc_cap_006_agentic_capable_is_derived_not_asserted(self):
        """`agentic_capable` must mean exactly 'this tier declares
        function_calling' — not a per-model guess someone hardcoded. Every
        configured tier must satisfy that identity."""
        from modules.model_selector import TIER_MODEL_CONFIG

        for tier in TIER_MODEL_CONFIG:
            caps = get_tier_capabilities(tier)
            assert caps["agentic_capable"] == caps["function_calling"], tier


# ---------------------------------------------------------------------------
# Route level — the shape the frontend actually receives.
# recurring-failures.md #1: a test that calls the handler as a function cannot
# see a broken Depends(...), so this goes through HTTP.
# ---------------------------------------------------------------------------

class TestTiersRouteCapabilities:
    def test_hc_cap_007_tiers_route_returns_capabilities_per_tier(self):
        from unittest.mock import patch, MagicMock

        from api.model_settings import router as ms_router
        from core.auth import get_profile_db_session
        from tests.support.routes import route_client

        hardware = MagicMock()
        hardware.recommended_tier = "mid"

        selector = MagicMock()
        selector.detect_hardware_tier.return_value = hardware
        selector.is_model_available.return_value = False

        with patch("api.model_settings.get_model_selector", return_value=selector), \
             patch("api.model_settings.can_run_tier", return_value=True):
            with route_client(ms_router, "/settings/model", profile_id="profile-a") as client:
                async def _profile_db():
                    return MagicMock()

                client.app.dependency_overrides[get_profile_db_session] = _profile_db
                resp = client.get("/settings/model/tiers")

        assert resp.status_code == 200, resp.text
        tiers = {t["tier"]: t for t in resp.json()["tiers"]}

        assert "capabilities" in tiers["low"], "tier rows carry no capability data"
        assert tiers["low"]["capabilities"]["agentic_capable"] is False
        assert tiers["template"]["capabilities"]["context_size"] == 0
