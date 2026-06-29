"""Read-only, profile-scoped agent tools (Phase 1–2).

Every tool registers with a Pydantic input AND output schema. Malformed args
fail validation and are NEVER executed (skills/healthcentral-agent). New tools
must be read-only and scoped to the unlocked profile vault session.
"""
