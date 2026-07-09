# HIPAA Technical Safeguards Mapping

## Overview

This document maps HealthCentral's technical controls to HIPAA Security Rule
requirements under 45 CFR 164.312.

## 164.312(a) — Access Control

### (a)(1) Unique User Identification

| Requirement | Implementation |
|-------------|----------------|
| Unique ID per user | Each profile has a UUID-based `profile_id` |
| Authentication | Password-based login with JWT tokens |
| Session management | Auto-lock after configurable timeout (default 15 min) |
| Token revocation | Logout invalidates JWT locally |

### (a)(2)(i) Emergency Access Procedure

| Requirement | Implementation |
|-------------|----------------|
| Emergency access | Backup/restore utility for data recovery |
| Data portability | CSV and JSON export of all observations |
| DR runbook | Documented in [disaster-recovery.md](disaster-recovery.md) |

### (a)(2)(ii) Automatic Logoff

| Requirement | Implementation |
|-------------|----------------|
| Inactivity timeout | `auto_lock_timeout_minutes` (default 15) |
| Session expiry | JWT token expiration |
| Manual lock | Profile lock endpoint available |

### (a)(2)(iv) Encryption and Decryption

| Requirement | Implementation |
|-------------|----------------|
| Encryption at rest | SQLCipher (AES-256) for profile vaults |
| Key derivation | Password-based key derivation |
| Master DB | Stores only metadata, not PHI |

## 164.312(b) — Audit Controls

| Requirement | Implementation |
|-------------|----------------|
| Audit logging | `core/audit.py` logs all significant operations |
| Event types | Profile, document, observation, export, auth events |
| Log format | Structured JSON with timestamps and correlation IDs |
| Security audit | `SecurityAuditMiddleware` emits application-log entries for mutating requests |
| Log persistence | Database audit log for core audit events; application logger for security middleware entries |
| Immutability | Audit log entries are append-only |

### Audited Events

| Event Type | Examples |
|------------|----------|
| `auth.*` | Login, logout, failed attempts |
| `profile.*` | Create, unlock, lock, delete |
| `document.*` | Import, view, delete |
| `observation.*` | Verify, edit, delete |
| `export.*` | Summary generation, data export |
| `feedback.*` | Feedback created, annotated, or exported for RL |
| Security middleware log entries | Mutating request summaries emitted to the application logger |

## 164.312(c) — Integrity Controls

### (c)(1) Mechanism to Authenticate ePHI

| Requirement | Implementation |
|-------------|----------------|
| Data integrity | SHA-256 checksums in backup manifests |
| Verification workflow | User verification of extracted observations |
| Source provenance | Document-to-observation traceability |
| Backup integrity | Verify command checks all file checksums |

### (c)(2) Protect Against Improper Alteration

| Requirement | Implementation |
|-------------|----------------|
| Input validation | `InputValidationMiddleware` (body size, null bytes) |
| SQL injection | SQLAlchemy ORM with parameterized queries |
| XSS prevention | Content-Type validation, security headers |
| Rate limiting | Per-IP sliding window counter |

## 164.312(d) — Person or Entity Authentication

| Requirement | Implementation |
|-------------|----------------|
| Authentication method | Password + JWT bearer token |
| Brute force protection | Auth rate limiter (10 attempts/60s) |
| Password security | SQLCipher key derivation (PBKDF2) |
| Session binding | JWT contains profile_id claim |

## 164.312(e) — Transmission Security

### (e)(1) Integrity Controls

| Requirement | Implementation |
|-------------|----------------|
| Local mode | Localhost-only binding (127.0.0.1) |
| Server mode | HSTS headers enforced |
| CORS | Restricted to configured origins |
| Security headers | X-Content-Type-Options, X-Frame-Options, CSP |

### (e)(2) Encryption

| Requirement | Implementation |
|-------------|----------------|
| Local mode | Localhost only — no network transmission |
| Server mode | HTTPS required (HSTS max-age 1 year) |
| API security | Bearer token authentication |
| Correlation | X-Correlation-ID for request tracing |

## Reinforcement Learning and Dataset Export

HealthCentral supports opt-in feedback collection and RL dataset export for model improvement:

| Control | Implementation |
|---------|----------------|
| Feedback audit logging | `api/feedback.py` creates `feedback.*` audit log entries for all feedback operations (create, annotate, export) |
| PHI redaction policy | `modules/rl_dataset.py` applies `modules/redaction.py` at the **strict** policy level before export (RL-REDACT-001, 2026-07-07): SSNs, emails, phones, context-prefixed names, DOB, street addresses, MRNs, and slash/dash numeric dates are removed. Exported JSONL can still contain lab values, biomarker names, medication names, and ISO-8601 collection timestamps — a recorded deferral (they are the training signal); see `docs/features/TASK_LIST.md` RL-REDACT-001. |
| User consent | Explicit `confirmed=true` required in `POST /feedback/export` request — never automatic or silent |
| Data retention | Feedback retained in profile DB until user deletion; exported datasets are persistent local files until manually deleted |

## Gaps and Future Work

| Gap | Priority | Plan |
|-----|----------|------|
| Multi-factor authentication | Medium | Planned for server mode |
| Key rotation | Medium | Manual via password change |
| Network segmentation | Low | N/A for local mode |
| Penetration testing | Medium | Scheduled for post-launch |
| Business Associate Agreement template | High | Required for server deployments |
