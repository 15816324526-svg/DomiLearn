from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.textbook import utcnow


class PassageSentence(Base):
    __tablename__ = "passage_sentences"
    __table_args__ = (UniqueConstraint("passage_id", "ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    passage_id: Mapped[str] = mapped_column(ForeignKey("passages.id"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(100))
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    core_pattern: Mapped[str | None] = mapped_column(Text)
    fixed_collocations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    source_line: Mapped[int] = mapped_column(Integer, nullable=False)
    preparation_issue: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImitationPreference(Base):
    __tablename__ = "imitation_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    default_source_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="masked")


class ImitationRound(Base):
    __tablename__ = "imitation_rounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    passage_id: Mapped[str] = mapped_column(ForeignKey("passages.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    background: Mapped[str] = mapped_column(Text, nullable=False)
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    draft: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="masked")
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlannedSentence(Base):
    __tablename__ = "planned_sentences"
    __table_args__ = (UniqueConstraint("round_id", "ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    round_id: Mapped[str] = mapped_column(ForeignKey("imitation_rounds.id"), nullable=False, index=True)
    source_sentence_id: Mapped[str] = mapped_column(ForeignKey("passage_sentences.id"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(100))
    chinese_text: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text)
    expected_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    fixed_collocations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class ImitationAttempt(Base):
    __tablename__ = "imitation_attempts"
    __table_args__ = (UniqueConstraint("round_id", "request_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    round_id: Mapped[str] = mapped_column(ForeignKey("imitation_rounds.id"), nullable=False, index=True)
    planned_sentence_id: Mapped[str] = mapped_column(ForeignKey("planned_sentences.id"), nullable=False)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    submitted_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    hint_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    feedback_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ImitationCallUsage(Base):
    __tablename__ = "imitation_call_usage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    round_id: Mapped[str | None] = mapped_column(ForeignKey("imitation_rounds.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(60), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImitationMemory(Base):
    __tablename__ = "imitation_memory"
    __table_args__ = (UniqueConstraint("round_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    round_id: Mapped[str] = mapped_column(ForeignKey("imitation_rounds.id"), nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImitationReport(Base):
    __tablename__ = "imitation_reports"
    __table_args__ = (UniqueConstraint("round_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    round_id: Mapped[str] = mapped_column(ForeignKey("imitation_rounds.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    summary_json: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
