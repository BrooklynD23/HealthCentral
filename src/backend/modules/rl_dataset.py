"""
RL-ready dataset export module.

RL-FEED-002: Generates DPO/GRPO/SFT JSONL files from response_feedback rows.

Output files:
  - dpo_pairs.jsonl   — {"prompt", "chosen", "rejected"}
  - sft_positives.jsonl — {"prompt", "completion"}  (when no natural pair)
  - grpo_rewards.jsonl — {"prompt", "response", "reward"}
  - metadata.json     — counts, date range, model distribution, schema version

Pairing logic:
  - For each unique (prompt_snapshot, session_id) group:
      - If a correction_text exists on a negative turn → chosen=correction, rejected=response
      - Elif a positive turn AND a negative turn exist → chosen=positive response, rejected=negative response
      - Positive-only turns with no pairable negative → SFT file
  - Redaction is always applied before writing.

Privacy: redaction.RedactionEngine(policy_level="standard") is applied to
prompt_snapshot, response_text, and correction_text before any write.

Python 3.10-compatible.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.feedback_constants import VALID_TAGS
from modules.redaction import RedactionEngine

logger = logging.getLogger(__name__)

# Bump when the export schema changes
SCHEMA_VERSION = "1.0"

@dataclass
class FeedbackRecord:
    """In-memory representation of one response_feedback row."""

    id: str
    profile_id: str
    session_id: str
    turn_id: str
    rating: int  # +1 or -1
    correction_text: Optional[str]
    feedback_tags: Optional[list]
    prompt_snapshot: Optional[str]
    response_text: Optional[str]
    model_name: Optional[str]
    provider: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class ExportResult:
    """Summary returned to the API caller."""

    dpo_pairs_count: int = 0
    sft_positives_count: int = 0
    grpo_rewards_count: int = 0
    dpo_path: str = ""
    sft_path: str = ""
    grpo_path: str = ""
    metadata_path: str = ""
    redacted_fields: int = 0


def _redact(engine: RedactionEngine, text: Optional[str]) -> tuple[str, int]:
    """Redact text; return (redacted_text, redaction_count)."""
    if not text:
        return ("", 0)
    result = engine.redact(text)
    return (result.text, result.redacted_count)


def export_rl_datasets(
    records: list[FeedbackRecord],
    output_dir: str | Path,
    profile_id: str,
) -> ExportResult:
    """
    Build DPO / SFT / GRPO JSONL files from feedback records.

    Args:
        records:    List of FeedbackRecord objects (all for one profile).
        output_dir: Directory where JSONL files are written.
        profile_id: Used only in the metadata header (no PII).

    Returns:
        ExportResult with file paths and row counts.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    engine = RedactionEngine(policy_level="standard")
    result = ExportResult()

    total_redacted = 0

    # ------------------------------------------------------------------ #
    # 1. GRPO reward file — one row per feedback record                    #
    # ------------------------------------------------------------------ #
    grpo_path = out / "grpo_rewards.jsonl"
    grpo_rows: list[dict[str, Any]] = []
    for rec in records:
        prompt, rc1 = _redact(engine, rec.prompt_snapshot)
        response, rc2 = _redact(engine, rec.response_text)
        total_redacted += rc1 + rc2
        if not prompt or not response:
            continue
        grpo_rows.append({
            "prompt": prompt,
            "response": response,
            "reward": rec.rating,
            "model_name": rec.model_name or "",
            "provider": rec.provider or "",
            "tags": rec.feedback_tags or [],
            "turn_id": rec.turn_id,
        })

    _write_jsonl(grpo_path, grpo_rows)
    result.grpo_path = str(grpo_path)
    result.grpo_rewards_count = len(grpo_rows)

    # ------------------------------------------------------------------ #
    # 2. DPO pairs + SFT positives                                         #
    # ------------------------------------------------------------------ #
    # Group records by prompt_snapshot (normalised).  When prompts differ
    # but belong to the same session, we still allow pairing by session_id
    # as a fallback grouping key.
    #
    # Primary key: prompt_snapshot (first 2000 chars) to avoid near-duplicates
    # from minor context changes.  Fallback key: session_id.

    def _prompt_key(rec: FeedbackRecord) -> str:
        snap = (rec.prompt_snapshot or "")[:2000]
        return snap if snap else rec.session_id

    # Build groups
    groups: dict[str, list[FeedbackRecord]] = {}
    for rec in records:
        key = _prompt_key(rec)
        groups.setdefault(key, []).append(rec)

    dpo_rows: list[dict[str, Any]] = []
    sft_rows: list[dict[str, Any]] = []

    for _key, grp in groups.items():
        positives = [r for r in grp if r.rating == 1]
        negatives = [r for r in grp if r.rating == -1]

        for neg in negatives:
            prompt, rc1 = _redact(engine, neg.prompt_snapshot)
            rejected, rc2 = _redact(engine, neg.response_text)
            total_redacted += rc1 + rc2
            if not prompt or not rejected:
                continue

            # Priority 1: correction_text on this negative turn
            if neg.correction_text and neg.correction_text.strip():
                chosen, rc3 = _redact(engine, neg.correction_text)
                total_redacted += rc3
                if chosen:
                    dpo_rows.append({
                        "prompt": prompt,
                        "chosen": chosen,
                        "rejected": rejected,
                        "chosen_source": "correction",
                        "model_name": neg.model_name or "",
                        "provider": neg.provider or "",
                        "turn_id": neg.turn_id,
                    })
                    continue

            # Priority 2: positive response from the same group
            if positives:
                pos = positives[0]
                chosen, rc3 = _redact(engine, pos.response_text)
                total_redacted += rc3
                if chosen:
                    dpo_rows.append({
                        "prompt": prompt,
                        "chosen": chosen,
                        "rejected": rejected,
                        "chosen_source": "positive_response",
                        "model_name": neg.model_name or "",
                        "provider": neg.provider or "",
                        "turn_id_rejected": neg.turn_id,
                        "turn_id_chosen": pos.turn_id,
                    })
                    continue

        # Positives with no pairable negative → SFT file
        paired_positive_ids = set()
        for row in dpo_rows:
            if "turn_id_chosen" in row:
                paired_positive_ids.add(row["turn_id_chosen"])

        for pos in positives:
            if pos.turn_id in paired_positive_ids:
                continue
            # Also skip if this positive was paired via correction in another group
            prompt, rc1 = _redact(engine, pos.prompt_snapshot)
            completion, rc2 = _redact(engine, pos.response_text)
            total_redacted += rc1 + rc2
            if not prompt or not completion:
                continue
            # Check whether a DPO row was already created for this turn_id
            already_chosen = any(
                row.get("turn_id") == pos.turn_id
                for row in dpo_rows
                if "chosen_source" in row and row["chosen_source"] == "correction"
            )
            if not already_chosen:
                sft_rows.append({
                    "prompt": prompt,
                    "completion": completion,
                    "model_name": pos.model_name or "",
                    "provider": pos.provider or "",
                    "turn_id": pos.turn_id,
                })

    dpo_path = out / "dpo_pairs.jsonl"
    sft_path = out / "sft_positives.jsonl"
    _write_jsonl(dpo_path, dpo_rows)
    _write_jsonl(sft_path, sft_rows)
    result.dpo_path = str(dpo_path)
    result.sft_path = str(sft_path)
    result.dpo_pairs_count = len(dpo_rows)
    result.sft_positives_count = len(sft_rows)
    result.redacted_fields = total_redacted

    # ------------------------------------------------------------------ #
    # 3. Metadata header                                                   #
    # ------------------------------------------------------------------ #
    model_dist: dict[str, int] = {}
    provider_dist: dict[str, int] = {}
    dates: list[str] = []
    for rec in records:
        m = rec.model_name or "unknown"
        p = rec.provider or "unknown"
        model_dist[m] = model_dist.get(m, 0) + 1
        provider_dist[p] = provider_dist.get(p, 0) + 1
        dates.append(rec.created_at.isoformat())

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "total_feedback_records": len(records),
        "dpo_pairs": len(dpo_rows),
        "sft_positives": len(sft_rows),
        "grpo_rewards": len(grpo_rows),
        "redacted_field_occurrences": total_redacted,
        "date_range": {
            "earliest": min(dates) if dates else None,
            "latest": max(dates) if dates else None,
        },
        "model_distribution": model_dist,
        "provider_distribution": provider_dist,
        "files": {
            "dpo_pairs": str(dpo_path),
            "sft_positives": str(sft_path),
            "grpo_rewards": str(grpo_path),
        },
    }
    metadata_path = out / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    result.metadata_path = str(metadata_path)

    logger.info(
        "RL dataset export complete: %d DPO pairs, %d SFT, %d GRPO, %d redactions",
        result.dpo_pairs_count,
        result.sft_positives_count,
        result.grpo_rewards_count,
        result.redacted_fields,
    )
    return result


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write list of dicts to a JSONL file (one JSON object per line)."""
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
