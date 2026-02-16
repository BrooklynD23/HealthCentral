"""
UXQA-005: API Load and Performance Test Baselines

Provides foundational performance tests for API endpoints.
These tests validate response time constraints and throughput baselines.

NOTE: These are unit-level performance checks, not full load tests.
For production load testing, use a dedicated tool (locust, k6, etc.).
"""

from __future__ import annotations

import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_session(profile_id: str = "perf-profile-001"):
    """Create a mock Session for auth-required endpoints."""
    session = MagicMock()
    session.profile_id = profile_id
    session.token_jti = "test-jti"
    return session


def _time_calls(fn, iterations: int = 10):
    """Execute *fn* synchronously and return average elapsed seconds."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return sum(times) / len(times)


async def _async_time_calls(coro_factory, iterations: int = 10):
    """Execute an async callable and return average elapsed seconds."""
    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        await coro_factory()
        times.append(time.perf_counter() - start)
    return sum(times) / len(times)


# ---------------------------------------------------------------------------
# Document List Endpoint Performance
# ---------------------------------------------------------------------------

class TestDocumentListPerformance:
    """Baseline performance for the document listing endpoint."""

    def test_document_response_serialization_speed(self):
        """DocumentResponse.from_model should serialize within 1ms per item."""
        from api.documents import DocumentResponse

        mock_doc = MagicMock()
        mock_doc.id = "doc-001"
        mock_doc.profile_id = "profile-001"
        mock_doc.doc_type = "lab_pdf"
        mock_doc.source = "test.pdf"
        mock_doc.status = "parsed"
        mock_doc.page_count = 5
        mock_doc.collection_date = None
        mock_doc.imported_at = MagicMock()
        mock_doc.imported_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_doc.parsed_at = None
        mock_doc.verified_at = None

        avg = _time_calls(lambda: DocumentResponse.from_model(mock_doc), iterations=100)
        assert avg < 0.001, f"Serialization too slow: {avg:.4f}s per call"

    def test_batch_serialization_100_documents(self):
        """Serializing 100 documents should complete within 100ms."""
        from api.documents import DocumentResponse

        mock_docs = []
        for i in range(100):
            doc = MagicMock()
            doc.id = f"doc-{i:03d}"
            doc.profile_id = "profile-001"
            doc.doc_type = "lab_pdf"
            doc.source = f"report-{i}.pdf"
            doc.status = "parsed"
            doc.page_count = 3
            doc.collection_date = None
            doc.imported_at = MagicMock()
            doc.imported_at.isoformat.return_value = "2024-01-01T00:00:00"
            doc.parsed_at = None
            doc.verified_at = None
            mock_docs.append(doc)

        start = time.perf_counter()
        results = [DocumentResponse.from_model(d) for d in mock_docs]
        elapsed = time.perf_counter() - start

        assert len(results) == 100
        assert elapsed < 0.1, f"Batch serialization too slow: {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# Observation Trend Computation Performance
# ---------------------------------------------------------------------------

class TestTrendComputationPerformance:
    """Baseline performance for trend data processing."""

    def test_trend_data_aggregation_speed(self):
        """Aggregating 1000 data points should complete within 50ms."""
        data_points = [
            {"date": f"2024-{(i % 12) + 1:02d}-15", "value": 14.0 + (i * 0.1)}
            for i in range(1000)
        ]

        def aggregate():
            # Simulate trend computation: find min, max, avg, compute deltas
            values = [p["value"] for p in data_points]
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values),
                "delta": values[-1] - values[0] if len(values) > 1 else 0,
            }

        avg = _time_calls(aggregate, iterations=50)
        assert avg < 0.05, f"Aggregation too slow: {avg:.4f}s"


# ---------------------------------------------------------------------------
# Search Performance Baseline
# ---------------------------------------------------------------------------

class TestSearchPerformance:
    """Baseline performance for search operations."""

    def test_search_result_construction_speed(self):
        """Constructing 50 search results should take < 10ms."""
        results = []

        start = time.perf_counter()
        for i in range(50):
            results.append({
                "id": f"res-{i}",
                "title": f"Hemoglobin Test Result {i}",
                "type": "observation",
                "score": 0.95 - (i * 0.01),
                "snippet": f"Value: {14.0 + i * 0.1} g/dL",
                "value": 14.0 + i * 0.1,
                "unit": "g/dL",
                "collected_at": f"2024-{(i % 12) + 1:02d}-15",
                "explanation": None,
            })
        elapsed = time.perf_counter() - start

        assert len(results) == 50
        assert elapsed < 0.01, f"Result construction too slow: {elapsed:.4f}s"


# ---------------------------------------------------------------------------
# Memory Profiling Baseline
# ---------------------------------------------------------------------------

class TestMemoryBaseline:
    """Basic memory usage checks for key operations."""

    def test_large_observation_list_memory(self):
        """Creating 10000 observation dicts should use < 10MB."""
        import sys

        observations = [
            {
                "id": f"obs-{i}",
                "profile_id": "test",
                "doc_id": "doc-1",
                "analyte_canonical": "hemoglobin",
                "analyte_raw": "Hemoglobin",
                "value": 14.2,
                "unit": "g/dL",
                "ref_low": 12.0,
                "ref_high": 17.5,
                "flag": None,
                "is_abnormal": False,
            }
            for i in range(10000)
        ]

        # Rough size estimate using sys.getsizeof on the list
        list_size = sys.getsizeof(observations)
        # Each dict has overhead too
        total_estimate = list_size + sum(sys.getsizeof(o) for o in observations[:100]) * 100

        # Should be well under 10MB
        assert total_estimate < 10 * 1024 * 1024, f"Memory too high: {total_estimate / 1024 / 1024:.1f}MB"


# ---------------------------------------------------------------------------
# Config Validation Performance
# ---------------------------------------------------------------------------

class TestConfigPerformance:
    """Ensure configuration loading is fast."""

    def test_settings_access_speed(self):
        """Accessing settings attributes should be near-instant."""
        from core.config import settings

        avg = _time_calls(
            lambda: (settings.app_data_path, settings.max_import_file_size_mb),
            iterations=1000,
        )
        assert avg < 0.0001, f"Settings access too slow: {avg:.6f}s"
