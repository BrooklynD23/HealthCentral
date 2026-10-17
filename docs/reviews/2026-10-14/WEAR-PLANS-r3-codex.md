# WEAR-PLANS r3 — Codex review after the owner answered D1-D8

**Target:** `docs/wearables-plans` @ `ad8e191` (owner-answer amendments: WEAR-D1..D8, commit `c53ba44`, PR #92) against `origin/main` (`8234990`). 2026-10-14. Codex default model; the companion `review` / `adversarial-review` subcommands expose no model option.
**Response:** [WEAR-PLANS-r3-response.md](WEAR-PLANS-r3-response.md)

Verbatim stdout+stderr of both commands.

## Native review (`review --base origin/main --wait`)

```text
[codex] Starting Codex review thread.
[codex] Thread ready (01a13bb4-c481-7aa2-be7b-16cc02563438).
[codex] Reviewer started: changes against 'origin/main'
[codex] Running command: /bin/bash -lc "cat /home/danny/.codex/skills/code-review/SKILL.md && printf '\\n---FILES---\\...
[codex] Running command: /bin/bash -lc 'git status --short; git rev-parse 823499043fe91c628062e7c3f6b915d3c1c08e1f; gi...
[codex] Running command: /bin/bash -lc 'pwd; git branch --show-current; git rev-parse HEAD; git status --short --branc...
[codex] Command completed: /bin/bash -lc 'git status --short; git rev-parse 823499043fe91c628062e7c3f6b915d3c1c08e1f; gi... (exit 0)
[codex] Command completed: /bin/bash -lc 'pwd; git branch --show-current; git rev-parse HEAD; git status --short --branc... (exit 0)
[codex] Running command: /bin/bash -lc "GIT_PAGER=cat git diff --stat 823499043fe91c628062e7c3f6b915d3c1c08e1f; find ....
[codex] Command failed: /bin/bash -lc "GIT_PAGER=cat git diff --stat 823499043fe91c628062e7c3f6b915d3c1c08e1f; find .... (exit 2)
[codex] Running command: /bin/bash -lc "git log --format='%H%n%s%n%b' 823499043fe91c628062e7c3f6b915d3c1c08e1f..HEAD; ...
[codex] Command completed: /bin/bash -lc "git log --format='%H%n%s%n%b' 823499043fe91c628062e7c3f6b915d3c1c08e1f..HEAD; ... (exit 0)
[codex] Running command: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-00-program.md docs/plans/2026-10-13-w...
[codex] Command completed: /bin/bash -lc 'for f in docs/plans/2026-10-13-wearables-00-program.md docs/plans/2026-10-13-w... (exit 0)
[codex] Running command: /bin/bash -lc "printf '%s\\n' '--- D6 references ---'; rg -n -C 2 'D6|temp-file|temporary fil...
[codex] Command completed: /bin/bash -lc "printf '%s\\n' '--- D6 references ---'; rg -n -C 2 'D6|temp-file|temporary fil... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-14-docs.md | sed -n '1,180p'; printf '\...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-14-docs.md | sed -n '1,180p'; printf '\... (exit 0)
[codex] Running command: /bin/bash -lc "git diff --no-ext-diff --unified=5 823499043fe91c628062e7c3f6b915d3c1c08e1f --...
[codex] Command completed: /bin/bash -lc "git diff --no-ext-diff --unified=5 823499043fe91c628062e7c3f6b915d3c1c08e1f --... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '1,45p;15...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-07-review-backend.md | sed -n '1,45p;15... (exit 0)
[codex] Running command: /bin/bash -lc 'python3 scripts/docs_lint.py --link-graph && python3 scripts/generate_docs_ind...
[codex] Running command: /bin/bash -lc "rg -n -A8 -B2 'wearables-09-packet|WEAR-09 —' docs/INDEX.md; sed -n '1,35p' do...
[codex] Command completed: /bin/bash -lc "rg -n -A8 -B2 'wearables-09-packet|WEAR-09 —' docs/INDEX.md; sed -n '1,35p' do... (exit 0)
[codex] Running command: /bin/bash -lc "sed -n '1,220p' scripts/generate_docs_index.py; printf '\\n--- changed index e...
[codex] Command completed: /bin/bash -lc "sed -n '1,220p' scripts/generate_docs_index.py; printf '\\n--- changed index e... (exit 0)
[codex] Running command: /bin/bash -lc 'python3 scripts/generate_docs_index.py --check'
[codex] Command failed: /bin/bash -lc 'python3 scripts/generate_docs_index.py --check' (exit 1)
[codex] Command failed: /bin/bash -lc 'python3 scripts/docs_lint.py --link-graph && python3 scripts/generate_docs_ind... (exit 1)
[codex] Running command: /bin/bash -lc "nl -ba .github/workflows/ci.yml | sed -n '1,55p'; nl -ba docs/INDEX.md | sed -...
[codex] Command completed: /bin/bash -lc "nl -ba .github/workflows/ci.yml | sed -n '1,55p'; nl -ba docs/INDEX.md | sed -... (exit 0)
[codex] Review output captured.
[codex] Reviewer finished.
[codex] Assistant message captured: The generated-docs freshness check fails in CI, and the privacy-documentation plan contradict...
[codex] Turn completed.
# Codex Review

Target: branch diff against origin/main

The generated-docs freshness check fails in CI, and the privacy-documentation plan contradicts the signed export decision. Regenerate the index and graph, then correct the D7 statement.

Full review comments:

- [P1] Regenerate the documentation index and link graph — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans/docs/INDEX.md:1133-1135
  `python3 scripts/generate_docs_index.py --check` exits 1, so the CI freshness step fails. The index still describes WEAR-09 as conditional symptom notes, while the plan now specifies a saved journal; `_link_graph.json` is stale as well. Regenerate both artifacts after the final plan edits.

- [P2] Correct the D7 export statement — /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans/docs/plans/2026-10-13-wearables-14-docs.md:76-76
  When WEAR-14 is followed, this directs the privacy documentation to say wearable data is absent from `/export/json`, contradicting the signed D7 decision and WEAR-13's opt-in wearable export block. Update this statement to describe the approved export behavior so the resulting privacy documentation is accurate.
```

## Adversarial review (`adversarial-review --wait --base origin/main "<focus>"`)

Focus: the symptom journal and its privacy/redaction path into the packet, audit (HC-AUD-004), delete/reset with FK cascades off; profile migration ordering (WEAR-02, WEAR-15 vs P6 013, G-C1 014, AUDIT-ORDER 015, GAM2 2b); the `garmin-fit-sdk` dependency (licence gate, pin, single importer, no-network, JSON-first); WEAR-D3 = 14 days consistency; `/export/json` block inside D3; misquoted owner answers.

```text
[codex] Starting Codex task thread.
[codex] Starting Codex task thread.
[codex] Thread ready (01a13bb5-3522-7661-b6f2-187a4b1f1838).
[codex] Turn started (01a13bb5-3e4f-7d83-9c6c-4e8dafbf12ef).
[codex] Assistant message captured: Step 1 of 3: I’m reading the review procedure and the actual branch diff; I’ll return only fi...
[codex] Running command: /bin/bash -lc 'cat /home/danny/.codex/skills/code-review/SKILL.md && git status --short && gi...
[codex] Command completed: /bin/bash -lc 'cat /home/danny/.codex/skills/code-review/SKILL.md && git status --short && gi... (exit 0)
[codex] Running command: /bin/bash -lc "git rev-parse origin/main && git rev-parse HEAD && git log origin/main..HEAD -...
[codex] Command completed: /bin/bash -lc "git rev-parse origin/main && git rev-parse HEAD && git log origin/main..HEAD -... (exit 0)
[codex] Assistant message captured: Step 2 of 3: the branch is 9 commits ahead of `origin/main`; the latest commit adds the sympt...
[codex] Running command: /bin/bash -lc "cat CONTRIBUTING.md && git show c53ba44:docs/capstone-report/owner-decisions-2...
[codex] Command completed: /bin/bash -lc "cat CONTRIBUTING.md && git show c53ba44:docs/capstone-report/owner-decisions-2... (exit 0)
[codex] Running command: /bin/bash -lc "git show c53ba44:docs/capstone-report/owner-decisions-2026-09-27.md | rg -n -A...
[codex] Command completed: /bin/bash -lc "git show c53ba44:docs/capstone-report/owner-decisions-2026-09-27.md | rg -n -A... (exit 0)
[codex] Running command: /bin/bash -lc "rg -n '14.?days|14 days|minimum|minimum_days|data on|coverage|/export/json|jou...
[codex] Command completed: /bin/bash -lc "rg -n '14.?days|14 days|minimum|minimum_days|data on|coverage|/export/json|jou... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-14-wearables-15-symptom-journal.md | sed -n '12,66p;...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-14-wearables-15-symptom-journal.md | sed -n '12,66p;... (exit 0)
[codex] Running command: /bin/bash -lc "nl -ba src/backend/core/audit.py | sed -n '30,42p;160,195p;306,336p;465,490p' ...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/core/audit.py | sed -n '30,42p;160,195p;306,336p;465,490p' ... (exit 0)
[codex] Running command: /bin/bash -lc "rg -n -C 5 'log_wearable_event|action_map|ALLOWED_ACTIONS|Listed|Viewed wearab...
[codex] Command completed: /bin/bash -lc "rg -n -C 5 'log_wearable_event|action_map|ALLOWED_ACTIONS|Listed|Viewed wearab... (exit 0)
[codex] Running command: /bin/bash -lc "rg -n -C 2 'G1|G2|G3|G4|§Copy|WEAR-D8|D8' docs/plans/2026-10-13-wearables-10-u...
[codex] Command completed: /bin/bash -lc "rg -n -C 2 'G1|G2|G3|G4|§Copy|WEAR-D8|D8' docs/plans/2026-10-13-wearables-10-u... (exit 0)
[codex] Running command: /bin/bash -lc "rg -n -C 3 'OW-W9|risk acceptance before M4|risk acceptance|M4|Visit' docs/pla...
[codex] Command completed: /bin/bash -lc "rg -n -C 3 'OW-W9|risk acceptance before M4|risk acceptance|M4|Visit' docs/pla... (exit 0)
[codex] Running command: /bin/bash -lc 'git diff --unified=2 HEAD''^ HEAD -- docs/plans/2026-10-13-wearables-09-packet...
[codex] Command completed: /bin/bash -lc 'git diff --unified=2 HEAD''^ HEAD -- docs/plans/2026-10-13-wearables-09-packet... (exit 0)
[codex] Assistant message captured: Step 2 of 3 done: the plan consistently names 14 days, but I found two concrete gaps: the jou...
[codex] Running command: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-tickets.md | sed -n '46,51p' nl -ba doc...
[codex] Command completed: /bin/bash -lc "nl -ba docs/plans/2026-10-13-wearables-tickets.md | sed -n '46,51p' nl -ba doc... (exit 0)
[codex] Starting collaboration tool: wait.
[codex] Collaboration tool wait completed.
[codex] Running command: /bin/bash -lc "nl -ba src/backend/api/profiles.py | sed -n '900,1000p' rg -n 'delete.*profile...
[codex] Command completed: /bin/bash -lc "nl -ba src/backend/api/profiles.py | sed -n '900,1000p' rg -n 'delete.*profile... (exit 0)
[codex] Assistant message captured: { "verdict": "needs-attention", "summary": "Step 3 of 3 done — no-ship: the journal’s known n...
[codex] Turn completion inferred after the main thread finished and subagent work drained.
# Codex Adversarial Review

Target: branch diff against origin/main
Verdict: needs-attention

Step 3 of 3 done — no-ship: the journal’s known name-redaction risk can pass M4 without OW-W9 resolution; preview and audit instructions also have gaps.

Findings:
- [high] M4 does not require the journal privacy decision (docs/plans/2026-10-13-wearables-00-program.md:63)
  The plan acknowledges that strict redaction can leave names in journal sentences and leaves OW-W9 open. The ticket says risk acceptance is due before M4, but these exit criteria allow M4 to pass with journal entries in the packet after preview alone. That could ship third-party disclosure of names without the separate owner decision. Require OW-W9 resolution in M4 and WEAR-09a, or keep journal entries out of the packet until resolved.
  Recommendation: Add explicit OW-W9 resolution to M4’s exit criteria.
- [medium] Packet confirmation is not bound to previewed content (docs/plans/2026-10-13-wearables-09-packet.md:85-90)
  The request carries only entry IDs and a client-set boolean. The final packet fetches journal rows by ID again, so an entry edited after preview can produce different text in the packet. A caller can also set the boolean without invoking the preview route; HC-WRB-931 explicitly permits this. Either case can include text the patient did not preview, including a name that strict redaction misses.
  Recommendation: Bind confirmation to a server-issued preview token for the selected IDs and content version, then generate from that same snapshot.
- [medium] Journal audit actions lack an event-to-action mapping (docs/plans/2026-10-14-wearables-15-symptom-journal.md:19-21)
  The amendment registers human-readable actions, but does not specify mapping `wearable.journal_*` events to those actions. The route table still uses those event strings, and the plan says unregistered actions fall back to the event type. HC-AUD-004 requires each helper’s action to be in `ALLOWED_ACTIONS`, so the planned journal cases will fail unless the helper gains a mapping that the approval text does not cover.
  Recommendation: Specify and test the four event-to-action mappings, reconcile the stale fallback instructions, and include the mapping in OW-W11’s approval scope.

Next steps:
- Add OW-W9 resolution to M4’s exit criteria.
```
