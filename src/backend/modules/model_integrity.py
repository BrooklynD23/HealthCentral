"""Model-artifact integrity verification (MODEL-INT-001).

`download_models.py` and `model_selector.py` had no checksum handling at all.
That matters more here than in a typical app: every guardrail threshold and
every golden eval in this repo is tuned against specific model artifacts, so a
silently swapped GGUF silently invalidates the safety evidence without failing
anything visibly.

Design notes:

- **Unpinned is reported, never assumed good.** Several tiers cannot be pinned
  yet (the Gemma 4 repo URLs in `TIER_MODEL_CONFIG` are still placeholders).
  Those return ``UNPINNED``, which callers surface — inventing a hash, or
  treating "no pin" as "verified", would defeat the point.
- **Verification is advisory at load by default.** A local-first desktop app
  that hard-fails on an unrecognised model leaves the user with a broken app
  and no path forward. The mismatch is logged loudly and exposed to the caller;
  enforcement is a policy decision for the caller, not this module.
- **Hashing a 7 GB GGUF is expensive**, so results are cached by
  (path, mtime, size) — the cheap triple that changes whenever the bytes do.

Usage:
    python -m modules.model_integrity --hash path/to/model.gguf
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1024 * 1024  # 1 MiB — bounded memory on multi-GB artifacts

# Repo root is four levels up: modules/ -> backend/ -> src/ -> repo
_DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "model_manifest.json"
)


class IntegrityStatus(str, Enum):
    """Outcome of an integrity check."""

    VERIFIED = "verified"          # hash matches the pin
    MISMATCH = "mismatch"          # hash does NOT match the pin — the dangerous case
    UNPINNED = "unpinned"          # manifest has an entry but no hash yet
    UNKNOWN_TIER = "unknown_tier"  # no manifest entry at all
    MISSING_FILE = "missing_file"


@dataclass(frozen=True)
class IntegrityResult:
    status: IntegrityStatus
    tier: str
    path: Optional[Path] = None
    expected_sha256: Optional[str] = None
    actual_sha256: Optional[str] = None

    @property
    def is_trustworthy(self) -> bool:
        """True only when the artifact was actually checked against a pin.

        Deliberately False for UNPINNED: "we did not check" is not "it is fine".
        """
        return self.status is IntegrityStatus.VERIFIED

    @property
    def is_known_bad(self) -> bool:
        """True when the artifact demonstrably differs from the pinned bytes."""
        return self.status is IntegrityStatus.MISMATCH

    def describe(self) -> str:
        if self.status is IntegrityStatus.VERIFIED:
            return f"Model artifact for tier '{self.tier}' matches its pinned SHA256."
        if self.status is IntegrityStatus.MISMATCH:
            return (
                f"Model artifact for tier '{self.tier}' does NOT match its pinned "
                f"SHA256. Guardrail thresholds and golden evals were tuned against "
                f"the pinned artifact and may not hold for this one."
            )
        if self.status is IntegrityStatus.UNPINNED:
            return (
                f"Model artifact for tier '{self.tier}' has no pinned SHA256 in the "
                f"manifest, so its identity was not verified."
            )
        if self.status is IntegrityStatus.UNKNOWN_TIER:
            return f"No manifest entry for tier '{self.tier}'; identity not verified."
        return f"Model artifact for tier '{self.tier}' was not found on disk."


# Cache key: (resolved path, mtime_ns, size) — changes whenever the bytes do.
_hash_cache: dict[tuple[str, int, int], str] = {}


def compute_sha256(path: Path, *, use_cache: bool = True) -> str:
    """SHA256 of a file, streamed and cached by (path, mtime, size)."""
    resolved = path.resolve()
    stat = resolved.stat()
    key = (str(resolved), stat.st_mtime_ns, stat.st_size)

    if use_cache and key in _hash_cache:
        return _hash_cache[key]

    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            digest.update(chunk)

    result = digest.hexdigest()
    if use_cache:
        _hash_cache[key] = result
    return result


def clear_hash_cache() -> None:
    """Drop cached hashes (used by tests)."""
    _hash_cache.clear()


def load_manifest(manifest_path: Optional[Path] = None) -> dict[str, Any]:
    """Load the model manifest. Returns an empty manifest if absent."""
    path = manifest_path or _DEFAULT_MANIFEST
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Model manifest not found at %s; integrity checks disabled", path)
        return {"models": {}}
    except json.JSONDecodeError as exc:
        logger.error("Model manifest is not valid JSON (%s); integrity checks disabled", exc)
        return {"models": {}}


def verify_model_file(
    path: Path,
    tier: str,
    *,
    manifest_path: Optional[Path] = None,
) -> IntegrityResult:
    """Check a model artifact against its pinned SHA256.

    Never raises on a bad artifact — it reports. Enforcement is the caller's
    decision (see the module docstring).
    """
    entry = load_manifest(manifest_path).get("models", {}).get(tier)

    if entry is None:
        return IntegrityResult(status=IntegrityStatus.UNKNOWN_TIER, tier=tier, path=path)

    if not path.exists():
        return IntegrityResult(status=IntegrityStatus.MISSING_FILE, tier=tier, path=path)

    expected = entry.get("sha256")
    if not expected:
        return IntegrityResult(status=IntegrityStatus.UNPINNED, tier=tier, path=path)

    actual = compute_sha256(path)
    status = (
        IntegrityStatus.VERIFIED
        if actual.lower() == str(expected).lower()
        else IntegrityStatus.MISMATCH
    )
    return IntegrityResult(
        status=status,
        tier=tier,
        path=path,
        expected_sha256=expected,
        actual_sha256=actual,
    )


def verify_and_log(path: Path, tier: str, *, manifest_path: Optional[Path] = None) -> IntegrityResult:
    """verify_model_file, with the outcome logged at an appropriate level."""
    result = verify_model_file(path, tier, manifest_path=manifest_path)

    if result.is_known_bad:
        logger.error("MODEL-INT-001: %s", result.describe())
    elif result.status in (IntegrityStatus.UNPINNED, IntegrityStatus.UNKNOWN_TIER):
        logger.warning("MODEL-INT-001: %s", result.describe())
    elif result.status is IntegrityStatus.MISSING_FILE:
        logger.warning("MODEL-INT-001: %s", result.describe())
    else:
        logger.info("MODEL-INT-001: %s", result.describe())

    return result


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Model artifact integrity helper")
    parser.add_argument("--hash", metavar="PATH", help="Print the SHA256 of a file")
    parser.add_argument("--verify", nargs=2, metavar=("PATH", "TIER"),
                        help="Verify a file against its manifest pin")
    args = parser.parse_args()

    if args.hash:
        print(compute_sha256(Path(args.hash)))
        return 0
    if args.verify:
        result = verify_model_file(Path(args.verify[0]), args.verify[1])
        print(f"{result.status.value}: {result.describe()}")
        if result.actual_sha256:
            print(f"actual: {result.actual_sha256}")
        return 1 if result.is_known_bad else 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
