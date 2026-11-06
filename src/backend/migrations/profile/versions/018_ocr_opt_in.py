"""Switch OCR off for every profile saved before OCR became opt-in.

OCR-OPT-IN-MIGRATION: ``006_ocr_preference`` added ``ocr_preference_enabled``
with a server default of 1. The model has defaulted to False since
OCR-DEFAULT-ON, but a settings row written earlier (a tier save, a voice toggle,
hardware detection) still holds 1, so an existing profile would keep reading
scans without the patient having chosen it.

``upgrade()`` sets every row to 0 with one UPDATE. Data only: no column, no
server default and no table rebuild changes, so the schema fingerprint of 018 is
the one of 017 (see ``DATA_ONLY_REVISIONS`` in test_fk_migration_017.py). A
profile that opted in on purpose after that change is switched off too; the
migration cannot tell an opt-in from an old default. The patient opts in again
in Settings.

``downgrade()`` is a no-op. The values before the upgrade cannot be known: a 1
could be an old default or a deliberate opt-in, and nothing was recorded.

Revision ID: 018_ocr_opt_in
Revises: 017_fk_cascade_alignment
Create Date: 2026-11-06
"""

from typing import Sequence, Union

from alembic import op

revision: str = "018_ocr_opt_in"
down_revision: Union[str, None] = "017_fk_cascade_alignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE user_model_settings SET ocr_preference_enabled = 0")


def downgrade() -> None:
    # Nothing to restore: the earlier values were not recorded and cannot be known.
    pass
