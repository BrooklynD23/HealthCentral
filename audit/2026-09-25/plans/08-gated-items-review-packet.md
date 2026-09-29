# Gated Items Owner-Review Packet Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-08):** Task 5 (audit retention) Step 2 no longer asserts that Asclexis "is not a HIPAA covered entity". HIPAA status is now conditional and routed to owner/legal review, and the six-year rule is scoped to 45 CFR 164.316 Security Rule documentation. Source check on 2026-09-27: the two HHS pages the review cited returned HTTP 403 to this session's fetcher and could not be re-read. §164.316(b)(2)(i) was read via the Cornell LII mirror because eCFR redirected to a bot wall. All five items stay owner-gated; this packet prepares decisions, it does not make them. **N-04 (conflicting record):** branch `origin/claude/asclexis-repo-audit-349pjq` records HC-M11 as "**Approved, scheduled after band A**" (`docs/plans/2026-09-08-backlog-closure-plan.md` §14 decision 2, commit `fe31e78`, 2026-09-08). That approval is scoped to building the cross-encoder behind a default-off flag. It explicitly excludes changing production scoring, thresholds, or anything else in the two ask-first files. Brief 5 must cite that record and ask the owner only what it leaves open, namely any production-behaviour change. It must not present HC-M11 as unapproved. **N-15:** Task 5 treats `logs/asclexis.log` as a second retention surface. No product code configures a file handler: `core/audit.py:254-261` logs to the logger, and `core/config.py:125` is a setting only. Verify whether a sink exists at runtime before the brief relies on it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This is a decision-packet plan, not an implementation plan.** Its deliverable is a single document the owner reads and signs. The only file it creates is `audit/2026-09-25/gated-items-decision-packet.md`. It changes **zero** product code.

**Goal:** Produce one owner-review decision packet covering the five gated items — MFA, key rotation, pen-test scope, audit retention, HC-M11 NLI faithfulness — each as a self-contained brief with evidence, options, a recommendation, and an explicit sign-off line.

**Architecture:** Five parallelizable "investigate → draft brief" tasks feeding one document. Each brief follows a fixed template (Global Constraints). Evidence seeds with exact `file:line` anchors are embedded in each task — the executor must *re-verify every anchor before citing it* (line numbers drift; `recurring-failures.md` mode: report-as-fact).

**Deliverable file:** `audit/2026-09-25/gated-items-decision-packet.md` — co-located with the audit report that created the gates, outside `docs/` so docs_lint's Last-Updated/index rules do not apply. (If the owner later wants these folded into `docs/compliance/`, that is an implementation-time move, not part of this plan.)

## Global Constraints

- **NO implementation until the owner signs each brief.** Owner answer recorded 2026-09-25 (`audit/2026-09-25/Devin-Audit-report.md` §21 Q6, §22 item 5): "still want them — keep gated; orchestrator should prep them for owner review, not implement unilaterally." This plan produces *briefs*, never code changes.
- **Ask-first files stay read-only.** `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, and anything auth/encryption (`core/security.py`, `core/auth.py`, `core/profile_database.py`, `api/profiles.py`) are read for evidence only. No edits, no refactor suggestions landed in code.
- **Tracker honesty.** Do not touch `feature_list.json` in this work. HC-M11 stays `pending`. The four HIPAA-adjacent items have no ledger rows today — the packet records their gate status; adding rows is itself a decision for the owner.
- **Evidence rule.** Every "current state" claim in the packet carries a `file:line` anchor that was re-read at write time. If an anchor moved, cite the new line; if the code changed, the brief says what the code says *now*, not what this plan expected.
- **Brief template (fixed, one per item):**
  1. **Current state** — table of `file:line` → what it proves.
  2. **Decision framing** — why this matters for a *local-first, single-user* medical app; name the threat it actually addresses.
  3. **Options table** — `| Option | Effort (S/M/L) | Risk | Value |` including a "do nothing / document only" baseline.
  4. **Recommendation** — one option, conservative, with one-paragraph rationale.
  5. **Owner decision** — the exact question(s) to approve/reject, ending with a sign-off line: `Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____`.
  6. **Implementation sketch** — *recommended option only*: files it would touch, approach in prose/pseudocode, test plan outline, rollout/rollback notes. No production code in the packet.
- **Post-sign-off path (documented, not executed):** each approved brief becomes its own implementation plan via the writing-plans skill, gets a `feature_list.json` row if it is new scope, and follows the CLAUDE.md ask-first protocol for safety files.
- **Commit cadence:** the packet is committed once complete (`docs: gated-items decision packet for owner review`), and amended (`docs:` prefix) as owner decisions are recorded — the sign-off is part of git history.
- **Sources of truth for gating:** `audit/2026-09-25/Devin-Audit-report.md` §11 P2/P3 items, §20 Q6, §21 Q6 answer, §22 item 5; `feature_list.json` HC-M11 (the only gated item with a ledger row); `docs/compliance/hipaa-controls.md` §"technical safeguards" table rows for MFA/key-rotation/pen-test; `docs/features/TASK_LIST.md` HIPAA technical-safeguards note (~line 549).

---

### Task 1: Scaffold the decision packet

**Files:**
- Create: `audit/2026-09-25/gated-items-decision-packet.md`
- Read: `audit/2026-09-25/Devin-Audit-report.md` (§11, §20, §21, §22 — already quoted below)

**Interfaces:**
- Produces: the file every later task appends to. Section anchors: `## Brief 1 — MFA`, `## Brief 2 — Key Rotation`, `## Brief 3 — Penetration-Test Scope`, `## Brief 4 — Audit Retention`, `## Brief 5 — HC-M11 NLI Faithfulness`, `## Sign-off ledger`.

- [ ] **Step 1: Write the packet skeleton**

Create `audit/2026-09-25/gated-items-decision-packet.md` with:

```markdown
# Gated Items — Owner Decision Packet

> Prepared for owner review per `Devin-Audit-report.md` §20 Q6 / §21 Q6
> ("still want them — keep gated, prep for owner review") and §22 item 5.
> Nothing here is implemented. Each brief ends in an explicit decision the
> owner can approve, reject, or defer. Approved items become their own
> implementation plans; rejected/deferred items get a one-line record here.

## How to read this packet
Each brief: current state (file:line evidence) → options (effort/risk/value)
→ recommendation → the decision you are being asked to make → sketch of the
recommended option only. Sign the ledger at the bottom (or per-brief).

## Brief 1 — MFA
_(pending)_

## Brief 2 — Key Rotation
_(pending)_

## Brief 3 — Penetration-Test Scope
_(pending)_

## Brief 4 — Audit Retention
_(pending)_

## Brief 5 — HC-M11 NLI Faithfulness
_(pending)_

## Sign-off ledger
| # | Item | Decision | Date | Notes |
|---|------|----------|------|-------|
| 1 | MFA | ☐ approve ☐ reject ☐ defer | | |
| 2 | Key rotation | ☐ approve ☐ reject ☐ defer | | |
| 3 | Pen-test scope | ☐ approve ☐ reject ☐ defer | | |
| 4 | Audit retention | ☐ approve ☐ reject ☐ defer | | |
| 5 | HC-M11 NLI | ☐ approve ☐ reject ☐ defer | | |
```

- [ ] **Step 2: Verify the scaffold**

Run: `head -60 audit/2026-09-25/gated-items-decision-packet.md`
Expected: all five section headers and the ledger table present.

- [ ] **Step 3: Commit**

```bash
git add audit/2026-09-25/gated-items-decision-packet.md
git commit -m "docs: scaffold gated-items owner decision packet"
```

---

### Task 2: Brief 1 — MFA for a local-first app

**Files:**
- Modify: `audit/2026-09-25/gated-items-decision-packet.md` (fill `## Brief 1 — MFA`)
- Read (verify every anchor): `src/backend/core/auth.py`, `src/backend/core/security.py`, `src/backend/core/config.py`, `src/backend/api/profiles.py`, `docs/compliance/hipaa-controls.md`, `docs/features/TASK_LIST.md` (~line 549), `docs/plans/2026-07-02-architect-review-proposal-tickets.md` (~line 46)

**Evidence seeds — re-verify before citing (expected state as of main @ 40f590e):**
- `core/auth.py:98-130` — `authenticate_profile` verifies bcrypt password only; no second factor exists.
- `core/auth.py:133-160` — `create_session_token` issues a JWT (`type:"session"`, 60-min expiry); `core/auth.py:163-214` — `get_current_session` validates signature + profile existence only.
- `core/security.py:38-39` — `ALGORITHM="HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES=60`; `:35` bcrypt rounds=12; `:86-127` JWT secret persisted at `<app_data>/.jwt_secret`; `core/token_revocation.py` + `config.py:53` `jwt_revocation_enabled=True`.
- `core/auth.py:361-402` + `core/profile_database.py:236-241` — the **password is also the DEK-unseal secret**: login both authenticates and opens the SQLCipher vault. A second factor added at login does not protect the vault file at rest — DPAPI sealing (`core/security.py:323-381`, `config.py:51` `use_dpapi=True`) already binds the sealed DEK to the Windows user account.
- `config.py:56-63` — existing brute-force controls: auth 10 attempts/60s, recovery 5/900s.
- `grep -rniE "totp|webauthn|otp|two.factor|multi.factor" src/` — expect zero product-code hits.
- `docs/compliance/hipaa-controls.md:168` — "Multi-factor authentication | Medium | Planned for server mode" (the existing gate wording).
- `docs/plans/2026-07-02-architect-review-proposal-tickets.md:46` — prior review already deferred MFA ("no MFA exists to compose with").

- [ ] **Step 1: Verify anchors** — open each file above, confirm the line numbers and content; correct any that drifted. Run the TOTP/webauthn grep and record its output.

- [ ] **Step 2: Fill the gap — enumerate what MFA would protect.** List the destructive/sensitive routes a second factor could gate: profile delete (`api/profiles.py:773`), restore (`api/backup.py` — confirm the `RESTORE MY DATA` phrase route), recovery-code issuance, export routes (`api/export.py`, `api/feedback.py` RL export). Answer in one paragraph: against a *localhost-bound, single-user* threat model (stolen unlocked laptop, shared Windows account, malicious local process — remote attack is impossible while uvicorn binds `127.0.0.1`, `main.py:167`), which of these does a second factor actually defend?

- [ ] **Step 3: Draft the brief** into `## Brief 1 — MFA` using the Global Constraints template. Required options:
  - **A — Document "not now":** record that password + DPAPI device binding is the current factor story; revisit if `app_mode=server` ever ships. Effort S.
  - **B — TOTP at login:** new dep (e.g., `pyotp`); must surface the *seed-storage paradox* — the master DB is unencrypted and the vault key isn't available until after the password check, so the TOTP secret needs its own sealed storage. Effort M–L.
  - **C — Step-up re-auth:** require password re-entry on destructive/sensitive routes only (delete profile, restore, recovery issue, exports). No new deps; defends the live-session threat (unlocked laptop walked away from). Effort S–M.
  - **D — Explicitly delegate device factor to the OS:** document DPAPI/Windows-account as the possession factor; combine with A or C.
  - Recommended option to draft: **C + D** (step-up for destructive ops; document DPAPI as the device factor), with B deferred to server mode. The brief must still present all four fairly — the owner signs, not the writer.
  - Implementation sketch for C: middleware/dependency `require_fresh_auth(max_age)` checking a new `auth_time` JWT claim or password re-verify endpoint; touch list = `core/auth.py`, the destructive routes named in Step 2, frontend confirmation dialog; test plan = `route_client` tests asserting 401 without recent auth (HTTP-level, per `tests/support/routes.py`).

- [ ] **Step 4: Self-check** — every claim has a `file:line`; the options table has effort/risk/value; the owner question is a single unambiguous sentence ("Approve step-up re-auth on destructive routes and document OS-level device binding as the second factor — deferring TOTP unless server mode ships?").

- [ ] **Step 5: Commit** — `git commit -am "docs: MFA decision brief"`

---

### Task 3: Brief 2 — Key rotation

**Files:**
- Modify: `audit/2026-09-25/gated-items-decision-packet.md` (fill `## Brief 2 — Key Rotation`)
- Read (verify): `src/backend/core/profile_database.py`, `src/backend/core/security.py`, `src/backend/core/document_crypto.py`, `src/backend/api/profiles.py` (~:660-770, ~:1071-1166), `src/backend/scripts/backup.py` (what a backup copies), `docs/compliance/hipaa-controls.md:169`, `src/backend/tests/test_profile_recovery.py` (~:210)

**Evidence seeds — re-verify before citing:**
- `api/profiles.py:1071-1166` — `change_password` unseals `key.bin` with the current password and **re-seals the same DEK** under the new password (`:1146-1147` writes `key.bin`/`key.method`). The SQLCipher database key never changes.
- `core/profile_database.py:341-349` — `PRAGMA key = "x'{hex_key}'"`: `vault.db` is keyed by the raw 32-byte DEK (raw-key mode, no PBKDF2 at open).
- `core/profile_database.py:146-158` — `key.recovery.bin` is a *second sealed copy of the same DEK* (SEC-RECOV-001).
- `core/profile_database.py:183-205` — `get_profile_key_paths` enumerates all four sealed-key artifacts and its own comment says: *"If DEK rotation is ever implemented, it must reseal every copy listed here"* — and backups carry copies too.
- `core/document_crypto.py:19-37` + `modules/ingest` — stored document files are AES-GCM-encrypted with **the same DEK** (`connection._encryption_key`). True DEK rotation must re-encrypt every stored document, not just the vault.
- `grep -rnE "rekey|sqlcipher_export" src/backend` — expect zero hits outside comments: **no rekey support exists today**.
- `tests/test_profile_recovery.py:210` — test comment already encodes the semantic: *"Simulate change_password: re-seal only the primary copy."*
- `api/profiles.py:662-666` — documented crash-safety write-order reasoning and the `_atomic_write` pattern (`:727-728`) — the existing re-seal machinery to reuse.
- `docs/compliance/hipaa-controls.md:169` — "Key rotation | Medium | Manual via password change" — flag this: **the doc implies password change = key rotation; at the DEK level that is not true.** The brief must state this gap plainly.
- `scripts/backup.py` — confirm which files a backup copies (expect vault + sealed keys verbatim per AGENT.md flow 4). Consequence: old backups remain decryptable by the old DEK *forever* — rotation cannot retro-protect them; it only changes forward-going exposure.
- Recovery-code consequence to surface: the recovery seal is derived from the code, which is never stored — so rotating the DEK **requires issuing a new recovery code** (matching SEC-RECOV-001 one-time semantics; see `api/profiles.py:735-740` which already rotates codes on use).
- Master DB: unencrypted (`core/audit.py:26-31` comment) — no master key exists to rotate. JWT secret rotation = regenerate `.jwt_secret` (trivial; invalidates all sessions — include as a cheap sub-option).

- [ ] **Step 1: Verify anchors** — re-read each file; confirm the backup file list in `scripts/backup.py` and record what it includes.

- [ ] **Step 2: Answer the framing question in one paragraph** — what does rotation buy when the attacker model is "copied the `data/` directory"? (Answer the brief should land: rotating the DEK limits exposure of *stolen sealed-key + later-learned password* combos and satisfies the "rotation exists" control, but old backups are a permanent decryption path for old DEKs — purge-or-rotate policy for backups must be part of the option.)

- [ ] **Step 3: Draft the brief** — required options:
  - **A — Keep re-seal-only; fix the docs:** amend `hipaa-controls.md` to say password change re-seals the key wrapper, not the DEK. Honest, zero risk, but "key rotation" remains unimplemented. Effort S.
  - **B — True DEK rotation as a guarded maintenance op:** generate new DEK → `sqlcipher_export` into a fresh `vault.db` → re-encrypt every AES-GCM document file → reseal primary + recovery copies (new recovery code issued) → atomic swap → audit row → old DEK destroyed. Effort M–L. Highest blast radius of the five items; the document re-encryption and forced new-recovery-code UX are the parts the owner must see.
  - **C — Split the keys first:** separate vault-DB DEK from document DEK (both sealed under password/DPAPI), so DB-key rotation later doesn't touch document files. Effort L (migration + dual seals); only worth it if rotation will be routine.
  - **D — JWT-secret rotation only** as a cheap adjacent control (plus optional "rotate on every boot" toggle).
  - Recommended option to draft: **B** with A's doc fix folded in — it is the only option that makes the control real; presented with an explicit warning that it touches the crypto-erase key enumeration and must re-run the full profile-delete + recovery test files.
  - Implementation sketch for B: new `modules/key_rotation.py` (or extend `profile_database.py`) with a `rotate_profile_dek(profile_id)` used by a new authenticated route; reuse `_atomic_write`, `seal_key_with_dpapi`, `_issue_recovery_code`; require profile open (locked vault can't rotate); test plan = new pytest file asserting post-rotation: old password fails, vault opens, documents decrypt, new recovery code works, old recovery code fails, `get_profile_key_paths` still covers all artifacts; plus a backup-note (old backups = old DEK).

- [ ] **Step 4: Self-check** — the brief states plainly that today "key rotation" does not exist (re-seal ≠ rekey); the recovery-code-rotation consequence and the backup-DEK limitation are visible to the owner in the decision question itself.

- [ ] **Step 5: Commit** — `git commit -am "docs: key-rotation decision brief"`

---

### Task 4: Brief 3 — Penetration-test scope

**Files:**
- Modify: `audit/2026-09-25/gated-items-decision-packet.md` (fill `## Brief 3 — Penetration-Test Scope`)
- Read (verify): `src/backend/main.py:86-174`, `src/backend/security/` (`rate_limit_middleware.py`, `input_validator.py`, `security_headers.py`, `audit_middleware.py`), `src/backend/core/config.py:56-84`, `src/backend/core/rate_limiter.py`, `src/backend/api/__init__.py` + `ls src/backend/api/` (enumerate all routers), `scripts/security_gate.py`, `.github/workflows/ci.yml` (security job), `docs/compliance/hipaa-controls.md:171`, `tests/support/routes.py` (route_client harness)

**Evidence seeds — re-verify before citing:**
- `main.py:105-147` — 7-layer middleware, outermost→innermost: CORS (localhost origins only in local mode, `allow_credentials=True`) → CorrelationId → SecurityHeaders → RateLimit (100 req/60s, `config.py:66-68`) → InputValidation (10MB body cap, `config.py:75`) → SecurityAuditMiddleware (`log_to_db=audit_security_events_to_db`, default **off**, `config.py:79`) → Timing.
- `main.py:167` — uvicorn binds `127.0.0.1` in local mode; `settings.host` only in server mode.
- `main.py:93-94` — `/docs`+`/redoc` exposed only when `settings.debug`; `config.py:28` `debug=True` default but `config.py:156-157` forces it off in production.
- `main.py:152-155` — `/health` public; `/api/v1/monitoring/metrics` auth-protected.
- Audit report §11 — known surface items to fold into the checklist: in-memory export stores (`api/export.py`), `/profiles/test/reset` coverage gap (6 profile tables missed), `POST /export/questions` unredacted `source_quote` (P2, quote-leak fix on unmerged branch1), security gate fail-open on main (P1 — fix on unmerged branch).
- `scripts/security_gate.py` — confirm what it already runs (expect bandit/pip-audit-style scanners) and confirm the fail-open behavior described in the audit (`FileNotFoundError`/`JSONDecodeError` → `[]` → exit 0).

- [ ] **Step 1: Verify anchors** — read the four `security/` middleware files and summarize each one's actual checks (rate limit key derivation, input rules enforced, headers set, audit events captured). Enumerate `src/backend/api/*.py` and count routers (audit report says 18–19 under `/api/v1`).

- [ ] **Step 2: Define the assessment surface in the brief** — one table: layer → control → how to attack it → evidence it held. Cover: auth/session (JWT forgery, revocation, rate limits), per-profile isolation (`require_profile_access` bypass attempts — must be tested through `route_client`, not direct handler calls, per recurring-failure #4), input validation (oversized bodies, path traversal in document IDs, FTS injection via search), middleware ordering (can a request reach routes without passing rate limit?), CORS (non-localhost origin), `debug` surfaces (`/docs`), and the audit-report P2 items above.

- [ ] **Step 3: Draft the brief** — required options:
  - **A — Scoped self-assessment checklist:** the Step-2 table as a repeatable checklist, executed by an agent + new `route_client` pytest cases; findings register appended to the packet. Effort M. Repeatable, stays in-repo, dogfoods the repo's own harness.
  - **B — Local automated tooling:** OWASP ZAP baseline against a running local uvicorn + confirm `scripts/security_gate.py` scanners + `pip-audit`/`npm audit` hygiene runs. Effort S–M. Produces scanner output, not judgment — pair with A.
  - **C — External/professional pen test:** scoped engagement or third-party review. Effort L/cost; arguably disproportionate for a localhost single-user app, but is the only option that satisfies "penetration testing" as compliance-speak. Present honestly.
  - Recommended option to draft: **A + B** — checklist executed and evidence collected now; C deferred unless the product is distributed to other users (server mode / packaged release). Evidence to owner = completed checklist + findings register + any new failing-then-passing tests.
  - Implementation sketch: `docs/compliance/pentest-checklist.md` (or `audit/…/`), one pytest file `tests/security/test_pentest_surface.py` for the automatable rows (auth isolation, rate-limit enforcement, body cap, headers present, `/docs` gated by debug), a findings table in the packet; all route tests via `tests/support/routes.py::route_client`.

- [ ] **Step 4: Self-check** — the brief distinguishes "assessment" from "attestation": it must say plainly that A+B is a self-assessment, and only C produces a third-party pen-test report.

- [ ] **Step 5: Commit** — `git commit -am "docs: pen-test scope decision brief"`

---

### Task 5: Brief 4 — Audit retention

**Files:**
- Modify: `audit/2026-09-25/gated-items-decision-packet.md` (fill `## Brief 4 — Audit Retention`)
- Read (verify): `src/backend/models/audit.py`, `src/backend/core/audit.py`, `src/backend/api/profiles.py` (~:900-940 — delete-profile purge + tombstone), `src/backend/security/audit_middleware.py`, `src/backend/core/config.py:79,125-126`, `src/backend/scripts/backup.py` (does a backup include the master DB / audit rows?), `ls src/backend/api/` (does an audit-viewer route exist?)

**Evidence seeds — re-verify before citing:**
- `models/audit.py:20-68` — `audit_logs` table on the master `Base` (unencrypted `asclexis.db`); `timestamp` indexed; default is `datetime.utcnow` (`:62` — one of the ~50 known invariant breaches).
- `core/audit.py:23-31` — design note: *"Audit rows live in the unencrypted master DB — the one place patient-linked data escapes the SQLCipher boundary"*; AUDIT-PHI-001 allowlist (`:36-106`) already minimizes row content (no free text, no filenames, enum-shaped values only).
- `api/profiles.py:909` + `:935` — the **only** purge that exists today runs inside `DELETE /profiles/{id}`: `delete(AuditLog).where(profile_id == …)` then an anonymized tombstone recording `audit_rows_purged`. Per-profile lifetime retention otherwise = forever.
- `core/audit.py:97` — `"audit_rows_purged"` is already an allowlisted detail key: the scrubber anticipated purge actions.
- `core/audit.py:254-261` — every row is *also* echoed to the plaintext app logger → `logs/asclexis.log` (`config.py:125`) is a second, unbounded retention surface the brief must include.
- `config.py:79` — `audit_security_events_to_db=False`: enabling SecurityAuditMiddleware DB logging would add another row source; retention policy must cover it.
- Audit report §11 P3 — "unbounded audit retention" is a listed risk; §16 row 7 pairs it with export-store persistence.
- Gap to fill: does `scripts/backup.py` include `asclexis.db` (i.e., do backups already capture audit history)? Read and record.

- [ ] **Step 1: Verify anchors + answer the gap** — confirm backup scope, and check `api/` for an audit-read route (does anything expose the log to the UI? affects whether retention loses user-visible history).

- [ ] **Step 2: PHI framing paragraph** — rows are minimized but still carry `profile_id` + event timestamps + entity UUIDs in an *unencrypted* database; retention shrinks the exposure window, and the plaintext log file is the same window. ~~Note Asclexis is not a HIPAA covered entity — "retention" here is data-minimization hygiene, not a 6-year legal mandate; say that so the owner isn't anchoring on a rule that doesn't apply.~~ *Corrected 2026-09-27 ([review F-08](../review/2026-09-27-followup.md)):* **do not state a HIPAA status.** Whether HIPAA applies depends on who operates Asclexis, under what contracts, and on whose behalf, for example a developer contracted to serve a covered entity's patients. Nothing in this repo establishes those facts. The packet must present status as **conditional**, list the facts that decide it (operator, contracts, data flow), and route the question to **owner/legal review**. Describe the six-year period narrowly: 45 CFR 164.316(b)(2)(i) requires retaining the Security Rule *documentation* (policies, procedures, and records of required actions/assessments) for six years. It is **not** a general rule for keeping audit-log rows. Retention options here are data-minimization choices unless and until legal review says otherwise.

- [ ] **Step 3: Draft the brief** — required options:
  - **A — Rolling time window:** purge rows older than N (owner picks: e.g., 90d / 1y / 6y); a scheduled purge in `main.py` lifespan like `backup_scheduler`, or on-startup sweep. Effort S–M.
  - **B — Size cap:** keep newest N rows per profile. Effort S. Crude but bounded; loses time-shape.
  - **C — Archive-into-backup:** before purge, append the rows to the profile's backup archive (backups are deliberately unredacted — AGENT.md flow 4 — so audit history lands inside the encrypted artifact, off the master DB). Effort M. Best PHI posture; depends on Step-1 finding about whether master DB is already in backups.
  - **D — Keep unbounded, document decision.** Effort S.
  - Recommended option to draft: **C + A combined** — archive to backup first (if backups don't already cover it), then rolling purge; plus one line covering `logs/asclexis.log` (rotate/truncate the file or stop echoing audit lines to it).
  - Implementation sketch: `modules/audit_retention.py` with `purge_before(cutoff)` / `archive_to_backup(profile_id)`; a `Retention sweep` audit event whose details use the existing `audit_rows_purged` allowlist key; owner-chosen window as a settings field; test plan = insert synthetic aged rows, run sweep, assert purge count + archive contents + tombstone row; remember audit DB is master — `get_db()`, not `ProfileDbSession`.

- [ ] **Step 4: Self-check** — the owner question includes the window value as an explicit choice (e.g., "approve archive-on-backup + rolling purge at ___ days"), and the log-file surface is named.

- [ ] **Step 5: Commit** — `git commit -am "docs: audit-retention decision brief"`

---

### Task 6: Brief 5 — HC-M11 NLI faithfulness

**Files:**
- Modify: `audit/2026-09-25/gated-items-decision-packet.md` (fill `## Brief 5 — HC-M11 NLI Faithfulness`)
- Read (verify): `src/backend/modules/faithfulness.py`, `src/backend/modules/verifier_agent.py`, `src/backend/core/config.py:145-152`, `feature_list.json` (HC-M11 row), `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md` (Area 1 — the planned NLI wiring `config.py:151` points to), `src/backend/scripts/download_models.py` (confirm it is GGUF-only today), `src/backend/modules/agent/eval/scorer.py` (does the eval gate's groundedness axis consume faithfulness/verifier output?)

**Evidence seeds — re-verify before citing:**
- `modules/faithfulness.py:95-121` — `score_claim(..., entailment_scores=None, ...)` accepts pre-computed NLI scores but **no production caller feeds it**; falls back to `_calculate_pseudo_entailment` (lexical entity coverage, `:191-214`).
- `modules/faithfulness.py:134` — `consistency_score = 1.0` — the disclosed placeholder ("Default to 1.0 if not checking consistency"; `enable_consistency_check` config exists at `:66` unused).
- `modules/verifier_agent.py:88` — `use_llm_entailment: bool = False`; `:223-226` dispatch; `:304-317` `_check_entailment_llm` is a stub that just calls `_check_entailment_rules` — flipping the flag today changes nothing.
- `core/config.py:146-152` — verification settings; `:151` comment cites the tech-upgrade survey Area 1.
- `feature_list.json` HC-M11 (pending, priority 3) — its own text names the candidate (`cross-encoder/nli-deberta-v3-xsmall`, MIT, ~22M params, via existing `sentence-transformers` dep), the blocker ("non-GGUF model-distribution support in `scripts/download_models.py`"), the ask-first warning ("touches two ask-before-touching files — requires its own owner approval when scheduled"), and the three verification steps (contradicted-claim-below-threshold test; flag-off = all existing tests pass; offline/no-network-at-inference test). Quote this text in the brief so the owner sees the pre-approved scope.
- Audit report §11 P2 — `consistency_score=1.0` is a disclosed placeholder; §5 lists NLI as docs-ahead.

- [ ] **Step 1: Verify anchors** — plus two gap answers: (a) read `scripts/download_models.py` and state exactly why a HF cross-encoder can't be distributed through it today (GGUF-only? repo-pinning?); (b) read `modules/agent/eval/scorer.py` / the faithfulness call sites and state whether NLI wiring would change the 74-case eval gate's behavior with the flag on.

- [ ] **Step 2: Draft the brief** — required content:
  - Current state: production faithfulness is 100% rule-based; the placeholder is disclosed, not hidden.
  - Model choices that stay local-first: `cross-encoder/nli-deberta-v3-xsmall` (~22M, MIT — tracker candidate), vs `nli-deberta-v3-small/base` (better accuracy, more RAM) vs ONNX/quantized variants. One line each on RAM/latency at single-user scale; all run offline via `sentence-transformers` `CrossEncoder` once downloaded — but the download itself is the one sanctioned network path (PHI never leaves; model pulls do), which is precisely what needs owner sign-off.
  - Options table: **A — implement as spec'd** (small model, flag default off, regex remains the floor); **B — larger model variant**; **C — defer** (keep placeholder + docs honest); **D — alternative without new model dep** (e.g., prompt the existing local LLM for entailment via ModelRunner — no new download, but slower and inside the LLM-trust boundary the verifier exists to check; flag as weaker).
  - What the owner must approve — list explicitly: (1) a new HF model dependency + the one-time download; (2) edits to `faithfulness.py` + `verifier_agent.py` (CLAUDE.md ask-first files); (3) `download_models.py` extension to non-GGUF artifacts; (4) flag-default-off rollout; (5) any eval-gate threshold note if scorer consumption exists.
  - Implementation sketch for A: lazy `CrossEncoder` load from a local path (`HF_HUB_OFFLINE`-style guarantee at inference), feed `entailment_scores` in `score_claim`, wire `_check_entailment_llm` to the real NLI call behind `use_llm_entailment`, extend `download_models.py` with a named non-GGUF entry + integrity check (`modules/model_integrity.py` exists — check and reuse), tests = the three tracker verification steps verbatim.
  - Cost honesty: ~90MB-class artifact, CPU-fine at ~22M params for per-response scoring; note scoring runs per claim × per source so the brief should cap NLI calls (e.g., only for claims regex leaves neutral).

- [ ] **Step 3: Self-check** — the brief does not mark HC-M11 anything other than `pending`; the decision question is exactly "approve HC-M11 implementation as scoped in the tracker (new model dep, flag default off), approve a different model, defer, or reject?"

- [ ] **Step 4: Commit** — `git commit -am "docs: HC-M11 NLI decision brief"`

---

### Task 7: Assemble, honesty-check, and present for sign-off

**Files:**
- Modify: `audit/2026-09-25/gated-items-decision-packet.md` (remove `_(pending)_` markers, final pass)
- Modify: `docs/features/TASK_LIST.md` — Session Notes entry per AGENT.md Definition of Done
- Read: `docs/agentic/recurring-failures.md` (required re-read before claiming done)

- [ ] **Step 1: Completeness check** — all five briefs present, each matching the Global Constraints template (current-state evidence table, options table with effort/risk/value, recommendation, explicit owner question, sign-off line, sketch of recommended option only). `grep -c "Owner decision:" audit/2026-09-25/gated-items-decision-packet.md` → expect ≥5.

- [ ] **Step 2: Evidence audit** — for every `file:line` cited in the packet, spot-check it resolves to the claimed content (at minimum: re-open 2 citations per brief). Fix or remove any that drifted. This is the recurring-failures "report-as-fact" recheck — a decision packet with wrong line numbers is worse than none.

- [ ] **Step 3: Cross-document honesty sweep** —
  - `git status` / `git diff` on `feature_list.json` → must be empty (HC-M11 stays `pending`; no new rows).
  - `git diff --stat` → the only repo files touched are the packet + TASK_LIST.md Session Notes. No code files.
  - The packet's opening paragraph states clearly: *no implementation begins until the owner signs each brief*.

- [ ] **Step 4: Log the work** — append a Session Notes entry to `docs/features/TASK_LIST.md`: date, "produced gated-items decision packet (audit/2026-09-25/gated-items-decision-packet.md), 5 briefs, awaiting owner sign-off".

- [ ] **Step 5: Read `docs/agentic/recurring-failures.md`** — confirm no listed mode applies (esp. green-suite-as-proof and report-as-fact). If this packet work produced a new instance of a listed mode, record it in the same commit.

- [ ] **Step 6: Commit and report** —

```bash
git add audit/2026-09-25/gated-items-decision-packet.md docs/features/TASK_LIST.md
git commit -m "docs: gated-items owner decision packet — awaiting sign-off"
```

Final report to owner: list the five decision questions verbatim (one line each), the recommendation in each, and where to sign (per-brief line or the ledger table). Then **stop** — implementation of any approved item is a separate writing-plans task.
