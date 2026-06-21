"""
SecureHall-RAG FastAPI REST API
Phase 5B - Professional web portal backend.

Usage:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from .main import app

__all__ = ["app"]
