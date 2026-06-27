"""
Phase 7.1 — Database Models
SQLAlchemy ORM models for Users, Roles, Sessions, Audit Logs.
Uses SQLite by default (database.db in project root).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
    Float,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

# ── Database path ─────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent.parent.parent / "database.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


# Enable WAL mode for SQLite (better concurrent read performance)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base ──────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── User ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum("admin", "hr", "employee", name="user_role"),
        nullable=False,
        default="employee",
    )
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True, index=True)
    reset_password_token = Column(String(255), nullable=True, index=True)
    reset_password_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    feedback = relationship(
        "QueryFeedback", back_populates="user", cascade="all, delete-orphan"
    )
    query_history = relationship(
        "QueryHistory", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


# ── Chat Session ──────────────────────────────────────────────────────────────
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.id[:8]} user={self.user_id[:8]}>"


# ── Chat Message ──────────────────────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(Enum("user", "assistant", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(Integer, nullable=True)  # 0-100 for assistant messages
    citations_json = Column(Text, nullable=True, default="[]")
    sources_json = Column(Text, nullable=True, default="[]")
    hallucination_risk = Column(String(50), nullable=True, default="unknown")
    uncertainty_tier = Column(String(50), nullable=True)
    latency_ms = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")


# ── Audit Log ─────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    query = Column(Text, nullable=False)
    answer_preview = Column(String(500), nullable=True)
    confidence = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    blocked = Column(Boolean, default=False, nullable=False)
    block_reason = Column(String(255), nullable=True)
    sources_count = Column(Integer, default=0, nullable=False)
    eval_mode = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.id[:8]} blocked={self.blocked}>"


# ── Query Feedback ────────────────────────────────────────────────────────────
class QueryFeedback(Base):
    __tablename__ = "query_feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(
        String(36),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating = Column(Enum("up", "down", name="feedback_rating"), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="feedback")


# ── Document Access Tag ───────────────────────────────────────────────────────
class DocumentAccess(Base):
    __tablename__ = "document_access"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(255), nullable=False, unique=True, index=True)
    filename = Column(String(500), nullable=False)
    access_level = Column(
        Enum("all", "hr", "admin", "employee", name="access_level"), nullable=False, default="employee"
    )
    uploaded_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ── Query History (Persistent Chat History) ───────────────────────────────────
class QueryHistory(Base):
    """Persists Q&A history so it survives server restarts.

    Replaces the old in-memory _history / _answers dicts in query.py.
    Citations and sources are serialised as JSON text columns.
    """
    __tablename__ = "query_history"

    answer_id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    citations_json = Column(Text, nullable=False, default="[]")
    sources_json = Column(Text, nullable=False, default="[]")
    confidence = Column(Integer, nullable=False, default=0)  # 0-100
    hallucination_risk = Column(String(50), nullable=False, default="unknown")
    uncertainty_tier = Column(String(50), nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    is_pinned = Column(Boolean, default=False, nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="query_history")

    def __repr__(self) -> str:
        return f"<QueryHistory {self.answer_id} user={self.user_id[:8]}>"


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    context = Column(Text, nullable=False)
    faithfulness_score = Column(Float, nullable=True)
    answer_relevance_score = Column(Float, nullable=True)
    context_recall_score = Column(Float, nullable=True)
    nli_faithfulness_score = Column(Float, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(36), nullable=True)


# ── DB Initialisation ────────────────────────────────────────────────────────
def init_db() -> None:
    """Create all tables, migrate schemas if needed, and seed a default admin user."""
    # Force reload/creation of tables
    Base.metadata.create_all(bind=engine)

    # Migrate chat_messages table (add columns added in session history Phase 10)
    with engine.begin() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info(chat_messages)").fetchall()
        existing_cols = {row[1] for row in result}
        
        missing_columns = {
            "citations_json": "TEXT NULL",
            "sources_json": "TEXT NULL",
            "hallucination_risk": "VARCHAR(50) NULL",
            "uncertainty_tier": "VARCHAR(50) NULL",
            "latency_ms": "INTEGER NULL DEFAULT 0"
        }
        
        for col_name, col_type in missing_columns.items():
            if col_name not in existing_cols:
                try:
                    conn.exec_driver_sql(f"ALTER TABLE chat_messages ADD COLUMN {col_name} {col_type}")
                    import logging
                    logging.getLogger("securehall-rag").info(
                        f"Migration: Added missing column '{col_name}' to chat_messages table."
                    )
                except Exception as alter_err:
                    import logging
                    logging.getLogger("securehall-rag").error(
                        f"Migration failed to add column '{col_name}': {alter_err}"
                    )

        # Migrate query_history table to add uncertainty_tier
        qh_result = conn.exec_driver_sql("PRAGMA table_info(query_history)").fetchall()
        qh_cols = {row[1] for row in qh_result}
        if "uncertainty_tier" not in qh_cols:
            try:
                conn.exec_driver_sql("ALTER TABLE query_history ADD COLUMN uncertainty_tier VARCHAR(50) NULL")
                import logging
                logging.getLogger("securehall-rag").info(
                    "Migration: Added missing column 'uncertainty_tier' to query_history table."
                )
            except Exception as alter_err:
                import logging
                logging.getLogger("securehall-rag").error(
                    f"Migration failed to add column 'uncertainty_tier': {alter_err}"
                )

        # Migrate evaluation_metrics table to add nli_faithfulness_score
        eval_result = conn.exec_driver_sql("PRAGMA table_info(evaluation_metrics)").fetchall()
        eval_cols = {row[1] for row in eval_result}
        if "nli_faithfulness_score" not in eval_cols:
            try:
                conn.exec_driver_sql("ALTER TABLE evaluation_metrics ADD COLUMN nli_faithfulness_score FLOAT NULL")
                import logging
                logging.getLogger("securehall-rag").info(
                    "Migration: Added missing column 'nli_faithfulness_score' to evaluation_metrics table."
                )
            except Exception as alter_err:
                import logging
                logging.getLogger("securehall-rag").error(
                    f"Migration failed to add column 'nli_faithfulness_score': {alter_err}"
                )

    # Seed default admin
    with SessionLocal() as db:
        from .auth_service import hash_password

        existing = db.query(User).filter(User.role == "admin").first()
        if not existing:
            admin = User(
                email="admin@securehall.local",
                username="admin",
                full_name="System Administrator",
                hashed_password=hash_password("Admin@123"),
                role="admin",
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            db.commit()
            import logging

            logging.getLogger("securehall-rag").info(
                "🔐 Default admin created — email: admin@securehall.local  password: Admin@123"
            )


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """Yield a database session (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
