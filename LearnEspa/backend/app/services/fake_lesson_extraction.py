from pathlib import Path

from app.services.lesson_extraction import LessonExtraction, PassageRecord, VocabularyRecord


def fake_first_lesson(_source_pdf: Path, _docling_json: Path) -> LessonExtraction:
    """Fast deterministic extraction used only with the fake PDF converter in tests."""
    return LessonExtraction(
        page_start=1,
        page_end=2,
        passages=(
            PassageRecord("I. Primer texto", "Ana: Hola.", 1, 1, "Ana: Hola."),
            PassageRecord("II. Segundo texto", "Paco: Buenos días.", 2, 2, "Paco: Buenos días."),
        ),
        vocabulary=(
            VocabularyRecord("hola", "interj.", "你好", 1, "hola | interj. | 你好"),
            VocabularyRecord("día", "m.", "天", 2, "día | m. | 天"),
        ),
    )
