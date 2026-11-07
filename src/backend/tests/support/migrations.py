"""Profile-chain head, kept in one place.

The value stays hard-coded on purpose: a test that compares the live head to
this constant still fails when a migration is added without updating it, so no
assertion is weakened. A later profile migration edits this one line instead of
every test that names the head (C-PMIG carrier, lane C section 3.0).
"""

PROFILE_HEAD: str = "019_export_artifacts"
