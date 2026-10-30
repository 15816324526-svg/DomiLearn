from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class PdfMetadata:
    page_count: int
    size_bytes: int
    sha256: str


class PdfValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_staged_pdf(
    path: Path,
    original_filename: str,
    max_bytes: int,
    *,
    known_sha256: str | None = None,
) -> PdfMetadata:
    if Path(original_filename).suffix.lower() != ".pdf":
        raise PdfValidationError("INVALID_PDF", "请选择 PDF 文件")
    size = path.stat().st_size
    if size == 0:
        raise PdfValidationError("INVALID_PDF", "PDF 文件为空")
    if size > max_bytes:
        raise PdfValidationError("PDF_TOO_LARGE", "PDF 文件不能超过 500 MB")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise PdfValidationError("INVALID_PDF", "文件不是有效的 PDF")
    try:
        reader = PdfReader(path)
        page_count = len(reader.pages)
    except Exception as exc:
        raise PdfValidationError("INVALID_PDF", "PDF 已损坏或无法读取") from exc
    if page_count < 1:
        raise PdfValidationError("INVALID_PDF", "PDF 中没有可读取的页面")
    sha256 = known_sha256 or _sha256(path)
    return PdfMetadata(page_count=page_count, size_bytes=size, sha256=sha256)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

