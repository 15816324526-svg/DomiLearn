from __future__ import annotations

import json
import time

from app.converters.base import ConversionRequest, ConversionResult
from app.services.artifact_validation import validate_artifacts


class FakeConverter:
    def convert(self, request: ConversionRequest) -> ConversionResult:
        started = time.perf_counter()
        request.work_dir.mkdir(parents=True, exist_ok=True)
        markdown = request.work_dir / "document.md"
        document_json = request.work_dir / "document.json"
        report = request.work_dir / "report.json"
        markdown.write_text("# 现代西班牙语1\n\n测试转换结果。\n", encoding="utf-8")
        document_json.write_text(
            json.dumps({"pages": {str(i): {} for i in range(1, request.expected_pages + 1)}}, ensure_ascii=False),
            encoding="utf-8",
        )
        page_count = validate_artifacts(markdown, document_json, request.expected_pages)
        duration = time.perf_counter() - started
        report.write_text(
            json.dumps({"converter": "fake", "page_count": page_count, "duration_seconds": duration}),
            encoding="utf-8",
        )
        return ConversionResult(
            markdown, document_json, report, page_count, duration, [], "fake", "1"
        )

