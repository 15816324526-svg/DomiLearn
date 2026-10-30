from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.services.pdf_validation import PdfMetadata, PdfValidationError


@dataclass(frozen=True)
class StagedUpload:
    path: Path
    display_filename: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class StoredSource:
    path: Path
    display_filename: str
    size_bytes: int
    sha256: str
    reused: bool


class SourceStorage:
    def __init__(self, storage_root: Path, max_bytes: int) -> None:
        self.storage_root = storage_root
        self.max_bytes = max_bytes

    async def stage_upload(self, upload: UploadFile) -> StagedUpload:
        display_filename = Path(upload.filename or "textbook.pdf").name
        temp_path = self.storage_root / ".tmp" / "uploads" / f"{uuid4()}.part"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        try:
            with temp_path.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise PdfValidationError("PDF_TOO_LARGE", "PDF 文件不能超过 500 MB")
                    digest.update(chunk)
                    output.write(chunk)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        return StagedUpload(temp_path, display_filename, size, digest.hexdigest())

    def ensure_conversion_space(self, size_bytes: int) -> None:
        required = max(2 * 1024**3, size_bytes * 3)
        free = shutil.disk_usage(self.storage_root).free
        if free < required:
            raise PdfValidationError("INSUFFICIENT_DISK", "磁盘空间不足，请释放空间后重试")

    def finalize(self, staged: StagedUpload, metadata: PdfMetadata) -> StoredSource:
        self.ensure_conversion_space(metadata.size_bytes)
        destination = (
            self.storage_root
            / "textbooks"
            / "modern-spanish-1"
            / "originals"
            / metadata.sha256
            / "source.pdf"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        reused = destination.exists()
        if reused:
            staged.path.unlink(missing_ok=True)
        else:
            os.replace(staged.path, destination)
        return StoredSource(
            destination,
            staged.display_filename,
            metadata.size_bytes,
            metadata.sha256,
            reused,
        )

    def cleanup(self, staged: StagedUpload | None) -> None:
        if staged is not None:
            staged.path.unlink(missing_ok=True)

