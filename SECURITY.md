# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email security concerns to the project maintainers privately, or use GitHub's private vulnerability reporting feature if available.

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Initial Assessment**: We will assess the vulnerability within 7 days
- **Resolution Timeline**: We aim to resolve critical vulnerabilities within 30 days
- **Disclosure**: We will coordinate disclosure timing with you

### Scope

The following are in scope for security reports:

- Authentication/authorization bypasses
- Encryption weaknesses or key exposure
- SQL injection or other injection attacks
- Cross-site scripting (XSS)
- Cross-site request forgery (CSRF)
- Sensitive data exposure
- Path traversal vulnerabilities
- Remote code execution

### Out of Scope

- Denial of service attacks
- Social engineering
- Physical security
- Issues in third-party dependencies (report to upstream)

## Security Architecture

Asclexis is designed with security as a core principle:

### Data Protection

- **Encryption at Rest**: All profile databases use SQLCipher (AES-256)
- **Per-Document Encryption**: Documents are encrypted with AES-GCM and per-document IVs
- **Key Management**: Keys are protected using Windows DPAPI or password-based encryption

### Authentication

- **Password Hashing**: bcrypt with automatic work factor adjustment
- **JWT Tokens**: Short-lived tokens (60 minutes) for API authentication
- **Profile Isolation**: Each profile has its own encrypted database

### Network Security

- **Local-First**: Default binding to 127.0.0.1 only
- **No External Calls**: All AI processing happens locally by default
- **CORS Protection**: Configured for development origins only

### Audit Logging

- All sensitive operations are logged
- Authentication events tracked
- Document access recorded

## Security Best Practices for Contributors

When contributing code:

1. **Never commit secrets**: No API keys, passwords, or tokens
2. **Use parameterized queries**: Always use SQLAlchemy ORM
3. **Validate inputs**: Check all user-provided data
4. **Handle errors safely**: Don't expose internal details
5. **Follow least privilege**: Request minimal permissions
6. **Keep dependencies updated**: Monitor for security advisories

## Known Limitations

For transparency, these are current security considerations:

- JWT tokens are revoked on logout using a local revocation list (`jti` claim).
  - Revocation is best-effort per backend process (in-memory checks) with on-disk persistence for restarts.
  - Tokens issued before `jti` support cannot be revoked and will expire naturally.
- Auth endpoints use lightweight in-memory rate limiting (per-process) to reduce brute-force risk.
- Running in "development" mode exposes API documentation

These items are tracked for improvement. See the audit report in `docs/` for details.
