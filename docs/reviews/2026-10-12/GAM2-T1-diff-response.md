# GAM2-T1 diff — author response to code review

Reviewer: code-reviewer subagent (Opus 5.5), verdict approve. Review: [GAM2-T1-diff-codereview.md](GAM2-T1-diff-codereview.md).

| Finding | Action |
|---|---|
| M1 client-supplied aware `ended_at` / `taken_at` stored without UTC normalisation | Not fixed here: predates this diff, lives in `api/medications.py`. Follow-up ticket. |
| L1 `<=` boundary not pinned | Fixed: `test_hc_gam_http_009_dose_at_ended_at_counts`. Break-check: with `<` it fails (1 failed). |
| L2 `http_006` asserts the exception, not a 500 | Not done: `route_client` has no `raise_server_exceptions` switch; the propagated error proves nothing is served. |
| L3 audit row shape not pinned | Fixed: `http_005` asserts `action == event_type`, `entity_id is None`, `details_json is None`. |
| L4 redundant local imports in the pre-existing naive-UTC test | Left: surgical-edit rule, test predates this diff. |

Found after review by the full suite: `test_hc_aud_ord_030_every_committing_handler_is_classified` failed because both routes now reach a commit. Classified both as `excluded: read route, audit_and_commit only` in `tests/test_audit_order_guard.py`, same as every other audited read route. Collected count re-measured after these changes: 1477.
