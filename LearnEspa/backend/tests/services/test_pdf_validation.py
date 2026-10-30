from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.services.pdf_validation import PdfValidationError, validate_staged_pdf


def write_pdf(path: Path, pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as stream:
        writer.write(stream)


def test_valid_pdf_reports_pages_and_hash(tmp_path: Path):
    path = tmp_path / "book.pdf"
    write_pdf(path, 2)
    result = validate_staged_pdf(path, "改过名字.PDF", 10 * 1024 * 1024)
    assert result.page_count == 2
    assert len(result.sha256) == 64


@pytest.mark.parametrize(
    ("filename", "content", "code"),
    [("book.txt", b"%PDF-fake", "INVALID_PDF"), ("book.pdf", b"", "INVALID_PDF"), ("book.pdf", b"hello", "INVALID_PDF")],
)
def test_rejects_invalid_inputs(tmp_path: Path, filename: str, content: bytes, code: str):
    path = tmp_path / "upload.part"
    path.write_bytes(content)
    with pytest.raises(PdfValidationError) as error:
        validate_staged_pdf(path, filename, 1024)
    assert error.value.code == code

