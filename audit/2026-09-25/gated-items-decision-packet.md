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
_(pending)_

## Brief 4 — Audit Retention
_(pending)_

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
