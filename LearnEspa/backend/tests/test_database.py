import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.models import ImportStatus, SourceFile, Textbook


def test_schema_creates_fixed_textbook(session_factory):
    with session_factory() as session:
        textbook = session.scalar(select(Textbook).where(Textbook.id == "modern-spanish-1"))
        assert textbook is not None
        assert textbook.title == "现代西班牙语1"

    tables = set(inspect(session_factory.kw["bind"]).get_table_names())
    assert {"textbooks", "source_files", "import_jobs", "conversion_versions"} <= tables


def test_import_status_includes_superseded():
    assert ImportStatus.SUPERSEDED.value == "superseded"


def test_source_sha256_is_unique(session_factory):
    first = SourceFile(
        id="source-1", sha256="d" * 64, original_filename="a.pdf",
        stored_path="a/source.pdf", size_bytes=1, page_count=1,
    )
    second = SourceFile(
        id="source-2", sha256="d" * 64, original_filename="b.pdf",
        stored_path="b/source.pdf", size_bytes=1, page_count=1,
    )
    with pytest.raises(IntegrityError), session_factory.begin() as session:
        session.add_all([first, second])

