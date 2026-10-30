from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.import_job import ImportJob


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Textbook(Base):
    __tablename__ = "textbooks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    current_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversion_versions.id", use_alter=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    current_version: Mapped[ConversionVersion | None] = relationship(
        foreign_keys=[current_version_id], post_update=True
    )


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConversionVersion(Base):
    __tablename__ = "conversion_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    textbook_id: Mapped[str] = mapped_column(ForeignKey("textbooks.id"), index=True)
    source_file_id: Mapped[str] = mapped_column(ForeignKey("source_files.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("import_jobs.id"), unique=True, index=True)
    display_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    converter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    converter_version: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(100), nullable=False)
    markdown_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    docling_json_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    report_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    log_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

