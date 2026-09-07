"""MODEL-INT-001 — model-artifact integrity manifest.

`download_models.py` and `model_selector.py` had zero checksum handling. A
silently swapped GGUF silently invalidates every tuned guardrail threshold and
golden eval, so artifact identity is now checked and reported.

Test IDs: HC-MINT-0NN.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from modules.model_integrity import (
    IntegrityStatus,
    clear_hash_cache,
    compute_sha256,
    load_manifest,
    verify_model_file,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_hash_cache()
    yield
    clear_hash_cache()


def _manifest(tmp_path, tier="low", sha256=None):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "models": {tier: {"repo": "r", "filename": "m.gguf", "sha256": sha256}}
    }))
    return path


def _artifact(tmp_path, content=b"pretend-gguf-bytes"):
    path = tmp_path / "m.gguf"
    path.write_bytes(content)
    return path


def test_hc_mint_001_compute_sha256_matches_hashlib(tmp_path):
    artifact = _artifact(tmp_path)
    assert compute_sha256(artifact) == hashlib.sha256(artifact.read_bytes()).hexdigest()


def test_hc_mint_002_matching_hash_verifies(tmp_path):
    artifact = _artifact(tmp_path)
    manifest = _manifest(tmp_path, sha256=compute_sha256(artifact))

    result = verify_model_file(artifact, "low", manifest_path=manifest)

    assert result.status is IntegrityStatus.VERIFIED
    assert result.is_trustworthy is True
    assert result.is_known_bad is False


def test_hc_mint_003_swapped_artifact_is_detected(tmp_path):
    """The case the whole ticket exists for."""
    artifact = _artifact(tmp_path)
    manifest = _manifest(tmp_path, sha256=compute_sha256(artifact))

    artifact.write_bytes(b"a-different-model-entirely")
    clear_hash_cache()

    result = verify_model_file(artifact, "low", manifest_path=manifest)

    assert result.status is IntegrityStatus.MISMATCH
    assert result.is_known_bad is True
    assert result.is_trustworthy is False
    assert "uardrail" in result.describe()  # "Guardrail thresholds ..."


def test_hc_mint_004_unpinned_is_not_treated_as_verified(tmp_path):
    """Several tiers cannot be pinned yet (placeholder repo URLs). "We did not
    check" must never read as "it is fine"."""
    artifact = _artifact(tmp_path)
    manifest = _manifest(tmp_path, sha256=None)

    result = verify_model_file(artifact, "low", manifest_path=manifest)

    assert result.status is IntegrityStatus.UNPINNED
    assert result.is_trustworthy is False
    assert result.is_known_bad is False


def test_hc_mint_005_unknown_tier_reported(tmp_path):
    result = verify_model_file(
        _artifact(tmp_path), "nonexistent", manifest_path=_manifest(tmp_path)
    )
    assert result.status is IntegrityStatus.UNKNOWN_TIER
    assert result.is_trustworthy is False


def test_hc_mint_006_missing_file_reported(tmp_path):
    manifest = _manifest(tmp_path, sha256="a" * 64)
    result = verify_model_file(tmp_path / "absent.gguf", "low", manifest_path=manifest)
    assert result.status is IntegrityStatus.MISSING_FILE


def test_hc_mint_007_hash_is_cached_by_path_mtime_size(tmp_path):
    """Hashing a multi-GB GGUF on every load would be unacceptable."""
    artifact = _artifact(tmp_path)
    first = compute_sha256(artifact)

    from modules import model_integrity

    calls = {"n": 0}
    real_open = type(artifact).open

    def counting_open(self, *args, **kwargs):
        calls["n"] += 1
        return real_open(self, *args, **kwargs)

    model_integrity.Path.open = counting_open  # type: ignore[assignment]
    try:
        assert compute_sha256(artifact) == first
        assert calls["n"] == 0, "cached hash should not re-read the file"
    finally:
        model_integrity.Path.open = real_open  # type: ignore[assignment]


def test_hc_mint_008_cache_invalidated_when_bytes_change(tmp_path):
    artifact = _artifact(tmp_path, b"first")
    first = compute_sha256(artifact)

    artifact.write_bytes(b"second-and-longer")
    assert compute_sha256(artifact) != first


def test_hc_mint_009_missing_manifest_degrades_quietly(tmp_path):
    assert load_manifest(tmp_path / "nope.json") == {"models": {}}


def test_hc_mint_010_malformed_manifest_degrades_quietly(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert load_manifest(bad) == {"models": {}}


def test_hc_mint_011_shipped_manifest_is_valid_and_honest():
    """The checked-in manifest must parse, and any entry claiming a hash must
    look like a real SHA256 rather than a placeholder."""
    manifest = load_manifest()
    assert manifest["models"], "shipped manifest should list the model tiers"

    for tier, entry in manifest["models"].items():
        sha = entry.get("sha256")
        assert "repo" in entry, f"{tier} has no repo"
        if sha is not None:
            assert len(sha) == 64 and all(c in "0123456789abcdefABCDEF" for c in sha), (
                f"{tier} has a malformed sha256 pin"
            )
            assert set(sha.lower()) != {"a"}, f"{tier} looks like a placeholder hash"
