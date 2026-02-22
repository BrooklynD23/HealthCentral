# Pre-Deployment Audit Checklist

Use this checklist before deploying HealthCentral to production or sharing with users.

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
| 18 | Security events logged (rate limit, input rejection) | [ ] |
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

## Backup and Recovery

| # | Item | Status |
|---|------|--------|
| 26 | Backup script tested and working | [ ] |
| 27 | Backup integrity verification passing | [ ] |
| 28 | Restore procedure tested successfully | [ ] |
| 29 | Backup retention policy configured (30 days default) | [ ] |
| 30 | Disaster recovery runbook reviewed and accessible | [ ] |

## Network Security (Server Mode)

| # | Item | Status |
|---|------|--------|
| 31 | CORS origins restricted to known domains | [ ] |
| 32 | API bound to appropriate interface (not 0.0.0.0 without firewall) | [ ] |
| 33 | HSTS enabled with max-age >= 1 year | [ ] |
| 34 | Debug mode disabled (`DEBUG=false`) | [ ] |
| 35 | API docs disabled in production (auto when debug=false) | [ ] |

## Security Headers

| # | Item | Status |
|---|------|--------|
| 36 | X-Content-Type-Options: nosniff | [ ] |
| 37 | X-Frame-Options: DENY | [ ] |
| 38 | Referrer-Policy set | [ ] |
| 39 | Permissions-Policy restricts camera/mic/geo | [ ] |
| 40 | X-Correlation-ID present on responses | [ ] |

## Monitoring

| # | Item | Status |
|---|------|--------|
| 41 | Health endpoint accessible (/health) | [ ] |
| 42 | Metrics collection enabled | [ ] |
| 43 | Error rates monitored | [ ] |
| 44 | Response times tracked | [ ] |

## Dependencies

| # | Item | Status |
|---|------|--------|
| 45 | pip-audit run with no critical vulnerabilities | [ ] |
| 46 | Bandit scan completed with no high-severity findings | [ ] |
| 47 | All dependencies pinned to specific versions | [ ] |

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Security Reviewer | | | |
| Project Lead | | | |
