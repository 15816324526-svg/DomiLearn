from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.textbook import utcnow


class VocabularySession(Base):
    __tablename__ = "vocabulary_sessions"
    __table_args__ = (UniqueConstraint("lesson_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default="choice")
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class VocabularyAttempt(Base):
    __tablename__ = "vocabulary_attempts"
    __table_args__ = (UniqueConstraint("session_id", "request_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("vocabulary_sessions.id"), nullable=False, index=True)
    word_id: Mapped[str] = mapped_column(ForeignKey("vocabulary_entries.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    submitted_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
