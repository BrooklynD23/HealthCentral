"""
Application configuration using Pydantic Settings.

Supports multiple deployment modes:
- local: Desktop application, SQLite, localhost only
- server: Web deployment, PostgreSQL, configurable origins (future)
"""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application mode
    app_mode: Literal["local", "server"] = "local"
    app_env: Literal["development", "production"] = "development"
    debug: bool = True
    
    # Server configuration
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # Database
    database_type: Literal["sqlite", "postgresql"] = "sqlite"
    sqlite_database_path: str = "data/healthcentral.db"
    database_encryption_enabled: bool = True
    # Require SQLCipher for profile databases. Set to False only for development.
    database_encryption_required: bool = True
    
    # PostgreSQL (future server mode)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "healthcentral"
    postgres_password: str = ""
    postgres_database: str = "healthcentral"
    
    # Security
    auto_lock_timeout_minutes: int = 15
    use_dpapi: bool = True
    jwt_secret: str = ""
    jwt_revocation_enabled: bool = True  # Allow logout to invalidate JWTs locally

    # Authentication hardening
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_max_attempts: int = 10
    auth_rate_limit_window_seconds: int = 60
    
    # Local AI models
    models_path: str = "models/"
    default_chat_model: str = "phi-3-mini"
    default_embeddings_model: str = "bge-small-en-v1.5"
    chat_context_size: int = 4096
    inference_threads: int = 0

    # Model Tier Settings (Phase 0.3)
    default_model_tier: str = "low"  # String tier: "low", "mid", "high"
    auto_detect_hardware: bool = True  # Run hardware detection on startup
    model_download_timeout: int = 3600  # Download timeout in seconds (1 hour)
    
    # Vector store
    vector_store_type: Literal["sqlite-vss", "faiss"] = "sqlite-vss"
    embedding_dimensions: int = 384
    
    # Document processing
    max_import_file_size_mb: int = 50
    supported_doc_types: str = "pdf,png,jpg,jpeg"
    ocr_enabled: bool = False
    allow_legacy_plaintext_documents: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_file_path: str = "logs/healthcentral.log"
    audit_log_enabled: bool = True

    # External API (Phase 2E) — per-user opt-in, default off
    external_api_provider: str = ""  # "", "openai", "anthropic"
    external_api_key: str = ""
    external_api_model: str = ""

    # Phase 4: AI Safety / Verification Settings
    verification_enabled: bool = True
    min_faithfulness_score: float = 0.6  # Minimum score for verified claims
    min_entailment_confidence: float = 0.7  # Minimum NLI confidence
    fail_on_contradiction: bool = True  # Fail if any source contradicts claim
    min_supporting_sources: int = 1  # Minimum sources needed to verify claim
    use_llm_entailment: bool = False  # Use LLM for complex entailment (vs rule-based)
    multi_pass_verification: bool = False  # Enable multi-pass consistency checking
    
    @property
    def app_data_path(self) -> Path:
        """Get the application data directory path."""
        if self.app_mode == "local":
            # Use local data directory for desktop app
            return Path("data")
        else:
            # Server mode uses configured paths
            return Path(self.sqlite_database_path).parent
    
    @property
    def database_url(self) -> str:
        """Get the database connection URL."""
        if self.database_type == "sqlite":
            db_path = self.app_data_path / "healthcentral.db"
            return f"sqlite+aiosqlite:///{db_path}"
        else:
            return (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
            )
    
    @property
    def supported_extensions(self) -> list[str]:
        """Get list of supported file extensions."""
        return [ext.strip().lower() for ext in self.supported_doc_types.split(",")]


settings = Settings()
