import pytest

from app.services.lesson_extraction import LessonExtractionError, extract_lesson_structure


def item(page: int, text: str, label: str = "text", parent: str = "#/body") -> dict:
    return {"prov": [{"page_no": page}], "text": text, "label": label, "parent": {"$ref": parent}}


def table(page: int) -> dict:
    return {
        "prov": [{"page_no": page, "bbox": {"l": 0, "r": 350, "t": 400, "b": 200}}],
        "data": {
            "num_cols": 6,
            "grid": [[
                {"start_col_offset_idx": index, "bbox": {"l": 10 + index * 50}}
                for index in range(6)
            ]],
        },
    }


def document() -> dict:
    return {
        "texts": [
            item(3, "UNIDAD", parent="#/pictures/1"),
            item(3, "第一课", parent="#/pictures/1"),
            item(4, "TEXTOS 课文", "section_header"),
            item(4, "I. Primer texto", "section_header"),
            item(4, "Ana: Hola.", parent="#/groups/1"),
            item(5, "II. Segundo texto", "section_header"),
            item(5, "Paco: Buenos días.", parent="#/groups/2"),
            item(5, "VOCABULARIO", parent="#/pictures/2"),
            item(6, "语音 FONÉTICA", "section_header"),
            item(7, "练习EJERCICIOS", "section_header"),
            item(7, "I. Unrelated exercise", "section_header"),
            item(7, "Wrong exercise text."),
            item(8, "第二课", parent="#/pictures/3"),
        ],
        "tables": [table(5), table(6)],
    }


def test_extracts_only_the_two_passages_and_vocabulary_table_bounds() -> None:
    result = extract_lesson_structure(document())
    assert (result.page_start, result.page_end) == (3, 7)
    assert [passage.title for passage in result.passages] == ["I. Primer texto", "II. Segundo texto"]
    assert [passage.content for passage in result.passages] == ["Ana: Hola.", "Paco: Buenos días."]
    assert [region.page_no for region in result.tables] == [5, 6]


def test_missing_lesson_boundary_fails_without_guessing() -> None:
    sample = document()
    sample["texts"] = [item for item in sample["texts"] if item["text"] != "第二课"]
    with pytest.raises(LessonExtractionError, match="边界"):
        extract_lesson_structure(sample)
