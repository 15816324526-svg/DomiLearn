from pathlib import Path

import pytest

from app.models import ImportStatus
from app.services.import_service import ImportService, ServiceError
from app.services.pdf_validation import PdfMetadata
from app.services.source_storage import StoredSource


def register_source(service: ImportService, storage_root: Path):
    path = storage_root / "textbooks/modern-spanish-1/originals/hash/source.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"pdf")
    return service.register_source(
        StoredSource(path, "改名教材.pdf", 3, "a" * 64, False),
        PdfMetadata(305, 3, "a" * 64),
    )


def test_only_one_active_job(session_factory, test_settings):
    service = ImportService(session_factory, test_settings.storage_root)
    source = register_source(service, test_settings.storage_root)
    first = service.create_import(source.id, "改名教材.pdf")
    assert first.status == ImportStatus.QUEUED
    with pytest.raises(ServiceError) as error:
        service.create_import(source.id, "another.pdf")
    assert error.value.code == "ACTIVE_JOB_EXISTS"


def test_retry_supersedes_awaiting_job(session_factory, test_settings):
    service = ImportService(session_factory, test_settings.storage_root)
    source = register_source(service, test_settings.storage_root)
    first = service.create_import(source.id, "改名教材.pdf")
    with session_factory.begin() as session:
        row = session.get(type(first), first.id)
        row.status = ImportStatus.AWAITING_CONFIRMATION
    retried = service.retry(first.id)
    with session_factory() as session:
        old = session.get(type(first), first.id)
        assert old.status == ImportStatus.SUPERSEDED
        assert old.superseded_by_job_id == retried.id

