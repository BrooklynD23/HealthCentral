"""Sprint 5 — Cutover + cache. Stories S5-1..S5-3."""

from __future__ import annotations

import pytest

from modules.agent.cache import CacheKey


# --- live: cache key REQUIRES profile_version (no version-blind caching) -----

def test_s5_2_cache_key_requires_profile_version():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CacheKey(normalized_question="why is my ldl 138?")  # missing profile_version


def test_s5_2_cache_key_distinguishes_versions():
    a = CacheKey(normalized_question="q", profile_version=1)
    b = CacheKey(normalized_question="q", profile_version=2)
    assert a != b  # new verified data (version bump) is a different key


# --- skip: behavior that lands when S5 is implemented ------------------------

@pytest.mark.skip(reason="S5-1 scaffold: flag default ON; legacy fallback reachable")
def test_s5_1_cutover_keeps_legacy_fallback():
    ...


@pytest.mark.skip(reason="S5-2 scaffold: repeat served from cache; invalidates on new verified data")
def test_s5_2_cache_hit_and_invalidation():
    ...


@pytest.mark.skip(reason="S5-3 scaffold: per-node p95 visible in /monitoring/metrics")
def test_s5_3_per_node_timing_surfaced():
    ...
