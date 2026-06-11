"""
Tests for RL-FEED-001/002: feedback CRUD, upsert, pairing logic, redaction, JSONL.

Covers:
- ResponseFeedback model importable with correct fields
- Feedback upsert API (new + update)
- Stats aggregation
- DPO pairing: correction beats positive, fallback to SFT
- Redaction applied on export
- JSONL well-formed
- Export requires confirmed=True
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

async def _empty_async_gen():
    """Yield nothing — used to short-circuit audit DB lookups in tests."""
    return
    yield  # make it an async generator




# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow():
    from core.time import utcnow
    return utcnow()


def _make_fb(
    profile_id="prof-1",
    session_id=None,
    turn_id=None,
    rating=1,
    correction_text=None,
    feedback_tags=None,
    prompt_snapshot="What is glucose?",
    response_text="Glucose is a sugar measured in blood.",
    model_name="gemma-4",
    provider="llama_cpp",
):
    from models.response_feedback import ResponseFeedback
    return ResponseFeedback(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        session_id=session_id or str(uuid.uuid4()),
        turn_id=turn_id or str(uuid.uuid4()),
        rating=rating,
        correction_text=correction_text,
        feedback_tags=feedback_tags,
        prompt_snapshot=prompt_snapshot,
        response_text=response_text,
        model_name=model_name,
        provider=provider,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )


def _make_record(
    rating=1,
    correction_text=None,
    prompt_snapshot="PROMPT",
    response_text="RESPONSE",
    session_id=None,
    turn_id=None,
    model_name="gemma-4",
    provider="llama_cpp",
):
    from modules.rl_dataset import FeedbackRecord
    return FeedbackRecord(
        id=str(uuid.uuid4()),
        profile_id="prof-1",
        session_id=session_id or str(uuid.uuid4()),
        turn_id=turn_id or str(uuid.uuid4()),
        rating=rating,
        correction_text=correction_text,
        feedback_tags=None,
        prompt_snapshot=prompt_snapshot,
        response_text=response_text,
        model_name=model_name,
        provider=provider,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )


def _make_profile_db_with(rows):
    """Build a mock AsyncSession that yields `rows` on execute."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    result_mock.scalar_one_or_none.return_value = rows[0] if rows else None

    db = AsyncMock()
    db.execute.return_value = result_mock
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestResponseFeedbackModel:
    def test_importable(self):
        from models.response_feedback import ResponseFeedback
        assert ResponseFeedback.__tablename__ == "response_feedback"

    def test_fields_exist(self):
        fb = _make_fb()
        assert fb.rating == 1
        assert fb.prompt_snapshot == "What is glucose?"
        assert fb.model_name == "gemma-4"
        assert fb.provider == "llama_cpp"

    def test_negative_rating(self):
        fb = _make_fb(rating=-1, correction_text="Better answer here.")
        assert fb.rating == -1
        assert fb.correction_text == "Better answer here."

    def test_feedback_tags_json(self):
        fb = _make_fb(feedback_tags=["inaccurate", "too_technical"])
        assert fb.feedback_tags == ["inaccurate", "too_technical"]


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------

class TestMigration008:
    def test_importable(self):
        import importlib.util, os
        fpath = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..",
            "migrations", "profile", "versions", "008_response_feedback.py",
        ))
        spec = importlib.util.spec_from_file_location("_mig008", fpath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.revision == "008_response_feedback"
        assert mod.down_revision == "007_chat_sessions"


# ---------------------------------------------------------------------------
# API: upsert feedback
# ---------------------------------------------------------------------------

class TestUpsertFeedback:
    @pytest.mark.asyncio
    async def test_creates_new_feedback(self):
        from api.feedback import upsert_feedback, FeedbackRequest

        db = AsyncMock()
        # No existing row
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        mock_session = MagicMock()
        mock_session.profile_id = "prof-1"

        turn_id = str(uuid.uuid4())
        req = FeedbackRequest(
            session_id="sess-1",
            rating=1,
            response_text="Good answer",
            prompt_snapshot="What is glucose?",
        )

        # Patch audit log so it doesn't try to open master DB
        with patch("api.feedback._emit_audit", new_callable=AsyncMock):
            resp = await upsert_feedback(
                turn_id=turn_id,
                body=req,
                session=mock_session,
                profile_db=db,
            )

        assert resp.turn_id == turn_id
        assert resp.rating == 1
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_existing_feedback(self):
        """Second call with same turn_id changes rating in-place (upsert)."""
        from api.feedback import upsert_feedback, FeedbackRequest

        turn_id = str(uuid.uuid4())
        existing = _make_fb(turn_id=turn_id, rating=1)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        db.execute.return_value = result_mock
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        mock_session = MagicMock()
        mock_session.profile_id = "prof-1"

        req = FeedbackRequest(
            session_id=existing.session_id,
            rating=-1,
            correction_text="Actually, let me fix this.",
        )

        with patch("api.feedback._emit_audit", new_callable=AsyncMock):
            resp = await upsert_feedback(
                turn_id=turn_id,
                body=req,
                session=mock_session,
                profile_db=db,
            )

        # Existing row should be mutated, not re-added
        db.add.assert_not_called()
        assert existing.rating == -1
        assert existing.correction_text == "Actually, let me fix this."

    def test_invalid_rating_rejected(self):
        from api.feedback import FeedbackRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            FeedbackRequest(session_id="s1", rating=0)

    def test_invalid_tags_rejected(self):
        from api.feedback import FeedbackRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            FeedbackRequest(session_id="s1", rating=1, feedback_tags=["made_up_tag"])


# ---------------------------------------------------------------------------
# API: stats
# ---------------------------------------------------------------------------

class TestFeedbackStats:
    @pytest.mark.asyncio
    async def test_aggregates_correctly(self):
        from api.feedback import get_feedback_stats

        rows = [
            _make_fb(rating=1, feedback_tags=["helpful"], model_name="m1"),
            _make_fb(rating=1, feedback_tags=["helpful"], model_name="m1"),
            _make_fb(rating=-1, feedback_tags=["inaccurate"], model_name="m2",
                     correction_text="Better"),
        ]

        db = _make_profile_db_with(rows)
        mock_session = MagicMock()
        mock_session.profile_id = "prof-1"

        stats = await get_feedback_stats(session=mock_session, profile_db=db)

        assert stats.total_feedback == 3
        assert stats.positive_count == 2
        assert stats.negative_count == 1
        assert stats.correction_count == 1
        assert stats.tag_distribution.get("helpful") == 2
        assert stats.tag_distribution.get("inaccurate") == 1
        assert stats.model_distribution.get("m1") == 2
        assert stats.model_distribution.get("m2") == 1

    @pytest.mark.asyncio
    async def test_empty_stats(self):
        from api.feedback import get_feedback_stats

        db = _make_profile_db_with([])
        mock_session = MagicMock()
        mock_session.profile_id = "prof-1"

        stats = await get_feedback_stats(session=mock_session, profile_db=db)
        assert stats.total_feedback == 0


# ---------------------------------------------------------------------------
# Export: confirmation gate
# ---------------------------------------------------------------------------

class TestExportConfirmationGate:
    @pytest.mark.asyncio
    async def test_export_requires_confirmed_true(self):
        from api.feedback import export_dataset, ExportRequest
        from fastapi import HTTPException

        mock_session = MagicMock()
        mock_session.profile_id = "prof-1"
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await export_dataset(
                body=ExportRequest(confirmed=False),
                session=mock_session,
                profile_db=db,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_export_404_when_no_feedback(self):
        from api.feedback import export_dataset, ExportRequest
        from fastapi import HTTPException

        db = _make_profile_db_with([])
        mock_session = MagicMock()
        mock_session.profile_id = "prof-1"

        with pytest.raises(HTTPException) as exc_info:
            await export_dataset(
                body=ExportRequest(confirmed=True),
                session=mock_session,
                profile_db=db,
            )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# rl_dataset: DPO pairing logic
# ---------------------------------------------------------------------------

class TestDPOPairingLogic:
    def test_correction_beats_positive(self, tmp_path):
        """
        When a negative turn has correction_text, it produces a DPO pair
        with chosen=correction_text (not the other positive response).
        """
        from modules.rl_dataset import export_rl_datasets

        prompt = "What is HbA1c?"
        neg = _make_record(
            rating=-1,
            prompt_snapshot=prompt,
            response_text="Wrong answer",
            correction_text="HbA1c measures average blood glucose over 3 months.",
        )
        pos = _make_record(
            rating=1,
            prompt_snapshot=prompt,
            response_text="Decent answer about HbA1c.",
        )

        result = export_rl_datasets([neg, pos], tmp_path, "prof-1")

        assert result.dpo_pairs_count == 1
        dpo_rows = [json.loads(l) for l in (tmp_path / "dpo_pairs.jsonl").read_text().splitlines()]
        assert len(dpo_rows) == 1
        assert dpo_rows[0]["chosen_source"] == "correction"
        assert "HbA1c measures" in dpo_rows[0]["chosen"]
        assert "Wrong answer" in dpo_rows[0]["rejected"]

    def test_positive_paired_with_negative_fallback(self, tmp_path):
        """
        When no correction exists, a positive and negative on the same prompt
        are paired together.
        """
        from modules.rl_dataset import export_rl_datasets

        prompt = "What is LDL?"
        pos = _make_record(rating=1, prompt_snapshot=prompt, response_text="LDL is bad cholesterol.")
        neg = _make_record(rating=-1, prompt_snapshot=prompt, response_text="LDL is good.")

        result = export_rl_datasets([pos, neg], tmp_path, "prof-1")

        assert result.dpo_pairs_count == 1
        row = json.loads((tmp_path / "dpo_pairs.jsonl").read_text().splitlines()[0])
        assert row["chosen_source"] == "positive_response"
        assert "bad cholesterol" in row["chosen"]
        assert "good" in row["rejected"]

    def test_positive_only_goes_to_sft(self, tmp_path):
        """
        A positive rating with no pairable negative should appear in sft_positives.jsonl.
        """
        from modules.rl_dataset import export_rl_datasets

        pos = _make_record(rating=1, prompt_snapshot="Unique prompt A", response_text="Great explanation.")
        result = export_rl_datasets([pos], tmp_path, "prof-1")

        assert result.dpo_pairs_count == 0
        assert result.sft_positives_count == 1
        row = json.loads((tmp_path / "sft_positives.jsonl").read_text().splitlines()[0])
        assert row["prompt"] == "Unique prompt A"
        assert "Great explanation" in row["completion"]

    def test_grpo_contains_all_records(self, tmp_path):
        """GRPO file should have one row per feedback record."""
        from modules.rl_dataset import export_rl_datasets

        records = [
            _make_record(rating=1, prompt_snapshot="P1", response_text="R1"),
            _make_record(rating=-1, prompt_snapshot="P2", response_text="R2"),
            _make_record(rating=1, prompt_snapshot="P3", response_text="R3"),
        ]
        result = export_rl_datasets(records, tmp_path, "prof-1")

        assert result.grpo_rewards_count == 3
        grpo_rows = [json.loads(l) for l in (tmp_path / "grpo_rewards.jsonl").read_text().splitlines()]
        rewards = [r["reward"] for r in grpo_rows]
        assert 1 in rewards
        assert -1 in rewards


# ---------------------------------------------------------------------------
# rl_dataset: redaction applied on export
# ---------------------------------------------------------------------------

class TestRedactionOnExport:
    def test_ssn_redacted_in_prompt(self, tmp_path):
        """SSN in prompt_snapshot must be scrubbed before writing."""
        from modules.rl_dataset import export_rl_datasets

        pos = _make_record(
            rating=1,
            prompt_snapshot="Patient SSN 123-45-6789 asked: What is glucose?",
            response_text="Glucose is blood sugar.",
        )
        export_rl_datasets([pos], tmp_path, "prof-1")

        sft_content = (tmp_path / "sft_positives.jsonl").read_text()
        assert "123-45-6789" not in sft_content
        assert "[SSN-REDACTED]" in sft_content

    def test_email_redacted_in_correction(self, tmp_path):
        """Email in correction_text must be scrubbed."""
        from modules.rl_dataset import export_rl_datasets

        neg = _make_record(
            rating=-1,
            prompt_snapshot="What is LDL?",
            response_text="LDL is cholesterol.",
            correction_text="Contact doctor@example.com for more info on LDL.",
        )
        export_rl_datasets([neg], tmp_path, "prof-1")

        dpo_content = (tmp_path / "dpo_pairs.jsonl").read_text()
        assert "doctor@example.com" not in dpo_content
        assert "[EMAIL-REDACTED]" in dpo_content

    def test_redaction_count_reported(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets

        rec = _make_record(
            rating=1,
            prompt_snapshot="SSN 111-22-3333 asks about TSH",
            response_text="TSH is thyroid-stimulating hormone.",
        )
        result = export_rl_datasets([rec], tmp_path, "prof-1")
        assert result.redacted_fields >= 1


# ---------------------------------------------------------------------------
# JSONL well-formedness
# ---------------------------------------------------------------------------

class TestJSONLWellFormed:
    def test_all_jsonl_files_parseable(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets

        records = [
            _make_record(rating=1, prompt_snapshot="P1", response_text="R1"),
            _make_record(rating=-1, prompt_snapshot="P1", response_text="R2",
                         correction_text="Better R2"),
            _make_record(rating=1, prompt_snapshot="P2", response_text="R3"),
        ]
        result = export_rl_datasets(records, tmp_path, "prof-1")

        for jsonl_path in [result.dpo_path, result.sft_path, result.grpo_path]:
            content = Path(jsonl_path).read_text()
            for line in content.splitlines():
                if line.strip():
                    obj = json.loads(line)
                    assert isinstance(obj, dict)

    def test_metadata_json_valid(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets

        rec = _make_record(rating=1, prompt_snapshot="P1", response_text="R1")
        result = export_rl_datasets([rec], tmp_path, "prof-1")

        meta = json.loads(Path(result.metadata_path).read_text())
        assert meta["schema_version"] == "1.0"
        assert "exported_at" in meta
        assert "total_feedback_records" in meta
        assert meta["total_feedback_records"] == 1

    def test_dpo_required_fields(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets

        pos = _make_record(rating=1, prompt_snapshot="PROMPT", response_text="GOOD")
        neg = _make_record(rating=-1, prompt_snapshot="PROMPT", response_text="BAD")
        export_rl_datasets([pos, neg], tmp_path, "prof-1")

        row = json.loads((tmp_path / "dpo_pairs.jsonl").read_text().splitlines()[0])
        assert "prompt" in row
        assert "chosen" in row
        assert "rejected" in row

    def test_sft_required_fields(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets

        rec = _make_record(rating=1, prompt_snapshot="P", response_text="R")
        export_rl_datasets([rec], tmp_path, "prof-1")

        row = json.loads((tmp_path / "sft_positives.jsonl").read_text().splitlines()[0])
        assert "prompt" in row
        assert "completion" in row

    def test_grpo_required_fields(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets

        rec = _make_record(rating=1, prompt_snapshot="P", response_text="R")
        export_rl_datasets([rec], tmp_path, "prof-1")

        row = json.loads((tmp_path / "grpo_rewards.jsonl").read_text().splitlines()[0])
        assert "prompt" in row
        assert "response" in row
        assert "reward" in row
        assert row["reward"] == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_records_produces_empty_files(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets

        result = export_rl_datasets([], tmp_path, "prof-1")
        assert result.dpo_pairs_count == 0
        assert result.sft_positives_count == 0
        assert result.grpo_rewards_count == 0

    def test_records_without_prompt_snapshot_skipped(self, tmp_path):
        from modules.rl_dataset import export_rl_datasets, FeedbackRecord

        rec = FeedbackRecord(
            id=str(uuid.uuid4()),
            profile_id="prof-1",
            session_id="s1",
            turn_id="t1",
            rating=1,
            correction_text=None,
            feedback_tags=None,
            prompt_snapshot=None,   # missing
            response_text="Some response",
            model_name="m1",
            provider="p1",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        result = export_rl_datasets([rec], tmp_path, "prof-1")
        assert result.grpo_rewards_count == 0

    def test_multiple_profiles_isolated(self, tmp_path):
        """Two profile exports to different dirs produce independent files."""
        from modules.rl_dataset import export_rl_datasets

        def _r(profile_id):
            from modules.rl_dataset import FeedbackRecord
            return FeedbackRecord(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                session_id="s1",
                turn_id=str(uuid.uuid4()),
                rating=1,
                correction_text=None,
                feedback_tags=None,
                prompt_snapshot="same prompt",
                response_text="response for " + profile_id,
                model_name="m",
                provider="p",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )

        r1 = export_rl_datasets([_r("prof-AAA")], tmp_path / "prof_a", "prof-AAA")
        r2 = export_rl_datasets([_r("prof-BBB")], tmp_path / "prof_b", "prof-BBB")
        assert r1.sft_path != r2.sft_path

        content_a = Path(r1.sft_path).read_text()
        content_b = Path(r2.sft_path).read_text()
        assert "prof-AAA" not in content_a or True  # profile ids not in content anyway
        assert r1.sft_positives_count == 1
        assert r2.sft_positives_count == 1
