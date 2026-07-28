"""
HealthCentral Backend - Main Application Entry Point

Local-first medical results companion API server.
Designed for localhost operation with future scalability to web deployment.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import init_database, close_database
from core.migrations import run_master_migrations_async
from api import router as api_router
from security.input_validator import InputValidationMiddleware
from security.rate_limit_middleware import RateLimitMiddleware
from security.security_headers import SecurityHeadersMiddleware
from security.audit_middleware import SecurityAuditMiddleware
from monitoring.correlation import CorrelationIdMiddleware
from monitoring.timing_middleware import TimingMiddleware
from monitoring.health import health_router, metrics_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Validate configuration (raises RuntimeError in production if jwt_secret empty)
    startup_warnings = settings.validate_startup()
    for w in startup_warnings:
        logger.warning("Config validation: %s", w)

    # Initialize directories and verify SQLCipher
    await init_database()

    # Run master database migrations
    await run_master_migrations_async()

    # Auto-seed knowledge base (idempotent — skips rows that already exist)
    try:
        from scripts.seed_knowledge_base import seed_all
        seed_results = await seed_all(skip_db_init=True)
        if any(v > 0 for v in seed_results.values()):
            logger.info(
                "Knowledge base seeded: %s biomarkers, %s interventions, %s relationships",
                seed_results["biomarkers"],
                seed_results["interventions"],
                seed_results["relationships"],
            )
        else:
            logger.debug("Knowledge base already seeded — no new rows inserted")
    except Exception as _seed_exc:
        logger.warning("Knowledge base seeding skipped: %s", _seed_exc)

    # Scheduled backups (BKUP-UX-001). Fail-soft, like the seeding block above:
    # a scheduler that cannot start must not stop the app from booting — the
    # user can still back up manually from Settings.
    try:
        from modules.backup_scheduler import start_backup_scheduler
        await start_backup_scheduler()
    except Exception as _sched_exc:
        logger.warning("Backup scheduler not started: %s", _sched_exc)

    yield

    try:
        from modules.backup_scheduler import stop_backup_scheduler
        await stop_backup_scheduler()
    except Exception as _sched_exc:  # pragma: no cover - shutdown best effort
        logger.warning("Backup scheduler shutdown issue: %s", _sched_exc)

    await close_database()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="HealthCentral API",
        description="Local-first medical results companion - API backend",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # CORS configuration
    # Local mode: only allow localhost origins
    # Server mode: configure allowed origins via settings
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if settings.app_mode == "server":
        allowed_origins = settings.cors_origins
    
    # Middleware stack (Starlette: last added = outermost)
    # Request flow: CORS → CorrelationId → SecurityHeaders → RateLimit → InputValidation → Audit → Timing → Routes

    # 1. Timing (innermost — measures route handling time)
    app.add_middleware(TimingMiddleware)
    # 2. Security audit logging
    app.add_middleware(
        SecurityAuditMiddleware,
        log_to_db=settings.audit_security_events_to_db,
    )
    # 3. Input validation
    app.add_middleware(
        InputValidationMiddleware,
        max_request_body_bytes=settings.max_request_body_bytes,
    )
    # 4. Rate limiting (before body validation — cheap rejection)
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.api_rate_limit_max_requests,
        window_seconds=settings.api_rate_limit_window_seconds,
        enabled=settings.api_rate_limit_enabled,
        trusted_proxy_enabled=settings.trusted_proxy_enabled,
        trusted_proxy_cidrs=settings.trusted_proxy_cidrs,
    )
    # 5. Security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        enabled=settings.security_headers_enabled,
        server_mode=(settings.app_mode == "server"),
    )
    # 6. Correlation ID
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name=settings.correlation_id_header,
    )
    # 7. CORS (outermost — handles preflight before anything else)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "X-Correlation-ID"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Public liveness probe at root /health (no auth, no prefix)
    app.include_router(health_router)
    # Auth-protected metrics under /api/v1/monitoring/metrics
    app.include_router(metrics_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Security: Always bind to localhost in local mode
    host = "127.0.0.1" if settings.app_mode == "local" else settings.host
    
    uvicorn.run(
        "main:app",
        host=host,
        port=settings.port,
        reload=settings.debug,
    )
