from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ConversionRequest:
    job_id: str
    source_path: Path
    work_dir: Path
    expected_pages: int
    timeout_seconds: int


@dataclass(frozen=True)
class ConversionResult:
    markdown_path: Path
    json_path: Path
    report_path: Path
    page_count: int
    duration_seconds: float
    warnings: list[str]
    converter_name: str
    converter_version: str
    configuration_version: str = "docling-cpu-rapidocr-ch-v1"


class ConversionError(RuntimeError):
    code = "CONVERSION_FAILED"


class ConversionFailed(ConversionError):
    pass


class ConversionTimedOut(ConversionError):
    code = "CONVERSION_TIMEOUT"


class InvalidArtifacts(ConversionError):
    code = "INVALID_ARTIFACTS"


class PdfConverter(Protocol):
    def convert(self, request: ConversionRequest) -> ConversionResult: ...

