"""
SecureHall-RAG FastAPI Application — Phase 5B.2 (Backend API Setup)

Main application entry point.
Configures FastAPI, CORS middleware, request logging, exception handlers,
and registers all API routers under /api/v1.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.exceptions import register_exception_handlers
from .routers import query, documents, settings as settings_router
from .routers import auth as auth_router
from .routers import admin as admin_router
from .routers import feedback as feedback_router
from .services.rag_engine import get_pipeline, is_pipeline_ready
from .db.models import init_db

# ─────────────────────────────────────────────────────────────────────────────
# Logging  (5B.2.7)
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("securehall-rag")


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan  (startup / shutdown hook)
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    logger.info("🚀 SecureHall-RAG API starting up...")
    logger.info(f"   Environment : {settings.ENVIRONMENT}")
    logger.info(f"   Version     : {settings.VERSION}")
    logger.info(f"   Debug Mode  : {settings.DEBUG}")
    logger.info(f"   API Prefix  : {settings.API_V1_PREFIX}")
    logger.info(f"   Upload Dir  : {settings.UPLOAD_DIR}")
    logger.info(f"   Max Upload  : {settings.MAX_UPLOAD_SIZE_MB} MB")
    logger.info(f"   Allowed Ext : {settings.ALLOWED_EXTENSIONS}")
    logger.info(f"   CORS Origins: {settings.CORS_ORIGINS}")

    # Pre-warm the RAG pipeline (non-blocking — keeps startup fast)
    try:
        get_pipeline()
        if is_pipeline_ready():
            logger.info("✅ RAG pipeline ready with indexed documents.")
        else:
            logger.info("ℹ️  RAG pipeline initialised — no documents indexed yet.")
    except Exception as e:
        logger.warning(f"⚠️  RAG pipeline unavailable at startup: {e}")

    # Phase 7.1 — Initialise SQLite database & seed default admin
    try:
        init_db()
        logger.info("✅ Database initialised.")
    except Exception as e:
        logger.warning(f"⚠️  Database init failed: {e}")

    yield  # ← application runs here

    logger.info("🛑 SecureHall-RAG API shutting down...")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App  (5B.2.1, 5B.2.6)
# ─────────────────────────────────────────────────────────────────────────────
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .core.limiter import limiter

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "**SecureHall-RAG** — A trustworthy, citation-backed document Q&A API.\n\n"
        "Upload documents (PDF, DOCX, TXT, MD), ask natural language questions, and receive "
        "verifiable answers with **inline citations**, **confidence scores**, and "
        "**hallucination risk assessment** powered by the SecureHall-RAG pipeline.\n\n"
        "---\n"
        "### Quick Start\n"
        "1. `POST /api/v1/documents/upload` — Upload your documents\n"
        "2. `POST /api/v1/query` — Ask a question\n"
        "3. `GET /api/v1/query/history` — Browse conversation history\n"
    ),
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Health check and pipeline status."},
        {
            "name": "Authentication",
            "description": "Register, login, JWT token management.",
        },
        {
            "name": "Query & Answers",
            "description": "Submit questions, get cited answers.",
        },
        {
            "name": "Document Management",
            "description": "Upload, list, inspect, delete documents.",
        },
        {
            "name": "Admin",
            "description": "Metrics, audit logs, user management (Admin/HR).",
        },
        {"name": "Feedback", "description": "Thumbs up/down on AI answers."},
        {"name": "Settings", "description": "User preferences and configuration."},
    ],
)
# Register rate limiter and its exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ─────────────────────────────────────────────────────────────────────────────
# CORS Middleware  
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Request Logging Middleware  (5B.2.7)
# ─────────────────────────────────────────────────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Assign a unique request ID to every request and log method, path, and
    elapsed time.  The ID is returned in the `X-Request-ID` response header
    and forwarded to the frontend for end-to-end tracing.
    """
    # Prefer the ID injected by the frontend (X-Request-ID header)
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:8]
    start_time = time.perf_counter()
    request.state.request_id = request_id

    logger.info(f"[{request_id}] ➡️  {request.method} {request.url.path}")

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        f"[{request_id}] ⬅️  {request.method} {request.url.path} "
        f"→ {response.status_code} ({elapsed_ms:.0f} ms)"
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed_ms:.0f}ms"
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Global Exception Handlers  (5B.2.5)
# ─────────────────────────────────────────────────────────────────────────────

register_exception_handlers(app)


# ─────────────────────────────────────────────────────────────────────────────
# API Routers  (5B.2.3)
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(
    query.router,
    prefix=f"{settings.API_V1_PREFIX}/query",
    tags=["Query & Answers"],
)

app.include_router(
    documents.router,
    prefix=f"{settings.API_V1_PREFIX}/documents",
    tags=["Document Management"],
)

app.include_router(
    settings_router.router,
    prefix=f"{settings.API_V1_PREFIX}/settings",
    tags=["Settings"],
)

# Phase 7 — Auth routes
app.include_router(
    auth_router.router,
    prefix=f"{settings.API_V1_PREFIX}",
)

# Phase 9 — Admin routes
app.include_router(
    admin_router.router,
    prefix=f"{settings.API_V1_PREFIX}",
)

# Phase 9.4 — Feedback routes
app.include_router(
    feedback_router.router,
    prefix=f"{settings.API_V1_PREFIX}",
)


# ─────────────────────────────────────────────────────────────────────────────
# Root & Health Endpoints  (5B.2.3, 5B.2.8)
# ─────────────────────────────────────────────────────────────────────────────


@app.get(
    "/",
    tags=["Health"],
    summary="Service info",
    description="Returns basic service metadata confirming the API is operational.",
)
async def root():
    """Root endpoint — confirms the API is running."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description=(
        "Lightweight health check for load balancers and monitoring systems. "
        "Also reports whether the RAG pipeline has indexed documents."
    ),
)
async def health_check():
    """Detailed health check endpoint."""
    pipeline_ready = is_pipeline_ready()
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "pipeline": {
            "initialized": get_pipeline() is not None,
            "index_ready": pipeline_ready,
            "status": "ready" if pipeline_ready else "awaiting_documents",
        },
    }


@app.get(
    f"{settings.API_V1_PREFIX}/health",
    tags=["Health"],
    summary="API-prefixed health check",
    description="Same as /health but accessible under the /api/v1 prefix.",
    include_in_schema=False,
)
async def api_health_check():
    """Alias of /health under the versioned prefix (used by the frontend)."""
    return await health_check()
