"""Phase 9.4 — User Feedback Router (thumbs up/down on answers)."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db.models import ChatMessage, QueryFeedback, User, get_db
from ..db.dependencies import get_current_user
import uuid

router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str  # "up" or "down"
    comment: str = ""


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit thumbs-up or thumbs-down for a chat message."""
    if body.rating not in ("up", "down"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Rating must be 'up' or 'down'"
        )
    # Upsert — allow changing your vote
    existing = (
        db.query(QueryFeedback)
        .filter(
            QueryFeedback.message_id == body.message_id,
            QueryFeedback.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        existing.rating = body.rating
        existing.comment = body.comment
        db.commit()
        return {"id": existing.id, "updated": True}
    fb = QueryFeedback(
        id=str(uuid.uuid4()),
        message_id=body.message_id,
        user_id=current_user.id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(fb)
    db.commit()
    return {"id": fb.id, "updated": False}
