import json

import pytest

from app.core.config import BACKEND_ROOT
from app.services.book_extraction import extract_book_structure
from app.services.lesson_extraction import LessonExtractionError


def _converted_document() -> dict:
    paths = list((BACKEND_ROOT / "storage/textbooks/modern-spanish-1/conversions").glob("*/document.json"))
    if not paths:
        pytest.skip("本地尚无已转换教材")
    return json.loads(paths[0].read_text(encoding="utf-8"))


def test_converted_book_has_sixteen_ordered_lessons_and_continuation_pages():
    lessons = extract_book_structure(_converted_document())
    assert [lesson.lesson_number for lesson in lessons] == list(range(1, 17))
    assert all(len(lesson.passages) == 2 for lesson in lessons)
    assert [region.page_no for region in lessons[0].vocabulary_regions] == [18, 19]
    assert [region.page_no for region in lessons[12].vocabulary_regions] == [218, 219]
    assert [region.page_no for region in lessons[11].vocabulary_regions] == [200]
    assert lessons[5].passages[0].title.startswith("I. Hora")


def test_missing_lesson_text_marker_has_visible_error():
    document = _converted_document()
    document["texts"] = [item for item in document["texts"] if not (
        item.get("prov", [{}])[0].get("page_no") == 17 and "TEXTOS" in item.get("text", "")
    )]
    with pytest.raises(LessonExtractionError, match="第1课未找到课文标题"):
        extract_book_structure(document)
