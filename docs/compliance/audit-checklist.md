# Pre-Deployment Audit Checklist

Use this checklist before deploying HealthCentral to production or sharing with users.

> **Note (2026-07-01):** All 50 items below are unchecked, which is correct — this checklist has not yet been run against an actual deployment, and checking a box here should mean "verified for this deployment," not "code capability exists." A 2026-07-01 doc-accuracy pass spot-checked items #6-7 (rate limiting), #14-20 (audit logging), and items in the Security Headers section against current code and confirmed working implementations exist in `src/backend/core/audit.py`, `src/backend/security/security_headers.py`, and `src/backend/core/rate_limiter.py`. That's evidence the *capability* is built, not a substitute for actually running this checklist before a real deployment — leave items unchecked until that happens.

## Access Control

| # | Item | Status |
|---|------|--------|
| 1 | Unique profile IDs assigned to all users | [ ] |
| 2 | Password authentication enforced | [ ] |
| 3 | JWT tokens have expiration configured | [ ] |
| 4 | Auto-lock timeout is set (default 15 min) | [ ] |
| 5 | Token revocation works on logout | [ ] |
| 6 | Rate limiting active on auth endpoints (10/60s) | [ ] |
| 7 | Rate limiting active on API endpoints (100/60s) | [ ] |

## Encryption

| # | Item | Status |
|---|------|--------|
| 8 | SQLCipher installed and verified | [ ] |
| 9 | Profile vaults encrypted with AES-256 | [ ] |
| 10 | `DATABASE_ENCRYPTION_REQUIRED=true` in production | [ ] |
| 11 | JWT secret set via environment variable (not default) | [ ] |
| 12 | Server mode uses HTTPS (HSTS header present) | [ ] |
| 13 | CSP header configured for server mode | [ ] |

## Audit Logging

| # | Item | Status |
|---|------|--------|
| 14 | Audit logging enabled (`AUDIT_LOG_ENABLED=true`) | [ ] |
| 15 | Auth events logged (login, logout, failed) | [ ] |
| 16 | Document events logged (import, view, delete) | [ ] |
| 17 | Observation events logged (verify, edit) | [ ] |
| 18 | Security middleware application-log entries captured and retained per policy | [ ] |
| 19 | Log files rotated and retained per policy | [ ] |
| 20 | Audit logs do not contain PHI in plaintext | [ ] |

## Input Validation

| # | Item | Status |
|---|------|--------|
| 21 | Request body size limit enforced (10 MB default) | [ ] |
| 22 | Null byte injection blocked in paths and queries | [ ] |
| 23 | SQL injection mitigated (ORM with parameterized queries) | [ ] |
| 24 | XSS headers present (X-Content-Type-Options, etc.) | [ ] |
| 25 | File upload types restricted to PDF/PNG/JPG/JPEG | [ ] |

## Reinforcement Learning and Feedback

| # | Item | Status |
|---|------|--------|
| 26 | RL feedback export requires explicit user confirmation (`confirmed=true`) | [ ] |
| 27 | Redaction of PHI in exported RL datasets verified (spot-check sample JSONL export for plaintext PHI) | [ ] |
| 28 | Audit log contains feedback export events (`feedback.*` event types) | [ ] |

## Backup and Recovery

| # | Item | Status |
|---|------|--------|
| 29 | Backup script tested and working | [ ] |
| 30 | Backup integrity verification passing | [ ] |
| 31 | Restore procedure tested successfully | [ ] |
| 32 | Backup retention policy configured (30 days default) | [ ] |
| 33 | Disaster recovery runbook reviewed and accessible | [ ] |

## Network Security (Server Mode)

| # | Item | Status |
|---|------|--------|
| 34 | CORS origins restricted to known domains | [ ] |
| 35 | API bound to appropriate interface (not 0.0.0.0 without firewall) | [ ] |
| 36 | HSTS enabled with max-age >= 1 year | [ ] |
| 37 | Debug mode disabled (`DEBUG=false`) | [ ] |
| 38 | API docs disabled in production (auto when debug=false) | [ ] |

## Security Headers

| # | Item | Status |
|---|------|--------|
| 39 | X-Content-Type-Options: nosniff | [ ] |
| 40 | X-Frame-Options: DENY | [ ] |
| 41 | Referrer-Policy set | [ ] |
| 42 | Permissions-Policy restricts camera/mic/geo | [ ] |
| 43 | X-Correlation-ID present on responses | [ ] |

## Monitoring

| # | Item | Status |
|---|------|--------|
| 44 | Health endpoint accessible (/health) | [ ] |
| 45 | Metrics collection enabled | [ ] |
| 46 | Error rates monitored | [ ] |
| 47 | Response times tracked | [ ] |

## Dependencies

| # | Item | Status |
|---|------|--------|
| 48 | pip-audit run with no critical vulnerabilities | [ ] |
| 49 | Bandit scan completed with no high-severity findings | [ ] |
| 50 | All dependencies pinned to specific versions | [ ] |

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Security Reviewer | | | |
| Project Lead | | | |
