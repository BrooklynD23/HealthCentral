"""Per-node timing / token tracking (Phase 5, story S5-3).

Records into the existing MetricsCollector (monitoring/metrics.py) keyed
``agent.<node>`` so p50/p95/p99 surface on ``/api/v1/monitoring/metrics``. The
release metric is p95 latency <= legacy single-shot path + 50% (AGILE_PLAN §1).
"""

from __future__ import annotations

from .audit import AgentNode  # re-use the node literal


def record_node_timing(node: AgentNode, duration_seconds: float, tokens: int | None = None) -> None:
    """SCAFFOLD: Sprint 5 (S5-3).

    At implementation time::

        metrics_collector.record_request(
            method="AGENT", route_template=f"agent.{node}",
            status_code=200, duration_seconds=duration_seconds,
        )
    """
    raise NotImplementedError("S5-3: surface per-node timing in monitoring dashboard")
