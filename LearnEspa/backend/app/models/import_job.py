from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.textbook import utcnow


class ImportStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    textbook_id: Mapped[str] = mapped_column(ForeignKey("textbooks.id"), index=True)
    source_file_id: Mapped[str] = mapped_column(ForeignKey("source_files.id"), index=True)
    status: Mapped[ImportStatus] = mapped_column(Enum(ImportStatus), index=True)
    display_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    log_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    superseded_by_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_jobs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

