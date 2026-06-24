"""
Query Router - Handles Q&A endpoints
Phase 5B.7 - Wired to real RAG pipeline.
Phase 10  - Session-based chat history (ChatSession + ChatMessage).
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.schemas import (
    QueryRequest,
    QueryResponse,
    CitationSchema,
    HistoryEntry,
    HistoryListResponse,
    HistoryUpdateRequest,
    FeedbackRequest,
    ChatSessionSchema,
    ChatSessionListResponse,
    ChatSessionDetailResponse,
    ChatMessageSchema,
)
from ..services.rag_engine import get_pipeline
from . import documents as documents_router
from .documents import get_accessible_doc_ids
from ...security.content_filter import ContentFilter, SeverityLevel
from ..db.models import AuditLog, QueryHistory, ChatSession, ChatMessage, get_db, SessionLocal
from ..db.dependencies import get_current_user_optional, get_current_user
from ..db.models import User
from ..core.limiter import limiter

logger = logging.getLogger("securehall-rag.query")
router = APIRouter()

# Singleton content filter — block SQL injection/jailbreaks, sanitize obfuscation
_content_filter = ContentFilter(
    sql_severity=SeverityLevel.BLOCK,
    jailbreak_severity=SeverityLevel.BLOCK,
    obfuscation_severity=SeverityLevel.SANITIZE,
)


# ── Helper: get or create a ChatSession ───────────────────────────────────────
def _get_or_create_session(
    db: Session, user_id: str, session_id: str | None, first_query: str
) -> ChatSession:
    """Return an existing session or create a new one."""
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if session:
            return session
        # If session_id provided but not found, create new with that id
        logger.warning(f"Session {session_id} not found, creating new session")

    # Create new session — title is first 80 chars of the first query
    session = ChatSession(
        id=session_id if session_id else str(uuid.uuid4()),
        user_id=user_id,
        title=first_query[:80],
    )
    db.add(session)
    db.flush()  # Get the ID without committing
    return session


# ── Helper: convert ChatMessage row to ChatMessageSchema ──────────────────────
def _row_to_message_schema(row: ChatMessage) -> ChatMessageSchema:
    """Convert a ChatMessage DB row into a ChatMessageSchema."""
    citations = []
    try:
        citations_raw = json.loads(row.citations_json or "[]")
        citations = [CitationSchema(**c) for c in citations_raw]
    except (json.JSONDecodeError, TypeError):
        pass

    sources = []
    try:
        sources = json.loads(row.sources_json or "[]")
    except (json.JSONDecodeError, TypeError):
        pass

    return ChatMessageSchema(
        id=row.id,
        role=row.role,
        content=row.content,
        confidence=(row.confidence / 100.0) if row.confidence is not None else None,
        citations=citations,
        sources=sources,
        hallucination_risk=row.hallucination_risk,
        latency_ms=float(row.latency_ms or 0),
        created_at=row.created_at,
    )


# ── Legacy helper (kept for backwards compat with /answer/{id}) ──────────────
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
@limiter.limit("30/minute")
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
    5. Persists to ChatSession/ChatMessage
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
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline not initialized. Upload documents first.",
        )

    # Load or create session and get history from SQLite BEFORE querying RAG pipeline
    try:
        session = _get_or_create_session(db, current_user.id, body.session_id, body.query)
        db_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        history_list = []
        for msg in db_messages:
            history_list.append({"role": msg.role, "content": msg.content})
    except Exception as sess_err:
        logger.warning(f"Failed to get/create session or fetch history: {sess_err}")
        session = None
        history_list = body.history or []

    try:
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

        result = pipeline.query(query_text, history=history_list, **run_kwargs)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    answer_id = str(uuid.uuid4())[:12]

    # Convert pipeline citations to API schema
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

        if source_doc.startswith("http://") or source_doc.startswith("https://"):
            source_name = source_doc
        else:
            source_name = Path(source_doc).name
            if len(source_name) > 13 and source_name[12] == "_":
                prefix = source_name[:12]
                if all(c.isalnum() or c == "-" for c in prefix):
                    source_name = source_name[13:]

        api_citations.append(
            CitationSchema(
                citation_id=idx,
                chunk_id=str(chunk_id),
                source_document=source_name,
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

    # ── Persist to ChatSession + ChatMessage ──────────────────────────────────
    try:
        if session is None:
            session = _get_or_create_session(db, current_user.id, body.session_id, body.query)

        # Save user message
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=body.query,
        )
        db.add(user_msg)

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=response.answer,
            confidence=int(response.confidence * 100),
            citations_json=json.dumps([c.model_dump() for c in api_citations], default=str),
            sources_json=json.dumps(response.sources, default=str),
            hallucination_risk=response.hallucination_risk,
            latency_ms=int(response.latency_ms),
        )
        db.add(assistant_msg)

        # Update session timestamp
        session.updated_at = datetime.utcnow()
        db.commit()

        # Add session_id to response for the frontend
        response.answer_id = f"{session.id}:{answer_id}"
        response.session_id = session.id
    except Exception as hist_err:
        logger.warning(f"Failed to persist to session: {hist_err}")

    # Also write to legacy QueryHistory (audit trail)
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


@router.post(
    "/stream",
    summary="Stream an answer via SSE",
    description="Stream the answer as Server-Sent Events (SSE) for a typing effect.",
)
@limiter.limit("30/minute")
async def stream_query(
    body: QueryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", "unknown")
    
    # 1. Security Check
    filter_result = _content_filter.filter_content(body.query)
    if filter_result.severity_level == SeverityLevel.BLOCK:
        # Log blocked query
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
    query_text = filter_result.filtered_input

    pipeline = get_pipeline()
    if pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

    user_role = current_user.role if current_user else "employee"
    allowed_doc_ids = get_accessible_doc_ids(db, user_role)
    
    run_kwargs: dict = {}
    if allowed_doc_ids is not None:
        run_kwargs["allowed_doc_ids"] = allowed_doc_ids
    if body.doc_ids:
        explicit = set(body.doc_ids)
        if allowed_doc_ids is not None:
            explicit &= set(allowed_doc_ids)
        run_kwargs["allowed_doc_ids"] = list(explicit)

    # Get or create session BEFORE entering the generator
    try:
        session = _get_or_create_session(db, current_user.id, body.session_id, body.query)
        session_id = session.id

        # Fetch past history from the database BEFORE saving the new user query
        db_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        history_list = []
        for msg in db_messages:
            history_list.append({"role": msg.role, "content": msg.content})

        # Save user message immediately
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=body.query,
        )
        db.add(user_msg)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to create session or fetch history: {e}")
        session_id = str(uuid.uuid4())
        history_list = []

    answer_id = str(uuid.uuid4())[:12]

    async def event_generator():
        try:
            full_answer = ""
            api_citations = []
            final_latency = 0.0
            confidence = 0.0
            sources = []

            for event in pipeline.query_stream(query_text, history=history_list, **run_kwargs):
                if event["type"] == "chunk":
                    full_answer += event["content"]
                elif event["type"] == "metadata":
                    # Convert citations for the frontend format
                    frontend_citations = []
                    confidence = event.get("confidence", 0.0)
                    for idx, cit in enumerate(event.get("citations", []), start=1):
                        source_doc = cit[1]
                        if source_doc.startswith("http://") or source_doc.startswith("https://"):
                            source_name = source_doc
                        else:
                            source_name = Path(source_doc).name
                            if len(source_name) > 13 and source_name[12] == "_":
                                prefix = source_name[:12]
                                if all(c.isalnum() or c == "-" for c in prefix):
                                    source_name = source_name[13:]

                        cit_obj = CitationSchema(
                            citation_id=idx,
                            chunk_id=str(cit[0]),
                            source_document=source_name,
                            text_excerpt=str(cit[2])[:500],
                            relevance_score=confidence,
                        )
                        api_citations.append(cit_obj)
                        frontend_citations.append(cit_obj.model_dump())
                    
                    event["citations"] = frontend_citations
                    sources = event.get("sources", [])
                elif event["type"] == "done":
                    final_latency = event.get("latency_ms", 0.0)
                    event["answer_id"] = answer_id
                    event["session_id"] = session_id

                # Send SSE format
                yield f"data: {json.dumps(event)}\n\n"

            # ── Stream complete. Persist assistant message to session ──────────
            with SessionLocal() as db_stream:
                try:
                    assistant_msg = ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=full_answer,
                        confidence=int(confidence * 100),
                        citations_json=json.dumps([c.model_dump() for c in api_citations], default=str),
                        sources_json=json.dumps(sources, default=str),
                        hallucination_risk="low" if confidence > 0.7 else "medium",
                        latency_ms=int(final_latency),
                    )
                    db_stream.add(assistant_msg)

                    # Update session timestamp
                    sess = db_stream.query(ChatSession).filter(ChatSession.id == session_id).first()
                    if sess:
                        sess.updated_at = datetime.utcnow()

                    db_stream.commit()
                except Exception as hist_err:
                    logger.warning(f"Failed to persist stream to session: {hist_err}")

                # Also write to legacy QueryHistory (audit trail)
                try:
                    history_row = QueryHistory(
                        answer_id=answer_id,
                        user_id=current_user.id,
                        query_text=body.query,
                        answer_text=full_answer,
                        citations_json=json.dumps([c.model_dump() for c in api_citations], default=str),
                        sources_json=json.dumps(sources, default=str),
                        confidence=int(confidence * 100),
                        hallucination_risk="low" if confidence > 0.7 else "medium",
                        latency_ms=int(final_latency),
                    )
                    db_stream.add(history_row)
                    db_stream.commit()
                except Exception as hist_err:
                    logger.warning(f"Failed to persist stream history: {hist_err}")

                # Also write to AuditLog (dashboard and analytics)
                try:
                    db_stream.add(
                        AuditLog(
                            user_id=current_user.id if current_user else None,
                            query=body.query[:1000],
                            answer_preview=full_answer[:500],
                            confidence=int(confidence * 100),
                            latency_ms=int(final_latency),
                            blocked=False,
                            sources_count=len(api_citations),
                            eval_mode=body.eval_mode,
                            ip_address=request.client.host if request.client else None,
                        )
                    )
                    db_stream.commit()
                except Exception as audit_err:
                    logger.warning(f"Failed to write stream audit log: {audit_err}")

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION-BASED HISTORY ENDPOINTS (New)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List chat sessions",
    description="Retrieve all chat sessions for the current user, newest first.",
)
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all chat sessions for the current user, ordered by most recent activity."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        msg_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.session_id == s.id
        ).scalar() or 0

        last_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

        result.append(ChatSessionSchema(
            session_id=s.id,
            title=s.title,
            message_count=msg_count,
            last_message_at=last_msg.created_at if last_msg else s.created_at,
            created_at=s.created_at,
        ))

    return ChatSessionListResponse(sessions=result, total_count=len(result))


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    summary="Get session messages",
    description="Retrieve all messages for a specific chat session.",
    responses={404: {"description": "Session not found"}},
)
async def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all messages in a session, ordered chronologically."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return ChatSessionDetailResponse(
        session_id=session.id,
        title=session.title,
        messages=[_row_to_message_schema(m) for m in messages],
        created_at=session.created_at,
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionSchema,
    summary="Update a session",
    description="Update the title of a chat session.",
)
async def update_session(
    session_id: str,
    update: HistoryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a session's title."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if update.title is not None:
        session.title = update.title
    db.commit()
    db.refresh(session)

    msg_count = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.session_id == session.id
    ).scalar() or 0

    return ChatSessionSchema(
        session_id=session.id,
        title=session.title,
        message_count=msg_count,
        last_message_at=session.updated_at,
        created_at=session.created_at,
    )


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a chat session",
    description="Delete a chat session and all its messages.",
)
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a session and cascade-delete all its messages."""
    deleted = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"message": f"Session {session_id} deleted."}


@router.delete(
    "/sessions",
    summary="Clear all sessions",
    description="Delete all chat sessions for the current user.",
)
async def clear_all_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all sessions for the current user."""
    db.query(ChatSession).filter(ChatSession.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All sessions cleared."}


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY HISTORY ENDPOINTS (kept for backwards compat)
# ═══════════════════════════════════════════════════════════════════════════════


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
    response_model=ChatSessionListResponse,
    summary="Get chat history",
    description="Retrieve the list of chat sessions (grouped conversations).",
)
async def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all sessions as the history — delegates to list_sessions."""
    return await list_sessions(db=db, current_user=current_user)


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
    # Delete sessions (cascades to messages)
    db.query(ChatSession).filter(ChatSession.user_id == current_user.id).delete()
    # Also clean legacy
    db.query(QueryHistory).filter(QueryHistory.user_id == current_user.id).delete()
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
