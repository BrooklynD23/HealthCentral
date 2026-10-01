# Gated Items — Owner Decision Packet

> Prepared for owner review per `Devin-Audit-report.md` §20 Q6 / §21 Q6
> ("still want them — keep gated, prep for owner review") and §22 item 5.
> Nothing here is implemented. Each brief ends in an explicit decision the
> owner can approve, reject, or defer. Approved items become their own
> implementation plans; rejected/deferred items get a one-line record here.
>
> **Posture (D10):** retention and controls in this packet are designed as if HIPAA applied (owner choice, 2026-09-27). This is a design posture, not a statement about legal status. Whether any rule applies depends on who operates Asclexis and under what contracts, which is for owner/legal review.
> **Nothing here is signed.** An agent prepared every brief. Only the owner fills a decision box.

## How to read this packet
Each brief: current state (file:line evidence) → options (effort/risk/value)
→ recommendation → the decision you are being asked to make → sketch of the
recommended option only. Sign the ledger at the bottom (or per-brief).

## Brief 1 — MFA

**Ask-first surface:** every option except A touches `core/auth.py` (CLAUDE.md §1). This brief proposes; it changes no code.

### Current state

| Anchor | Proves |
|---|---|
| `core/auth.py:98-131` @start8064244 | `authenticate_profile` checks bcrypt password only; no second factor exists |
| `core/auth.py:133-157` @start8064244 | `create_session_token` issues a JWT (`type:"session"`, `ACCESS_TOKEN_EXPIRE_MINUTES=60`) |
| `core/auth.py:163-214` @start8064244 | `get_current_session` validates signature + profile existence only |
| `core/auth.py:361-402` @start8064244 (D6 hooks, landed) | `open_profile_database_on_login` — login both authenticates and opens the SQLCipher vault |
| `core/auth.py:405-419` @start8064244 | `close_profile_database_on_logout` |
| `core/security.py:38-39` @start8064244 | `ALGORITHM="HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES=60` |
| `core/security.py:35` @start8064244 | `PASSWORD_HASH_ROUNDS = 12` (bcrypt) |
| `core/security.py:86-127` @start8064244 | JWT secret persisted at `<app_data>/.jwt_secret`, cached in-process |
| `core/config.py:51` @start8064244 | `use_dpapi: bool = True` — sealed DEK bound to the Windows user account |
| `core/config.py:53` @start8064244 | `jwt_revocation_enabled: bool = True` (logout can invalidate JWTs locally) |
| `core/config.py:56-63` @start8064244 | existing brute-force controls: auth 10 attempts/60s, recovery 5 attempts/900s |
| `docs/compliance/hipaa-controls.md:168` @start8064244 | "Multi-factor authentication \| Medium \| Planned for server mode" |
| `docs/plans/2026-07-02-architect-review-proposal-tickets.md:46` (cited, not re-opened this pass) | prior review already deferred MFA |

Grep run 2026-10-01 on the start tree: `grep -rniE "totp|webauthn|otp|two.factor|multi.factor" --include="*.py" src/backend | grep -v test` → zero product-code hits (one unrelated match in `modules/agent/graph.py:4`, the word "approves", not a factor mechanism).

The password is also the DEK-unseal secret: login both authenticates and opens the vault (`core/auth.py:361-402` @start8064244). A second factor added only at login does not protect the vault file at rest — DPAPI sealing already binds the sealed DEK to the Windows user account (`core/security.py` DPAPI sealing path; `config.py:51` @start8064244).

### Decision framing

Against a *localhost-bound, single-user* threat model (stolen unlocked laptop, shared Windows account, malicious local process — remote attack is not reachable while uvicorn binds `127.0.0.1`, `main.py:167` @start8064244 `host = "127.0.0.1" if settings.app_mode == "local" else settings.host`), the destructive/sensitive routes a second factor could gate are: profile delete, restore, recovery-code issuance, and export routes. The live-session threat (an unlocked laptop walked away from) is the one a step-up re-auth actually defends; a TOTP app does not add protection beyond what DPAPI + the OS login already provide for a device-bound single-user app.

### Options

| Option | Effort | Risk | Value |
|---|---|---|---|
| A — Document "not now" | S | Low | Keeps the gate accurate; revisit if `app_mode=server` ships |
| B — TOTP at login | M–L | New dep (`pyotp`); the TOTP secret needs its own sealed storage because the vault key is not available until after the password check (seed-storage paradox) | Classic MFA story, but weak fit for a single-device app |
| C — Step-up re-auth on destructive routes | S–M | No new deps | Defends the live-session threat directly |
| D — Delegate device factor to the OS | S | None | Documents DPAPI/Windows-account as the possession factor |

### Recommendation

**C + D**: step-up re-auth for destructive/sensitive routes (profile delete, restore, recovery-code issuance, exports), plus documenting DPAPI as the device factor. B (TOTP) deferred unless `app_mode=server` ships, since the seed-storage paradox makes it awkward before then.

### Owner decision

"Approve step-up re-auth on destructive routes and document OS-level device binding as the second factor — deferring TOTP unless server mode ships?"

Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____

### Implementation sketch (C only, no code here)

A new dependency `require_fresh_auth(max_age)` checking a new `auth_time` JWT claim, or a password re-verify endpoint, placed in front of the destructive routes (profile delete, restore, recovery-code issuance, export routes) plus a frontend confirmation dialog. Test plan: `tests/support/routes.py::route_client` HTTP-level tests asserting 401 without recent auth. No ask-first file is edited without a separate yes; this brief proposes only.

## Brief 2 — Key Rotation

**Ask-first surface:** options B and C touch `core/profile_database.py`, `core/security.py`, `core/document_crypto.py` and `api/profiles.py` (encryption). Brief only; no code.

### Current state

| Anchor | Proves |
|---|---|
| `api/profiles.py:1072` @start8064244 (`change_password` def; the decorator sits at `:1071`) | unseals `key.bin` with the current password |
| `api/profiles.py:1094-1106` @start8064244 | re-seals the **same** DEK under the new password (`unseal_key_with_dpapi` then `seal_key_with_dpapi`) |
| `api/profiles.py:1146-1147` @start8064244 | writes the re-sealed `key.bin`/`key.method` — the SQLCipher key itself never changes |
| `core/profile_database.py:349` @start8064244 | `PRAGMA key = "x'{hex_key}'"` — `vault.db` is keyed by the raw 32-byte DEK (raw-key mode) |
| `core/profile_database.py:153` @start8064244 | `key.recovery.bin` is a second sealed copy of the same DEK (SEC-RECOV-001) |
| `core/profile_database.py:183-205` @start8064244, comment at `:192` | `get_profile_key_paths` enumerates all sealed-key artifacts; comment: "If DEK rotation is ever implemented, it must reseal every copy listed here" |
| `core/document_crypto.py:19-37` @start8064244 | stored documents are encrypted with the same DEK (`connection._encryption_key`); true rotation must re-encrypt every document, not just the vault |
| `grep -rnE "rekey\|sqlcipher_export" src/backend` (run 2026-10-01) | zero hits outside this brief's prose — **no rekey support exists today** |
| `tests/test_profile_recovery.py:210` @start8064244 | test comment: "Simulate change_password: re-seal only the primary copy" |
| `api/profiles.py:730-739` @start8064244 | recovery already rotates the one-time code on use — the existing re-seal machinery this brief would reuse |
| `docs/compliance/hipaa-controls.md:169` @start8064244 | "Key rotation \| Medium \| Manual via password change" — **this overstates**: at the DEK level, a password change does not rotate the key, it only re-seals the same key under a new wrapper |
| `scripts/backup.py:75,236-240` @start8064244 | a backup copies the master DB (plaintext, scoped to the profile via `_scope_master_to_profile`, `scripts/backup.py:243-262` @start8064244) plus `vaults/<id>/{key.bin,key.method,key.recovery.bin,key.recovery.method}` verbatim (sealed, opaque blobs) |
| `scripts/backup.py:658-673` @start8064244 | default prune window is 30 days (`retention_days: int = 30`); `retention_days=0` means never-prune, not "prune everything" |

Old backups keep the old DEK's sealed copies until pruned (default 30 days, `scripts/backup.py:658-673` @start8064244) or swept on profile delete. Rotating the DEK does not retro-protect anything already backed up under the old key.

### Decision framing

Against the attacker model "copied the `data/` directory": rotating the DEK limits exposure of a *stolen sealed-key + later-learned password* combination and satisfies "rotation exists" as a control, but old backups remain a permanent decryption path for old DEKs unless a purge/rotate policy for backups is included.

### Options

| Option | Effort | Risk | Value |
|---|---|---|---|
| A — Keep re-seal-only; fix the docs | S | None | Honest, but "key rotation" stays unimplemented |
| B — True DEK rotation as a guarded maintenance op | M–L | Highest blast radius of the five items: re-encrypts every document, forces a new recovery code, touches `core/document_crypto.py`/`core/profile_database.py`/`core/security.py` | Makes the control real |
| C — Split vault-DB DEK from document DEK first | L | Migration + dual seals | Only worth it if rotation becomes routine |
| D — JWT-secret rotation only | S | Cheap, orthogonal | A real but narrow "rotation" (invalidates all sessions) |

### Recommendation

**B**, with A's doc fix folded in — B is the only option that makes "key rotation" true. The owner must see explicitly: it re-encrypts every stored document file, forces issuance of a new recovery code, and must re-run the full profile-delete + recovery test suite.

### Owner decision

"Approve true DEK rotation (option B) as a future guarded maintenance operation, with the `hipaa-controls.md` wording corrected in the meantime (option A), or reject/defer?"

Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____

### Implementation sketch (B only, no code here)

A new `modules/key_rotation.py` (or extension of `profile_database.py`) with `rotate_profile_dek(profile_id)`, used by a new authenticated route; reuse `_atomic_write` (`api/profiles.py:535,727-728` @start8064244), `seal_key_with_dpapi`, and `_issue_recovery_code`. Requires the vault already open. Test plan: a new pytest file asserting post-rotation — old password fails, vault opens, documents decrypt, new recovery code works, old recovery code fails, `get_profile_key_paths` still covers all artifacts — plus a note that old backups remain decryptable by the old DEK.

### Downstream: hipaa-controls.md:169
This brief must be signed before P4 edits `docs/compliance/hipaa-controls.md:169` @main40f590e (unchanged by A/B; re-verified @start8064244)
(program P4, "after plan 08 brief 2 is signed"). P4 applies the row matching the signed option:
- If A (docs only) or reject/defer: `| Key rotation | Medium | Not implemented. A password change re-seals the existing data key under the new password; the database and document key itself does not change. |`
- If B or C approved: `| Key rotation | Medium | Owner-approved <date>, not yet implemented (plan: <link>). Until it ships, a password change re-seals the existing data key only. |`
- If D only: A's row, plus `| Session-secret rotation | Low | <as implemented> |`

## Brief 3 — Penetration-Test Scope

### Current state

| Anchor | Proves |
|---|---|
| `main.py:109-147` @start8064244 | 7-layer middleware (Starlette: last-added is outermost). Request flow: CORS → CorrelationId → SecurityHeaders → RateLimit → InputValidation → SecurityAuditMiddleware → Timing → Routes |
| `main.py:111-114` @start8064244 | `SecurityAuditMiddleware(log_to_db=settings.audit_security_events_to_db)` — DB logging default off (`config.py:79`) |
| `main.py:167` @start8064244 | uvicorn binds `127.0.0.1` in local mode; `settings.host` only in server mode |
| `main.py:93-94` @start8064244 | `/docs`/`/redoc` exposed only when `settings.debug` (`config.py:28` default `True`; forced off in production, `config.py:155-156`) |
| `main.py:153,155` @start8064244 | `/health` is public (no prefix); `/api/v1/monitoring/metrics` sits under the authenticated API prefix |
| `ls src/backend/api/*.py` (run 2026-10-01, excl. `__init__.py`) | 18 routers under `/api/v1` |
| `core/config.py:67-68,75` @start8064244 | rate limit 100 req/60s; body cap 10,485,760 bytes (10 MB) |
| `security/rate_limit_middleware.py`, `input_validator.py`, `security_headers.py`, `audit_middleware.py` @start8064244 | each implements exactly one ASGI middleware class; rate limiting uses a sliding-window counter keyed by client IP (`_extract_client_ip`), input validation enforces the body-size cap, headers middleware sets response headers, audit middleware captures the response for logging |
| `scripts/security_gate.py:58,84` @start8064244 | `check_bandit`/`check_pip_audit` raise `ReportError` on `FileNotFoundError`/`JSONDecodeError`, which the gate treats as exit 2 (fail-closed) |
| `api/export.py:115,126` @start8064244 | `/export/questions`'s `source_quote` field is emitted unredacted — an open surface (canonical owner item **EXPORT-QUESTIONS**, cross-referenced to W-2 O-4) |
| `core/database.py:46`, `core/profile_database.py:308`, `core/config.py:28` @start8064244 | both SQLAlchemy engines set `echo=settings.debug`; in the default dev config this echoes every statement with bound parameters to stderr (F-P8-3) |

**R10 — security gate, measured 2026-10-01:**
```
$ python3 scripts/security_gate.py --bandit /nonexistent.json --pip-audit /nonexistent.json; echo $?
ERROR: Could not parse bandit report '/nonexistent.json': [Errno 2] No such file or directory: '/nonexistent.json'
2
```
This is a **verify fail-closed** row, not a known open hole: the gate already fails closed on a missing/unparseable report (post-P1).

**R11 — `/export/questions` `source_quote`:** unchanged by P1. Stays an open surface; cross-reference **EXPORT-QUESTIONS** (W-2 O-4).

**F-P8-3 — debug SQL echo:** in the default development config (`debug=True`), `core/database.py:46` and `core/profile_database.py:308` set `echo=settings.debug`, so SQLAlchemy logs every statement with bound parameters to stderr, including profile-vault writes. Production forces `debug` off (`core/config.py:155-156`). Listed here as a surface row; see Brief 4 Step 1 for the measured probe output. Not fixed in this phase (owner-gated separately; **SQL-ECHO** is already owner-signed 2026-09-28 and its implementation, `docs/plans/2026-09-27-S01-sql-echo-phi-leak.md`, is in progress on a separate branch not yet merged at this packet's start tree).

### Decision framing

The assessment surface: auth/session (JWT forgery, revocation, rate limits), per-profile isolation (bypass attempts tested through `route_client`, never direct handler calls — recurring-failure #4), input validation (oversized bodies, path traversal, FTS injection), middleware ordering (can a request reach a route without passing rate limiting?), CORS (non-localhost origin), `debug` surfaces (`/docs`), and the audit-report P2 items above (R10, R11, F-P8-3).

### Options

| Option | Effort | Risk | Value |
|---|---|---|---|
| A — Scoped self-assessment checklist, executed via `route_client` pytest cases | M | Self-assessed, not independently verified | Repeatable, stays in-repo, dogfoods the harness |
| B — Local automated tooling (ZAP baseline, `scripts/security_gate.py`, `pip-audit`/`npm audit`) | S–M | Produces scanner output, not judgment | Pair with A |
| C — External/professional pen test | L / cost | Arguably disproportionate for a localhost single-user app | Only option that satisfies "penetration testing" as compliance-speak |

### Recommendation

**A + B** now; **C** deferred unless the product is distributed to other users (server mode / packaged release). Evidence delivered to the owner would be the completed checklist, a findings register, and any new tests that moved from failing to passing.

### Owner decision

"Approve a self-assessment (checklist + automated tooling, options A+B) now, deferring an external/professional pen test (option C) until server mode or packaged distribution?"

Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____

### Implementation sketch (A+B only, no code here)

`docs/compliance/pentest-checklist.md` (or an `audit/…` location) holding the layer→control→attack→evidence table; one new pytest file, `tests/security/test_pentest_surface.py`, for the automatable rows (auth isolation, rate-limit enforcement, body cap, headers present, `/docs` gated by debug), all through `tests/support/routes.py::route_client`; a findings table appended to this packet. This brief distinguishes "assessment" from "attestation": A+B is a self-assessment; only C produces a third-party pen-test report.

## Brief 4 — Audit Retention

Audit retention and audit-data protection here are designed as if HIPAA applied (owner choice, 2026-09-27).
This is a design posture, not a statement of legal status; applicability depends on the operator,
its contracts and data flows, which are for owner/legal review.

Regulatory text used (read 2026-09-27 via the Cornell LII mirror of 45 CFR; the official eCFR/HHS
text was not re-read — citation to verify by legal/owner):
- 164.316(b)(1): "(i) Maintain the policies and procedures implemented to comply with this subpart in
  written (which may be electronic) form; and (ii) If an action, activity or assessment is required by
  this subpart to be documented, maintain a written (which may be electronic) record…"
- 164.316(b)(2)(i) Time limit (Required): "Retain the documentation required by paragraph (b)(1) of this section for 6 years from the date of its creation or the date when it last was in effect, whichever is later."
- 164.312(b) Audit controls (standard): "Implement hardware, software, and/or procedural mechanisms that
  record and examine activity in information systems that contain or use electronic protected health information."
  The text read states no retention period for the activity records themselves.
- 164.312(a)(2)(iv) Encryption and decryption (Addressable): "Implement a mechanism to encrypt and decrypt
  electronic protected health information."
- 164.308(a)(1)(ii)(D) Information system activity review (Required): "Implement procedures to regularly
  review records of information system activity, such as audit logs, access reports, and security incident
  tracking reports."

The six-year period attaches to the documentation in 164.316(b)(1). It is not, by that text, a period for keeping every audit-log row. Treating rows the same way would be an extra owner choice.

### Step 1: log-sink measurement (`TestClient`)

Interpreter: `~/venvs/asclexis-311/bin/python` 3.11.16. Start SHA: `8064244` (worktree HEAD at measurement). Run 2026-10-01:

```
debug: True | create status: 201
core.audit INFO enabled: False
AUDIT: records reaching core.audit handlers: 0
root level: WARNING root handlers: ['StreamHandler']
FileHandlers: []
INSERT INTO audit_logs echoed: 1 | display name echoed: True
logs/asclexis.log exists: False
```

No FileHandler appears anywhere in the logger hierarchy. `logs/asclexis.log` does not exist after a profile-create request. `data-privacy.md:33` @A692fdf3 ("Audit logs | Master DB + log file") therefore overstates — there is no log-file sink in the default configuration.

### Step 1b: log-sink measurement (`uvicorn` CLI, real server)

Same interpreter, start SHA `8064244`, run 2026-10-01:

```
create=201
log file: absent
AUDIT lines on stderr: 0
audit INSERT echoed on stderr: 2
display name on stderr: 1
```

Confirms Step 1: no file sink; `core.audit` never echoes "AUDIT:" lines to stderr by itself; but the SQLAlchemy `echo=True` debug path does print `INSERT INTO audit_logs` (twice — once for the profile row, once for the audit row) including the plaintext display name, to stderr (F-P8-3).

### Step 2: current-state table

| Anchor (post-P1, re-verified @start8064244) | Proves |
|---|---|
| `models/audit.py:20-68` @start8064244 (`timestamp` default `:60-62`) | `audit_logs` sits on the master `Base` (plaintext DB) |
| `core/config.py:179-184` @start8064244 | master URL is plain `sqlite+aiosqlite` (AUD-04) |
| `core/audit.py:23-32` @start8064244 | design note: rows live in the unencrypted master; "Phase B (encrypting the master DB) is explicitly out of scope and gated" |
| `core/audit.py:36-112` @start8064244 | AUDIT-PHI-001 allowlist minimizes content (`audit_rows_purged` key at `:100`) |
| `core/audit.py:257-265` @start8064244 + Step 1/1b output | the INFO echo exists in code; measured sinks show it never reaches a file, and the `core.audit` logger is not at INFO level by default (0 "AUDIT:" lines observed) |
| `core/database.py:46`, `core/profile_database.py:308`, `core/config.py:28` @start8064244 + Step 1/1b output | debug SQL echo of bound parameters, including the display name (F-P8-3) |
| `api/profiles.py:890-900,909,935` @start8064244 | profile delete sweeps backups, purges `audit_logs` rows for that profile, writes the anonymized tombstone with `audit_rows_purged` |
| `scripts/backup.py:75,236-240,243,658-673` @start8064244 | backups carry a plaintext, profile-scoped master copy including audit rows; 30-day default prune |
| `ls src/backend/api/` + `git grep -n "AuditLog" -- src/backend/api` (run 2026-10-01) | only `api/profiles.py` references `AuditLog` — no audit-read route exists, so there is no patient-visible history to lose |
| `docs/compliance/data-privacy.md:33,61,144-156` @A692fdf3 (not re-opened for line drift this pass; cited per plan) | "Indefinite"; "Master DB + log file"; the 2026-07-27 purge decision |
| `docs/compliance/hipaa-controls.md:49-52` @start8064244 (checked against code, not repeated as fact) | the doc's "Structured JSON … correlation IDs" and "append-only" claims — the audit log is written via `models/audit.py`'s SQLAlchemy columns (not free-form JSON lines) and there is no code-enforced append-only guarantee beyond the one purge path above; the doc overstates relative to what the code does |

### Step 4: three decision parts

**4a: Security Rule documentation (six years, under the posture).**
What counts as documentation: `docs/compliance/*.md`, this packet and its signed ledger, dated owner-decision records, the Session Notes that record them, and any future risk analysis or activity-review record.
- **A.** Git history on the owner's canonical remote is the store. Add a documentation register listing each document and its six-year horizon ("6 years from creation or last in effect"). Docs only. S.
- **B.** A plus an exported archive (signed tag or release) per year. S.
- **C.** Do nothing.
- Risk to name: force-push or repo deletion defeats A.
- Recommend A.

**4b: Audit-log rows.**
Rows are unbounded today (AUD-03), except for purge-on-erase.
- **A.** Six-year rolling window, chosen to mirror 4a by owner choice and not required by the text above. Purge-on-erase unchanged. S–M.
- **B.** Shorter window (owner fills in days), as data minimization. S–M.
- **C.** Unbounded, documented. S.
- **D.** Revisit the 2026-07-27 purge-on-erase: keep rows after erase for the window.

**D contradicts the 2026-07-27 decision** (`data-privacy.md:150-153` @A692fdf3, which rejected "retaining the full audit trail for HIPAA-style accountability"). D10 does not by itself reverse it, because D10 licenses design posture and is silent on erase.

Note: if the owner adopts an activity-review procedure (164.308(a)(1)(ii)(D) text above), the *records of those reviews* fall under 4a, and the rows they summarise do not.
Recommend A with purge-on-erase kept, and the anonymized tombstone kept as the deletion record.

**4c: Audit data at rest (AUD-04).**
- **A.** Document the current state: plaintext master, minimized rows, the measured sinks from Step 1/1b. S.
- **B.** Encrypt the master DB (SQLCipher with an install key sealed by DPAPI). L. **Ask-first** (encryption, `core/database.py`), and it must preserve pre-login audit events (failed logins happen before any vault is open).
- **C.** Move profile-linked rows into each vault. L. **Ask-first.** Breaks pre-unlock events and changes crypto-erase semantics.
- **D.** Stop plaintext echo surfaces: the `core/audit.py:257-265` echo and debug SQL echo (F-P8-3). S–M.
- **E.** Encrypt the master copy inside backups. M. **Ask-first** (backup + keys).
Recommend A now, plus a separate owner decision on D. B, C and E each need their own plan and an explicit ask-first yes.

**Implementation sketch** (recommended options only; prose, no code):
- 4a: docs-only register.
- 4b: a `modules/audit_retention.py`-style sweep over the master `get_db()` (never `ProfileDbSession`). Delete rows with `timestamp < utcnow() - window` (naive UTC, `core.time.utcnow`), excluding NULL-profile tombstones. Handle the NULL row explicitly. The sweep writes one audit row using the existing `audit_rows_purged` key. HTTP tests via `tests/support/routes.py::route_client` for any new route. A test inserts aged, fresh and NULL-profile rows and asserts which survive. Break it on purpose: flip the comparison and watch the test go red.
- State plainly: **this brief implements nothing; a signed 4b needs its own `writing-plans` plan.**

### Step 5: owner questions

Q4a: "Approve keeping Security Rule documentation (list above) for 6 years from creation or last in effect, stored as git history plus a register (option A)?"
Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____

Q4b: "Approve an audit-row window of ☐ 6 years ☐ ____ days ☐ unbounded, **keeping** the 2026-07-27 purge-on-erase (tombstone kept)? If you want rows kept after erase, say so explicitly; that reverses the 2026-07-27 decision."
Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____

Q4c: "Approve documenting the current at-rest state now (A), and commissioning a plan for D (stop plaintext echo surfaces)? B, C and E would each come back as their own ask-first brief."
Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____

## Brief 5 — HC-M11 NLI Faithfulness
_(pending)_

## Sign-off ledger
| # | Item | Decision | Date | Notes |
|---|---|---|---|---|
| 1 | MFA | ☐ approve ☐ reject ☐ defer | | |
| 2 | Key rotation (gates P4 `hipaa-controls.md:169`) | ☐ approve ☐ reject ☐ defer | | |
| 3 | Pen-test scope | ☐ approve ☐ reject ☐ defer | | |
| 4a | Security Rule documentation retention | ☐ approve ☐ reject ☐ defer | | |
| 4b | Audit-row window + purge-on-erase | ☐ approve ☐ reject ☐ defer | | |
| 4c | Audit data at rest | ☐ approve ☐ reject ☐ defer | | |
| 5a | HC-M11 production-behaviour change | ☐ approve ☐ reject ☐ defer | | |
| 5b | HC-M11 NLI-model distribution | ☐ approve ☐ reject ☐ defer | | |
