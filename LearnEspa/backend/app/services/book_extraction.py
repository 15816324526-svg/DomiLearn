"""Extract the sixteen lessons from the already converted textbook artifact."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.lesson_extraction import (
    LessonExtractionError, PassageRecord, TableRegion, VocabularyRecord, _columns,
)


@dataclass(frozen=True)
class ExtractedLesson:
    lesson_number: int
    title: str
    page_start: int
    page_end: int
    passages: tuple[PassageRecord, ...]
    vocabulary: tuple[VocabularyRecord, ...]
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class BookLessonStructure:
    lesson_number: int
    title: str
    page_start: int
    page_end: int
    passages: tuple[PassageRecord, ...]
    vocabulary_regions: tuple[TableRegion, ...]
    issues: tuple[str, ...] = ()


_TITLE = re.compile(r"^(?:(?:\d{1,2}-\d|\d{2})\s*)?(?:0\s*)?(I{1,3}|Il|1|2)\.\s+\S", re.I)
_MAJOR_SECTION = re.compile(r"FON[ÉE]TICA|GRAM[ÁA]TICA|EJERCICIOS|PALABRAS ADICIONALES|VERBOS\s*IRREGULARES", re.I)
_SOURCE_LABELS = {"text", "list_item", "caption", "section_header"}


def _page(item: dict[str, Any]) -> int | None:
    prov = item.get("prov") or []
    return int(prov[0]["page_no"]) if prov else None


def _bbox(item: dict[str, Any]) -> dict:
    prov = item.get("prov") or []
    return prov[0].get("bbox") or {} if prov else {}


def _top(item: dict[str, Any]) -> float:
    return float(_bbox(item).get("t", 0))


def _left(item: dict[str, Any]) -> float:
    return float(_bbox(item).get("l", 0))


def _is_title(value: str, lesson_number: int) -> bool:
    if _TITLE.match(value):
        return True
    if lesson_number == 15 and value.strip() == "Discurso de bienvenida":
        return True
    return False


def _clean_title(value: str, lesson_number: int) -> str:
    title = re.sub(r"^(?:\d{1,2}-\d|\d{2})\s*", "", value.strip())
    title = re.sub(r"^0\s+(?=I|Il|1|2)", "", title)
    title = re.sub(r"\s+[0O](?:\s+[0O])*$", "", title).strip()
    if lesson_number == 15 and title == "Discurso de bienvenida":
        return "I. Discurso de bienvenida"
    title = re.sub(r"^Il\.", "II.", title, flags=re.I)
    title = re.sub(r"^1\.", "I.", title)
    title = re.sub(r"^2\.", "II.", title)
    title = title.replace("Profesorhispanohablante", "Profesor hispanohablante")
    return title


def _content_lines(lines: list[str]) -> str:
    result: list[str] = []
    for value in lines:
        value = value.strip()
        if not value:
            continue
        if result and re.fullmatch(r"[^:：]{1,50}[:：]", result[-1]):
            result[-1] += " " + value
        else:
            result.append(value)
    return "\n".join(result)


def _region_columns(tables: list[dict], page: int) -> tuple[float, float, float, float, float, float]:
    six = [table for table in tables if table.get("data", {}).get("num_cols") == 6]
    if six:
        largest = max(six, key=lambda table: float(_bbox(table).get("r", 0)) - float(_bbox(table).get("l", 0)))
        try:
            return _columns(largest)
        except LessonExtractionError:
            pass
    left_tables = [table for table in tables if float(_bbox(table).get("l", 999)) < 250]
    base = min((float(_bbox(table).get("l", 0)) + 7 for table in left_tables), default=(45 if page % 2 == 0 else 65))
    return (base, base + 65, base + 120, base + 210, base + 275, base + 330)


def _vocabulary_pages(first_page: int, end_page: int, texts_by_page: dict[int, list[dict]], tables_by_page: dict[int, list[dict]]) -> list[int]:
    pages = [first_page]
    next_page = first_page + 1
    if next_page > end_page:
        return pages
    relevant = [item for item in texts_by_page.get(next_page, []) if item.get("label") not in ("page_header", "page_footer")]
    first = [item for item in relevant if not re.search(r"现代西班牙语学生用书", item.get("text", ""))][:6]
    has_vocab_table = any(table.get("data", {}).get("num_cols") in (3, 5, 6) for table in tables_by_page.get(next_page, []))
    looks_like_word_list = any(re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", item.get("text", "")) for item in first) and any(
        re.search(r"[\u3400-\u9fff]", item.get("text", "")) for item in first
    )
    if (has_vocab_table or looks_like_word_list) and not any(_MAJOR_SECTION.search(item.get("text", "")) for item in first):
        pages.append(next_page)
    return pages


def extract_book_structure(document: dict[str, Any]) -> tuple[BookLessonStructure, ...]:
    texts = document.get("texts")
    tables = document.get("tables")
    if not isinstance(texts, list) or not isinstance(tables, list):
        raise LessonExtractionError("Docling JSON 缺少文字或表格")
    texts_by_page: dict[int, list[dict]] = defaultdict(list)
    tables_by_page: dict[int, list[dict]] = defaultdict(list)
    for item in texts:
        page = _page(item)
        if page is not None:
            texts_by_page[page].append(item)
    for item in tables:
        page = _page(item)
        if page is not None:
            tables_by_page[page].append(item)
    for page in texts_by_page:
        texts_by_page[page].sort(key=lambda item: (-_top(item), _left(item)))

    overview_pages = sorted(page for page, items in texts_by_page.items() if 15 <= page < 294 and any(
        "FUNCI" in item.get("text", "").upper() and "COMUNICATIVA" in item.get("text", "").upper()
        for item in items
    ))
    if len(overview_pages) != 16:
        raise LessonExtractionError(f"应识别 16 个单元概览，实际识别 {len(overview_pages)} 个")
    output: list[BookLessonStructure] = []
    for index, start in enumerate(overview_pages):
        number = index + 1
        end = (overview_pages[index + 1] - 1) if index + 1 < 16 else 293
        text_headings = [item for page in range(start + 1, min(start + 4, end + 1)) for item in texts_by_page.get(page, []) if "TEXTOS" in item.get("text", "").upper()]
        if not text_headings:
            raise LessonExtractionError(f"第{number}课未找到课文标题")
        text_page = _page(text_headings[0])
        assert text_page is not None
        vocab_headings = [item for page in range(text_page + 1, min(text_page + 5, end + 1)) for item in texts_by_page.get(page, []) if "VOCABULARIO" in item.get("text", "").upper()]
        if vocab_headings:
            vocab_page = min(_page(item) for item in vocab_headings if _page(item) is not None)
        else:
            candidates = [page for page in range(text_page + 1, min(text_page + 5, end + 1)) if any(table.get("data", {}).get("num_cols") in (3, 5, 6) for table in tables_by_page.get(page, []))]
            if not candidates:
                raise LessonExtractionError(f"第{number}课无法定位词汇表")
            vocab_page = candidates[0]
        heading_top = max((_top(item) for item in vocab_headings if _page(item) == vocab_page), default=None)
        cutoff = heading_top if heading_top is not None else max((_top(item) for item in tables_by_page.get(vocab_page, [])), default=0) + 20

        passages: list[PassageRecord] = []
        current_title: str | None = None
        current_start = text_page
        current_end = text_page
        lines: list[str] = []
        for page in range(text_page, vocab_page + 1):
            for item in texts_by_page.get(page, []):
                if page == text_page and _top(item) >= _top(text_headings[0]):
                    continue
                if page == vocab_page and _top(item) <= cutoff:
                    continue
                label = item.get("label")
                value = " ".join(str(item.get("text", "")).split())
                if label not in _SOURCE_LABELS or not value:
                    continue
                if re.search(r"[\u3400-\u9fff]", value) or re.fullmatch(r"\d+", value):
                    continue
                if "TEXTOS" in value.upper() or "VOCABULARIO" in value.upper() or value.startswith("UNIDAD") or re.fullmatch(r"第[一二三四五六七八九十]+课", value) or re.fullmatch(r"\d{1,2}-\d", value):
                    continue
                if _is_title(value, number):
                    if current_title and lines:
                        content = _content_lines(lines)
                        passages.append(PassageRecord(current_title, content, current_start, current_end, content))
                    current_title = _clean_title(value, number)
                    current_start = page
                    current_end = page
                    lines = []
                elif current_title:
                    lines.append(value)
                    current_end = page
        if current_title and lines:
            content = _content_lines(lines)
            passages.append(PassageRecord(current_title, content, current_start, current_end, content))

        regions: list[TableRegion] = []
        for page in _vocabulary_pages(vocab_page, end, texts_by_page, tables_by_page):
            page_tables = [table for table in tables_by_page.get(page, []) if table.get("data", {}).get("num_cols") in (3, 5, 6)]
            if page_tables:
                top = max(float(_bbox(table).get("t", 0)) for table in page_tables)
                bottom = min(float(_bbox(table).get("b", 0)) for table in page_tables)
            else:
                top = 650.0 if page != vocab_page else (cutoff - 25 if cutoff else 450.0)
                bottom = 45.0
            if page == vocab_page and heading_top is not None:
                top = max(top, heading_top - 15)
            regions.append(TableRegion(page, {"l": 35.0, "r": 475.0, "t": top, "b": bottom}, _region_columns(page_tables, page)))
        issues = []
        if not passages:
            issues.append("未识别课文篇目")
        if len({item.title for item in passages}) != len(passages):
            issues.append("课文标题重复")
        output.append(BookLessonStructure(number, f"第{number}课", start, end, tuple(passages), tuple(regions), tuple(issues)))
    return tuple(output)


def extract_book(source_pdf: Path, docling_json: Path) -> tuple[ExtractedLesson, ...]:
    from app.services.vocabulary_ocr import extract_vocabulary

    try:
        document = json.loads(docling_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LessonExtractionError("无法读取 Docling JSON") from exc
    structures = extract_book_structure(document)
    result = []
    for structure in structures:
        words = extract_vocabulary(source_pdf, list(structure.vocabulary_regions))
        issues = list(structure.issues)
        if len(words) < 10:
            issues.append(f"词汇过少：{len(words)} 条")
        result.append(ExtractedLesson(
            structure.lesson_number, structure.title, structure.page_start, structure.page_end,
            structure.passages, tuple(words), tuple(issues),
        ))
    return tuple(result)
