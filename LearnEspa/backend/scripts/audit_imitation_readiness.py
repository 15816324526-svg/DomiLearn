r"""Write an explicit 16-lesson readiness report for the confirmed textbook.

Run from ``backend``: ``.\.venv\Scripts\python.exe scripts\audit_imitation_readiness.py``.
``--strict`` also requires every sentence to have a source-verified core pattern,
which is populated when a passage is first planned with the configured model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.db.session import create_engine_from_settings, make_session_factory, upgrade_database  # noqa: E402
from app.models import ConversionVersion, Lesson, Passage, Textbook, VocabularyEntry  # noqa: E402
from app.services.sentence_preparation import prepare_passage  # noqa: E402


def audit(strict: bool = False) -> dict:
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    upgrade_database(engine)
    factory = make_session_factory(engine)
    with factory.begin() as db:
        textbook = db.get(Textbook, "modern-spanish-1")
        version = db.get(ConversionVersion, textbook.current_version_id) if textbook and textbook.current_version_id else None
        if version is None or version.confirmed_at is None:
            return {"ready": False, "blocking_issues": ["尚无已确认的教材版本"], "lessons": []}
        lessons = list(db.scalars(select(Lesson).where(
            Lesson.conversion_version_id == version.id,
        ).order_by(Lesson.lesson_number)))
        rows = []
        blocking: list[str] = []
        numbers = {lesson.lesson_number for lesson in lessons}
        for number in range(1, 17):
            if number not in numbers:
                blocking.append(f"第{number}课缺失")
        for lesson in lessons:
            passages = list(db.scalars(select(Passage).where(Passage.lesson_id == lesson.id).order_by(Passage.ordinal)))
            word_count = db.scalar(select(func.count(VocabularyEntry.id)).where(
                VocabularyEntry.lesson_id == lesson.id,
            )) or 0
            lesson_issues = []
            if not passages:
                lesson_issues.append("缺少课文")
            if not word_count:
                lesson_issues.append("缺少词汇")
            prepared = 0
            pattern_pending = 0
            details = []
            for passage in passages:
                sentences, issues = prepare_passage(db, passage)
                prepared += len(sentences)
                pattern_pending += sum(not item.core_pattern for item in sentences)
                if issues:
                    lesson_issues.append(f"{passage.title}：" + "；".join(issues))
                details.append({
                    "id": passage.id, "title": passage.title,
                    "sentence_count": len(sentences), "issues": issues,
                })
            if strict and pattern_pending:
                lesson_issues.append(f"{pattern_pending} 句尚未固定核心句式")
            if lesson_issues:
                blocking.append(f"第{lesson.lesson_number}课：" + "；".join(lesson_issues))
            rows.append({
                "lesson_number": lesson.lesson_number, "title": lesson.title,
                "page_start": lesson.page_start, "page_end": lesson.page_end,
                "passage_count": len(passages), "vocabulary_count": word_count,
                "sentence_count": prepared, "pattern_pending": pattern_pending,
                "issues": lesson_issues, "passages": details,
            })
        return {
            "version_id": version.id, "strict": strict,
            "ready": not blocking, "blocking_issues": blocking, "lessons": rows,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.strict)
    output = args.output or get_settings().storage_root / "reports" / "imitation-readiness.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ready": result["ready"], "lessons": len(result["lessons"]),
        "blocking_issues": len(result["blocking_issues"]), "output": str(output),
    }, ensure_ascii=True))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
