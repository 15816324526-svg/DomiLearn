"""Fill the confirmed textbook's sixteen lessons from its saved Docling JSON.

Run from backend: python -m scripts.backfill_book [--apply]
The default run only writes an extraction audit; --apply saves validated lessons.
"""

from __future__ import annotations

import argparse
import json
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine_from_settings, make_session_factory, upgrade_database
from app.models import ConversionVersion, Lesson, Passage, SourceFile, Textbook, VocabularyEntry
from app.services.book_extraction import extract_book
from app.services.lesson_repository import save_book


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Save validated lessons into the confirmed textbook version")
    args = parser.parse_args()
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    upgrade_database(engine)
    factory = make_session_factory(engine)
    with factory() as db:
        textbook = db.get(Textbook, "modern-spanish-1")
        if textbook is None or not textbook.current_version_id:
            raise SystemExit("请先确认《现代西班牙语 1》的转换版本")
        version = db.get(ConversionVersion, textbook.current_version_id)
        if version is None or version.confirmed_at is None:
            raise SystemExit("当前转换版本尚未确认")
        source = db.get(SourceFile, version.source_file_id)
        if source is None:
            raise SystemExit("原始 PDF 已丢失")
        version_id = version.id
        pdf = settings.storage_root / source.stored_path
        document = settings.storage_root / version.docling_json_path
    lessons = extract_book(pdf, document)
    report = [{
        "lesson": lesson.lesson_number,
        "pages": [lesson.page_start, lesson.page_end],
        "passages": [{"title": item.title, "characters": len(item.content)} for item in lesson.passages],
        "vocabulary_count": len(lesson.vocabulary),
        "issues": list(lesson.issues),
    } for lesson in lessons]
    report_path = settings.storage_root / "reports" / "full-book-backfill.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in report:
        print(f"第{row['lesson']:02d}课：{len(row['passages'])}篇课文，{row['vocabulary_count']}条单词，问题：{row['issues']}")
    if not args.apply:
        print(f"审查报告：{report_path}")
        return
    if len(lessons) != 16 or any(item.issues for item in lessons):
        raise SystemExit("整本教材尚未通过解析校验，未写入数据库")
    with factory.begin() as db:
        save_book(db, version_id, lessons)
    with factory() as db:
        saved = list(db.scalars(select(Lesson).where(Lesson.conversion_version_id == version_id).order_by(Lesson.lesson_number)))
        counts = [(
            item.lesson_number,
            db.query(Passage).filter(Passage.lesson_id == item.id).count(),
            db.query(VocabularyEntry).filter(VocabularyEntry.lesson_id == item.id).count(),
        ) for item in saved]
    print(f"已保存版本 {version_id}：{counts}")


if __name__ == "__main__":
    main()
