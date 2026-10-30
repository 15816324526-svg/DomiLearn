from app.services.lesson_extraction import TableRegion
from app.services.vocabulary_ocr import OCRLine, parse_vocabulary_lines


def test_pairs_columns_and_wrapped_meanings_without_a_pos() -> None:
    region = TableRegion(
        page_no=18,
        bbox={"l": 0, "r": 340, "t": 400, "b": 200, "page_height": 720},
        column_starts=(10, 50, 90, 200, 240, 280),
    )
    lines = [
        OCRLine(10, 340, "hola"), OCRLine(50, 340, "interj."), OCRLine(90, 338, "你"),
        OCRLine(90, 345, "好"), OCRLine(10, 365, "me llamo"), OCRLine(90, 365, "我叫"),
        OCRLine(200, 340, "amigo, ga"), OCRLine(240, 340, "m.,f."),
        OCRLine(280, 340, "朋友"), OCRLine(200, 365, "Paco"), OCRLine(280, 365, "帕科"),
        OCRLine(10, 600, "outside"),
    ]
    result = parse_vocabulary_lines(lines, region)
    assert [(word.headword, word.meaning) for word in result] == [
        ("hola", "你 好"), ("me llamo", "我叫"), ("amigo, ga", "朋友"), ("Paco", "帕科")
    ]
    assert result[0].part_of_speech == "interj."
    assert result[1].part_of_speech is None
    assert all(word.source_page == 18 for word in result)
