"""
HealthCentral Backend - Main Application Entry Point

Local-first medical results companion API server.
Designed for localhost operation with future scalability to web deployment.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import init_database, close_database
from core.migrations import run_master_migrations_async
from api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Initialize directories and verify SQLCipher
    await init_database()

    # Run master database migrations (non-blocking via thread)
    await run_master_migrations_async()

    yield
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
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "mode": settings.app_mode,
            "version": "0.1.0"
        }
    
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
