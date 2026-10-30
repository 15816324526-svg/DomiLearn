from pathlib import Path

import pytest

from app.services.pdf_validation import PdfMetadata, PdfValidationError
from app.services.source_storage import SourceStorage, StagedUpload


def test_identical_uploads_share_one_hash_path_and_keep_display_names(
    test_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = SourceStorage(test_settings.storage_root, test_settings.max_pdf_bytes)
    monkeypatch.setattr(storage, "ensure_conversion_space", lambda _size: None)
    digest = "a" * 64
    metadata = PdfMetadata(page_count=2, size_bytes=3, sha256=digest)

    first_path = test_settings.storage_root / ".tmp" / "uploads" / "first.part"
    second_path = test_settings.storage_root / ".tmp" / "uploads" / "second.part"
    first_path.write_bytes(b"pdf")
    second_path.write_bytes(b"pdf")
    first = storage.finalize(StagedUpload(first_path, "原名.pdf", 3, digest), metadata)
    second = storage.finalize(StagedUpload(second_path, "改名.pdf", 3, digest), metadata)

    assert first.path == second.path
    assert first.reused is False
    assert second.reused is True
    assert first.display_filename == "原名.pdf"
    assert second.display_filename == "改名.pdf"
    assert second_path.exists() is False
    assert "改名" not in first.path.as_posix()


def test_insufficient_disk_space_has_stable_error(test_settings, monkeypatch) -> None:
    storage = SourceStorage(test_settings.storage_root, test_settings.max_pdf_bytes)
    disk = type("Disk", (), {"total": 10, "used": 9, "free": 1})()
    monkeypatch.setattr("app.services.source_storage.shutil.disk_usage", lambda _path: disk)

    with pytest.raises(PdfValidationError) as error:
        storage.ensure_conversion_space(100)
    assert error.value.code == "INSUFFICIENT_DISK"
