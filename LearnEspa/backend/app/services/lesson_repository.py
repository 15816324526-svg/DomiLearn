from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lesson, Passage, VocabularyEntry
from app.services.lesson_extraction import LessonExtraction
from app.services.book_extraction import ExtractedLesson


def save_first_lesson(session: Session, version_id: str, extraction: LessonExtraction) -> Lesson:
    existing = session.scalar(
        select(Lesson).where(
            Lesson.conversion_version_id == version_id,
            Lesson.lesson_number == 1,
        )
    )
    if existing is not None:
        return existing
    lesson = Lesson(
        id=str(uuid4()),
        conversion_version_id=version_id,
        lesson_number=1,
        title="第一课",
        page_start=extraction.page_start,
        page_end=extraction.page_end,
    )
    lesson.passages = [
        Passage(
            id=str(uuid4()),
            ordinal=index,
            title=item.title,
            content=item.content,
            source_page_start=item.source_page_start,
            source_page_end=item.source_page_end,
            raw_ocr=item.raw_ocr,
        )
        for index, item in enumerate(extraction.passages, start=1)
    ]
    lesson.vocabulary = [
        VocabularyEntry(
            id=str(uuid4()),
            ordinal=index,
            headword=item.headword,
            part_of_speech=item.part_of_speech,
            meaning=item.meaning,
            source_page=item.source_page,
            raw_ocr=item.raw_ocr,
        )
        for index, item in enumerate(extraction.vocabulary, start=1)
    ]
    session.add(lesson)
    session.flush()
    return lesson


def save_lesson(session: Session, version_id: str, extraction: ExtractedLesson) -> Lesson:
    if extraction.issues or not extraction.passages or len(extraction.vocabulary) < 10:
        raise ValueError(f"第{extraction.lesson_number}课解析未通过：{'、'.join(extraction.issues)}")
    if any(not passage.content.strip() for passage in extraction.passages):
        raise ValueError(f"第{extraction.lesson_number}课存在空课文")
    if any(not word.headword.strip() or not word.meaning.strip() for word in extraction.vocabulary):
        raise ValueError(f"第{extraction.lesson_number}课存在空词条")
    existing = session.scalar(select(Lesson).where(
        Lesson.conversion_version_id == version_id,
        Lesson.lesson_number == extraction.lesson_number,
    ))
    if existing is not None:
        return existing
    lesson = Lesson(
        id=str(uuid4()), conversion_version_id=version_id,
        lesson_number=extraction.lesson_number, title=extraction.title,
        page_start=extraction.page_start, page_end=extraction.page_end,
    )
    lesson.passages = [Passage(
        id=str(uuid4()), ordinal=index, title=item.title, content=item.content,
        source_page_start=item.source_page_start, source_page_end=item.source_page_end,
        raw_ocr=item.raw_ocr,
    ) for index, item in enumerate(extraction.passages, start=1)]
    lesson.vocabulary = [VocabularyEntry(
        id=str(uuid4()), ordinal=index, headword=item.headword,
        part_of_speech=item.part_of_speech, meaning=item.meaning,
        source_page=item.source_page, raw_ocr=item.raw_ocr,
    ) for index, item in enumerate(extraction.vocabulary, start=1)]
    session.add(lesson)
    session.flush()
    return lesson


def save_book(session: Session, version_id: str, lessons: tuple[ExtractedLesson, ...]) -> tuple[Lesson, ...]:
    if [lesson.lesson_number for lesson in lessons] != list(range(1, 17)):
        raise ValueError("教材必须包含连续的 16 课")
    return tuple(save_lesson(session, version_id, lesson) for lesson in lessons)
