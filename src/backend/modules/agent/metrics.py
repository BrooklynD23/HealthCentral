"""Per-node timing / token tracking (Phase 5, story S5-3).

Records into the existing MetricsCollector (monitoring/metrics.py) keyed
``agent.<node>`` so p50/p95/p99 surface on ``/api/v1/monitoring/metrics``. The
release metric is p95 latency <= legacy single-shot path + 50% (AGILE_PLAN §1).
"""

from __future__ import annotations

from monitoring.metrics import metrics_collector

from .audit import AgentNode  # re-use the node literal


def record_node_timing(node: AgentNode, duration_seconds: float, tokens: int | None = None) -> None:
    """Record one node's wall-clock duration into the shared MetricsCollector.

    Keyed ``agent.<node>`` (method ``"AGENT"``, status 200 — nodes don't have
    HTTP status codes; every recorded node run is a successful execution of
    that node, not a request outcome) so ``GET /api/v1/monitoring/metrics``
    surfaces p50/p95/p99 per node alongside the regular HTTP route stats.
    ``tokens`` is accepted for future token-tracking but not yet recorded
    (MetricsCollector.record_request has no token field) — trivial overhead,
    a single dict append under a lock.
    """
    _ = tokens  # reserved for future token tracking; not yet part of RequestRecord
    metrics_collector.record_request(
        method="AGENT",
        route_template=f"agent.{node}",
        status_code=200,
        duration_seconds=duration_seconds,
    )
