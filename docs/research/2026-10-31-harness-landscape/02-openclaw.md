# OpenClaw: self-authored skills, loop detection and the skill-market incidents

**Last Updated:** 2026-10-31
**Owner:** repository owner
**Refresh Trigger:** an OpenClaw release that changes Skill Workshop modes, approval binding or loop detection; a new skill-supply-chain incident report; an owner answer in [the harness improvements plan](../../plans/2026-10-31-harness-improvements-plan.md#drafted-owner-questions-not-asked).

> **Point-in-time research (2026-10-31).** Docs only. Haiku notes re-checked by the Opus planner against the primary pages on 2026-10-31; WebFetch returns a summary, so quotes are as summarised. Markers: **[V]** confirmed; **[C]** changed after the re-check; **[X]** not confirmed, dropped. Summary: [00-README.md](00-README.md).

## 1. Skill Workshop (self-authored skills)

From https://docs.openclaw.ai/tools/skill-workshop?full=true [V]:
- Modes: `"auto"` (default: background review, unused-skill cleanup, "skill diet"), `"propose"` (background review saves drafts for the user to review), `"off"`.
- Triggers: the agent patches a learned skill that proved wrong; saves a procedure after hard multi-step work; a background review runs after 10 accumulated model iterations; `/learn` on demand. Unused learned skills are archived after 30 days.
- A version is saved before every change; the newest 10 per skill are kept; undo is itself undoable; the change feed keeps 500 entries.
- Validation: name pattern, frontmatter `name` must match the directory, `SKILL.md` ≤ 40000 bytes by default, absolute paths, path traversal and symlinks refused; "a critical security-scanner finding, such as a literal secret, refuses the write".

From the 2026.8.1 release notes, https://docs.openclaw.ai/releases/2026.8.1/skills [V]:
- "New and unconfigured installations start in `auto`, while upgrades keep their existing choice."
- "Critical prompt-injection findings block application."
- "Every decision stays bound to the exact proposal revision you reviewed, so a later revision returns for review." **[C]**: the note attributed approval binding to the Skill Workshop doc; it is in the release notes only.

## 2. Loop detection

https://docs.openclaw.ai/tools/loop-detection [V]: the identical-error guard keys on "the same tool, arguments, and error result" **[C]** (the note said an arguments *hash*; the page says arguments); "After three consecutive identical tool errors" it "blocks that exact action and gives the model one recovery opportunity"; it is always on, independent of `tools.loopDetection`; the rolling no-progress detector is "disabled by default".

## 3. Logging

https://docs.openclaw.ai/logging [V]: "Log messages should contain IDs, sizes, and outcomes, never message text, prompts, tool arguments, or tool results" (in the Redaction section); "Redaction is best-effort"; transcripts "can contain credentials and other private data returned by tools or supplied in conversation". This is the same rule as our mod's (README `:17`), stated as guidance rather than enforced by construction.

## 4. Skill-market incidents (why scanners are not the boundary)

- **CVE-2026-25253**, CVSS 3.1 8.8: the Control UI took `gatewayUrl` from the query string, auto-connected and sent the stored gateway token, with no WebSocket origin check; fixed in 2026.1.29 [V] (https://osv.dev/vulnerability/CVE-2026-25253, https://thehackernews.com/2026/02/openclaw-bug-enables-one-click-remote.html; read via search summary).
- **VirusTotal partnership**, 7 Feb 2026: SHA-256 of the bundle checked against VirusTotal, Code Insight (LLM) review, benign / suspicious / malicious, daily rescan; "this is not a silver bullet" and "A clean scan doesn't mean a skill is safe" [V] **[C]** (the note's "won't catch everything" is a paraphrase) (https://www.openclaw.ai/blog/virustotal-partnership).
- **Snyk ToxicSkills**, 5 Feb 2026: 3,984 skills from ClawHub and skills.sh scanned, 76 confirmed malicious by human review, "91% of malicious skills combine prompt injection with traditional malware" [V] (https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/).
- **Trail of Bits**, 3 Jun 2026: bypassed ClawHub's VirusTotal and guard-model check by padding (100,000 newlines; the scanner truncated), and skills.sh's scanners and Cisco's skill-scanner by `.docx` indirection, `.pyc` poisoning and policy-framed prompt injection; "No amount of scanning or LLM analysis can reliably detect malicious content in agent skills" [V] (https://blog.trailofbits.com/2026/06/03/the-sorry-state-of-skill-distribution/).
- **Trojan's Whisper** (Liu et al., arXiv 2603.19974, 20 Mar 2026): "94% of our malicious skills evade detection by existing static and LLM-based scanners"; attack success "from 16.0% to 64.2%" across six backends [V] (https://arxiv.org/abs/2603.19974).
- **ClawHavoc counts [X]**: the Koi URL now redirects to a vendor product page, and the Antiy figure was not re-read. Not used.

## 5. What transfers to Asclexis

| Idea | Verdict | Where |
|---|---|---|
| Approval bound to the exact reviewed revision | **Already ours**: the owner merges a specific PR head on GitHub (RSI-4). A separate hash binding is rejected on merit | Plan, rejected ideas |
| Identical-error breaker | **Reject on our data**: 0 `retry: true` rows among the 14,270 tool rows of the archived rsi-logs, 1 retry in each of the two mined windows (8210 and 7499 calls) | Plan, rejected ideas |
| Log IDs, sizes and outcomes only | **Already ours**, enforced by construction (fixed literals, mod README `:17`) | — |
| Scanners and LLM critics are not the security boundary | **Keep**: a deterministic lint on rule messages so the injection check holds when the Codex critic is unavailable (today an unavailable critic admits the candidate, `rsi-loop.js:334`, `:341`) | Plan row RSI-REPLAY-STRICT |
| A skill is a persistence channel | **Keep, as above**: a hint `message` is appended to what the model reads (`register.ts:91`), so it is our persistence channel | Plan row RSI-REPLAY-STRICT |
| Auto mode for new installs | **Reject**: RSI-4 human gate | Plan, rejected ideas |
| Pin and rescan external skills | **Reject for this repo**: no marketplace skills are installed by the repo; vendored skills are in git, and CI pins the CLI (`ci.yml:332`) | Plan, rejected ideas |
