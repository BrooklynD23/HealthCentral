R1 (codex) dispositions:
1. [MAJOR] D8 vs D8-delivery wording -> ACCEPTED: distinguish them; D8-delivery (owner, 2026-09-27, "Script + offline load"): one-time download_models.py fetch into a local models dir; HF offline at runtime; fails closed if absent; installer bundles later (G-C4); no weights in git.
2. [MAJOR] §1 forbids docs/plans/** but §15 is an execution record in this plan -> ACCEPTED: exempt this plan's §15 only.
3. [BLOCKER] Task 12 commits with directory pathspec .serena/memories/ -> ACCEPTED: the seven exact file paths.
4. [MAJOR] pytest | tail without pipefail -> ACCEPTED (GLOBAL rules).
Ownership ruling to reflect: CLAUDE.md:62 (D11) is never P4's; if W-10 Q1 is unsigned it stays unchanged as an open owner item. Apply reviews/GLOBAL-rules.md.
R2 (codex) dispositions:
1. [BLOCKER] Task 14 deletes scripts/download_models.py without an owner approval covering it -> ACCEPTED. P4 is docs-only (program P4 sign-off: none beyond D2/D3); deleting a script is not licensed. Default: P4 fixes the doc references only; the deletion becomes an owner-gated option with an unsigned sign-off line (quote the exact path), executed only if signed, as its own commit.
2. [MAJOR] Task 15 continues if W-1 not merged, but P3/W-1 is a hard prerequisite and AGENT.md order needs it -> ACCEPTED: missing P3/W-1 is a STOP gate; remove the continue instruction.
