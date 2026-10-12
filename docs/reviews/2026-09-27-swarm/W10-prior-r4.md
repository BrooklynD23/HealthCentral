R1 (codex) dispositions:
1. [BLOCKER] export inventory misses multiline `/feedback/export` (api/feedback.py:306 @B, mounted api/__init__.py:58) -> ACCEPTED. Orchestrator verified: route exists; docstring says it applies RedactionEngine and requires confirmed=true (feedback.py:1-12, :319). Fix: inventory mounted routes with a multiline-aware method (e.g. python ast over api/*.py for router decorators, or `git grep -n -A3 "@router\."`); classify /feedback/export from CODE evidence (verify the redaction call path in modules/rl_dataset, not the docstring); DP-2 covers every export-shaped route; S5 stops on any unclassified one.
2. [MAJOR] GREEN/break-it commands hard-code --c3 and omit Q2 flag -> ACCEPTED: one ARGS variable derived from signed Q1–Q3, used by every assertion run.
3. [MAJOR] implemented-variant selection needs only IDs + passing -> ACCEPTED: variant I requires the W-item PR's recorded red-first output + break-it evidence (+ route_client for routes); otherwise variant "approved, not yet implemented".
Also fix the broken DOC-007 link "-> target" in your plan, and the ownership ruling: if Q1 is unsigned, CLAUDE.md:62 stays unchanged and becomes an open owner item — it does NOT go to P4 (fix plan :52). Apply reviews/GLOBAL-rules.md.
R2 (codex) dispositions:
1. [MAJOR] file-wide route_client grep -> ACCEPTED: verify the specific HC test function calls route_client (AST or function-scoped grep) and record the call line as evidence.
2. [MAJOR] merged-without-evidence keeps "not yet implemented" -> ACCEPTED: label "merged; conformance unverified" until the variant-I evidence exists.
R3 (codex) dispositions — fixed after round 3 (owner asked about round 4):
1. [MAJOR] AST inventory prints router-local paths vs mounted paths -> ACCEPTED: include each router's mount prefix (api/__init__.py include_router prefixes) in the output.
2. [MAJOR] Q2 re-gates what D12 already approves -> ACCEPTED: D12 text "keep break-glass only with audit + UI warning. Amend CLAUDE.md to name the exception" licenses naming audited break-glass. Remove Q2 as a gate; include the clause unconditionally, worded strictly within D12's text.
Add "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."
