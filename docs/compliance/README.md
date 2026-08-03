# Compliance Documentation

## Privacy guarantees added 2026-07-27

Three previously-open items landed together; each is documented in the file
named beside it.

| Guarantee | Where | What changed |
|---|---|---|
| **Audit rows carry no PHI** | [`hipaa-controls.md`](hipaa-controls.md) | `core/audit.py` allowlist-scrubs every row before write. Actions are static templates; `details` keeps only ids, counts, booleans and spaceless enums. Filenames, analyte names, medication names, observation values and query text are dropped. Coverage is unchanged — content is minimized, no event removed. |
| **Right to erase** | [`data-privacy.md`](data-privacy.md) | `DELETE /profiles/{id}` destroys the sealed keys (the cryptographic erase), sweeps the vault, purges that profile's audit rows and leaves one anonymized tombstone. The claim made is file deletion plus key destruction — never byte overwriting, which SSD wear-levelling makes false. |
| **Recoverable encryption** | [`data-privacy.md`](data-privacy.md) | A one-time recovery code seals a second copy of the data key, so a forgotten password is no longer permanent loss of the record. The code is never persisted, logged, or hashed. |

**Known residual:** audit rows written *before* the minimization landed may
still contain filenames and analyte names. They are deliberately left untouched
rather than rewritten — an append-only audit trail is a worse property to give
up than the exposure it would remove. Profile deletion is the only path that
removes them.

## Overview

Asclexis implements security and privacy controls aligned with HIPAA
technical safeguards for protected health information (PHI).

## Documents

| Document | Description |
|----------|-------------|
| [HIPAA Controls](hipaa-controls.md) | HIPAA 164.312 technical safeguards mapping |
| [Data Privacy](data-privacy.md) | Data classification, encryption, retention |
| [AI Safety](ai-safety.md) | Refusal/escalation boundaries, grounding, injection and PHI-leakage evals |
| [Audit Checklist](audit-checklist.md) | Pre-deployment compliance checklist |
| [Disaster Recovery](disaster-recovery.md) | Backup and recovery runbook |
| [Security Review — Sprint 06](security-review-sprint06.md) | Static security analysis of Sprint 06 code |
| [Advisories](advisories.md) | Security/observability advisories and their resolution |
| [RL Dataset Export Policy](data-privacy.md#reinforcement-learning-dataset-export) | Feedback collection, export, and redaction safeguards |

## Scope

These documents apply to the Asclexis application in all deployment modes
(local and server). Server deployments have additional requirements for network
security, HSTS, and CSP headers.
