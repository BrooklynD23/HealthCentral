# 05 — First-run onboarding, local error reporting, crash-safe backups

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** `scripts/backup.py` or `api/backup.py` changes; the SQLite journal mode changes (WAL); owner answers Q4 in [07-owner-questions.md](07-owner-questions.md); a diagnostics export is proposed.

> **Point-in-time research (2026-10-22).** Markers as in [00-README.md](00-README.md). Backup and restore handle sealed keys, so any change to them is ask-first (CLAUDE.md §1).

## 1. First run and onboarding

What a stakeholder meets today (F-9 dry run and code at `d2843e8`):

- `/` redirects to `/setup`, which only creates a profile. There is no unlock or sign-in screen. The `useLogin` and `useUnlockProfile` hooks exist (`src/frontend/src/services/profiles.ts:139-180`), but no page calls them. The JWT lasts 60 minutes (`core/security.py:39`). After it expires, or after a backend restart, the only way back is `/recover` with the recovery code, which then rotates.
- The recovery-code screen exists ("Save your recovery code", Copy/Print, an acknowledge checkbox).

Guidance from primary sources:

| Source | Point | Use here |
|---|---|---|
| NN/g, progressive disclosure **[A]** | "Designs that go beyond 2 disclosure levels typically have low usability"; wizards suit "distinct, loosely connected steps" | keep first run to two levels: create/unlock, then optional settings (model, OCR) |
| NHS design system, warning callout **[A]** | use for health-affecting information; at most two per page, "to reassure people, not to scare them" | one plain disclaimer callout, not a wall of text |
| GOV.UK patterns **[A]** | "Start using a service", "Create accounts", "Check a service is suitable" | a short "is this for you" start page: education only, data stays on this computer |
| 1Password Emergency Kit **[A]** | a printable sheet; keep a printed copy safe | offer a printable recovery sheet; say plainly that losing both the password and the code means the data cannot be recovered |
| Bitwarden export **[A]** | plaintext exports carry "do not store or send ... over insecure channels, like email" | the same warning on CSV/JSON export (D3 keeps them unredacted) |

Recommendations: an unlock screen that lists existing profiles (owner Q4). A one-sentence local-storage statement on the first screen. An empty Inbox state that says what to import (text PDFs) and what happens next (values arrive unverified).

## 2. Local-only error reporting

| Option | Licence | Network | Verdict |
|---|---|---|---|
| stdlib `logging.handlers.RotatingFileHandler` | PSF | none | **use**; the file rotates silently when near `maxBytes` **[A]** (docs.python.org/3/library/logging.handlers.html) |
| A redacting `logging.Filter` | PSF | none | strip provider text and values (see RUNNER-EXC-CHAIN); no new dependency |
| structlog | MIT **[A]** | none | optional; not needed for a small app |
| Sentry self-hosted | FSL-1.1-Apache-2.0 **[A]** | sends events over HTTP to a server you run | **no**: it breaks the no-network rule |
| React error boundary + `window.onerror` / `unhandledrejection` | MIT (React) | localhost only | boundaries do not catch event-handler or async errors **[A]** (react.dev/reference/react/Component), so add both global handlers |
| User-triggered "Export diagnostics" zip | — | none; the user saves and shares it | post-MVP. Contents: app version, OS, Python/SQLCipher versions, redacted log tail, no DB contents. A new export path, so owner and redaction rule first (CLAUDE.md "Redaction before anything leaves") |

## 3. Crash-safe SQLCipher backups

Code at `d2843e8` (`src/backend/scripts/backup.py`):

- The keyed vault snapshot uses `VACUUM INTO` on the already-keyed pool connection, inside one read transaction (`keyed_snapshotter`). SQLite: "The VACUUM INTO command is transactional in the sense that the generated output database is a consistent snapshot of the original database" **[A]**. The same page warns that if the command is interrupted by power loss, the output "might be incomplete and corrupt" **[A]**.
- The master uses `Connection.backup()` with a progress deadline (`_backup_sqlite`, `:179-216`). Python's backup loop retries on BUSY/LOCKED by itself, so lock contention reaches the deadline path, not the file-copy fallback **[A]** (orchestrator reading of the CPython `sqlite3` backup loop, https://github.com/python/cpython/blob/3.11/Modules/_sqlite/connection.c; an agent claim to the contrary was rejected). The vault path, when the profile is closed, runs through the `sqlcipher3` module's own copy of that loop (`_backup_sqlite(..., sqlite_module=...)`), which is a fork of the same code **[U]**.
- `manifest.json` is written with `write_text` (`:513`): no temp file, no fsync.
- Restore copies each file straight over the live file with `shutil.copy2` (`:718-723`). It does not delete a sibling `-journal`.
- No `journal_mode` pragma is set, so both DBs use the default rollback journal.

Primary-source rules:

| Rule | Source |
|---|---|
| "Overwriting a database file with another without also deleting any hot journal associated with the original database" corrupts it | sqlite.org/howtocorrupt.html **[A]** (page reachable **[V]**) |
| A WAL database separated from its `-wal` file can lose committed transactions; copy WAL DBs only through the backup API or `VACUUM INTO` | sqlite.org/wal.html **[A]** |
| `VACUUM INTO` target must not exist (or be empty); added in SQLite 3.27.0 | sqlite.org/lang_vacuum.html **[A]**; sqlite.org/releaselog/3_27_0.html **[A]** |
| The backup API copies "even if the database is being accessed by other clients"; a single step holds a read lock for the whole copy | docs.python.org/3/library/sqlite3.html **[A]**; sqlite.org/backup.html **[A]** |
| `sqlcipher_export()` copies to a database with a different key | zetetic.net/sqlcipher/sqlcipher-api **[A]** |
| `synchronous=FULL` is the rollback-journal default; EXTRA for durability across power loss | sqlite.org/pragma.html **[A]** |

Recommended pattern (post-MVP, ask-first):

1. Build each backup in `backup_<ts>.partial/`. Write the manifest to `manifest.json.tmp`, fsync it, `os.replace` it, rename the directory to its final name, then fsync the parent directory.
2. Restore: close the handles, copy each file to `<db>.restore-tmp`, fsync, delete `<db>-journal` and `<db>-wal`, then `os.replace`. Keep the `.bak` safety copies as now.
3. If WAL is ever turned on, retire the file-copy fallback.

## Sources

- https://www.nngroup.com/articles/progressive-disclosure/ ; https://design-system.service.gov.uk/patterns/ ; https://service-manual.nhs.uk/design-system/components/warning-callout
- https://support.1password.com/emergency-kit/ ; https://bitwarden.com/help/export-your-data/
- https://docs.python.org/3/library/logging.handlers.html ; https://github.com/hynek/structlog ; https://github.com/getsentry/self-hosted/blob/master/LICENSE.md ; https://react.dev/reference/react/Component
- https://www.sqlite.org/lang_vacuum.html ; https://www.sqlite.org/releaselog/3_27_0.html ; https://www.sqlite.org/wal.html ; https://www.sqlite.org/howtocorrupt.html ; https://www.sqlite.org/backup.html ; https://www.sqlite.org/pragma.html
- https://docs.python.org/3/library/sqlite3.html ; https://docs.python.org/3/library/os.html ; https://www.zetetic.net/sqlcipher/sqlcipher-api/
