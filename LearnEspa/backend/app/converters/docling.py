from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.converters.base import (
    ConversionFailed,
    ConversionRequest,
    ConversionResult,
    ConversionTimedOut,
)
from app.services.artifact_validation import validate_artifacts


class DoclingConverter:
    def convert(self, request: ConversionRequest) -> ConversionResult:
        request.work_dir.mkdir(parents=True, exist_ok=True)
        request_file = request.work_dir / "request.json"
        result_file = request.work_dir / "result.json"
        request_file.write_text(
            json.dumps(
                {
                    "source_path": str(request.source_path),
                    "output_dir": str(request.work_dir),
                    "expected_pages": request.expected_pages,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        command = [sys.executable, "-m", "app.converters.docling_runner", str(request_file)]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=request.timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConversionTimedOut("Docling 解析超过两小时") from exc
        (request.work_dir / "child-process.log").write_text(
            f"STDOUT\n{completed.stdout}\nSTDERR\n{completed.stderr}", encoding="utf-8"
        )
        if completed.returncode != 0:
            raise ConversionFailed("Docling 解析失败")
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConversionFailed("Docling 没有返回有效结果") from exc
        markdown = request.work_dir / "document.md"
        document_json = request.work_dir / "document.json"
        report = request.work_dir / "report.json"
        page_count = validate_artifacts(markdown, document_json, request.expected_pages)
        return ConversionResult(
            markdown_path=markdown,
            json_path=document_json,
            report_path=report,
            page_count=page_count,
            duration_seconds=float(payload["duration_seconds"]),
            warnings=list(payload.get("warnings", [])),
            converter_name="docling",
            converter_version=str(payload["docling_version"]),
        )

