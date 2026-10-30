from app.converters.fake import FakeConverter
from app.models import ConversionVersion, ImportStatus, Lesson
from app.services.import_service import ImportService
from app.services.fake_lesson_extraction import fake_first_lesson
from app.services.book_extraction import ExtractedLesson
from app.services.lesson_extraction import LessonExtractionError
from app.services.lesson_extraction import PassageRecord, VocabularyRecord
from app.services.pdf_validation import PdfMetadata
from app.services.source_storage import StoredSource
from app.workers.import_worker import ImportWorker


def test_worker_creates_awaiting_version(session_factory, test_settings):
    service = ImportService(session_factory, test_settings.storage_root)
    source_path = test_settings.storage_root / "textbooks/modern-spanish-1/originals/hash/source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"pdf")
    source = service.register_source(
        StoredSource(source_path, "book.pdf", 3, "b" * 64, False),
        PdfMetadata(2, 3, "b" * 64),
    )
    job = service.create_import(source.id, "book.pdf")
    worker = ImportWorker(session_factory, test_settings.storage_root, FakeConverter(), 60, lesson_extractor=fake_first_lesson)
    assert worker.run_once() is True
    state = service.get_job(job.id)
    assert state.status == ImportStatus.AWAITING_CONFIRMATION
    assert state.processed_pages == 2
    with session_factory() as session:
        assert session.query(ConversionVersion).filter_by(job_id=job.id).one().page_count == 2
        assert session.query(Lesson).one().lesson_number == 1


def test_classification_failure_does_not_publish_version(session_factory, test_settings):
    service = ImportService(session_factory, test_settings.storage_root)
    source_path = test_settings.storage_root / "textbooks/modern-spanish-1/originals/hash/source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"pdf")
    source = service.register_source(
        StoredSource(source_path, "book.pdf", 3, "f" * 64, False),
        PdfMetadata(2, 3, "f" * 64),
    )
    job = service.create_import(source.id, "book.pdf")

    def fail(_source, _json):
        raise LessonExtractionError("未找到第一课")

    worker = ImportWorker(
        session_factory, test_settings.storage_root, FakeConverter(), 60,
        lesson_extractor=fail,
    )
    assert worker.run_once() is True
    state = service.get_job(job.id)
    assert state.status == ImportStatus.FAILED
    assert state.error_code == "LESSON_EXTRACTION_FAILED"
    with session_factory() as session:
        assert session.query(ConversionVersion).count() == 0
        assert session.query(Lesson).count() == 0


def test_worker_publishes_only_after_sixteen_lessons_are_classified(session_factory, test_settings):
    service = ImportService(session_factory, test_settings.storage_root)
    source_path = test_settings.storage_root / "textbooks/modern-spanish-1/originals/all/source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"pdf")
    source = service.register_source(StoredSource(source_path, "book.pdf", 3, "c" * 64, False), PdfMetadata(2, 3, "c" * 64))
    job = service.create_import(source.id, "book.pdf")
    lessons = tuple(ExtractedLesson(
        number, f"第{number}课", number, number,
        (PassageRecord("I. Texto", "Hola.", number, number, "Hola."),),
        tuple(VocabularyRecord(f"palabra{index}", None, "单词", number, "raw") for index in range(10)),
    ) for number in range(1, 17))
    worker = ImportWorker(session_factory, test_settings.storage_root, FakeConverter(), 60, lesson_extractor=lambda *_: lessons)
    assert worker.run_once() is True
    assert service.get_job(job.id).status == ImportStatus.AWAITING_CONFIRMATION
    with session_factory() as db:
        assert db.query(Lesson).count() == 16

