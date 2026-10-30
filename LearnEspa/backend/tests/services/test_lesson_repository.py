from dataclasses import replace

import pytest
from sqlalchemy import func, select

from app.converters.fake import FakeConverter
from app.models import ConversionVersion, Lesson, Passage, Textbook, VocabularyEntry
from app.services.fake_lesson_extraction import fake_first_lesson
from app.services.import_service import ImportService
from app.services.book_extraction import ExtractedLesson
from app.services.lesson_extraction import PassageRecord, VocabularyRecord
from app.services.lesson_repository import save_book, save_first_lesson
from app.services.pdf_validation import PdfMetadata
from app.services.source_storage import StoredSource
from app.workers.import_worker import ImportWorker


def test_repeated_save_does_not_duplicate_classification(session_factory, test_settings) -> None:
    service = ImportService(session_factory, test_settings.storage_root)
    source_path = test_settings.storage_root / "textbooks/modern-spanish-1/originals/hash/source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"pdf")
    source = service.register_source(
        StoredSource(source_path, "book.pdf", 3, "e" * 64, False),
        PdfMetadata(2, 3, "e" * 64),
    )
    job = service.create_import(source.id, "book.pdf")
    worker = ImportWorker(
        session_factory, test_settings.storage_root, FakeConverter(), 60,
        lesson_extractor=fake_first_lesson,
    )
    worker.run_once()
    with session_factory.begin() as session:
        version = session.scalar(select(ConversionVersion).where(ConversionVersion.job_id == job.id))
        assert version is not None
        save_first_lesson(session, version.id, fake_first_lesson(source_path, source_path))

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Lesson)) == 1
        assert session.scalar(select(func.count()).select_from(VocabularyEntry)) == 2
        assert session.scalar(select(func.count()).select_from(Passage)) == 2
        assert [word.source_page for word in session.scalars(select(VocabularyEntry).order_by(VocabularyEntry.ordinal))] == [1, 2]

    service.confirm(job.id)
    second_job = service.retry(job.id)
    worker.run_once()
    with session_factory() as session:
        textbook = session.get(Textbook, "modern-spanish-1")
        assert textbook is not None
        assert textbook.current_version_id == version.id
        lessons = session.scalars(select(Lesson).order_by(Lesson.created_at)).all()
        assert len(lessons) == 2
        assert {lesson.conversion_version_id for lesson in lessons} == {
            version.id,
            session.scalar(select(ConversionVersion.id).where(ConversionVersion.job_id == second_job.id)),
        }
        assert session.scalar(select(func.count()).select_from(VocabularyEntry)) == 4


def test_book_backfill_keeps_first_lesson_ids_and_rolls_back_invalid_book(session_factory, test_settings) -> None:
    importer = ImportService(session_factory, test_settings.storage_root)
    source_path = test_settings.storage_root / "textbooks/modern-spanish-1/originals/hash/source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"pdf")
    source = importer.register_source(StoredSource(source_path, "book.pdf", 3, "a" * 64, False), PdfMetadata(2, 3, "a" * 64))
    job = importer.create_import(source.id, "book.pdf")
    ImportWorker(session_factory, test_settings.storage_root, FakeConverter(), 60, lesson_extractor=fake_first_lesson).run_once()
    with session_factory() as db:
        version = db.scalar(select(ConversionVersion).where(ConversionVersion.job_id == job.id))
        first = db.scalar(select(Lesson).where(Lesson.lesson_number == 1))
        assert version is not None and first is not None
        version_id, first_id = version.id, first.id
    lessons = tuple(ExtractedLesson(
        number, f"第{number}课", number, number + 1,
        (PassageRecord("I. Texto", "Hola. Buen día.", number, number, "Hola. Buen día."),),
        tuple(VocabularyRecord(f"palabra{index}", None, "单词", number, "raw") for index in range(10)),
    ) for number in range(1, 17))
    with pytest.raises(ValueError, match="第16课"):
        with session_factory.begin() as db:
            save_book(db, version_id, lessons[:-1] + (replace(lessons[-1], issues=("OCR不完整",)),))
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Lesson)) == 1
    with session_factory.begin() as db:
        save_book(db, version_id, lessons)
        save_book(db, version_id, lessons)
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Lesson)) == 16
        assert db.get(Lesson, first_id) is not None
        assert db.scalar(select(func.count()).select_from(VocabularyEntry).where(VocabularyEntry.lesson_id == first_id)) == 2
