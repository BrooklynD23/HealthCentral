"""
Enhanced health and metrics endpoints.

/health - Public health check with optional metrics summary.
/monitoring/metrics - Auth-required full metrics dashboard.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core.config import settings
from .metrics import metrics_collector

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint with optional metrics summary."""
    response = {
        "status": "healthy",
        "mode": settings.app_mode,
        "version": "0.1.0",
    }
    if settings.metrics_enabled:
        summary = metrics_collector.get_summary()
        response["metrics"] = {
            "total_requests": summary.total_requests,
            "error_rate": round(summary.error_rate, 4),
            "p50_ms": round(summary.p50_ms, 2),
            "p95_ms": round(summary.p95_ms, 2),
            "uptime_seconds": round(summary.uptime_seconds, 1),
        }
    return response


@router.get("/monitoring/metrics")
async def get_metrics():
    """
    Full metrics dashboard.

    Returns detailed per-endpoint statistics.
    Should be auth-protected in production.
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
