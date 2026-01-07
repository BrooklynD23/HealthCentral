 HealthCentral Expert Security & Architecture Panel Report

  Executive Summary

  I've completed a comprehensive audit of the HealthCentral project. While the architectural documentation shows thoughtful security planning, the implementation has critical gaps that must be addressed before handling real patient data, especially in a multi-user context.

  ---
  🔴 CRITICAL Issues (Must Fix Immediately)

  1. Application Cannot Start - Missing Models

  Location: src/backend/models/ directory does not exist
  - Impact: Import statements fail (from models import Profile, AuditLog)
  - Severity: CRITICAL - Blocks all development/testing

  2. Documents Stored in Plaintext

  Location: src/backend/modules/ingest.py:154-157
  # TODO: Encrypt and store document
  # For now, store plaintext (encryption to be added)
  doc_path.write_bytes(file_data)  # ⚠️ RAW BYTES - NO ENCRYPTION
  - PRD Requirement: "Encrypted at rest: database, vector index, stored documents"

  3. DPAPI Fallback Returns Keys Unprotected

  Location: src/backend/core/security.py:162-167
  except Exception:
      # DPAPI operation failed
      return key  # ⚠️ Returns plaintext key on ANY failure
  - On non-Windows or ANY DPAPI failure, encryption keys are stored unprotected

  4. No Authentication on Any Endpoint

  - All API endpoints accept profile_id as a parameter
  - No verification that the caller has permission to access that profile
  - Any process on localhost can read ANY user's medical data

  5. JWT Secret Regenerated on Every Restart

  Location: src/backend/core/security.py:34-39
  - Sessions become invalid after server restart
  - In development this is annoying; in production it's a security issue

  ---
  🟠 HIGH Priority Security Issues
  ┌──────────────────────────────┬──────────────────────┬──────────────────────────────────────────┐
  │            Issue             │       Location       │                   Risk                   │
  ├──────────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
  │ No multi-user data isolation │ All API routes       │ Users can access each other's data       │
  ├──────────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
  │ Path traversal risk          │ documents.py:240     │ Malicious document_id could escape vault │
  ├──────────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
  │ Shared DB for all profiles   │ config.py:86-87      │ Violates per-profile vault architecture  │
  ├──────────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
  │ Verbose error messages       │ documents.py:263-267 │ Leaks internal file paths                │
  ├──────────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
  │ No CSRF protection           │ frontend api.ts      │ Cross-site request forgery possible      │
  └──────────────────────────────┴──────────────────────┴──────────────────────────────────────────┘
  ---
  🟡 Code Quality Issues
  ┌──────────────────────────────────────────┬──────────────────────────────────────────────────┐
  │                  Issue                   │                      Impact                      │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ create_audit_log() duplicated in 3 files │ Maintenance burden, inconsistency risk           │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ No database migrations (Alembic)         │ Schema changes require manual DB management      │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ Inconsistent error handling              │ Some endpoints raise HTTPException, others don't │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ dict[str, any] wrong case                │ Should be dict[str, Any]                         │
  ├──────────────────────────────────────────┼──────────────────────────────────────────────────┤
  │ No input validation for UUIDs            │ Invalid IDs could cause unexpected behavior      │
  └──────────────────────────────────────────┴──────────────────────────────────────────────────┘
  ---
  🤖 AI Hallucination Reduction Analysis

  Current Good Practices (in rag.py)

  ✅ Citation requirement in system prompt
  ✅ Response segmentation (report_facts, general_info, uncertainty)
  ✅ Prohibited content detection (diagnosis, treatment, medication)
  ✅ Conservative refusal policy

  Missing Components for Your Requirements

  User Request: "AI model response should be fact-checked by another AI agent"

  Recommended Architecture: Dual-Agent Verification

  ┌─────────────────────────────────────────────────────┐
  │                  RAG Pipeline                       │
  ├─────────────────────────────────────────────────────┤
  │  1. Query → Embed → Retrieve relevant chunks        │
  │  2. Primary Agent generates response with citations │
  │  3. Claim Extractor parses individual facts         │
  │  4. VERIFIER AGENT checks each claim:               │
  │     - Does cited text support this claim?           │
  │     - Is this within the source's authority?        │
  │  5. Only return verified claims to user             │
  └─────────────────────────────────────────────────────┘

  Additional Strategies:
  1. Source Authority Tiers:
    - Tier 1: User's verified lab documents (for "your results")
    - Tier 2: Peer-reviewed medical references
    - Tier 3: General medical information
  2. Confidence Calibration: Multiple generation passes with consistency check
  3. Faithfulness Scoring: NLI-based entailment verification between claims and sources

  ---
  👥 Multi-User Data Protection Architecture

  Your Requirement: "In the case that multiple users login, we should be able to protect other users data to prevent leakage."

  Current State

  - ❌ No user authentication
  - ❌ Shared database for all profiles
  - ❌ Profile ID passed as parameter (anyone can access any profile)

  Required Architecture

  ┌────────────────────────────────────────────────────────────┐
  │                   Authentication Layer                      │
  ├────────────────────────────────────────────────────────────┤
  │  Profile Selection → Password/PIN Entry → Session Created  │
  │                                                            │
  │  Session Token contains:                                   │
  │  - Authenticated profile_id (encrypted)                    │
  │  - Expiration timestamp                                    │
  │  - HMAC signature                                          │
  └────────────────────────────────────────────────────────────┘
                                │
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │                  Per-Profile Isolation                      │
  ├────────────────────────────────────────────────────────────┤
  │  Each profile has:                                         │
  │  ├── vault_{profile_id}/                                   │
  │  │   ├── vault.db (SQLCipher encrypted with unique key)   │
  │  │   ├── docs/ (AES-GCM encrypted documents)              │
  │  │   └── key.bin (DPAPI + password-KDF sealed master key) │
  │                                                            │
  │  Database opened ONLY with authenticated session           │
  │  API middleware verifies session.profile_id == request.id  │
  └────────────────────────────────────────────────────────────┘

  ---
  📋 Prioritized Remediation Roadmap

  Phase 1: Make App Runnable

  1. Create src/backend/models/ with SQLAlchemy model definitions
  2. Define Profile, Document, Observation, AuditLog, Chunk, Embedding models
  3. Verify app starts and database initializes

  Phase 2: Basic Security

  4. Implement profile password authentication
  5. Add session management with JWT
  6. Add authorization middleware to all endpoints
  7. Fix DPAPI fallback (fail secure, not insecure)
  8. Implement document encryption in ingest module

  Phase 3: Multi-User Isolation

  9. Implement per-profile SQLCipher databases
  10. Session-profile binding enforcement
  11. Memory clearing on profile lock

  Phase 4: AI Safety

  12. Implement verifier agent pattern
  13. Add source authority scoring
  14. Implement claim extraction + verification

  ---
  ✅ Serena MCP Setup Complete

  I've onboarded Serena for this project with the following memories created:
  - project_overview.md - Purpose, tech stack, structure
  - suggested_commands.md - Development commands
  - code_style_conventions.md - Python/TypeScript patterns
  - task_completion_checklist.md - Pre-commit checklist
  - security_audit_findings.md - This audit's findings

  These are stored in Serena's project memories and will be available for future sessions and other developers working on this project.

  ---
  Expert Panel Attribution

  This audit synthesized perspectives from:
  - Michael Nygard (Release It!): Production failure modes, circuit breakers for auth
  - Sam Newman (Microservices): Service boundaries, per-profile isolation
  - Karl Wiegers: Requirements analysis - implementation gaps vs PRD
  - Lisa Crispin: Testing strategy recommendations
  - OWASP Guidelines: Security vulnerability classification