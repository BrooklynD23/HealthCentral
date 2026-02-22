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
- `--profile-id <id>`: Back up only a specific profile (plus master DB)
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
