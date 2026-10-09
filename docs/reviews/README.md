# Codex Review Archive

**Last Updated:** 2026-10-09

Every Codex plan review (`<ID>-rN-*`) and adversarial diff review (`<ID>-diff-codex.txt`), kept next to its prompt (`*-prompt.md`) and the author's response (`*-response.md`). Files were moved here byte-identical from `audit/2026-09-25/reviews/`, `audit/2026-09-25/swarm-2026-09-27/reviews/` and `audit/2026-09-29/reviews/` on 2026-10-09.

- `2026-09-25/` — DDI, SAFE-CHAT, SAFE-INTERP (Wave 3 PR reviews).
- `2026-09-27-swarm/` — the 2026-09-27 plan set; also holds `GLOBAL-rules.md`, `POSTPASS-baseline.md`, `*-prior-rN.md` and `reviewer-log.tsv`.
- `2026-09-29/` — P01 and S02.

New reviews go in `docs/reviews/<date>/<ID>-r<N>-{prompt.md,codex.txt,response.md}`; add a row here. Process: [../agentic/orchestration.md](../agentic/orchestration.md).

Verdict is the reviewer's last `VERDICT:` line (plan reviews: PASS / REVISE; diff reviews: approve / needs-attention). Date is the commit date the output was first added.

| Folder | Plan | Round | Verdict | Date | Files |
|---|---|---|---|---|---|
| 2026-09-25 | DDI | diff | needs-attention | 2026-10-04 | [codex](2026-09-25/DDI-diff-codex.txt)  |
| 2026-09-25 | DDI | r1 | REVISE | 2026-10-04 | [codex](2026-09-25/DDI-r1-codex.txt) [prompt](2026-09-25/DDI-r1-prompt.md) [response](2026-09-25/DDI-r1-response.md) |
| 2026-09-25 | DDI | r2 | REVISE | 2026-10-04 | [codex](2026-09-25/DDI-r2-codex.txt) [prompt](2026-09-25/DDI-r2-prompt.md) [response](2026-09-25/DDI-r2-response.md) |
| 2026-09-25 | SAFECHAT | diff | needs-attention | 2026-10-04 | [codex](2026-09-25/SAFECHAT-diff-codex.txt)  |
| 2026-09-25 | SAFECHAT | r1 | REVISE | 2026-10-04 | [codex](2026-09-25/SAFECHAT-r1-codex.txt) [prompt](2026-09-25/SAFECHAT-r1-prompt.md) [response](2026-09-25/SAFECHAT-r1-response.md) |
| 2026-09-25 | SAFEINTERP | diff | needs-attention | 2026-10-04 | [codex](2026-09-25/SAFEINTERP-diff-codex.txt)  |
| 2026-09-25 | SAFEINTERP | r1 | REVISE | 2026-10-04 | [codex](2026-09-25/SAFEINTERP-r1-codex.txt) [prompt](2026-09-25/SAFEINTERP-r1-prompt.md) [response](2026-09-25/SAFEINTERP-r1-response.md) |
| 2026-09-25 | SAFEINTERP | r2 | REVISE | 2026-10-04 | [codex](2026-09-25/SAFEINTERP-r2-codex.txt) [prompt](2026-09-25/SAFEINTERP-r2-prompt.md) [response](2026-09-25/SAFEINTERP-r2-response.md) |
| 2026-09-27-swarm | P04 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P04-r1-codex.txt) [prompt](2026-09-27-swarm/P04-r1-prompt.md) [response](2026-09-27-swarm/P04-r1-response.md) |
| 2026-09-27-swarm | P04 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P04-r2-codex.txt) [prompt](2026-09-27-swarm/P04-r2-prompt.md) [response](2026-09-27-swarm/P04-r2-response.md) |
| 2026-09-27-swarm | P04 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P04-r3-codex.txt) [prompt](2026-09-27-swarm/P04-r3-prompt.md) [response](2026-09-27-swarm/P04-r3-response.md) |
| 2026-09-27-swarm | P04 | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P04-r4-codex.txt) [prompt](2026-09-27-swarm/P04-r4-prompt.md) [response](2026-09-27-swarm/P04-r4-response.md) |
| 2026-09-27-swarm | P08 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P08-r1-codex.txt) [prompt](2026-09-27-swarm/P08-r1-prompt.md) [response](2026-09-27-swarm/P08-r1-response.md) |
| 2026-09-27-swarm | P08 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P08-r2-codex.txt) [prompt](2026-09-27-swarm/P08-r2-prompt.md) [response](2026-09-27-swarm/P08-r2-response.md) |
| 2026-09-27-swarm | P08 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P08-r3-codex.txt) [prompt](2026-09-27-swarm/P08-r3-prompt.md) [response](2026-09-27-swarm/P08-r3-response.md) |
| 2026-09-27-swarm | P08 | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/P08-r4-codex.txt) [prompt](2026-09-27-swarm/P08-r4-prompt.md) [response](2026-09-27-swarm/P08-r4-response.md) |
| 2026-09-27-swarm | RTN | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/RTN-r1-codex.txt) [prompt](2026-09-27-swarm/RTN-r1-prompt.md) [response](2026-09-27-swarm/RTN-r1-response.md) |
| 2026-09-27-swarm | S01 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/S01-r1-codex.txt) [prompt](2026-09-27-swarm/S01-r1-prompt.md) [response](2026-09-27-swarm/S01-r1-response.md) |
| 2026-09-27-swarm | S01 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/S01-r2-codex.txt) [prompt](2026-09-27-swarm/S01-r2-prompt.md) [response](2026-09-27-swarm/S01-r2-response.md) |
| 2026-09-27-swarm | S01 | r3 | PASS | 2026-09-28 | [codex](2026-09-27-swarm/S01-r3-codex.txt) [prompt](2026-09-27-swarm/S01-r3-prompt.md) [response](2026-09-27-swarm/S01-r3-response.md) |
| 2026-09-27-swarm | W01 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W01-r1-codex.txt) [prompt](2026-09-27-swarm/W01-r1-prompt.md) [response](2026-09-27-swarm/W01-r1-response.md) |
| 2026-09-27-swarm | W01 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W01-r2-codex.txt) [prompt](2026-09-27-swarm/W01-r2-prompt.md) [response](2026-09-27-swarm/W01-r2-response.md) |
| 2026-09-27-swarm | W01 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W01-r3-codex.txt) [prompt](2026-09-27-swarm/W01-r3-prompt.md) [response](2026-09-27-swarm/W01-r3-response.md) |
| 2026-09-27-swarm | W01 | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W01-r4-codex.txt) [prompt](2026-09-27-swarm/W01-r4-prompt.md) [response](2026-09-27-swarm/W01-r4-response.md) |
| 2026-09-27-swarm | W02 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W02-r1-codex.txt) [prompt](2026-09-27-swarm/W02-r1-prompt.md) [response](2026-09-27-swarm/W02-r1-response.md) |
| 2026-09-27-swarm | W02 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W02-r2-codex.txt) [prompt](2026-09-27-swarm/W02-r2-prompt.md) [response](2026-09-27-swarm/W02-r2-response.md) |
| 2026-09-27-swarm | W02 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W02-r3-codex.txt) [prompt](2026-09-27-swarm/W02-r3-prompt.md) [response](2026-09-27-swarm/W02-r3-response.md) |
| 2026-09-27-swarm | W02 | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W02-r4-codex.txt) [prompt](2026-09-27-swarm/W02-r4-prompt.md) [response](2026-09-27-swarm/W02-r4-response.md) |
| 2026-09-27-swarm | W03 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W03-r1-codex.txt) [prompt](2026-09-27-swarm/W03-r1-prompt.md) [response](2026-09-27-swarm/W03-r1-response.md) |
| 2026-09-27-swarm | W03 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W03-r2-codex.txt) [prompt](2026-09-27-swarm/W03-r2-prompt.md) [response](2026-09-27-swarm/W03-r2-response.md) |
| 2026-09-27-swarm | W03 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W03-r3-codex.txt) [prompt](2026-09-27-swarm/W03-r3-prompt.md) [response](2026-09-27-swarm/W03-r3-response.md) |
| 2026-09-27-swarm | W03 | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W03-r4-codex.txt) [prompt](2026-09-27-swarm/W03-r4-prompt.md) [response](2026-09-27-swarm/W03-r4-response.md) |
| 2026-09-27-swarm | W04 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W04-r1-codex.txt) [prompt](2026-09-27-swarm/W04-r1-prompt.md) [response](2026-09-27-swarm/W04-r1-response.md) |
| 2026-09-27-swarm | W04 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W04-r2-codex.txt) [prompt](2026-09-27-swarm/W04-r2-prompt.md) [response](2026-09-27-swarm/W04-r2-response.md) |
| 2026-09-27-swarm | W04 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W04-r3-codex.txt) [prompt](2026-09-27-swarm/W04-r3-prompt.md) [response](2026-09-27-swarm/W04-r3-response.md) |
| 2026-09-27-swarm | W04 | r4 | PASS | 2026-09-28 | [codex](2026-09-27-swarm/W04-r4-codex.txt) [prompt](2026-09-27-swarm/W04-r4-prompt.md) |
| 2026-09-27-swarm | W05 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W05-r1-codex.txt) [prompt](2026-09-27-swarm/W05-r1-prompt.md) [response](2026-09-27-swarm/W05-r1-response.md) |
| 2026-09-27-swarm | W05 | r2 | PASS | 2026-09-28 | [codex](2026-09-27-swarm/W05-r2-codex.txt) [prompt](2026-09-27-swarm/W05-r2-prompt.md) |
| 2026-09-27-swarm | W06 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W06-r1-codex.txt) [prompt](2026-09-27-swarm/W06-r1-prompt.md) [response](2026-09-27-swarm/W06-r1-response.md) |
| 2026-09-27-swarm | W06 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W06-r2-codex.txt) [prompt](2026-09-27-swarm/W06-r2-prompt.md) [response](2026-09-27-swarm/W06-r2-response.md) |
| 2026-09-27-swarm | W06 | r3 | PASS | 2026-09-28 | [codex](2026-09-27-swarm/W06-r3-codex.txt) [prompt](2026-09-27-swarm/W06-r3-prompt.md) |
| 2026-09-27-swarm | W07 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W07-r1-codex.txt) [prompt](2026-09-27-swarm/W07-r1-prompt.md) [response](2026-09-27-swarm/W07-r1-response.md) |
| 2026-09-27-swarm | W07 | r2 | PASS | 2026-09-28 | [codex](2026-09-27-swarm/W07-r2-codex.txt) [prompt](2026-09-27-swarm/W07-r2-prompt.md) |
| 2026-09-27-swarm | W08 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W08-r1-codex.txt) [prompt](2026-09-27-swarm/W08-r1-prompt.md) [response](2026-09-27-swarm/W08-r1-response.md) |
| 2026-09-27-swarm | W08 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W08-r2-codex.txt) [prompt](2026-09-27-swarm/W08-r2-prompt.md) [response](2026-09-27-swarm/W08-r2-response.md) |
| 2026-09-27-swarm | W08 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W08-r3-codex.txt) [prompt](2026-09-27-swarm/W08-r3-prompt.md) [response](2026-09-27-swarm/W08-r3-response.md) |
| 2026-09-27-swarm | W08 | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W08-r4-codex.txt) [prompt](2026-09-27-swarm/W08-r4-prompt.md) [response](2026-09-27-swarm/W08-r4-response.md) |
| 2026-09-27-swarm | W10 | diff | approve | 2026-10-08 | [codex](2026-09-27-swarm/W10-diff-codex.txt)  |
| 2026-09-27-swarm | W10 | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W10-r1-codex.txt) [prompt](2026-09-27-swarm/W10-r1-prompt.md) [response](2026-09-27-swarm/W10-r1-response.md) |
| 2026-09-27-swarm | W10 | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W10-r2-codex.txt) [prompt](2026-09-27-swarm/W10-r2-prompt.md) [response](2026-09-27-swarm/W10-r2-response.md) |
| 2026-09-27-swarm | W10 | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W10-r3-codex.txt) [prompt](2026-09-27-swarm/W10-r3-prompt.md) [response](2026-09-27-swarm/W10-r3-response.md) |
| 2026-09-27-swarm | W10 | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W10-r4-codex.txt) [prompt](2026-09-27-swarm/W10-r4-prompt.md) [response](2026-09-27-swarm/W10-r4-response.md) |
| 2026-09-27-swarm | W10 | r5 | REVISE | 2026-10-08 | [codex](2026-09-27-swarm/W10-r5-codex.txt) [prompt](2026-09-27-swarm/W10-r5-prompt.md) [response](2026-09-27-swarm/W10-r5-response.md) |
| 2026-09-27-swarm | W10 | r6 | REVISE | 2026-10-08 | [codex](2026-09-27-swarm/W10-r6-codex.txt) [prompt](2026-09-27-swarm/W10-r6-prompt.md) [response](2026-09-27-swarm/W10-r6-response.md) |
| 2026-09-27-swarm | W11a | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11a-r1-codex.txt) [prompt](2026-09-27-swarm/W11a-r1-prompt.md) [response](2026-09-27-swarm/W11a-r1-response.md) |
| 2026-09-27-swarm | W11a | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11a-r2-codex.txt) [prompt](2026-09-27-swarm/W11a-r2-prompt.md) [response](2026-09-27-swarm/W11a-r2-response.md) |
| 2026-09-27-swarm | W11a | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11a-r3-codex.txt) [prompt](2026-09-27-swarm/W11a-r3-prompt.md) [response](2026-09-27-swarm/W11a-r3-response.md) |
| 2026-09-27-swarm | W11a | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11a-r4-codex.txt) [prompt](2026-09-27-swarm/W11a-r4-prompt.md) [response](2026-09-27-swarm/W11a-r4-response.md) |
| 2026-09-27-swarm | W11b | r1 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11b-r1-codex.txt) [prompt](2026-09-27-swarm/W11b-r1-prompt.md) [response](2026-09-27-swarm/W11b-r1-response.md) |
| 2026-09-27-swarm | W11b | r2 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11b-r2-codex.txt) [prompt](2026-09-27-swarm/W11b-r2-prompt.md) [response](2026-09-27-swarm/W11b-r2-response.md) |
| 2026-09-27-swarm | W11b | r3 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11b-r3-codex.txt) [prompt](2026-09-27-swarm/W11b-r3-prompt.md) [response](2026-09-27-swarm/W11b-r3-response.md) |
| 2026-09-27-swarm | W11b | r4 | REVISE | 2026-09-28 | [codex](2026-09-27-swarm/W11b-r4-codex.txt) [prompt](2026-09-27-swarm/W11b-r4-prompt.md) [response](2026-09-27-swarm/W11b-r4-response.md) |
| 2026-09-29 | P01 | r1 | REVISE | 2026-09-29 | [codex](2026-09-29/P01-r1-codex.txt) [prompt](2026-09-29/P01-r1-prompt.md) [response](2026-09-29/P01-r1-response.md) |
| 2026-09-29 | S02 | r1 | REVISE | 2026-09-29 | [codex](2026-09-29/S02-r1-codex.txt) [prompt](2026-09-29/S02-r1-prompt.md) [response](2026-09-29/S02-r1-response.md) |
