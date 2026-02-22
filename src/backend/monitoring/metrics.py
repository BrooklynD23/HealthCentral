"""
Metrics collection with ring buffer for request statistics.

Thread-safe, bounded memory. Keyed by route template (not raw paths)
to avoid UUID cardinality explosion.
"""

from __future__ import annotations

import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestRecord:
    """Single request metric record."""
    method: str
    route_template: str
    status_code: int
    duration_seconds: float
    timestamp: float


@dataclass(frozen=True)
class EndpointStats:
    """Stats for a single endpoint."""
    route_template: str
    request_count: int
    avg_duration_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    error_count: int
    error_rate: float


@dataclass(frozen=True)
class MetricsSummary:
    """Aggregate metrics summary."""
    total_requests: int
    total_errors: int
    error_rate: float
    avg_duration_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    requests_per_second: float
    uptime_seconds: float
    endpoints: list[EndpointStats] = field(default_factory=list)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Compute percentile from sorted list."""
    if not sorted_values:
        return 0.0
    idx = int(len(sorted_values) * pct / 100)
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]


class MetricsCollector:
    """
    Thread-safe metrics collector with ring buffer.

    Records request metrics and computes aggregated statistics.
    Buffer is capped at `buffer_size` to prevent unbounded memory growth.
    """

    def __init__(self, buffer_size: int = 10000) -> None:
        self._buffer_size = buffer_size
        self._lock = threading.Lock()
        self._records: deque[RequestRecord] = deque(maxlen=buffer_size)
        self._start_time = time.time()

    def record_request(
        self,
        method: str,
        route_template: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record a request metric."""
        record = RequestRecord(
            method=method,
            route_template=route_template,
            status_code=status_code,
            duration_seconds=duration_seconds,
            timestamp=time.time(),
        )
        with self._lock:
            self._records.append(record)

    def get_summary(self) -> MetricsSummary:
        """Compute aggregate metrics from the buffer."""
        with self._lock:
            records = list(self._records)

        if not records:
            return MetricsSummary(
                total_requests=0,
                total_errors=0,
                error_rate=0.0,
                avg_duration_ms=0.0,
                p50_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                requests_per_second=0.0,
                uptime_seconds=time.time() - self._start_time,
            )

        durations = sorted(r.duration_seconds * 1000 for r in records)
        errors = sum(1 for r in records if r.status_code >= 400)
        total = len(records)
        uptime = time.time() - self._start_time

        # RPS from buffer time span
        if total > 1:
            time_span = records[-1].timestamp - records[0].timestamp
            rps = total / time_span if time_span > 0 else 0.0
        else:
            rps = 0.0

        # Per-endpoint stats
        routes: dict[str, list[RequestRecord]] = {}
        for r in records:
            routes.setdefault(r.route_template, []).append(r)

        endpoint_stats = []
        for template, route_records in routes.items():
            route_durations = sorted(r.duration_seconds * 1000 for r in route_records)
            route_errors = sum(1 for r in route_records if r.status_code >= 400)
            route_count = len(route_records)
            endpoint_stats.append(EndpointStats(
                route_template=template,
                request_count=route_count,
                avg_duration_ms=statistics.mean(route_durations),
                p50_ms=_percentile(route_durations, 50),
                p95_ms=_percentile(route_durations, 95),
                p99_ms=_percentile(route_durations, 99),
                error_count=route_errors,
                error_rate=route_errors / route_count if route_count > 0 else 0.0,
            ))

        return MetricsSummary(
            total_requests=total,
            total_errors=errors,
            error_rate=errors / total,
            avg_duration_ms=statistics.mean(durations),
            p50_ms=_percentile(durations, 50),
            p95_ms=_percentile(durations, 95),
            p99_ms=_percentile(durations, 99),
            requests_per_second=rps,
            uptime_seconds=uptime,
            endpoints=endpoint_stats,
        )

    def get_endpoint_stats(self, route_template: str) -> EndpointStats | None:
        """Get stats for a specific endpoint."""
        summary = self.get_summary()
        for ep in summary.endpoints:
            if ep.route_template == route_template:
                return ep
        return None


# Singleton instance
metrics_collector = MetricsCollector()
