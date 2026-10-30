from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.converters.base import ConversionRequest
from app.converters.docling import DoclingConverter
from scripts.build_docling_sample import build_sample


@pytest.mark.docling
def test_real_docling_converts_five_scanned_pages(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[3] / "TextBook" / "现代西班牙语1.pdf"
    if not source.exists():
        pytest.skip(f"本地教材不存在：{source}")

    sample = build_sample(source, tmp_path / "sample.pdf")
    result_dir = tmp_path / "conversion"
    result = DoclingConverter().convert(ConversionRequest(
        job_id="sample", source_path=sample, work_dir=result_dir,
        expected_pages=5, timeout_seconds=15 * 60,
    ))
    assert result.page_count == 5
    assert (result_dir / "document.md").stat().st_size > 0
    document = json.loads((result_dir / "document.json").read_text(encoding="utf-8"))
    assert len(document["pages"]) == 5
    report = json.loads((result_dir / "report.json").read_text(encoding="utf-8"))
    assert report["converter"] == "docling"
    assert report["remote_services"] is False
    assert report["llm_used"] is False
