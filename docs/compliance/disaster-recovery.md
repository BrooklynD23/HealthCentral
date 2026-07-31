# Disaster Recovery Runbook

## Overview

This document describes the backup and recovery procedures for HealthCentral.
All databases are SQLite/SQLCipher files stored in the `data/` directory.

## Data Scope

| File | Description |
|------|-------------|
| `data/healthcentral.db` | Master database (profiles, audit logs, settings) |
| `data/vaults/*.db` | Per-profile encrypted vault databases (documents, observations, medications) |

## 1. Backup Schedule

| Frequency | Type | Retention |
|-----------|------|-----------|
| Daily | Full backup via SQLite backup API | 30 days |
| Before updates | Manual backup | Until verified |
| After critical data entry | Optional manual backup | 7 days |

## 2. Creating a Backup

### Online Backup (Recommended)

The backup script uses SQLite's built-in `backup()` API, which creates an atomic,
consistent snapshot even while the application is running.

```bash
python src/backend/scripts/backup.py --action backup --data-dir data/ --backup-dir backups/
```

Options:
- `--profile-id <id>`: Back up only a specific profile (its vault, its sealed
  keys, and only that profile's rows from the master DB)
- `--backup-dir <path>`: Custom backup destination (default: `backups/`)

### What Happens

1. Each `.db` file is backed up using `sqlite3.backup()` (online, consistent)
2. A `manifest.json` is created with SHA-256 checksums for each file
3. The backup directory is timestamped: `backup_YYYYMMDD_HHMMSS/`

### Offline Backup (Fallback)

If SQLCipher databases cannot be backed up via the API (e.g., missing pysqlcipher3),
the script falls back to raw file copy. In this case, **stop the application first**
to ensure WAL mode does not leave partial transactions.

```bash
# Stop the application
# Then run backup
python src/backend/scripts/backup.py --action backup --data-dir data/
```

## 3. Verifying a Backup

```bash
python src/backend/scripts/backup.py --action verify --backup-dir backups/
```

Verification checks:
- All files listed in `manifest.json` exist
- SHA-256 checksums match (detects single-byte corruption)
- Reports any missing or corrupted files

## 4. Restore Procedure

### Pre-Restore Checklist

- [ ] Stop the HealthCentral application
- [ ] Verify the backup integrity (step 3)
- [ ] Note the current data directory state
- [ ] Confirm you have sufficient disk space

### Running Restore

```bash
python src/backend/scripts/backup.py --action restore \
    --backup-dir backups/ \
    --data-dir data/
```

The restore process:
1. Verifies backup integrity before proceeding
2. Creates `.bak` safety copies of all existing database files
3. Copies backed-up files to the data directory
4. Reports the number of files restored and safety copy locations

### Whole-install restore vs. profile-scoped restore

The CLI above is a **whole-install** restore: every file in the manifest is
copied back, including the master database. That is right when rebuilding a
machine, and wrong for a single profile.

A backup taken with `--profile-id` is **profile-scoped**: the master database it
stores holds only that profile's rows — its profile row, its audit entries and
its backup schedule — so one profile's backup no longer carries another
profile's credentials. The manifest records the scope in a top-level
`"profile_id"` field (`null` for a whole-install backup).

That makes the two kinds of backup non-interchangeable, and the restore
enforces it: **a profile-scoped backup cannot be restored as a whole install.**
Copying its master over the live one would delete every other profile. Running
the CLI above against a scoped backup directory therefore fails immediately,
before any file is touched, naming the profile the backup belongs to. Re-run it
with the matching `--profile-id`:

```bash
python src/backend/scripts/backup.py --action restore \
    --backup-dir backups/ \
    --data-dir data/ \
    --profile-id <id>
```

Backups taken before scoping was introduced have no `"profile_id"` field and
contain a full master database. They are treated as whole-install backups and
restore exactly as they always have, by either path.

`POST /backup/{id}/restore` is always **profile-scoped** (BK-01): vault and
sealed key files are restored verbatim, but instead of copying the master DB
over the live one, only that profile's row is re-applied from the backed-up
copy. The row travels with the restore rather than being skipped because
`password_hash`/`password_salt` live in the master DB while the sealed key
lives in the vault — restoring old keys against a newer hash would let the user
log in and then find the vault refuses to open. Other profiles' rows, and the
live audit trail, are left alone.

### Post-Restore Validation

```bash
# 1. Verify database integrity
sqlite3 data/healthcentral.db "PRAGMA integrity_check;"

# 2. Start the application
python src/backend/main.py

# 3. Check health endpoint
curl http://localhost:8000/health

# 4. Verify profile access
# Log in and confirm data is present
```

## 5. Pruning Old Backups

```bash
python src/backend/scripts/backup.py --action prune \
    --backup-dir backups/ \
    --retention-days 30
```

`--retention-days 0` means **never prune**, not "prune everything" — the same
reading the Settings UI and the scheduler use. To clear backups deliberately,
delete the directory.

## 6. Escalation

If recovery fails:
1. Check `.bak` files created during restore — these are your pre-restore safety copies
2. Check application logs in `logs/healthcentral.log`
3. Verify SQLite file integrity: `sqlite3 <file> "PRAGMA integrity_check;"`
4. If databases are encrypted (SQLCipher), ensure the encryption key is available
5. Contact the development team with the error output and manifest.json contents

## Appendix: Backup Manifest Format

```json
{
    "timestamp": "20260221_143000",
    "created_at": "2026-02-21T14:30:00Z",
    "app_version": "0.1.0",
    "backup_method": "sqlite_backup",
    "profile_id": null,
    "files": [
        {
            "path": "healthcentral.db",
            "sha256": "abc123...",
            "size_bytes": 102400,
            "method": "sqlite_backup"
        }
    ]
}
```
