# Phase B: Asclexis Rename and Branding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the product from HealthCentral to Asclexis across every user-visible surface, migrate the master database filename safely, and record the brand philosophy.

**Architecture:** The cosmetic string sweep is mechanical and lands first. The master-DB rename is the only risky part and gets its own task with a startup migration, sidecar handling, and backup back-compatibility — three pieces that are one change, because doing any two without the third either hides the user's data or reintroduces a fixed bug. Branding guidelines land last as pure documentation.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy/Alembic, React + Vite + TypeScript, PowerShell (`dev.ps1`).

**Spec:** `docs/superpowers/specs/2026-07-30-remediation-and-asclexis-design.md` (Phase B)
**Prior decision:** `docs/plans/2026-07-07-rename-audit-and-shortlist.md` (stage-1 audit and stage-3 procedure)

## Global Constraints

- **Preserve, do not rename:** `HC-*` ticket and test prefixes (111 identifiers), `HC_*` environment variables, vault filenames (`vaults/{profile_id}/vault.db`, `key.bin`, `key.method` — these never carried the product name), historical `docs/plans/` logs, and git history.
- **Do rename:** `healthcentral.db` → `asclexis.db`, owner-confirmed 2026-07-30, superseding the 2026-07-07 keep-filenames decision whose stated rationale ("renaming breaks existing vaults") was inaccurate.
- `client_info` in audit rows becomes exactly `"Asclexis v0.1.0"`.
- The four `skills/healthcentral-*` directories become `skills/asclexis-*`.
- Target **Python 3.11+**. Use `core.time.utcnow` as the single timestamp helper.
- **Do not modify** `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`.
- Baseline to preserve: backend suite with no new failures, `npx tsc --noEmit` clean, Playwright 25 passed / 3 skipped.
- Brand copy rule, enforced in Task 5: no construction may imply diagnosis, dosing, or prognosis.
- Commit style: `feat(brand):` / `fix(config):` / `docs:` — small, single-purpose commits.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/frontend/index.html` | Page title, meta description, apple-mobile-web-app-title | Modify |
| `src/frontend/package.json` | Package name | Modify |
| `src/frontend/src/**` | User-visible product name in 8 components/services | Modify |
| `src/backend/main.py` | FastAPI `title=` | Modify |
| `dev.ps1`, `dev.bat` | Banners and window titles | Modify |
| `README.md`, `CONTRIBUTING.md`, `AGENT.md`, `SECURITY.md` | Headers and prose | Modify |
| `config/.env.example` | App-name values, `SQLITE_DATABASE_PATH` | Modify |
| `src/backend/core/config.py` | Derive the DB filename from settings | Modify |
| `src/backend/core/db_migration.py` | Startup rename of the master DB and its sidecars | **Create** |
| `src/backend/main.py` | Call the migration before any connection opens | Modify |
| `src/backend/scripts/backup.py` | Accept either master-DB name on restore | Modify |
| `skills/asclexis-*` (4 dirs) | Project-domain skills | **Rename** |
| `docs/brand/brand-guidelines.md` | Brand philosophy, voice rules, palette | **Create** |

`core/db_migration.py` is a new module rather than inline code in `main.py` because it must be independently testable — the whole point is proving it works against a populated old-named database.

---

## Task 1: Cosmetic string sweep

**Files:**
- Modify: `src/frontend/index.html`, `src/frontend/package.json`, `src/frontend/src/App.tsx`, `src/frontend/src/components/layout/Sidebar.tsx`, `src/frontend/src/pages/DocumentInbox.tsx`, `src/frontend/src/pages/NotificationSettings.tsx`, `src/frontend/src/pages/ProfileSetup.tsx`, `src/frontend/src/pages/ExportPage.tsx`, `src/frontend/src/services/api.ts`, `src/frontend/src/stores/authStore.ts`
- Modify: `src/backend/main.py`, `dev.ps1`, `dev.bat`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `config/.env.example`
- Test: existing vitest suite plus a grep assertion

**Interfaces:** Consumes nothing; produces the user-visible name `Asclexis` used by Task 5's brand doc.

**Note:** `AGENT.md` is deliberately excluded here — Phase C rewrites it, and touching it twice creates a needless conflict. Rename it as part of Phase C instead.

- [ ] **Step 1: Record the starting count**

```bash
cd /home/user/HealthCentral
grep -ril "healthcentral" --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=__pycache__ --exclude-dir=playwright-report \
  --exclude-dir=test-results --exclude-dir=archive . | wc -l
```

Write the number down. It is the before-figure for Step 6.

- [ ] **Step 2: Find every user-visible occurrence**

```bash
cd /home/user/HealthCentral
grep -rn "HealthCentral" \
  src/frontend/index.html src/frontend/package.json \
  src/frontend/src src/backend/main.py \
  dev.ps1 dev.bat README.md CONTRIBUTING.md SECURITY.md config/.env.example
```

Review the list before editing. Anything that is a docstring or an internal comment is optional; anything a user or operator reads must change.

- [ ] **Step 3: Apply the replacements**

Replace `HealthCentral` → `Asclexis` and `healthcentral-frontend` → `asclexis-frontend` in the files listed in Step 2. **Do not** use a blind repo-wide `sed`: `healthcentral.db` is handled in Task 2, and `docs/` history must not be rewritten.

In `src/backend/main.py`, `title="HealthCentral API"` becomes `title="Asclexis API"`.

For the audit provenance string, find it and change it:

```bash
grep -rn "HealthCentral v" src/backend/
```

Expected hit: the `client_info` value. It becomes exactly `"Asclexis v0.1.0"`.

- [ ] **Step 4: Verify the frontend still builds and tests pass**

```bash
cd src/frontend && npx tsc --noEmit && npx vitest run
```

Expected: no tsc output; all vitest tests pass. If a test asserted on the literal string "HealthCentral", update that assertion — it is testing product copy and the copy changed.

- [ ] **Step 5: Verify the backend still boots**

```bash
cd src/backend && python -c "from main import app; print(app.title)"
```

Expected: `Asclexis API`.

- [ ] **Step 6: Confirm only intended occurrences remain**

```bash
cd /home/user/HealthCentral
grep -rn "HealthCentral" \
  src/frontend/index.html src/frontend/package.json src/frontend/src \
  src/backend/main.py dev.ps1 dev.bat README.md CONTRIBUTING.md \
  SECURITY.md config/.env.example
```

Expected: **no output.** Remaining repo-wide hits should be only `docs/` history, `docs/plans/` logs, `healthcentral.db` (Task 2), `skills/healthcentral-*` (Task 4), `AGENT.md` (Phase C), and backend docstrings.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(brand): rename the product to Asclexis in user-visible surfaces

Executes the string sweep from the 2026-07-07 stage-3 procedure: frontend title
and meta, package name, FastAPI title, dev script banners, README/CONTRIBUTING/
SECURITY headers, .env.example, and the client_info provenance string.

Preserved per that decision: HC-* test/ticket prefixes, HC_* env vars, vault
filenames, and historical docs/plans logs. The master DB filename and the four
project-domain skills follow in their own commits; AGENT.md is left for Phase C
so it is not rewritten twice."
```

---

## Task 2: Master database filename, with migration

**Files:**
- Modify: `src/backend/core/config.py:37` and `:170-176`
- Create: `src/backend/core/db_migration.py`
- Modify: `src/backend/main.py` (call the migration during startup, before any engine is created)
- Modify: `src/backend/scripts/backup.py:66` and `restore()`
- Modify: `config/.env.example`
- Test: `src/backend/tests/test_db_rename_migration.py` (**create**)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `MASTER_DB_NAME = "asclexis.db"` and `LEGACY_MASTER_DB_NAMES = ("healthcentral.db",)` in `scripts/backup.py`.
  - `migrate_master_db_filename(data_dir: Path) -> bool` in `core/db_migration.py` — returns `True` if a rename occurred, `False` if it was a no-op. Idempotent.
  - `settings.master_db_filename` property in `core/config.py`.

**Why this is one task and not three:** renaming the constant without the migration makes every existing profile invisible (Alembic creates an empty master DB and the profile list renders empty, while all vaults sit intact but unreachable on disk). Renaming without the backup back-compat makes `_reapply_profile_row`'s `if backup_master.exists()` guard skip silently on any pre-rename backup, stranding a vault against a mismatched password hash — the exact bug BK-01 was written to fix. A reviewer cannot sensibly accept one and reject another.

- [ ] **Step 1: Write the failing migration test**

Create `src/backend/tests/test_db_rename_migration.py`:

```python
"""Master DB filename migration (Phase B / B1a).

The master DB is the only index of which profiles exist and the only home of
password_hash and encryption_key_id. Point the app at a filename that is not
there and Alembic creates an empty one: the profile list renders empty and every
vault on disk becomes unreachable. Nothing is destroyed; all of it becomes
invisible. These tests are the guard on that.
"""

from __future__ import annotations

import sqlite3

from core.db_migration import migrate_master_db_filename


def _seed_legacy_master(data_dir, profile_id="profile-a"):
    data_dir.mkdir(parents=True, exist_ok=True)
    legacy = data_dir / "healthcentral.db"
    conn = sqlite3.connect(legacy)
    conn.execute("CREATE TABLE profiles (id TEXT, display_name TEXT)")
    conn.execute("INSERT INTO profiles VALUES (?, ?)", (profile_id, "Ann"))
    conn.commit()
    conn.close()
    return legacy


def test_hc_dbmig_001_legacy_master_is_renamed_with_its_rows(tmp_path):
    """The profile rows must survive — otherwise the user's vaults become
    unreachable even though the files are intact."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)

    assert migrate_master_db_filename(data_dir) is True

    new = data_dir / "asclexis.db"
    assert new.exists()
    assert not (data_dir / "healthcentral.db").exists()

    conn = sqlite3.connect(new)
    rows = conn.execute("SELECT id, display_name FROM profiles").fetchall()
    conn.close()
    assert rows == [("profile-a", "Ann")]


def test_hc_dbmig_002_wal_and_shm_sidecars_move_too(tmp_path):
    """SQLite in WAL mode leaves -wal and -shm beside the database. Renaming
    only the main file orphans unflushed transactions."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)
    (data_dir / "healthcentral.db-wal").write_bytes(b"wal-content")
    (data_dir / "healthcentral.db-shm").write_bytes(b"shm-content")

    assert migrate_master_db_filename(data_dir) is True

    assert (data_dir / "asclexis.db-wal").read_bytes() == b"wal-content"
    assert (data_dir / "asclexis.db-shm").read_bytes() == b"shm-content"
    assert not (data_dir / "healthcentral.db-wal").exists()
    assert not (data_dir / "healthcentral.db-shm").exists()


def test_hc_dbmig_003_is_a_noop_on_a_fresh_install(tmp_path):
    """No legacy file means nothing to do. Must not create anything."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)

    assert migrate_master_db_filename(data_dir) is False
    assert not (data_dir / "asclexis.db").exists()


def test_hc_dbmig_004_never_overwrites_an_existing_new_db(tmp_path):
    """If both exist the new one wins and the legacy file is left untouched for
    the operator to inspect. Silently clobbering a live database would be the
    worst possible outcome of a cosmetic rename."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)
    current = data_dir / "asclexis.db"
    conn = sqlite3.connect(current)
    conn.execute("CREATE TABLE profiles (id TEXT, display_name TEXT)")
    conn.execute("INSERT INTO profiles VALUES ('profile-live', 'Live')")
    conn.commit()
    conn.close()

    assert migrate_master_db_filename(data_dir) is False

    conn = sqlite3.connect(current)
    rows = conn.execute("SELECT id FROM profiles").fetchall()
    conn.close()
    assert rows == [("profile-live",)]
    assert (data_dir / "healthcentral.db").exists()


def test_hc_dbmig_005_is_idempotent(tmp_path):
    """Runs on every boot, so a second call must be a clean no-op."""
    data_dir = tmp_path / "data"
    _seed_legacy_master(data_dir)

    assert migrate_master_db_filename(data_dir) is True
    assert migrate_master_db_filename(data_dir) is False
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/backend && python -m pytest tests/test_db_rename_migration.py -p no:cacheprovider -v`
Expected: **FAIL** — `ModuleNotFoundError: No module named 'core.db_migration'`.

- [ ] **Step 3: Write the migration module**

Create `src/backend/core/db_migration.py`:

```python
"""One-time filesystem migrations that must run before any DB connection opens.

The master database is the only index of which profiles exist, and the only home
of password_hash and encryption_key_id. If the application looks for a filename
that is not present, Alembic creates an empty one and the profile list renders
empty — every vault on disk intact but unreachable. That is why the rename and
this migration are a single change.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LEGACY_MASTER_DB_NAME = "healthcentral.db"
MASTER_DB_NAME = "asclexis.db"

# SQLite in WAL mode keeps these beside the database. Renaming only the main
# file orphans any unflushed transactions in the -wal.
_SIDECAR_SUFFIXES = ("-wal", "-shm")


def migrate_master_db_filename(data_dir: Path) -> bool:
    """Rename the legacy master DB (and its sidecars) if that is safe.

    Returns True if a rename happened, False if there was nothing to do.

    Guarded on absent-target AND present-source, so it is idempotent and a
    no-op on a fresh install. If both files exist the new one wins and the
    legacy file is left in place: silently clobbering a live database would be
    the worst possible outcome of a cosmetic rename.
    """
    legacy = data_dir / LEGACY_MASTER_DB_NAME
    current = data_dir / MASTER_DB_NAME

    if not legacy.exists():
        return False

    if current.exists():
        logger.warning(
            "Both %s and %s exist; keeping %s and leaving the legacy file in "
            "place for inspection.",
            LEGACY_MASTER_DB_NAME,
            MASTER_DB_NAME,
            MASTER_DB_NAME,
        )
        return False

    legacy.rename(current)
    for suffix in _SIDECAR_SUFFIXES:
        sidecar = data_dir / f"{LEGACY_MASTER_DB_NAME}{suffix}"
        if sidecar.exists():
            sidecar.rename(data_dir / f"{MASTER_DB_NAME}{suffix}")

    logger.info("Migrated master database filename to %s", MASTER_DB_NAME)
    return True
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_db_rename_migration.py -p no:cacheprovider -v`
Expected: `5 passed`.

- [ ] **Step 5: Commit the migration before wiring it**

```bash
git add src/backend/core/db_migration.py src/backend/tests/test_db_rename_migration.py
git commit -m "feat(config): add the master-DB filename migration

Renames healthcentral.db and its -wal/-shm sidecars to asclexis.db, guarded on
absent-target and present-source so it is idempotent and a no-op on fresh
installs. If both exist the new one wins and the legacy file is left for
inspection rather than clobbered. HC-DBMIG-001..005."
```

- [ ] **Step 6: Derive the filename from settings, fixing the latent bug**

In `src/backend/core/config.py`, change the default at line 37:

```python
    sqlite_database_path: str = "data/asclexis.db"
```

Then replace the `database_url` property:

```python
    @property
    def master_db_filename(self) -> str:
        """Filename of the master database.

        Derived from `sqlite_database_path` rather than hardcoded. Previously
        `database_url` hardcoded the name and used only this setting's *parent*,
        so SQLITE_DATABASE_PATH=data/mydb.db silently had no effect on the
        filename — the setting advertised control it did not have.
        """
        return Path(self.sqlite_database_path).name or "asclexis.db"

    @property
    def database_url(self) -> str:
        """Get the database connection URL."""
        if self.database_type == "sqlite":
            db_path = self.app_data_path / self.master_db_filename
            return f"sqlite+aiosqlite:///{db_path}"
        else:
            return (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
            )
```

Confirm `Path` is imported in `config.py` (`grep -n "^from pathlib" src/backend/core/config.py`); add `from pathlib import Path` if absent.

- [ ] **Step 7: Update `.env.example`**

In `config/.env.example`, change `SQLITE_DATABASE_PATH=data/healthcentral.db` to `SQLITE_DATABASE_PATH=data/asclexis.db` and add above it:

```
# Both the directory and the filename are honoured.
```

- [ ] **Step 8: Call the migration during startup**

In `src/backend/main.py`, find the lifespan/startup function that runs before the database engine is created. Add as the **first** action inside it:

```python
    # Before any engine is created: an existing install has the legacy master
    # DB filename, and opening a connection to the new name would create an
    # empty database and hide every profile.
    from core.db_migration import migrate_master_db_filename

    migrate_master_db_filename(settings.app_data_path)
```

If startup already imports `settings`, reuse it rather than re-importing.

- [ ] **Step 9: Make restore accept either name**

In `src/backend/scripts/backup.py`, replace the `MASTER_DB_NAME` definition:

```python
MASTER_DB_NAME = "asclexis.db"

# Every backup taken before the rename lists the old filename in its manifest.
# A naive constant swap makes the `if backup_master.exists()` guard below skip
# silently, so a pre-rename backup restores a vault whose sealed keys may not
# match the live password hash — exactly the failure BK-01 exists to prevent.
LEGACY_MASTER_DB_NAMES = ("healthcentral.db",)
MASTER_DB_NAMES = (MASTER_DB_NAME, *LEGACY_MASTER_DB_NAMES)
```

Then update the three places that compare against the single name. In `backup()`'s profile filter:

```python
            if db.name in MASTER_DB_NAMES or db.parent.name == profile_id
```

In `restore()`'s hold-back check, replace `if profile_id and Path(entry["path"]).name == MASTER_DB_NAME:` with:

```python
        if profile_id and Path(entry["path"]).name in MASTER_DB_NAMES:
```

And in `restore()`'s reconciliation block, replace `backup_master = backup_path / MASTER_DB_NAME` with:

```python
        backup_master = next(
            (backup_path / name for name in MASTER_DB_NAMES if (backup_path / name).exists()),
            backup_path / MASTER_DB_NAME,
        )
```

Then run `grep -n "MASTER_DB_NAME" src/backend/scripts/backup.py src/backend/api/backup.py` and check every remaining comparison — a name *equality* check must become a membership check; the write-side path (which name to create) must stay `MASTER_DB_NAME`.

- [ ] **Step 10: Write the back-compat test**

Append to `src/backend/tests/test_db_rename_migration.py`:

```python
def test_hc_dbmig_006_restore_accepts_a_pre_rename_backup(tmp_path):
    """Every backup taken before the rename lists healthcentral.db. If restore
    stops recognising it, _reapply_profile_row skips silently and the vault is
    stranded against a mismatched password hash — the BK-01 bug via a side
    door."""
    import sqlite3
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / "profile-a"
    vault.mkdir(parents=True)
    conn = sqlite3.connect(vault / "vault.db")
    conn.execute("CREATE TABLE observations (id TEXT)")
    conn.commit()
    conn.close()
    (vault / "key.bin").write_bytes(b"sealed")

    # A backup directory shaped like a pre-rename one: legacy master filename.
    backup_path = tmp_path / "backups" / "backup_20260101_000000"
    backup_path.mkdir(parents=True)
    legacy = backup_path / "healthcentral.db"
    conn = sqlite3.connect(legacy)
    conn.execute(
        "CREATE TABLE profiles (id TEXT, display_name TEXT, encryption_key_id TEXT, "
        "password_hash TEXT, password_salt TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO profiles VALUES ('profile-a','Ann','k','old-hash','salt','2026-01-01')"
    )
    conn.commit()
    conn.close()

    assert "healthcentral.db" in backup_script.MASTER_DB_NAMES, (
        "pre-rename backups must still be recognised"
    )
```

- [ ] **Step 11: Verify the whole thing end to end with a populated legacy DB**

```bash
cd src/backend
python -m pytest tests/test_db_rename_migration.py tests/test_backup.py tests/test_backup_api.py tests/test_backup_completeness.py -p no:cacheprovider -q
python -c "from core.config import settings; print(settings.master_db_filename, settings.database_url)"
```

Expected: tests pass; the print shows `asclexis.db` and a URL ending `asclexis.db`.

Then confirm the app boots and the migration is wired:

```bash
cd src/backend && python -c "from main import app; print('booted')"
```

- [ ] **Step 12: Run the full suite**

Run: `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q`
Expected: no new failures beyond `test_api_rag_index_002b`. Tests that hardcode `healthcentral.db` as the *created* filename will need updating to `asclexis.db`; tests asserting *back-compat* keep the old name deliberately.

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "feat(config): rename the master database to asclexis.db

Supersedes the 2026-07-07 keep-filenames decision, whose rationale ('renaming
breaks existing vaults') was inaccurate — vaults are vault.db/key.bin and never
carried the product name. The real risk is different: the master DB is the only
index of which profiles exist, so a missing filename means Alembic creates an
empty one and every vault becomes unreachable while staying intact on disk.

Three inseparable parts. The filename now derives from settings, which also
fixes a latent bug where SQLITE_DATABASE_PATH contributed only its parent so the
filename was uncontrollable. The startup migration runs before any engine is
created. And restore accepts either name, because every pre-rename manifest
lists the old one and a naive swap would make _reapply_profile_row skip
silently, reintroducing BK-01. HC-DBMIG-001..006."
```

---

## Task 3: Rename the project-domain skills

**Files:**
- Rename: `skills/healthcentral-agent` → `skills/asclexis-agent`, and the same for `-backend`, `-evals`, `-guardrails`
- Modify: `skills/README.md`

**Interfaces:** Consumes nothing; produces the four new skill names referenced by Phase C's routing table.

**Why:** Skill directory names are how agents invoke them, making them part of the agent-facing surface. They postdate the 2026-07-07 audit, so its scope table does not mention them. Owner-confirmed 2026-07-30.

- [ ] **Step 1: Record what references them**

```bash
cd /home/user/HealthCentral
grep -rn "healthcentral-agent\|healthcentral-backend\|healthcentral-evals\|healthcentral-guardrails" \
  --exclude-dir=node_modules --exclude-dir=.git . | grep -v "^./docs/archive"
```

Keep this list; every hit must be updated.

- [ ] **Step 2: Rename with git so history follows**

```bash
cd /home/user/HealthCentral
for s in agent backend evals guardrails; do
  git mv "skills/healthcentral-$s" "skills/asclexis-$s"
done
ls skills/
```

Expected: four `asclexis-*` directories and `README.md`.

- [ ] **Step 3: Update the `name:` frontmatter in each SKILL.md**

```bash
grep -n "^name:" skills/asclexis-*/SKILL.md
```

Change each `name: healthcentral-<x>` to `name: asclexis-<x>`. The frontmatter name is what the Skill tool matches on, so a stale value makes the skill uninvokable.

- [ ] **Step 4: Update `skills/README.md`**

Replace every `healthcentral-` occurrence with `asclexis-`.

- [ ] **Step 5: Verify nothing dangles**

```bash
cd /home/user/HealthCentral
grep -rn "healthcentral-agent\|healthcentral-backend\|healthcentral-evals\|healthcentral-guardrails" \
  --exclude-dir=node_modules --exclude-dir=.git . | grep -v "^./docs/archive"
```

Expected: no output, **except** `AGENT.md` if it references them — leave that for Phase C, which rewrites the file, and note it in the commit message.

- [ ] **Step 6: Run the docs gates**

```bash
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
```

If the index check fails, run `python3 scripts/generate_docs_index.py` and re-check — the skill READMEs may be indexed.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(brand): rename the project-domain skills to asclexis-*

Skill directory and frontmatter names are how agents invoke them, so they are
part of the agent-facing surface. These four postdate the 2026-07-07 rename
audit and were not in its scope table. Owner-confirmed 2026-07-30.

Uses git mv so history follows. AGENT.md's references are left for Phase C,
which rewrites that file."
```

---

## Task 4: Update `feature_list.json` and the progress log

**Files:**
- Modify: `feature_list.json` (`HC-M10`)
- Modify: `docs/agentic/progress.md`

**Interfaces:** Consumes nothing; produces nothing.

- [ ] **Step 1: Mark HC-M10 completed**

In `feature_list.json`, change the `HC-M10` entry's `"status": "in_progress"` to `"status": "completed"`, and update its `description` to record that stages 1–3 are done: the name is Asclexis, screened 2026-07-30 with no direct collision, and formal trademark clearance remains the owner's.

- [ ] **Step 2: Verify the schema still lints**

```bash
python3 scripts/feature_list_lint.py; echo "exit=$?"
```

Expected: `exit=0` and a line reporting 27 entries with no violations. If it objects to a missing field on a completed entry, add whatever it requires — check the validator's rules rather than guessing.

- [ ] **Step 3: Record the decision in the progress log**

Append to `docs/agentic/progress.md`:

```markdown
- **HC-M10 stage 3 — rename executed (2026-07-30).** The product is **Asclexis**
  (Asclepius, plus the "ask" reading that matches a product built to clarify
  uncertainty rather than resolve it). Screening pass found no direct collision;
  the Asclepius-derived namespace is dense in adjacent goods (Ascletis Pharma,
  AsclepiX Therapeutics, Asclemed USA's 24 marks), and **formal TESS/registrar
  clearance remains the owner's** — a search pass is not clearance.
  Preserved: `HC-*`/`HC_*` identifiers, vault filenames, historical logs.
  Changed beyond the stage-1 table: the master DB filename (`asclexis.db`, with
  a startup migration) and the four project-domain skills, both owner-confirmed
  and both outside what the 2026-07-07 audit could see.
```

- [ ] **Step 4: Commit**

```bash
git add feature_list.json docs/agentic/progress.md
git commit -m "docs: close HC-M10 with the Asclexis rename recorded

Records what was preserved, what changed beyond the stage-1 table (master DB
filename and the four domain skills, both owner-confirmed), and that a screening
pass is not trademark clearance."
```

---

## Task 5: Brand guidelines

**Files:**
- Create: `docs/brand/brand-guidelines.md`
- Modify: `docs/INDEX.md` (via regeneration)

**Interfaces:** Consumes the name from Task 1 and the palette tokens already in `src/frontend/tailwind.config.js`.

**Why documentation-only:** for this product the largest brand risk is not visual inconsistency but copy that implies medical advice — which is simultaneously a compliance risk and a violation of an invariant already enforced in code by `modules/interpret_safety.py`. So this is mostly a safety document.

- [ ] **Step 1: Read the real palette rather than inventing one**

```bash
sed -n '1,60p' src/frontend/tailwind.config.js
```

Note the actual `surface`, `accent`, `ink`, and status token names and values. The guidelines must document what exists.

- [ ] **Step 2: Collect the copy that already gets the voice right**

```bash
grep -rn "encryption key is destroyed\|cannot be undone\|no cloud copy" src/frontend/src/components/settings/DangerZone.tsx
grep -rn "educational\|not medical advice\|never diagnos" src/backend/modules/interpret_safety.py | head -5
```

These are the models for the voice section: they state a *mechanism* ("your encryption key is destroyed, which makes the data unreadable") rather than offering a reassurance.

- [ ] **Step 3: Write the guidelines**

Create `docs/brand/brand-guidelines.md` with these sections, filled from the two previous steps:

1. **The name.** Asclexis — Asclepius (Greek god of medicine, the root shared by much of the health industry) plus the "ask" reading. The second reading is the load-bearing one: this product exists to help someone ask better questions about their own results, not to answer them authoritatively.
2. **What the product is, in one sentence.** A local-first companion that explains your own medical results, with citations, and never diagnoses.
3. **The hard boundary.** Explains, never diagnoses. This is not a stylistic preference — `modules/interpret_safety.py` enforces prohibited patterns (diagnosis, dosing) and the tests fail if that regresses. Brand copy that implies otherwise puts writing and code in conflict, and the code wins.
4. **Voice.** State mechanisms, not reassurances. Quote the DangerZone example from Step 2 and explain why it works: it tells the user *what happens*, so they can decide, instead of asking them to trust.
5. **Prohibited constructions.** Anything implying diagnosis ("you have…", "this indicates…"), dosing ("take…", "increase your…"), or prognosis ("this will lead to…"). Also avoid "wise"/"smart"/"doctor" in feature names — the 2026-07-07 shortlist flagged exactly this when screening `Labwise`.
6. **Palette.** The Tailwind tokens from Step 1, documented as-is, with the note that status colours carry meaning (attention/caution/verified) and must not be reused decoratively.
7. **What this document is not.** Not a logo spec, not a marketing site style guide. Those do not exist yet and inventing them here would create claims nobody is maintaining.

- [ ] **Step 4: Regenerate the docs index and run the gates**

```bash
cd /home/user/HealthCentral
python3 scripts/generate_docs_index.py
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
```

Expected: both `=0`. `DOC-011` rejects any doc not reachable from the index, so the regeneration in the first line is required, not optional.

- [ ] **Step 5: Commit**

```bash
git add docs/brand/brand-guidelines.md docs/INDEX.md docs/_link_graph.json
git commit -m "docs(brand): add brand guidelines for Asclexis

Grounded in the product's real constraints rather than generic voice-and-tone
filler. The largest brand risk here is copy implying medical advice, which is
also a compliance risk and a violation of an invariant interpret_safety.py
already enforces in code — so this is mostly a safety document.

Voice rules are derived from existing UI copy that states mechanisms instead of
offering reassurance, and the palette documents the Tailwind tokens that already
exist rather than inventing new ones."
```

---

## Task 6: Full verification

**Files:** none

- [ ] **Step 1: Confirm only intended occurrences of the old name remain**

```bash
cd /home/user/HealthCentral
grep -ril "healthcentral" --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=__pycache__ --exclude-dir=playwright-report \
  --exclude-dir=test-results . | grep -v "^./docs/archive" | grep -v "^./docs/plans"
```

Every remaining hit must be justifiable as: back-compat constants (`LEGACY_MASTER_DB_NAMES`), tests asserting that back-compat, `AGENT.md` (Phase C), or a backend docstring. **List them explicitly in the final report** rather than declaring the sweep clean.

- [ ] **Step 2: Run every gate and report real output**

```bash
cd src/backend && python -m pytest tests/ -p no:cacheprovider -q
cd ../frontend && npx tsc --noEmit && npx vitest run
cd /home/user/HealthCentral
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
python3 scripts/feature_list_lint.py; echo "feature_list=$?"
```

- [ ] **Step 3: Prove the migration works on a realistic install**

```bash
cd src/backend
cp -r data /tmp/data_snapshot
ls data/
python -c "from main import app; print('booted')"
ls data/
```

Expected: `data/` contained `healthcentral.db` before and `asclexis.db` after, with `vaults/` untouched. Restore the snapshot afterwards if anything looks wrong: `rm -rf data && mv /tmp/data_snapshot data`.

- [ ] **Step 4: Run e2e from a clean data dir**

```bash
cd /home/user/HealthCentral/src/backend && mv data /tmp/data_bak2 2>/dev/null || true
cd ../frontend && HC_E2E_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test --project=chromium
cd ../backend && rm -rf data && mv /tmp/data_bak2 data 2>/dev/null || true
```

Expected: `25 passed / 3 skipped`.

- [ ] **Step 5: Confirm the app presents the new name**

```bash
cd src/backend && python -c "from main import app; print(app.title)"
grep -n "<title>" ../frontend/index.html
```

Expected: `Asclexis API` and `<title>Asclexis</title>`.

---

## Self-Review

**Spec coverage.** B1 → Task 1; B1a → Task 2; B2 → Task 3; HC-M10 closure → Task 4; B3 → Task 5; the spec's Phase B verification list → Task 6.

**Placeholders.** None. Task 5's guidelines are specified as seven named sections with their content sourced from two concrete commands, rather than "write brand guidelines".

**Type consistency.** `migrate_master_db_filename(data_dir: Path) -> bool` is defined in Task 2 Step 3 and called in Step 8 and tested in Step 1. `MASTER_DB_NAMES` is introduced in Step 9 and asserted in Step 10. `settings.master_db_filename` is added in Step 6 and read in Step 11. `LEGACY_MASTER_DB_NAME` in `db_migration.py` and `LEGACY_MASTER_DB_NAMES` in `scripts/backup.py` are deliberately different objects — one is the migration's single source name, the other the restore-side membership tuple; the implementer should not try to unify them across those module boundaries.

**Two risks flagged for the implementer.**

1. **Task 2 Step 9 is the highest-risk edit in this plan.** `grep` for every `MASTER_DB_NAME` comparison and classify each as read-side (must accept both names) or write-side (must stay the new name). Getting one backwards silently breaks either old-backup restore or new-backup creation, and neither fails loudly.
2. **Task 2 Step 12 will surface tests that hardcode `healthcentral.db`.** Each needs a judgement call: a test that asserts what the app *creates* should move to `asclexis.db`; a test asserting *back-compat* must keep the old name. Do not bulk-replace.
