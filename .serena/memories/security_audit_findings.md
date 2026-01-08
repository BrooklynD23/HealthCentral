# Security Audit Findings (January 2026)

## Implementation Status (Updated January 7, 2026)

### COMPLETED Fixes:
- ✅ Created models directory with all SQLAlchemy models (Profile, Document, Observation, AuditLog, Chunk, Embedding)
- ✅ Fixed DPAPI fallback to fail securely with KeySealingError exception
- ✅ Implemented JWT secret persistence (stores to data/.jwt_secret on first run)
- ✅ Added AES-GCM document encryption in IngestModule
- ✅ Created centralized audit logging in core/audit.py
- ✅ Added UUID validation to all API endpoints (path traversal protection)
- ✅ Sanitized error messages to not leak internal paths

### REMAINING Work:
- ✅ Profile password authentication (Phase 2) - COMPLETED 2026-01-07
- ✅ Authorization middleware for all endpoints - COMPLETED 2026-01-07
- ✅ Per-profile SQLCipher databases (Phase 3) - COMPLETED 2026-01-07
- ✅ Verifier agent pattern for AI safety (Phase 4) - COMPLETED 2026-01-07

### Phase 4 Implementation Details (2026-01-07):
- Created `modules/claim_extractor.py` with `ClaimExtractor` class:
  - Parses LLM responses into individual verifiable claims
  - Classifies claim types (factual, comparative, temporal, causal)
  - Links claims to citations
  - Filters verifiable vs unverifiable claims
- Created `modules/source_authority.py` with `SourceAuthorityScorer`:
  - Four-tier authority system (Tier 1-4)
  - Tier 1: User-verified personal documents (highest trust)
  - Tier 2: Peer-reviewed medical references
  - Tier 3: Educational content
  - Tier 4: Unverified sources (lowest trust)
  - Validates authority requirements per claim type
- Created `modules/verifier_agent.py` with `VerifierAgent`:
  - Entailment checking (rule-based, LLM-ready)
  - Contradiction detection with pattern matching
  - Faithfulness scoring integration
  - Batch verification support
- Created `modules/faithfulness.py` with `FaithfulnessScorer`:
  - Multi-component scoring: entailment, lexical, semantic
  - Configurable weights and thresholds
  - N-gram overlap analysis
  - Entity extraction and matching
- Updated `modules/rag.py` with verification pipeline:
  - `_run_verification_pipeline()` orchestrates all Phase 4 components
  - `VerificationMetadata` dataclass for transparency
  - Integrated into `validate_response()` and `query()` methods
- Updated `api/assistant.py`:
  - Added `VerificationInfo` response model
  - `/chat` endpoint now returns verification metadata
  - New `/verification-status` endpoint for system info
- Updated `core/config.py` with verification settings:
  - `verification_enabled`, `min_faithfulness_score`
  - `fail_on_contradiction`, `min_supporting_sources`
  - `use_llm_entailment`, `multi_pass_verification`

### Phase 3 Implementation Details (2026-01-07):
- Created `core/profile_database.py` with `PerProfileDatabaseManager` class
- Implemented per-profile SQLCipher encrypted database architecture:
  - Master DB: Profile metadata, AuditLog (for login/listing)
  - Per-Profile DB: Document, Observation, Chunk, Embedding (encrypted)
- Session-bound database connections:
  - DB opened on login/unlock with password for key unsealing
  - DB closed on logout/lock with key clearing from memory
- Updated models to use `ProfileDatabaseBase` for per-profile tables
- Added `ProfileDbSession` dependency for authenticated API endpoints
- Memory clearing on logout/lock to prevent residual data access

### Phase 2 Implementation Details (2026-01-07):
- Created `core/auth.py` with JWT session management
- Added password field to ProfileCreate with validation (8+ chars, upper/lower/digit)
- Added `/login`, `/logout`, `/me` endpoints
- Added `RequireAuth` dependency to all protected endpoints
- Added `require_profile_access()` for profile-specific authorization
- All API modules (documents, observations, assistant, export) now require authentication
- Removed legacy insecure `seal_key_with_dpapi_legacy` usage from profiles.py

---


## CRITICAL Issues

### 1. Missing Models Directory
- **Location**: `src/backend/models/` (doesn't exist)
- **Impact**: Application cannot start
- **Files Affected**: database.py:56, profiles.py:21, documents.py:19, observations.py:16
- **Action**: Create SQLAlchemy model definitions

### 2. Documents Stored in Plaintext
- **Location**: `src/backend/modules/ingest.py:154-157`
- **Impact**: Medical documents not encrypted despite PRD requirements
- **Code**: `doc_path.write_bytes(file_data)` - raw bytes, no encryption
- **Action**: Implement AES-GCM encryption with per-document keys

### 3. DPAPI Fallback Returns Plaintext Keys
- **Location**: `src/backend/core/security.py:162-167, 191-193`
- **Impact**: Encryption keys stored unprotected on non-Windows or DPAPI failure
- **Code**: `return key` fallback instead of secure failure
- **Action**: Require DPAPI or implement alternative (password-based KDF)

### 4. No Authentication on API Endpoints
- **Location**: All API routes in `src/backend/api/`
- **Impact**: Any process on localhost can access any profile's data
- **Action**: Implement session-based authentication with profile password/PIN

### 5. JWT Secret Not Persisted
- **Location**: `src/backend/core/security.py:34-39`
- **Impact**: All sessions invalidated on server restart
- **Action**: Generate and securely store JWT secret on first run

## HIGH Priority Issues

### 6. No Profile-Level Access Control
- **Impact**: Multi-user isolation impossible - users can access each other's data
- **Action**: Add authorization middleware, bind sessions to profiles

### 7. Path Traversal Risk
- **Location**: `src/backend/api/documents.py:240-241`
- **Code**: `vault_path / f"{document_id}.bin"`
- **Action**: Validate document_id as UUID format

### 8. Shared Database Without Isolation
- **Location**: `src/backend/core/config.py:86-87`
- **Impact**: Single DB for all profiles violates PRD per-profile vault design
- **Action**: Implement per-profile SQLCipher databases

### 9. Verbose Error Messages
- **Location**: `src/backend/api/documents.py:263-267`
- **Impact**: Could leak internal paths/system info
- **Action**: Sanitize exception messages in responses

## MEDIUM Priority Issues

### 10. Duplicated Audit Log Function
- **Locations**: profiles.py:59-78, documents.py:71-90, observations.py:126-145
- **Action**: Centralize in core/audit.py

### 11. No Database Migrations
- **Impact**: Schema changes require manual DB management
- **Action**: Set up Alembic

### 12. No Rate Limiting
- **Action**: Add rate limiting middleware

### 13. CORS Allow All Headers
- **Location**: `src/backend/main.py:49`
- **Action**: Restrict to specific required headers

## AI/RAG Hallucination Mitigation Recommendations

### Current Good Practices (in rag.py)
- Citation requirement in prompt template
- Response segmentation (report_facts, general_info, uncertainty)
- Prohibited content detection

### Recommended Enhancements
1. **Verifier Agent**: Secondary LLM to validate claims against citations
2. **Source Authority Tiers**: Weight medical references by reliability
3. **Claim Extraction Pipeline**: Parse claims and verify entailment
4. **Confidence Scoring**: Add faithfulness metrics

## Multi-User Data Protection Requirements

1. Profile authentication (password/PIN)
2. Per-profile encrypted databases
3. Session-profile binding
4. Authorization middleware on all endpoints
5. Memory clearing on profile lock
