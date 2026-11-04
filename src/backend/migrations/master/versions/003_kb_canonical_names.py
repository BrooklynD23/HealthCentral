"""Rename knowledge-base rows to the names the normalizer stores (KB-CANONICAL-NAMES).

Revision ID: 003_kb_canonical_names
Revises: 002_backup_schedules
Create Date: 2026-11-04

`NormalizeModule.normalize_analyte` stores `white_blood_cells`, `hba1c` and `glucose`.
The knowledge base was seeded as `wbc`, `hemoglobin_a1c` and `glucose_fasting`, and
read by exact match, so those rows never loaded. The lipid relationship rows were
seeded under panel `lipid_panel`, but the panel key is `lipid`.

Data only, in the MASTER chain (the knowledge tables are in the master database).
No model or seed import, no row is added, and rows keep their ids, so a stored
`[KB:id]` citation stays valid. Every statement matches on the old value, so a second
run changes nothing.

When a row under the new name already exists (for example the standalone seed script
added it beside the old one), the row under the new name is kept and the old row is
deleted. `biomarker_knowledge.analyte_canonical` is unique, and the seeds look rows up
with `scalar_one_or_none` on the other two tables, so a duplicate would raise at the
next startup.

Downgrade runs the same logic with the maps inverted, so the old code's seed finds
its rows again instead of adding a second one beside a renamed one.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_kb_canonical_names"
down_revision: Union[str, None] = "002_backup_schedules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen on purpose: the migration must not follow later edits to the seed.
ANALYTE_RENAMES = {
    "glucose_fasting": "glucose",
    "hemoglobin_a1c": "hba1c",
    "wbc": "white_blood_cells",
}
PANEL_RENAMES = {"lipid_panel": "lipid"}

# The `diabetes` relationship panel_name stays: no PANEL_DEFINITIONS key is called that.


def _rename_biomarkers(bind, old: str, new: str) -> None:
    params = {"old": old, "new": new}
    # analyte_canonical is unique: decide the collision first.
    bind.execute(
        sa.text(
            "DELETE FROM biomarker_knowledge WHERE analyte_canonical = :old "
            "AND EXISTS (SELECT 1 FROM biomarker_knowledge WHERE analyte_canonical = :new)"
        ),
        params,
    )
    bind.execute(
        sa.text("UPDATE biomarker_knowledge SET analyte_canonical = :new WHERE analyte_canonical = :old"),
        params,
    )


def _rename_interventions(bind, old: str, new: str) -> None:
    params = {"old": old, "new": new}
    # The seed's key is (analyte_canonical, condition_type, intervention_title).
    bind.execute(
        sa.text(
            "DELETE FROM intervention_mappings WHERE analyte_canonical = :old AND EXISTS ("
            "SELECT 1 FROM intervention_mappings n WHERE n.analyte_canonical = :new "
            "AND n.condition_type = intervention_mappings.condition_type "
            "AND n.intervention_title = intervention_mappings.intervention_title)"
        ),
        params,
    )
    bind.execute(
        sa.text("UPDATE intervention_mappings SET analyte_canonical = :new WHERE analyte_canonical = :old"),
        params,
    )


def _rename_relationships(bind, analytes: dict[str, str]) -> None:
    # primary_analyte and related_analyte can both need a rename in one row, so the key
    # (primary, related, relationship_type) is mapped in Python and compared as a whole.
    rows = bind.execute(
        sa.text(
            "SELECT id, primary_analyte, related_analyte, relationship_type "
            "FROM biomarker_relationships ORDER BY id"
        )
    ).fetchall()
    for row_id, primary, related, rel_type in rows:
        new_primary = analytes.get(primary, primary)
        new_related = analytes.get(related, related)
        if (new_primary, new_related) == (primary, related):
            continue
        target = {"p": new_primary, "r": new_related, "t": rel_type, "id": row_id}
        taken = bind.execute(
            sa.text(
                "SELECT 1 FROM biomarker_relationships WHERE primary_analyte = :p "
                "AND related_analyte = :r AND relationship_type = :t AND id != :id"
            ),
            target,
        ).first()
        if taken:
            bind.execute(sa.text("DELETE FROM biomarker_relationships WHERE id = :id"), target)
        else:
            bind.execute(
                sa.text(
                    "UPDATE biomarker_relationships SET primary_analyte = :p, related_analyte = :r "
                    "WHERE id = :id"
                ),
                target,
            )


def _apply(analytes: dict[str, str], panels: dict[str, str]) -> None:
    bind = op.get_bind()
    for old, new in analytes.items():
        _rename_biomarkers(bind, old, new)
        _rename_interventions(bind, old, new)
    _rename_relationships(bind, analytes)
    for old, new in panels.items():
        bind.execute(
            sa.text("UPDATE biomarker_relationships SET panel_name = :new WHERE panel_name = :old"),
            {"old": old, "new": new},
        )


def upgrade() -> None:
    _apply(ANALYTE_RENAMES, PANEL_RENAMES)


def downgrade() -> None:
    _apply(
        {new: old for old, new in ANALYTE_RENAMES.items()},
        {new: old for old, new in PANEL_RENAMES.items()},
    )
