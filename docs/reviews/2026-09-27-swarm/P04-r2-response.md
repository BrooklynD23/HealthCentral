R2 (codex) dispositions:
1. [BLOCKER] Task 14 deletes scripts/download_models.py without an owner approval covering it -> ACCEPTED. P4 is docs-only (program P4 sign-off: none beyond D2/D3); deleting a script is not licensed. Default: P4 fixes the doc references only; the deletion becomes an owner-gated option with an unsigned sign-off line (quote the exact path), executed only if signed, as its own commit.
2. [MAJOR] Task 15 continues if W-1 not merged, but P3/W-1 is a hard prerequisite and AGENT.md order needs it -> ACCEPTED: missing P3/W-1 is a STOP gate; remove the continue instruction.
