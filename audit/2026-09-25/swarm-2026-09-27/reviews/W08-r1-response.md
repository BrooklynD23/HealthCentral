R1 (codex) findings and orchestrator dispositions:
1. [MAJOR] interpret-grounded 501 not tested over HTTP -> ACCEPTED. Fix: route_client test for POST /interpretations/observations/{id}/interpret-grounded asserting 501 and the fixed detail (no file path), plus break-it on the route mapping. Keep Q-FC owner gate on the wording.
Also apply repo-wide executability rules: absolute WT path, no relative cd after cd, pipefail/PIPESTATUS for piped exit codes, count updates in the same commit that changes collection.
