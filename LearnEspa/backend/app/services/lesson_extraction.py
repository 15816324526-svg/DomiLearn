from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.converters.base import ConversionError


class LessonExtractionError(ConversionError):
    code = "LESSON_EXTRACTION_FAILED"


@dataclass(frozen=True)
class PassageRecord:
    title: str
    content: str
    source_page_start: int
    source_page_end: int
    raw_ocr: str


@dataclass(frozen=True)
class TableRegion:
    page_no: int
    bbox: dict[str, float | str]
    column_starts: tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class VocabularyRecord:
    headword: str
    part_of_speech: str | None
    meaning: str
    source_page: int
    raw_ocr: str


@dataclass(frozen=True)
class LessonStructure:
    page_start: int
    page_end: int
    passages: tuple[PassageRecord, ...]
    tables: tuple[TableRegion, ...]


@dataclass(frozen=True)
class LessonExtraction:
    page_start: int
    page_end: int
    passages: tuple[PassageRecord, ...]
    vocabulary: tuple[VocabularyRecord, ...]


def _page(item: dict[str, Any]) -> int | None:
    provenance = item.get("prov") or []
    return int(provenance[0]["page_no"]) if provenance else None


def _is_text(item: dict[str, Any]) -> bool:
    return item.get("label") == "text" and not item.get("parent", {}).get("$ref", "").startswith("#/pictures/")


def _columns(table: dict[str, Any]) -> tuple[float, float, float, float, float, float]:
    by_column: list[list[float]] = [[] for _ in range(6)]
    for row in table.get("data", {}).get("grid", []):
        for cell in row:
            column = cell.get("start_col_offset_idx")
            box = cell.get("bbox") or {}
            if isinstance(column, int) and 0 <= column < 6 and box.get("l", 0) > 0:
                by_column[column].append(float(box["l"]))
    if any(not values for values in by_column):
        raise LessonExtractionError("第一课词表列无法定位")
    starts = tuple(sorted(values)[len(values) // 2] for values in by_column)
    if any(left >= right for left, right in zip(starts, starts[1:])):
        raise LessonExtractionError("第一课词表列顺序异常")
    return starts  # type: ignore[return-value]


def extract_lesson_structure(document: dict[str, Any]) -> LessonStructure:
    texts = document.get("texts")
    tables = document.get("tables")
    if not isinstance(texts, list) or not isinstance(tables, list):
        raise LessonExtractionError("Docling JSON 缺少文字或表格")

    first_markers = [_page(item) for item in texts if item.get("text", "").strip() == "第一课"]
    second_markers = [_page(item) for item in texts if item.get("text", "").strip() == "第二课"]
    first_markers = [page for page in first_markers if page is not None]
    second_markers = [page for page in second_markers if page is not None]
    if not first_markers or not second_markers:
        raise LessonExtractionError("未找到第一课和第二课的边界")
    start = min(first_markers)
    next_start = min((page for page in second_markers if page > start), default=None)
    if next_start is None:
        raise LessonExtractionError("未找到第二课起始页")

    text_heading_pages = [
        _page(item) for item in texts
        if start <= (_page(item) or 0) < next_start
        and re.search(r"TEXTOS\s*课文|课文\s*TEXTOS", item.get("text", ""), re.I)
    ]
    vocab_heading_pages = [
        _page(item) for item in texts
        if start <= (_page(item) or 0) < next_start
        and "VOCABULARIO" in item.get("text", "").upper()
    ]
    if not text_heading_pages or not vocab_heading_pages:
        raise LessonExtractionError("第一课课文或词表标题缺失")
    text_page = min(text_heading_pages)
    vocab_page = min(vocab_heading_pages)
    if vocab_page < text_page:
        raise LessonExtractionError("第一课板块顺序异常")

    passages: list[PassageRecord] = []
    current_title: str | None = None
    current_page = 0
    content_lines: list[str] = []
    last_page = 0
    for item in texts:
        page = _page(item)
        if page is None or not text_page <= page <= vocab_page:
            continue
        value = item.get("text", "").strip()
        if item.get("label") == "section_header" and re.match(r"^(?:I|II)\.\s*\S", value):
            if current_title and content_lines:
                raw = "\n".join(content_lines)
                passages.append(PassageRecord(current_title, raw, current_page, last_page, raw))
            current_title = re.sub(r"\s+[0O](?:\s+[0O])*$", "", value)
            current_page = page
            last_page = page
            content_lines = []
        elif current_title and "VOCABULARIO" in value.upper():
            break
        elif current_title and _is_text(item) and value:
            content_lines.append(value)
            last_page = page
    if current_title and content_lines:
        raw = "\n".join(content_lines)
        passages.append(PassageRecord(current_title, raw, current_page, last_page, raw))
    if len(passages) != 2:
        raise LessonExtractionError(f"第一课应有两篇课文，实际识别到 {len(passages)} 篇")

    regions: list[TableRegion] = []
    for table in tables:
        page = _page(table)
        if page is not None and vocab_page <= page <= vocab_page + 1 and page < next_start:
            if table.get("data", {}).get("num_cols") == 6:
                regions.append(TableRegion(page, table["prov"][0]["bbox"], _columns(table)))
    if {region.page_no for region in regions} != {vocab_page, vocab_page + 1}:
        raise LessonExtractionError("第一课两页词表未完整识别")
    return LessonStructure(start, next_start - 1, tuple(passages), tuple(regions))


def extract_first_lesson(source_pdf: Path, docling_json: Path) -> LessonExtraction:
    from app.services.vocabulary_ocr import extract_vocabulary

    try:
        document = json.loads(docling_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LessonExtractionError("无法读取 Docling JSON") from exc
    structure = extract_lesson_structure(document)
    vocabulary = extract_vocabulary(source_pdf, list(structure.tables))
    if len(vocabulary) < 20:
        raise LessonExtractionError(f"第一课单词识别过少：{len(vocabulary)} 条")
    return LessonExtraction(structure.page_start, structure.page_end, structure.passages, tuple(vocabulary))
