"""
Phase 9.1 + 9.3 — Admin Router
Endpoints for audit logs, user management, system metrics, and feedback.
All routes require admin role.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..db.models import AuditLog, ChatMessage, QueryFeedback, User, get_db
from ..db.auth_service import create_user, get_user_by_id, hash_password
from ..db.dependencies import require_admin, require_hr_admin, get_current_user

logger = logging.getLogger("securehall-rag")
router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: str = ""
    role: str = "employee"


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None


class AuditLogOut(BaseModel):
    id: str
    user_id: Optional[str]
    query: str
    answer_preview: Optional[str]
    confidence: Optional[int]
    latency_ms: Optional[int]
    blocked: bool
    block_reason: Optional[str]
    sources_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── System Metrics ─────────────────────────────────────────────────────────────
@router.get("/metrics")
async def get_metrics(
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_admin),
):
    """Dashboard overview metrics."""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    total_queries = db.query(func.count(AuditLog.id)).scalar() or 0
    queries_24h = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.created_at >= last_24h)
        .scalar()
        or 0
    )
    blocked_total = (
        db.query(func.count(AuditLog.id)).filter(AuditLog.blocked == True).scalar() or 0
    )
    blocked_24h = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.blocked == True, AuditLog.created_at >= last_24h)
        .scalar()
        or 0
    )
    avg_latency = (
        db.query(func.avg(AuditLog.latency_ms))
        .filter(AuditLog.latency_ms.isnot(None))
        .scalar()
        or 0
    )
    avg_confidence = (
        db.query(func.avg(AuditLog.confidence))
        .filter(AuditLog.confidence.isnot(None))
        .scalar()
        or 0
    )

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = (
        db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    )

    thumbs_up = (
        db.query(func.count(QueryFeedback.id))
        .filter(QueryFeedback.rating == "up")
        .scalar()
        or 0
    )
    thumbs_down = (
        db.query(func.count(QueryFeedback.id))
        .filter(QueryFeedback.rating == "down")
        .scalar()
        or 0
    )

    return {
        "queries": {
            "total": total_queries,
            "last_24h": queries_24h,
            "blocked_total": blocked_total,
            "blocked_24h": blocked_24h,
            "block_rate_pct": round(blocked_total / max(total_queries, 1) * 100, 1),
        },
        "performance": {
            "avg_latency_ms": round(avg_latency, 1),
            "avg_confidence": round(avg_confidence, 1),
        },
        "users": {
            "total": total_users,
            "active": active_users,
        },
        "feedback": {
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_pct": round(
                thumbs_up / max(thumbs_up + thumbs_down, 1) * 100, 1
            ),
        },
    }


# ── Audit Logs ─────────────────────────────────────────────────────────────────
@router.get("/audit-logs", response_model=List[AuditLogOut])
async def list_audit_logs(
    blocked_only: bool = Query(False),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_admin),
):
    """List audit log entries, optionally filtering for blocked queries only."""
    q = db.query(AuditLog).order_by(desc(AuditLog.created_at))
    if blocked_only:
        q = q.filter(AuditLog.blocked == True)
    return q.offset(offset).limit(limit).all()


# ── User Management ────────────────────────────────────────────────────────────
@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all users."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin: create a new user with any role."""
    from ..db.auth_service import get_user_by_email, get_user_by_username

    if get_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")
    if get_user_by_username(db, body.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
    if body.role not in ("admin", "hr", "employee"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role")
    return create_user(
        db, body.email, body.username, body.password, body.full_name, body.role
    )


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Admin: update role, active status, or full name of a user."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == current_admin.id and body.role and body.role != "admin":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot change your own admin role"
        )
    if body.role is not None:
        if body.role not in ("admin", "hr", "employee"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.full_name is not None:
        user.full_name = body.full_name
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Admin: deactivate (soft-delete) a user account."""
    if user_id == current_admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Cannot deactivate your own account"
        )
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()


# ── Feedback Review ────────────────────────────────────────────────────────────
@router.get("/feedback")
async def list_feedback(
    rating: Optional[str] = Query(None, pattern="^(up|down)$"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_hr_admin),
):
    """List user feedback (thumbs up/down) on AI answers."""
    q = db.query(QueryFeedback).order_by(desc(QueryFeedback.created_at))
    if rating:
        q = q.filter(QueryFeedback.rating == rating)
    items = q.limit(limit).all()
    return [
        {
            "id": f.id,
            "message_id": f.message_id,
            "user_id": f.user_id,
            "rating": f.rating,
            "comment": f.comment,
            "created_at": f.created_at.isoformat(),
        }
        for f in items
    ]


from fastapi import BackgroundTasks
from ..services.rag_engine import get_pipeline

class FineTuneEntry(BaseModel):
    question: str
    positive: str

class FineTuneRequest(BaseModel):
    qa_pairs: List[FineTuneEntry]
    epochs: Optional[int] = 3
    batch_size: Optional[int] = 16

def run_background_finetune(qa_pairs_data: list[dict], epochs: int, batch_size: int):
    try:
        from src.training.finetune_embeddings import EmbeddingFineTuner
        tuner = EmbeddingFineTuner()
        examples = tuner.prepare_training_data(qa_pairs_data)
        model_path = tuner.train(examples, epochs=epochs, batch_size=batch_size)
        
        # Swap model in active pipeline
        pipeline = get_pipeline()
        if pipeline:
            pipeline.use_finetuned_embeddings(model_path)
            logger.info("Successfully loaded fine-tuned embeddings into RAG pipeline.")
    except Exception as e:
        logger.error(f"Background fine-tuning failed: {e}")

@router.get("/cache/stats", dependencies=[Depends(require_admin)])
async def get_cache_stats():
    """Get semantic cache metrics and statistics."""
    pipeline = get_pipeline()
    if hasattr(pipeline, "cache") and pipeline.cache is not None:
        return pipeline.cache.stats()
    return {"enabled": False, "message": "Semantic cache is not initialized."}

@router.post("/embeddings/finetune", dependencies=[Depends(require_admin)])
async def trigger_embeddings_finetune(
    body: FineTuneRequest,
    background_tasks: BackgroundTasks
):
    """Trigger contrastive fine-tuning of the embedding model as a background task."""
    try:
        from src.training.finetune_embeddings import _TRAINING_AVAILABLE
    except ImportError:
        _TRAINING_AVAILABLE = False

    if not _TRAINING_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding fine-tuning dependencies are not available in current virtual environment."
        )

    if not body.qa_pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="qa_pairs list cannot be empty."
        )

    qa_pairs_data = [{"question": p.question, "positive": p.positive} for p in body.qa_pairs]

    # Enqueue background task
    background_tasks.add_task(
        run_background_finetune,
        qa_pairs_data,
        body.epochs,
        body.batch_size
    )

    return {
        "status": "started",
        "message": "Fine-tuning embedding model in background. The model will be swapped automatically once complete.",
        "output_dir": "models/finetuned-embeddings",
        "epochs": body.epochs,
        "batch_size": body.batch_size,
        "training_examples_count": len(body.qa_pairs)
    }
