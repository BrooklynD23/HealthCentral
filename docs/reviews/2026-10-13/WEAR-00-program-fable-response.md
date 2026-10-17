# WEAR-00 program plan — response to the Fable review (round 1)

**Review:** [WEAR-00-program-fable.md](WEAR-00-program-fable.md) — GO WITH AMENDMENTS, 5 MAJOR, 7 MINOR.
**Responder:** Wearables Planning Sub-Orchestrator (Opus 5.5), 2026-10-13. Evidence re-read at `8234990` before each disposition (`api/profiles.py:939-942` and `:498-515`, `core/profile_database.py:405-418`, `core/audit.py:36`, `fastapi/routing.py:430,481` in `~/venvs/asclexis-311`, `security/input_validator.py:18-21,38,41,70-71`).

| # | Finding | Sev | Disposition | Program change |
|---|---|---|---|---|
| F1 | One shared import limit; flag-off upload still spooled | MAJOR | **ACCEPTED.** D4 (a) is now a per-prefix limit map, wearables entry active only when the flag is on; flag-off uploads stay under the 10 MB default before the 404. | §3 Off bullet, D4, §7 gate |
| F2 | FK cascade not enforced; no package owns delete | MAJOR | **ACCEPTED.** Explicit child delete; delete route moved into WEAR-07. | A2, WEAR-07 row |
| F3 | Reset tuple and `create_all` import list missing | MAJOR | **ACCEPTED.** Owned by WEAR-02 with a reset test. | A12, M1 |
| F4 | OS temp spool is unencrypted and survives a crash | MAJOR | **ACCEPTED.** New owner decision D6 (default: app-owned temp path + `finally` delete + startup sweep). The old D6 (OM-4/OM-5) moves to "carried open" and OW-W6. | A10, R6, D6, §10 |
| F5 | `route_client` cannot see mount, middleware cap, real prefix | MAJOR | **ACCEPTED.** A13: `TestClient(main.app)` checks at each milestone. | A13, M1, M2 |
| F6 | `core/audit.py` edited by many packages; keys silently scrubbed | MINOR | **ACCEPTED.** WEAR-02 reserves all actions/keys once; security-reviewer on every audit diff. | A12, §7 |
| F7 | 08 needs 10; shared frontend files; 09/13 share `api/export.py` | MINOR | **ACCEPTED.** | §6 table, wave map |
| F8 | Router-level dependency also gates `/status` | MINOR | **ACCEPTED.** Two routers on one prefix. | §3 |
| F9 | Zip caps must count bytes read, not headers | MINOR | **ACCEPTED.** | A9 |
| F10 | Ambiguous path for `implementation-program.md` | MINOR | **ACCEPTED.** Full paths in A11. | A11 |
| F11 | No package owns docs | MINOR | **ACCEPTED.** New WEAR-14. | §6 table, wave WD |
| F12 | Hash pass must stream then `seek(0)` | MINOR | **ACCEPTED.** | A5b |

12 of 12 accepted. No re-run: the next review of this file is the Codex review of the plan set.
