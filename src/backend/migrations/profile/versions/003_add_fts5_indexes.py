"""Add FTS5 virtual tables for search.

Revision ID: 003
Revises: 002
Create Date: 2026-02-15

Design Decision DD-5: Index both observations and chunks for full-text search.
"""

revision = "003"
down_revision = "002"

from alembic import op


def upgrade() -> None:
    # FTS5 for observations (analyte names, text values, notes)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
        USING fts5(
            analyte_canonical,
            analyte_raw,
            value_text,
            notes,
            content=observations,
            content_rowid=rowid
        )
    """)

    # FTS5 for document chunks (full text content)
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(
            text,
            content=chunks,
            content_rowid=rowid
        )
    """)

    # Triggers to keep FTS indexes in sync with source tables
    # Observations
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS observations_ai AFTER INSERT ON observations BEGIN
            INSERT INTO observations_fts(rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES (new.rowid, new.analyte_canonical, new.analyte_raw, new.value_text, new.notes);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS observations_ad AFTER DELETE ON observations BEGIN
            INSERT INTO observations_fts(observations_fts, rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES ('delete', old.rowid, old.analyte_canonical, old.analyte_raw, old.value_text, old.notes);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS observations_au AFTER UPDATE ON observations BEGIN
            INSERT INTO observations_fts(observations_fts, rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES ('delete', old.rowid, old.analyte_canonical, old.analyte_raw, old.value_text, old.notes);
            INSERT INTO observations_fts(rowid, analyte_canonical, analyte_raw, value_text, notes)
            VALUES (new.rowid, new.analyte_canonical, new.analyte_raw, new.value_text, new.notes);
        END
    """)

    # Chunks
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text)
            VALUES (new.rowid, new.text);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text)
            VALUES ('delete', old.rowid, old.text);
        END
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text)
            VALUES ('delete', old.rowid, old.text);
            INSERT INTO chunks_fts(rowid, text)
            VALUES (new.rowid, new.text);
        END
    """)

    # Backfill existing data into FTS indexes
    op.execute("""
        INSERT INTO observations_fts(rowid, analyte_canonical, analyte_raw, value_text, notes)
        SELECT rowid, analyte_canonical, analyte_raw, value_text, notes FROM observations
    """)
    op.execute("""
        INSERT INTO chunks_fts(rowid, text)
        SELECT rowid, text FROM chunks
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS observations_ai")
    op.execute("DROP TRIGGER IF EXISTS observations_ad")
    op.execute("DROP TRIGGER IF EXISTS observations_au")
    op.execute("DROP TRIGGER IF EXISTS chunks_ai")
    op.execute("DROP TRIGGER IF EXISTS chunks_ad")
    op.execute("DROP TRIGGER IF EXISTS chunks_au")
    op.execute("DROP TABLE IF EXISTS observations_fts")
    op.execute("DROP TABLE IF EXISTS chunks_fts")
