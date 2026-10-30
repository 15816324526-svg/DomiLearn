from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from pathlib import Path

from app.services.lesson_extraction import LessonExtractionError, TableRegion, VocabularyRecord


@dataclass(frozen=True)
class OCRLine:
    x: float
    y: float
    text: str


_POS_SUFFIX = re.compile(
    r"\s+(m[.,]+f\.|f\.|m\.|adj\.|adv\.|art\.|num\.|pron\.|"
    r"interj\.|prep\.|conj\.|p\.p\.|prnl\.|tr\.|intr\.)$",
    re.I,
)


def _column(x: float, starts: tuple[float, float, float, float, float, float]) -> int:
    boundaries = [(starts[index] + starts[index + 1]) / 2 for index in range(5)]
    return bisect.bisect_right(boundaries, x)


def parse_vocabulary_lines(lines: list[OCRLine], region: TableRegion) -> list[VocabularyRecord]:
    """Associate OCR lines using the textbook's two three-column vocabulary panels."""
    top = float(region.bbox["t"])
    bottom = float(region.bbox["b"])
    page_height = float(region.bbox.get("page_height", 732))
    y_min = page_height - top - 7
    y_max = page_height - bottom + 7
    columns: list[list[OCRLine]] = [[] for _ in range(6)]
    for line in lines:
        value = " ".join(line.text.split())
        if y_min <= line.y <= y_max and value:
            col = _column(line.x, region.column_starts)
            columns[col].append(OCRLine(line.x, line.y, value))
    for column in columns:
        column.sort(key=lambda line: line.y)

    entries: list[VocabularyRecord] = []
    for offset in (0, 3):
        words = columns[offset]
        positions = [item.y for item in words]
        if not words:
            continue
        associated: list[dict[str, list[str]]] = [dict(pos=[], meaning=[]) for _ in words]
        for col, key in ((offset + 1, "pos"), (offset + 2, "meaning")):
            for line in columns[col]:
                index = bisect.bisect_right(positions, line.y + 6) - 1
                if index >= 0:
                    associated[index][key].append(line.text)
        for word, parts in zip(words, associated):
            headword = word.text
            pos = " ".join(parts["pos"]).strip() or None
            if not pos:
                match = _POS_SUFFIX.search(headword)
                if match:
                    pos = match.group(1)
                    headword = headword[:match.start()].strip()
            meaning = " ".join(parts["meaning"]).strip()
            if not meaning or not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ¿¡]", headword):
                continue
            if not re.search(r"[\u3400-\u9fff]", meaning):
                continue
            raw = " | ".join([word.text, pos or "", meaning])
            entries.append(VocabularyRecord(headword, pos, meaning, region.page_no, raw))
    return entries


def extract_vocabulary(source_pdf: Path, tables: list[TableRegion]) -> list[VocabularyRecord]:
    import pypdfium2
    from rapidocr import RapidOCR

    try:
        pdf = pypdfium2.PdfDocument(str(source_pdf))
        ocr = RapidOCR()
        entries: list[VocabularyRecord] = []
        scale = 1.5
        for region in sorted(tables, key=lambda table: table.page_no):
            page = pdf[region.page_no - 1]
            image = page.render(scale=scale).to_pil()
            page_height = image.height / scale
            result = ocr(image)
            if result.boxes is None or result.txts is None:
                raise LessonExtractionError(f"第 {region.page_no} 页词表 OCR 未返回文字")
            lines = [
                OCRLine(
                    min(float(point[0]) for point in box_points) / scale,
                    min(float(point[1]) for point in box_points) / scale,
                    text,
                )
                for box_points, text in zip(result.boxes, result.txts)
            ]
            normalized_region = TableRegion(
                region.page_no,
                {**region.bbox, "page_height": page_height},
                region.column_starts,
            )
            entries.extend(parse_vocabulary_lines(lines, normalized_region))
        return entries
    except LessonExtractionError:
        raise
    except Exception as exc:
        raise LessonExtractionError("第一课词表 OCR 失败") from exc
