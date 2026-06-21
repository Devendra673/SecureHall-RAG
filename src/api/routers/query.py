"""
Query Router - Handles Q&A endpoints
Phase 5B.7 - Wired to real RAG pipeline.
Phase 10  - Persistent chat history (SQLite-backed).
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..models.schemas import (
    QueryRequest,
    QueryResponse,
    CitationSchema,
    HistoryEntry,
    HistoryListResponse,
    HistoryUpdateRequest,
    FeedbackRequest,
)
from ..services.rag_engine import get_pipeline
from . import documents as documents_router
from .documents import get_accessible_doc_ids
from ...security.content_filter import ContentFilter, SeverityLevel
from ..db.models import AuditLog, QueryHistory, get_db
from ..db.dependencies import get_current_user_optional, get_current_user
from ..db.models import User

logger = logging.getLogger("securehall-rag.query")
router = APIRouter()

# Singleton content filter — block SQL injection/jailbreaks, sanitize obfuscation
_content_filter = ContentFilter(
    sql_severity=SeverityLevel.BLOCK,
    jailbreak_severity=SeverityLevel.BLOCK,
    obfuscation_severity=SeverityLevel.SANITIZE,
)


# ── Helper: reconstruct QueryResponse from a DB row ──────────────────────────
def _row_to_response(row: QueryHistory) -> QueryResponse:
    """Deserialise a QueryHistory DB row back into a full QueryResponse."""
    try:
        citations_raw = json.loads(row.citations_json or "[]")
    except (json.JSONDecodeError, TypeError):
        citations_raw = []

    citations = [
        CitationSchema(**c) for c in citations_raw
    ]

    try:
        sources = json.loads(row.sources_json or "[]")
    except (json.JSONDecodeError, TypeError):
        sources = []

    return QueryResponse(
        answer_id=row.answer_id,
        query=row.query_text,
        answer=row.answer_text,
        citations=citations,
        confidence=row.confidence / 100.0,
        hallucination_risk=row.hallucination_risk or "unknown",
        latency_ms=float(row.latency_ms or 0),
        sources=sources,
    )


def _row_to_history_entry(row: QueryHistory) -> HistoryEntry:
    """Convert a QueryHistory DB row into an API HistoryEntry."""
    try:
        citations_count = len(json.loads(row.citations_json or "[]"))
    except (json.JSONDecodeError, TypeError):
        citations_count = 0

    return HistoryEntry(
        answer_id=row.answer_id,
        query=row.query_text,
        answer_preview=row.answer_text[:200],
        citation_count=citations_count,
        confidence=row.confidence / 100.0,
        timestamp=row.created_at,
        is_pinned=row.is_pinned or False,
        title=row.title,
    )


@router.post(
    "",
    response_model=QueryResponse,
    summary="Submit a question",
    description=(
        "Submit a natural language question about your uploaded documents. "
        "Returns an answer with inline citations, confidence score, and source references."
    ),
    responses={
        400: {"description": "Invalid query (empty or too long)"},
        503: {"description": "RAG pipeline not initialized — upload documents first"},
    },
)
async def submit_query(
    body: QueryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process a user question through the RAG pipeline.

    1. Validates the query
    2. Retrieves relevant document chunks via hybrid search
    3. Generates an answer with the LLM
    4. Returns structured response with citations
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(f"[{request_id}] Query received: {body.query[:80]}")

    # ── Security: screen the query before touching the pipeline ──────────────
    filter_result = _content_filter.filter_content(body.query)
    if filter_result.severity_level == SeverityLevel.BLOCK:
        logger.warning(
            f"[{request_id}] Query BLOCKED by content filter: {filter_result.reason}"
        )
        # Phase 9.1 — log blocked query
        try:
            db.add(
                AuditLog(
                    user_id=current_user.id if current_user else None,
                    query=body.query[:1000],
                    blocked=True,
                    block_reason=filter_result.reason,
                    ip_address=request.client.host if request.client else None,
                )
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail=f"Query rejected by security filter: {filter_result.reason}",
        )
    # Use sanitised text if filter applied changes (SANITIZE level)
    query_text = filter_result.filtered_input

    pipeline = get_pipeline()

    if pipeline is None:
        # Check how many documents have been uploaded so we can give the user
        # accurate feedback about WHY we can't answer.
        doc_store = documents_router._documents
        total_docs = len(doc_store)
        ready_docs = sum(1 for d in doc_store.values() if d.status == "ready")
        processing_docs = sum(1 for d in doc_store.values() if d.status == "processing")

        if total_docs == 0:
            answer_text = (
                "The RAG pipeline is not available (ML dependencies may not be installed) "
                "and no documents have been uploaded yet. "
                "Please upload documents and ensure the backend has all required dependencies."
            )
        else:
            answer_text = (
                f"{total_docs} document(s) uploaded ({ready_docs} ready, {processing_docs} processing), "
                "but the RAG pipeline could not be initialised — "
                "ML dependencies (sentence-transformers, faiss, etc.) may not be installed in the environment. "
                "Run `pip install -r requirements.txt` in the project root and restart the backend."
            )

        answer_id = str(uuid.uuid4())[:12]
        response = QueryResponse(
            answer_id=answer_id,
            query=body.query,
            answer=answer_text,
            citations=[],
            confidence=0.0,
            hallucination_risk="high",
            latency_ms=0.0,
            sources=[],
        )
        _history.append(
            HistoryEntry(
                answer_id=answer_id,
                query=body.query,
                answer_preview=response.answer[:200],
                citation_count=0,
                confidence=0.0,
                timestamp=datetime.utcnow(),
            )
        )
        _answers[answer_id] = response
        return response

    try:
        # Determine which documents the user can access (role-based)
        user_role = current_user.role if current_user else "employee"
        allowed_doc_ids = get_accessible_doc_ids(db, user_role)

        # Build pipeline kwargs
        run_kwargs: dict = {}
        if body.eval_mode:
            run_kwargs["eval_mode"] = body.eval_mode
        # Pass allowed doc IDs if doc-level access control is active
        if allowed_doc_ids is not None:
            run_kwargs["allowed_doc_ids"] = allowed_doc_ids
        # Also honour explicit user-supplied doc_ids (intersection with allowed)
        if body.doc_ids:
            explicit = set(body.doc_ids)
            if allowed_doc_ids is not None:
                explicit &= set(allowed_doc_ids)
            run_kwargs["allowed_doc_ids"] = list(explicit)

        result = pipeline.query(query_text, **run_kwargs)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    answer_id = str(uuid.uuid4())[:12]

    # Convert pipeline citations to API schema
    # pipeline.query() returns citations as list of (chunk_id, source_file, text) tuples
    api_citations: list[CitationSchema] = []
    for idx, citation in enumerate(result.get("citations", []), start=1):
        if isinstance(citation, tuple) and len(citation) >= 3:
            chunk_id, source_doc, text_excerpt = citation[0], citation[1], citation[2]
        elif isinstance(citation, dict):
            chunk_id = citation.get("chunk_id", f"chunk_{idx}")
            source_doc = citation.get("source_document", "unknown")
            text_excerpt = citation.get("text_excerpt", "")
        else:
            continue

        api_citations.append(
            CitationSchema(
                citation_id=idx,
                chunk_id=str(chunk_id),
                source_document=Path(source_doc).name,
                text_excerpt=str(text_excerpt)[:500],
                relevance_score=min(float(result.get("confidence", 0.0)), 1.0),
                page_number=None,
            )
        )

    response = QueryResponse(
        answer_id=answer_id,
        query=body.query,
        answer=result.get("answer", "No answer generated."),
        citations=api_citations,
        confidence=min(float(result.get("confidence", 0.0)), 1.0),
        hallucination_risk="low" if result.get("confidence", 0) > 0.7 else "medium",
        latency_ms=float(result.get("latency_ms", 0.0)),
        sources=result.get("sources", []),
    )

    # Persist to database (replaces old in-memory _history / _answers)
    try:
        history_row = QueryHistory(
            answer_id=answer_id,
            user_id=current_user.id,
            query_text=body.query,
            answer_text=response.answer,
            citations_json=json.dumps(
                [c.model_dump() for c in api_citations], default=str
            ),
            sources_json=json.dumps(response.sources, default=str),
            confidence=int(response.confidence * 100),
            hallucination_risk=response.hallucination_risk,
            latency_ms=int(response.latency_ms),
        )
        db.add(history_row)
        db.commit()
    except Exception as hist_err:
        logger.warning(f"Failed to persist query history: {hist_err}")

    # Phase 9.1 — write audit log entry
    try:
        db.add(
            AuditLog(
                user_id=current_user.id if current_user else None,
                query=body.query[:1000],
                answer_preview=response.answer[:500],
                confidence=int(response.confidence * 100),
                latency_ms=int(response.latency_ms),
                blocked=False,
                sources_count=len(api_citations),
                eval_mode=body.eval_mode,
                ip_address=request.client.host if request.client else None,
            )
        )
        db.commit()
    except Exception as audit_err:
        logger.warning(f"Audit log write failed: {audit_err}")

    logger.info(
        f"[{request_id}] Query answered in {response.latency_ms:.0f}ms, confidence={response.confidence:.2f}"
    )
    return response


@router.get(
    "/answer/{answer_id}",
    response_model=QueryResponse,
    summary="Fetch a specific answer",
    description="Retrieve a previously generated answer by its ID, including full citations.",
    responses={404: {"description": "Answer not found"}},
)
async def get_answer(
    answer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific answer by ID from the database."""
    row = db.query(QueryHistory).filter(
        QueryHistory.answer_id == answer_id,
        QueryHistory.user_id == current_user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Answer '{answer_id}' not found.")
    return _row_to_response(row)


@router.get(
    "/history",
    response_model=HistoryListResponse,
    summary="Get chat history",
    description="Retrieve the list of previous queries and answers.",
)
async def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all conversation history entries for the current user, newest first."""
    rows = (
        db.query(QueryHistory)
        .filter(QueryHistory.user_id == current_user.id)
        .order_by(QueryHistory.created_at.desc())
        .all()
    )
    entries = [_row_to_history_entry(r) for r in rows]
    return HistoryListResponse(
        entries=entries,
        total_count=len(entries),
    )


@router.delete(
    "/history",
    summary="Clear chat history",
    description="Delete all conversation history entries (used by New Chat).",
)
async def clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all history entries for the current user."""
    db.query(QueryHistory).filter(
        QueryHistory.user_id == current_user.id
    ).delete()
    db.commit()
    return {"message": "Chat history cleared."}


@router.delete(
    "/history/{answer_id}",
    summary="Delete a single chat history entry",
    description="Delete a specific conversation history entry by its answer ID.",
)
async def delete_history_entry(
    answer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a single history entry from the database."""
    deleted = db.query(QueryHistory).filter(
        QueryHistory.answer_id == answer_id,
        QueryHistory.user_id == current_user.id,
    ).delete()
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found.")
    return {"message": f"Entry {answer_id} deleted."}


@router.patch(
    "/history/{answer_id}",
    response_model=HistoryEntry,
    summary="Update a chat history entry",
    description="Update metadata like title or pinned status for a history entry.",
)
async def update_history_entry(
    answer_id: str,
    update: HistoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a history entry's title or pinned status in the database."""
    row = db.query(QueryHistory).filter(
        QueryHistory.answer_id == answer_id,
        QueryHistory.user_id == current_user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found.")

    if update.title is not None:
        row.title = update.title
    if update.is_pinned is not None:
        row.is_pinned = update.is_pinned
    db.commit()
    db.refresh(row)
    return _row_to_history_entry(row)


@router.post(
    "/answer/{answer_id}/feedback",
    summary="Submit feedback for an answer",
    description="Record whether the user found the answer helpful (thumbs up/down).",
)
async def submit_feedback(
    answer_id: str,
    feedback: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Submit feedback for an AI response and persist to database."""
    row = db.query(QueryHistory).filter(QueryHistory.answer_id == answer_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Answer not found.")

    rating = "up" if feedback.is_positive else "down"
    user_id = current_user.id if current_user else None

    # Persist to database
    if user_id:
        try:
            from ..db.models import QueryFeedback
            import uuid as _uuid

            # Upsert: update if already voted on this answer
            existing = (
                db.query(QueryFeedback)
                .filter(
                    QueryFeedback.message_id == answer_id,
                    QueryFeedback.user_id == user_id,
                )
                .first()
            )
            if existing:
                existing.rating = rating
                existing.comment = feedback.comment or ""
            else:
                fb = QueryFeedback(
                    id=str(_uuid.uuid4()),
                    message_id=answer_id,
                    user_id=user_id,
                    rating=rating,
                    comment=feedback.comment or "",
                )
                db.add(fb)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist feedback: {e}")

    logger.info(
        f"Feedback received for {answer_id}: positive={feedback.is_positive}, comment={feedback.comment}"
    )

    return {"message": "Feedback recorded successfully."}
