"""
Application configuration using Pydantic Settings.

Supports multiple deployment modes:
- local: Desktop application, SQLite, localhost only
- server: Web deployment, PostgreSQL, configurable origins (future)
"""

import shutil
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

    # API rate limiting (OPS-003)
    api_rate_limit_enabled: bool = True
    api_rate_limit_max_requests: int = 100
    api_rate_limit_window_seconds: int = 60

    # Proxy trust (SEC-007)
    trusted_proxy_enabled: bool = False
    trusted_proxy_cidrs: list[str] = []  # e.g. ["127.0.0.1/32", "10.0.0.0/8"]

    # Input validation (OPS-003)
    max_request_body_bytes: int = 10_485_760  # 10 MB

    # Security headers (OPS-003)
    security_headers_enabled: bool = True
    audit_security_events_to_db: bool = False

    # Monitoring (OPS-001)
    metrics_enabled: bool = True
    metrics_buffer_size: int = 10000
    correlation_id_header: str = "X-Correlation-ID"
    
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

    # LLM Provider Selection (P1: provider abstraction)
    # llm_provider: which inference backend to use.
    #   "llama_cpp"  — local GGUF via llama-cpp-python (default, always local)
    #   "ollama"     — local Ollama daemon at localhost:11434 (optional)
    llm_provider: str = "llama_cpp"

    # llm_model: model identifier for the selected provider.
    #   llama_cpp:  path to a .gguf file (empty = auto-detect from models_path)
    #   ollama:     Ollama model tag, e.g. "gemma4:12b", "gemma4:e4b", "gemma4:26b"
    llm_model: str = ""

    # Ollama base URL (must be localhost — non-local URLs are rejected at startup)
    ollama_base_url: str = "http://127.0.0.1:11434"
    
    # Vector store
    embedding_dimensions: int = 384
    
    # Document processing
    max_import_file_size_mb: int = 50
    supported_doc_types: str = "pdf,png,jpg,jpeg"
    ocr_enabled: bool = False
    # Reserved for future AI-assisted lab JSON extraction (no pipeline wiring yet)
    ai_assisted_lab_extraction: bool = False
    allow_legacy_plaintext_documents: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_file_path: str = "logs/healthcentral.log"
    audit_log_enabled: bool = True

    # Memory store (ASSIST-MEM-001)
    max_memory_items_per_profile: int = 100
    assistant_memory_enabled: bool = True  # ASSIST-MEM-003: inject memory into RAG context
    assistant_memory_max_items_in_prompt: int = 20
    assistant_memory_max_prompt_chars: int = 2000

    # Redaction (PRIV-RED-001) — applied before external API calls
    redaction_enabled: bool = True
    redaction_policy_level: str = "strict"  # "strict", "standard", "minimal"
    # Break-glass: allow unsafe external prompts in production (NOT recommended).
    external_api_redaction_break_glass: bool = False

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
    
    def model_post_init(self, __context) -> None:
        """Enforce production safety invariants at construction time."""
        if self.app_env == "production" and self.debug:
            object.__setattr__(self, "debug", False)

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

    def validate_startup(self) -> list[str]:
        """
        Validate configuration at startup.

        Returns list of warning strings for non-fatal issues.
        Raises RuntimeError in production if jwt_secret is empty.
        """
        warnings: list[str] = []

        # Check models_path exists or can be created
        models_dir = Path(self.models_path)
        if not models_dir.exists():
            try:
                models_dir.mkdir(parents=True, exist_ok=True)
                warnings.append(f"Created missing models directory: {self.models_path}")
            except OSError as e:
                warnings.append(f"Cannot create models directory '{self.models_path}': {e}")

        # Check OCR availability
        if self.ocr_enabled and not shutil.which("tesseract"):
            warnings.append(
                "OCR enabled but tesseract not found on PATH; disabling OCR"
            )
            self.ocr_enabled = False

        # Production hard-fail: JWT secret required
        if self.app_env == "production" and not self.jwt_secret:
            raise RuntimeError(
                "jwt_secret must be set in production environment"
            )

        # Redaction config validation (F-001/F-002)
        from modules.redaction import VALID_POLICY_LEVELS

        if self.redaction_policy_level not in VALID_POLICY_LEVELS:
            raise RuntimeError(
                f"Invalid redaction_policy_level '{self.redaction_policy_level}'; "
                f"must be one of {sorted(VALID_POLICY_LEVELS)}"
            )

        if self.external_api_redaction_break_glass:
            warnings.append(
                "EXTERNAL_API_REDACTION_BREAK_GLASS is enabled; external prompts may be sent with reduced/no redaction"
            )

        if self.app_env == "production" and not self.external_api_redaction_break_glass:
            if not self.redaction_enabled:
                raise RuntimeError(
                    "redaction_enabled must be True in production (required for external API calls). "
                    "To override (NOT recommended), set EXTERNAL_API_REDACTION_BREAK_GLASS=true."
                )
            if self.redaction_policy_level != "strict":
                raise RuntimeError(
                    "redaction_policy_level must be 'strict' in production (required for external API calls). "
                    "To override (NOT recommended), set EXTERNAL_API_REDACTION_BREAK_GLASS=true."
                )
        elif self.app_env == "production" and self.external_api_redaction_break_glass:
            if not self.redaction_enabled:
                warnings.append(
                    "Redaction is disabled in production while EXTERNAL_API_REDACTION_BREAK_GLASS=true; "
                    "external prompts may be sent unredacted"
                )
            elif self.redaction_policy_level != "strict":
                warnings.append(
                    f"Non-strict redaction policy '{self.redaction_policy_level}' in production while "
                    "EXTERNAL_API_REDACTION_BREAK_GLASS=true; external prompts may include PHI/PII"
                )

        # Production safety: debug is already forced off by model_post_init.
        # No additional action needed here.

        return warnings


settings = Settings()


def is_tesseract_on_path() -> bool:
    """True if the Tesseract binary is discoverable on PATH."""
    return shutil.which("tesseract") is not None


def is_ocr_available() -> bool:
    """
    Server-level OCR capability: deployment allows OCR and Tesseract is installed.

    Startup validation may set ocr_enabled False if Tesseract was missing at boot.
    Per-profile user preference is handled separately via compute_ocr_effective.
    """
    return settings.ocr_enabled and is_tesseract_on_path()


def user_ocr_preference_enabled(user_settings: object | None) -> bool:
    """Default ON when no settings row exists yet."""
    if user_settings is None:
        return True
    return bool(getattr(user_settings, "ocr_preference_enabled", True))


def compute_ocr_effective(user_pref_enabled: bool) -> tuple[bool, list[str]]:
    """
    Effective OCR for a profile: env cap, Tesseract, and user toggle.

    Returns:
        (effective, blockers) where blockers are stable codes for the UI:
        disabled_by_admin, tesseract_missing, user_disabled
    """
    blockers: list[str] = []
    if not settings.ocr_enabled:
        blockers.append("disabled_by_admin")
    if not is_tesseract_on_path():
        blockers.append("tesseract_missing")
    if not user_pref_enabled:
        blockers.append("user_disabled")
    effective = settings.ocr_enabled and is_tesseract_on_path() and user_pref_enabled
    return effective, blockers
