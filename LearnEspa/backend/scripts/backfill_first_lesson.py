from __future__ import annotations

import argparse

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_engine_from_settings, make_session_factory, upgrade_database
from app.models import ConversionVersion, Lesson, SourceFile
from app.services.lesson_extraction import extract_first_lesson
from app.services.lesson_repository import save_first_lesson


def backfill(version_id: str | None = None) -> list[tuple[str, int, int]]:
    settings = get_settings()
    settings.ensure_directories()
    engine = create_engine_from_settings(settings)
    upgrade_database(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        query = select(ConversionVersion).order_by(ConversionVersion.created_at)
        if version_id:
            query = query.where(ConversionVersion.id == version_id)
        versions = session.scalars(query).all()
        if version_id and not versions:
            raise ValueError(f"找不到转换版本：{version_id}")
        pending = []
        for version in versions:
            existing = session.scalar(
                select(Lesson).where(
                    Lesson.conversion_version_id == version.id,
                    Lesson.lesson_number == 1,
                )
            )
            if existing is None:
                source = session.get(SourceFile, version.source_file_id)
                if source is None:
                    raise ValueError(f"转换版本缺少源 PDF：{version.id}")
                pending.append((version.id, source.stored_path, version.docling_json_path))

    results = []
    for current_id, source_path, json_path in pending:
        extraction = extract_first_lesson(
            settings.storage_root / source_path,
            settings.storage_root / json_path,
        )
        with factory.begin() as session:
            save_first_lesson(session, current_id, extraction)
        results.append((current_id, len(extraction.vocabulary), len(extraction.passages)))
    engine.dispose()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="为已有转换版本补齐第一课分类")
    parser.add_argument("--version-id", help="只处理指定的转换版本；默认处理所有尚未分类的版本")
    args = parser.parse_args()
    results = backfill(args.version_id)
    if not results:
        print("所有匹配版本都已分类，无须重复写入。")
    for version_id, words, passages in results:
        print(f"{version_id}: {words} 条单词，{passages} 篇课文")


if __name__ == "__main__":
    main()
