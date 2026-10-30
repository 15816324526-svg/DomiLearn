from __future__ import annotations

import importlib.metadata
import json
import sys
import time
from pathlib import Path


def run(request_file: Path) -> None:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    payload = json.loads(request_file.read_text(encoding="utf-8"))
    source = Path(payload["source_path"])
    output_dir = Path(payload["output_dir"])
    started = time.perf_counter()

    options = PdfPipelineOptions()
    options.do_ocr = True
    options.do_table_structure = True
    options.enable_remote_services = False
    options.do_picture_description = False
    options.ocr_options = RapidOcrOptions(lang=["ch"], mode=OcrMode.FULL_PAGE)
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    result = converter.convert(source)
    result.document.save_as_markdown(output_dir / "document.md")
    result.document.save_as_json(output_dir / "document.json")
    duration = time.perf_counter() - started
    report = {
        "converter": "docling",
        "docling_version": importlib.metadata.version("docling"),
        "duration_seconds": duration,
        "page_count": len(result.document.pages),
        "configuration": "docling-cpu-rapidocr-ch-v1",
        "remote_services": False,
        "llm_used": False,
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "result.json").write_text(
        json.dumps(
            {
                "duration_seconds": duration,
                "docling_version": report["docling_version"],
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]))

