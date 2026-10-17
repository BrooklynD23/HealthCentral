# WEAR-PLANS r3 — response to the Codex review of the owner-answer amendments

**Review:** [WEAR-PLANS-r3-codex.md](WEAR-PLANS-r3-codex.md) — native: 1 P1, 1 P2; adversarial: **needs-attention**, 1 high, 2 medium. The adversarial run found no misquoted owner answer, no migration-ordering defect and no FIT-dependency defect, and confirmed the 14-day threshold is applied consistently.
**Responder:** Wearables Planning Sub-Orchestrator (Opus 5.5), 2026-10-14. This is round 1 for this amendment (owner answers); fixes applied after it are not re-reviewed.

| # | Finding | Sev | Disposition | Change |
|---|---|---|---|---|
| N1 | `docs/INDEX.md` and `_link_graph.json` stale (`generate_docs_index.py --check` exits 1) | P1 | **ACCEPTED.** Regenerated after the final edits; `--check` run before push. | `docs/INDEX.md`, `docs/_link_graph.json` |
| N2 | WEAR-14 still says wearable data is absent from `/export/json` (D7 b) | P2 | **ACCEPTED.** Now describes WEAR-D7 (a): versioned block under `?include_wearables=true`, CSV unchanged, journal only if OW-W10. | WEAR-14 |
| ADV-1 | M4 can pass with journal entries in the packet while OW-W9 (names in free text) is open | high | **ACCEPTED.** M4 now requires OW-W9 answered by the owner before any journal entry reaches the packet; otherwise WEAR-09 ships the metrics section only. The journal part of 09a/09b is gated on OW-W9. | Program M4; WEAR-09 |
| ADV-2 | Packet confirmation is a client boolean and re-reads rows after preview | medium | **ACCEPTED.** Replaced `journal_preview_confirmed` with a server-issued `journal_preview_id`. The preview route stores a snapshot (profile, ids, redacted text, `updated_at`, 15-min expiry) in memory beside `_packet_store`; the packet renders that snapshot and returns 409 if an entry changed. HC-WRB-915 and HC-WRB-931 rewritten to test forged, foreign, mismatched, expired and stale previews. | WEAR-09 |
| ADV-3 | Journal actions registered without event→action mappings | medium | **ACCEPTED.** WEAR-15 §0 now adds the 4 mappings to `log_wearable_event`'s map; OW-W11's question covers both the action strings and the mappings. | WEAR-15 §0; program OW-W11 |

**Totals:** 5 findings, 5 accepted, 0 declined.
