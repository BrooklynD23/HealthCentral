"""HC-VERIFY-001..006 — `download_models.py verify` checks every configured
tier repo against HuggingFace before anyone tries to download one.

Three of the repo paths in TIER_MODEL_CONFIG have never been confirmed to
exist (the Gemma 4 family, and the Phi-4-mini community quantizer that
replaced Phi-3-mini). huggingface.co is unreachable from the sandbox this was
written in, so the check has to run on a machine that can reach it — which
makes a scriptable, exit-coded check the deliverable, not a one-off lookup.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from download_models import RepoCheck, verify_repo  # noqa: E402


def _repo_not_found():
    """Build a real RepositoryNotFoundError the way huggingface_hub does.

    It requires a keyword-only `response`, and subclasses OSError — both facts
    matter to what this module has to get right.
    """
    import httpx
    from huggingface_hub.errors import RepositoryNotFoundError

    return RepositoryNotFoundError(
        "404 Client Error", response=httpx.Response(404, request=httpx.Request("GET", "https://hf.co"))
    )


class TestVerifyRepo:
    def test_hc_verify_001_ok_when_pattern_matches_a_file(self):
        files = ["README.md", "microsoft_Phi-4-mini-instruct-Q4_K_M.gguf"]
        with patch("download_models.list_repo_files", return_value=files):
            result = verify_repo("some/repo", filename_pattern="q4_k_m", filename=None)
        assert result.status == "ok"
        assert result.resolved == "microsoft_Phi-4-mini-instruct-Q4_K_M.gguf"

    def test_hc_verify_002_pattern_match_is_case_insensitive(self):
        """Track 5 found the repo's hardcoded casing disagrees with what HF
        publishes (q4_k_m vs Q4_K_M). Casing must not decide the verdict."""
        with patch("download_models.list_repo_files", return_value=["Model-Q4_K_M.gguf"]):
            result = verify_repo("some/repo", filename_pattern="q4_k_m", filename=None)
        assert result.status == "ok"

    def test_hc_verify_003_exact_filename_missing_is_reported(self):
        with patch("download_models.list_repo_files", return_value=["other.gguf"]):
            result = verify_repo("some/repo", filename_pattern=None, filename="wanted.gguf")
        assert result.status == "missing_file"
        assert "wanted.gguf" in result.detail

    def test_hc_verify_004_no_gguf_matching_pattern_is_reported(self):
        with patch("download_models.list_repo_files", return_value=["README.md", "model-q8_0.gguf"]):
            result = verify_repo("some/repo", filename_pattern="q4_k_m", filename=None)
        assert result.status == "missing_file"

    def test_hc_verify_005_missing_repo_is_reported_not_raised(self):
        """A missing repo must be classified `not_found`, NOT `unreachable`.

        huggingface_hub's RepositoryNotFoundError subclasses OSError, so a
        handler that catches OSError before the specific type would silently
        report every bad repo path as a network problem — and nobody would
        ever fix the config.
        """
        with patch("download_models.list_repo_files", side_effect=_repo_not_found()):
            result = verify_repo("ghost/repo", filename_pattern="q4_k_m", filename=None)
        assert result.status == "not_found", (
            "a missing repo was misclassified — check exception-handler ordering"
        )

    def test_hc_verify_006_network_failure_is_distinct_from_missing(self):
        """An unreachable network must not be reported as 'this repo does not
        exist' — that is the difference between 'verify later' and 'the config
        is wrong', and conflating them would send someone editing good config."""
        with patch("download_models.list_repo_files", side_effect=OSError("proxy 403")):
            result = verify_repo("some/repo", filename_pattern="q4_k_m", filename=None)
        assert result.status == "unreachable"
        assert result.status != "not_found"


class TestRepoCheckModel:
    def test_hc_verify_007_only_ok_counts_as_verified(self):
        assert RepoCheck(tier="t", repo="r", status="ok").verified is True
        for bad in ("not_found", "missing_file", "unreachable", "gated"):
            assert RepoCheck(tier="t", repo="r", status=bad).verified is False
