"""HC-MMP: config/model_manifest.json repos must agree with TIER_MODEL_CONFIG (MODEL-MANIFEST-MID-PHI3)."""
import json
from pathlib import Path

from modules.model_selector import TIER_MODEL_CONFIG

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = json.loads((REPO_ROOT / "config" / "model_manifest.json").read_text(encoding="utf-8"))["models"]


def test_hc_mmp_001_manifest_repos_match_tier_model_config():
    shared = set(MANIFEST) & set(TIER_MODEL_CONFIG)
    assert {"low", "mid", "high"} <= shared
    mismatches = {
        k: (MANIFEST[k]["repo"], TIER_MODEL_CONFIG[k]["repo"])
        for k in sorted(shared)
        if MANIFEST[k]["repo"] != TIER_MODEL_CONFIG[k]["repo"]
    }
    assert not mismatches, mismatches
