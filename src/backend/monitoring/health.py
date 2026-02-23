"""
Enhanced health and metrics endpoints.

/health - Public liveness probe (no sensitive data).
/monitoring/metrics - Auth-required full metrics dashboard.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.auth import RequireAuth
from core.config import settings
from .metrics import metrics_collector

# Public liveness probe — mounted at root (no /api/v1 prefix)
health_router = APIRouter()

# Auth-protected metrics — mounted under /api/v1
metrics_router = APIRouter()


@health_router.get("/health")
async def health_check():
    """Lightweight liveness probe — no metrics, no computation."""
    return {
        "status": "healthy",
        "mode": settings.app_mode,
        "version": "0.1.0",
    }


@metrics_router.get("/monitoring/metrics")
async def get_metrics(session: RequireAuth):
    """
    Full metrics dashboard.

    Returns detailed per-endpoint statistics.
    Requires Bearer token authentication.
    """
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics not enabled")

    summary = metrics_collector.get_summary()
    return {
        "total_requests": summary.total_requests,
        "total_errors": summary.total_errors,
        "error_rate": round(summary.error_rate, 4),
        "avg_duration_ms": round(summary.avg_duration_ms, 2),
        "p50_ms": round(summary.p50_ms, 2),
        "p95_ms": round(summary.p95_ms, 2),
        "p99_ms": round(summary.p99_ms, 2),
        "requests_per_second": round(summary.requests_per_second, 2),
        "uptime_seconds": round(summary.uptime_seconds, 1),
        "endpoints": [
            {
                "route": ep.route_template,
                "count": ep.request_count,
                "avg_ms": round(ep.avg_duration_ms, 2),
                "p95_ms": round(ep.p95_ms, 2),
                "error_rate": round(ep.error_rate, 4),
            }
            for ep in summary.endpoints
        ],
    }
