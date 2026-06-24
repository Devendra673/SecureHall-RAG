"""
RAG Engine Service — Phase 5B.2 (Backend API Setup) / 5B.3
Thin service wrapper around the existing src.rag_pipeline.RAGPipeline.

Provides:
  • Singleton pipeline instance (lazy-initialised on first call)
  • is_pipeline_ready()  — quick status check used by health endpoint
  • pipeline_stats()     — document count and index status for health endpoint
  • reset_pipeline()     — force re-initialisation (useful after errors)
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("securehall-rag.services.rag_engine")

_pipeline_instance = None
_init_error: Optional[str] = None


def get_pipeline():
    """
    Return the singleton RAG pipeline instance, creating it on first call.

    Returns:
        RAGPipeline instance, or None if the pipeline cannot be loaded
        (e.g. missing dependencies in development mode).
    """
    global _pipeline_instance, _init_error

    if _pipeline_instance is not None:
        return _pipeline_instance

    try:
        from ...rag_pipeline import RAGPipeline
        from ..core.config import settings

        _pipeline_instance = RAGPipeline(
            llm_model=settings.LLM_MODEL,
            dense_model=settings.DENSE_MODEL,
            chunk_size_tokens=settings.CHUNK_SIZE_TOKENS,
            retrieval_top_k=settings.RETRIEVAL_TOP_K,
            temperature=settings.LLM_TEMPERATURE,
            reranker_model=settings.RERANKER_MODEL,
            enable_reranking=settings.ENABLE_RERANKING,
            data_dir="app_data",
        )
        _init_error = None
        logger.info("✅ RAG pipeline initialised successfully.")
        return _pipeline_instance

    except ImportError as e:
        _init_error = f"Import error: {e}"
        logger.warning(f"RAG pipeline unavailable (missing deps): {e}")
        logger.warning(
            "API will run in placeholder mode — upload endpoints still work."
        )
        return None

    except Exception as e:
        _init_error = str(e)
        logger.error(f"RAG pipeline initialisation failed: {e}", exc_info=True)
        return None


def is_pipeline_ready() -> bool:
    """
    Return True if the pipeline is initialised AND has at least one document
    indexed (i.e. queries will return real answers).
    """
    pipeline = get_pipeline()
    if pipeline is None:
        return False
    return bool(getattr(pipeline, "index_built", False))


def pipeline_stats() -> dict:
    """
    Return a status dictionary for the /health endpoint.
    """
    pipeline = get_pipeline()
    return {
        "initialized": pipeline is not None,
        "index_ready": is_pipeline_ready(),
        "status": (
            "ready"
            if is_pipeline_ready()
            else ("awaiting_documents" if pipeline is not None else "unavailable")
        ),
        "init_error": _init_error,
        "doc_count": getattr(pipeline, "doc_count", 0) if pipeline else 0,
    }


def reset_pipeline() -> None:
    """Force re-initialisation of the pipeline (call after a fatal error)."""
    global _pipeline_instance, _init_error
    _pipeline_instance = None
    _init_error = None
    logger.info("Pipeline instance reset — will re-initialise on next request.")
