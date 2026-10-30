from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.textbook import utcnow


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("conversion_version_id", "lesson_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversion_version_id: Mapped[str] = mapped_column(
        ForeignKey("conversion_versions.id"), index=True, nullable=False
    )
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    vocabulary: Mapped[list[VocabularyEntry]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", order_by="VocabularyEntry.ordinal"
    )
    passages: Mapped[list[Passage]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", order_by="Passage.ordinal"
    )


class VocabularyEntry(Base):
    __tablename__ = "vocabulary_entries"
    __table_args__ = (UniqueConstraint("lesson_id", "ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    headword: Mapped[str] = mapped_column(String(300), nullable=False)
    part_of_speech: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_ocr: Mapped[str] = mapped_column(Text, nullable=False)

    lesson: Mapped[Lesson] = relationship(back_populates="vocabulary")


class Passage(Base):
    __tablename__ = "passages"
    __table_args__ = (UniqueConstraint("lesson_id", "ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    source_page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_ocr: Mapped[str] = mapped_column(Text, nullable=False)

    lesson: Mapped[Lesson] = relationship(back_populates="passages")
