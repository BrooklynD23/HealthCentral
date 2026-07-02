# Security & Compliance

**Owner:** Project Lead
**Refresh Trigger:** A compliance finding's status changes, or a new HIPAA control is added

## Scope

HIPAA technical safeguards, PHI/PII redaction, encryption boundaries (SQLCipher, JWT, password
hashing), audit logging, and disaster recovery. **CLAUDE.md hard rule:** always ask before touching
`modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`,
`modules/verifier_agent.py`, or anything auth/encryption.

## Start here

- [`docs/03_data_confidentiality_pipeline_plan.md`](../03_data_confidentiality_pipeline_plan.md) — confidentiality pipeline design
- [`docs/compliance/hipaa-controls.md`](../compliance/hipaa-controls.md) — HIPAA technical safeguards status
- [`docs/compliance/data-privacy.md`](../compliance/data-privacy.md) — data privacy posture
- [`docs/compliance/audit-checklist.md`](../compliance/audit-checklist.md) — pre-deployment sign-off checklist (unchecked by design until an actual deployment audit runs)
- [`docs/compliance/disaster-recovery.md`](../compliance/disaster-recovery.md) — backup/restore
- [`docs/compliance/security-review-sprint06.md`](../compliance/security-review-sprint06.md) — Sprint 06 findings (S06-SEC-001/002 resolved/mitigated, S06-SEC-003 still open as of 2026-07)
- [`docs/compliance/f006-profile-id-removal-review.md`](../compliance/f006-profile-id-removal-review.md) — F-006 review (not started)
- [`../../SECURITY.md`](../../SECURITY.md) — top-level security policy

## Related roles

- [`ai-llm-pipeline-and-safety.md`](ai-llm-pipeline-and-safety.md) — RL export redaction gap (`RL-REDACT-001`, see `docs/features/TASK_LIST.md`)
- [`data-and-migrations.md`](data-and-migrations.md) — encryption at the storage layer
