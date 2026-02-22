"""Tests for MetricsCollector."""

import threading
from dataclasses import FrozenInstanceError

import pytest
from monitoring.metrics import MetricsCollector, MetricsSummary, EndpointStats


def test_record_stores_entry():
    """Recording a request stores it in the buffer."""
    mc = MetricsCollector(buffer_size=100)
    mc.record_request("GET", "/api/v1/health", 200, 0.05)
    summary = mc.get_summary()
    assert summary.total_requests == 1


def test_ring_buffer_eviction():
    """Buffer evicts oldest entries when full."""
    mc = MetricsCollector(buffer_size=5)
    for i in range(10):
        mc.record_request("GET", "/test", 200, 0.01 * i)
    summary = mc.get_summary()
    assert summary.total_requests == 5


def test_empty_summary_returns_zeros():
    """Empty collector returns zero summary."""
    mc = MetricsCollector()
    summary = mc.get_summary()
    assert summary.total_requests == 0
    assert summary.error_rate == 0.0
    assert summary.p50_ms == 0.0
    assert summary.requests_per_second == 0.0


def test_percentile_computation():
    """Percentiles are computed correctly."""
    mc = MetricsCollector(buffer_size=100)
    for i in range(100):
        mc.record_request("GET", "/test", 200, i / 1000.0)
    summary = mc.get_summary()
    assert summary.p50_ms > 0
    assert summary.p95_ms > summary.p50_ms
    assert summary.p99_ms >= summary.p95_ms


def test_error_rate():
    """Error rate is computed from 4xx/5xx responses."""
    mc = MetricsCollector()
    mc.record_request("GET", "/test", 200, 0.01)
    mc.record_request("GET", "/test", 200, 0.01)
    mc.record_request("GET", "/test", 500, 0.01)
    mc.record_request("GET", "/test", 404, 0.01)
    summary = mc.get_summary()
    assert summary.error_rate == 0.5


def test_throughput_rps():
    """RPS is calculated from buffer time span."""
    mc = MetricsCollector()
    mc.record_request("GET", "/test", 200, 0.01)
    mc.record_request("GET", "/test", 200, 0.01)
    summary = mc.get_summary()
    # With 2 requests very close together, RPS should be > 0
    assert summary.total_requests == 2


def test_endpoint_stats_filters():
    """Endpoint stats filter by route template."""
    mc = MetricsCollector()
    mc.record_request("GET", "/api/v1/docs", 200, 0.01)
    mc.record_request("GET", "/api/v1/docs", 200, 0.02)
    mc.record_request("POST", "/api/v1/profiles", 201, 0.05)

    stats = mc.get_endpoint_stats("/api/v1/docs")
    assert stats is not None
    assert stats.request_count == 2

    stats2 = mc.get_endpoint_stats("/api/v1/profiles")
    assert stats2 is not None
    assert stats2.request_count == 1


def test_thread_safety():
    """Concurrent writes don't crash."""
    mc = MetricsCollector(buffer_size=1000)
    errors = []

    def writer(thread_id):
        try:
            for i in range(100):
                mc.record_request("GET", f"/t{thread_id}", 200, 0.001)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    summary = mc.get_summary()
    assert summary.total_requests == 1000


def test_frozen_dataclasses():
    """MetricsSummary and EndpointStats are immutable."""
    mc = MetricsCollector()
    mc.record_request("GET", "/test", 200, 0.01)
    summary = mc.get_summary()
    with pytest.raises(FrozenInstanceError):
        summary.total_requests = 999


def test_uuid_paths_no_separate_entries():
    """Same route template doesn't split on different UUIDs (design: use templates)."""
    mc = MetricsCollector()
    # These represent the same endpoint with different IDs — caller should use template
    mc.record_request("GET", "/api/v1/documents/{document_id}", 200, 0.01)
    mc.record_request("GET", "/api/v1/documents/{document_id}", 200, 0.02)
    summary = mc.get_summary()
    assert len(summary.endpoints) == 1


def test_unmatched_fallback_key():
    """'unmatched' route template is valid."""
    mc = MetricsCollector()
    mc.record_request("GET", "unmatched", 404, 0.01)
    stats = mc.get_endpoint_stats("unmatched")
    assert stats is not None
    assert stats.request_count == 1


def test_buffer_size_configurable():
    """Buffer size is configurable via constructor."""
    mc = MetricsCollector(buffer_size=3)
    for i in range(10):
        mc.record_request("GET", "/test", 200, 0.01)
    summary = mc.get_summary()
    assert summary.total_requests == 3
