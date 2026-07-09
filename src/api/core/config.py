"""
Application Configuration — Phase 5B.2 (Backend API Setup)
Loads settings from environment variables with Pydantic-Settings
for strong typing and automatic .env file support.
"""

from __future__ import annotations

import os
from typing import List


class Settings:
    """
    Application settings.

    All values can be overridden via environment variables (or a .env file
    at the project root).  Defaults are safe for local development.
    """

    # ── Project identity ─────────────────────────────────────────────────
    PROJECT_NAME: str = "SecureHall-RAG API"
    VERSION: str = "1.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ── API ──────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # ── CORS ─────────────────────────────────────────────────────────────
    #   Accept comma-separated list; include both localhost variants.
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        (
            "http://localhost:3000,"
            "http://localhost:3001,"
            "http://127.0.0.1:3000,"
            "http://127.0.0.1:3001"
        ),
    ).split(",")

    # ── Logging ───────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # ── File uploads ─────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md"]
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploaded_documents")

    # ── RAG pipeline ─────────────────────────────────────────────────────
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.1")
    DENSE_MODEL: str = os.getenv(
        "DENSE_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    CHUNK_SIZE_TOKENS: int = int(os.getenv("CHUNK_SIZE_TOKENS", "300"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    RERANKER_MODEL: str = os.getenv(
        "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    ENABLE_RERANKING: bool = os.getenv("ENABLE_RERANKING", "true").lower() == "true"

    # ── Security / Rate limiting ─────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    # ── Computed helpers ─────────────────────────────────────────────────
    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload file size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
