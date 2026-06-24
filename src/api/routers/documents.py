"""
Documents Router - Handles document upload and management endpoints
Phase 5B.7 - Triggers RAG pipeline ingestion on upload.
"""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session
import re

from ..core.config import settings
from ..core.limiter import limiter
from ..models.schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentSchema,
    DocumentUploadResponse,
)
from ..services.rag_engine import get_pipeline
from ..db.models import DocumentAccess, get_db
from ..db.dependencies import get_current_user, require_hr_admin
from ..db.models import User
import re

logger = logging.getLogger("securehall-rag.documents")
router = APIRouter()

# In-memory document store
_documents: dict[str, DocumentSchema] = {}

ACCESS_LEVELS = ("all", "hr", "admin", "employee")
ROLE_ACCESS_MAP = {
    "admin": {"all", "hr", "admin"},  # Specifically excludes "employee" docs
    "hr": {"all", "hr", "employee"},
    "employee": {"all", "employee"},
}


def get_accessible_doc_ids(db: Session, user_role: str) -> Optional[list[str]]:
    """
    Return a list of doc_ids the user may access, or None if all are accessible.
    None means "no restriction" (e.g. admin without any access-tagged documents).
    """
    allowed_levels = ROLE_ACCESS_MAP.get(user_role, {"all"})
    # If admin has access to everything, we still filter so restricted docs
    # remain hidden from lower-privileged roles.
    rows = db.query(DocumentAccess).all()
    if not rows:
        return None  # no access tags set — unrestricted
    return [r.document_id for r in rows if r.access_level in allowed_levels]


def _sync_documents_from_db(db: Session):
    """Repopulate the in-memory _documents dict from persistent database and disk state."""
    global _documents
    
    # Query all document access records
    rows = db.query(DocumentAccess).all()
    upload_dir = _get_upload_dir()
    pipeline = get_pipeline()
    
    for row in rows:
        if row.document_id in _documents:
            continue
            
        # Sanitize filename to find the file on disk
        safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', row.filename or "unknown")
        safe_filename = re.sub(r'\.{2,}', '.', safe_filename).lstrip('.')
        file_path = upload_dir / f"{row.document_id}_{safe_filename}"
        
        if not file_path.exists():
            # Check any file starting with doc_id_
            found_paths = list(upload_dir.glob(f"{row.document_id}_*"))
            if found_paths:
                file_path = found_paths[0]
            else:
                continue
                
        # Calculate chunk count from pipeline
        chunk_count = 0
        status = "ready"
        if pipeline:
            prefix = f"{file_path.stem}_"
            chunk_count = sum(1 for cid in pipeline.chunk_id_to_text.keys() if cid.startswith(prefix))
            if chunk_count == 0:
                status = "processing"
                
        # Populate _documents
        _documents[row.document_id] = DocumentSchema(
            doc_id=row.document_id,
            filename=row.filename,
            file_size_bytes=file_path.stat().st_size if file_path.exists() else 0,
            file_type=Path(row.filename).suffix.lower(),
            upload_timestamp=row.created_at or datetime.utcnow(),
            chunk_count=chunk_count,
            status=status,
        )


def _get_upload_dir() -> Path:
    """Ensure and return the upload directory path."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _ingest_document_background(doc_id: str, file_path: str):
    """
    Background task: ingest the uploaded file into the RAG pipeline.
    Updates document status in _documents when done.
    """
    pipeline = get_pipeline()
    if pipeline is None:
        logger.warning(f"RAG pipeline not available; skipping ingestion for {doc_id}")
        if doc_id in _documents:
            _documents[doc_id] = _documents[doc_id].model_copy(
                update={"status": "error"}
            )
        return

    try:
        logger.info(f"Starting ingestion for doc_id={doc_id}, path={file_path}")
        chunk_count = pipeline.ingest_documents([file_path])
        if doc_id in _documents:
            _documents[doc_id] = _documents[doc_id].model_copy(
                update={"status": "ready", "chunk_count": chunk_count}
            )
        logger.info(f"Ingestion complete for {doc_id}: {chunk_count} chunks")

        # Persist indices to disk so documents survive server restarts
        try:
            pipeline.persist()
        except Exception as persist_exc:
            logger.warning(f"Index persistence failed (non-fatal): {persist_exc}")
    except Exception as exc:
        logger.error(f"Ingestion failed for {doc_id}: {exc}")
        if doc_id in _documents:
            _documents[doc_id] = _documents[doc_id].model_copy(
                update={"status": "error"}
            )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a document",
    description=(
        "Upload a PDF, DOCX, TXT, or MD file for processing. "
        f"The document will be parsed, chunked, and indexed for Q&A in the background. "
        "Maximum file size is configurable via the MAX_UPLOAD_SIZE_MB environment variable."
    ),
    responses={
        400: {"description": "Invalid file type or file too large"},
        500: {"description": "Upload processing failed"},
    },
)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The document file to upload."),
    access_level: str = Form(
        default="all", description="Who can access: all | hr | admin"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Handle document file upload and trigger background ingestion.

    1. Validates file type and size
    2. Saves file to disk
    3. Registers document metadata (status=processing)
    4. Triggers async ingestion pipeline in the background
    """
    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{file_ext}'. "
                f"Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            ),
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size (use computed property from config)
    if file_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File too large ({file_size / 1_048_576:.1f} MB). "
                f"Maximum allowed: {settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        )

    # Generate document ID and save
    doc_id = str(uuid.uuid4())[:12]
    upload_dir = _get_upload_dir()
    
    # Sanitize filename to prevent path traversal
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename or "unknown")
    # Collapse consecutive dots (prevents ".." traversal) and strip leading dots
    safe_filename = re.sub(r'\.{2,}', '.', safe_filename).lstrip('.')
    if not safe_filename:
        safe_filename = "unknown"
    save_path = upload_dir / f"{doc_id}_{safe_filename}"

    try:
        with open(save_path, "wb") as f:
            f.write(content)
    except OSError as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    # Validate access_level
    if access_level not in ACCESS_LEVELS:
        access_level = current_user.role
        
    # Only admin/hr can tag as restricted (admin/hr). Employees are forced to 'employee'
    if current_user.role not in ("admin", "hr"):
        access_level = "employee"
    elif access_level == "all" and current_user.role == "employee":
        access_level = "employee"

    # Register document metadata (status=processing until ingestion finishes)
    doc_meta = DocumentSchema(
        doc_id=doc_id,
        filename=file.filename or "unknown",
        file_size_bytes=file_size,
        file_type=file_ext,
        upload_timestamp=datetime.utcnow(),
        chunk_count=0,
        status="processing",
    )
    _documents[doc_id] = doc_meta

    # Persist access tag to DB
    try:
        da = DocumentAccess(
            document_id=doc_id,
            filename=file.filename or "unknown",
            access_level=access_level,
            uploaded_by=current_user.id if current_user else None,
        )
        db.add(da)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not save DocumentAccess record: {e}")

    logger.info(
        f"Document saved: {file.filename} ({file_size / 1024:.1f} KB) → {doc_id} [access={access_level}]"
    )

    # Kick off background ingestion
    background_tasks.add_task(_ingest_document_background, doc_id, str(save_path))

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=file.filename or "unknown",
        file_size_bytes=file_size,
        status="processing",
        message=f"Document '{file.filename}' uploaded successfully. Indexing in progress...",
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="Retrieve a list of all uploaded documents with their metadata and ingestion status.",
)
async def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return documents visible to the current user based on their role."""
    _sync_documents_from_db(db)
    user_role = current_user.role
    accessible = get_accessible_doc_ids(db, user_role)
    docs = [
        d for d in _documents.values() if accessible is None or d.doc_id in accessible
    ]
    return DocumentListResponse(
        documents=docs,
        total_count=len(docs),
    )


@router.get(
    "/{doc_id}",
    response_model=DocumentSchema,
    summary="Get document status",
    description="Get metadata and ingestion status for a single document.",
    responses={404: {"description": "Document not found"}},
)
async def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single document by ID — enforces access control."""
    _sync_documents_from_db(db)
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    user_role = current_user.role
    accessible = get_accessible_doc_ids(db, user_role)
    if accessible is not None and doc_id not in accessible:
        raise HTTPException(status_code=403, detail="Access denied to this document.")
    return _documents[doc_id]


@router.delete(
    "/{doc_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document",
    description="Remove a document and its processed data from the system.",
    responses={404: {"description": "Document not found"}},
)
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(require_hr_admin),
):
    """Delete a document (HR/Admin only)."""
    _sync_documents_from_db(db)
    if doc_id not in _documents:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")

    doc = _documents.pop(doc_id)

    # 1. Clean up from RAG pipeline index
    pipeline = get_pipeline()
    if pipeline:
        try:
            pipeline.delete_document(doc_id)
        except Exception as e:
            logger.warning(f"Failed to delete document {doc_id} from RAG pipeline: {e}")

    # 2. Delete access permissions from DB table
    try:
        db.query(DocumentAccess).filter(DocumentAccess.document_id == doc_id).delete()
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to delete DocumentAccess record for {doc_id}: {e}")

    # 3. Clean up file from disk
    upload_dir = _get_upload_dir()
    for file_path in upload_dir.glob(f"{doc_id}_*"):
        try:
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
        except OSError as e:
            logger.warning(f"Could not delete file {file_path}: {e}")

    logger.info(f"Document deleted: {doc.filename} ({doc_id})")

    return DocumentDeleteResponse(
        doc_id=doc_id,
        filename=doc.filename,
        message=f"Document '{doc.filename}' deleted successfully.",
    )
