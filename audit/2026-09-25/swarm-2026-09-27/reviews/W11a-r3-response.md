R3 (codex) dispositions — fixed after round 3 (owner asked about round 4):
1. [MAJOR] HC-PGUARD-003 builds its own FastAPI/TestClient instead of route_client -> ACCEPTED: after P7 lands, extend tests/support/routes.py::route_client with an opt-in real-auth mode (W-11a runs after P7, which owns that file first) and use it; if the extension is not feasible, STOP and report rather than bypass.
2. [MAJOR] audit/repository-audit-dashboard.html:255 still says "155 vitest, 25 Playwright" -> ACCEPTED: add to the inventory; update with measured counts or mark as a dated historical snapshot.
Add "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."
