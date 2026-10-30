from app.models import ImportStatus
from app.services.import_service import ImportService
from app.services.job_recovery import recover_interrupted_jobs
from app.services.pdf_validation import PdfMetadata
from app.services.source_storage import StoredSource


def test_recovery_marks_active_jobs_failed_and_is_idempotent(session_factory, test_settings) -> None:
    service = ImportService(session_factory, test_settings.storage_root)
    source_path = test_settings.storage_root / "textbooks/modern-spanish-1/originals/hash/source.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"pdf")
    source = service.register_source(
        StoredSource(source_path, "book.pdf", 3, "c" * 64, False),
        PdfMetadata(2, 3, "c" * 64),
    )
    job = service.create_import(source.id, "book.pdf")

    with session_factory.begin() as session:
        assert recover_interrupted_jobs(session) == 1
    state = service.get_job(job.id)
    assert state.status == ImportStatus.FAILED
    assert state.error_code == "INTERRUPTED"

    with session_factory.begin() as session:
        assert recover_interrupted_jobs(session) == 0
