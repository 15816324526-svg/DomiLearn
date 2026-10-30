"""Remove obvious page-label OCR artifacts from derived passages.

Only changes lessons without imitation rounds. The original OCR text remains
in Passage.raw_ocr. Run from backend: python -m scripts.repair_passage_artifacts
"""

from __future__ import annotations

import json
import re

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import ImitationRound, Lesson, Passage, PassageSentence, Textbook
from app.services.sentence_preparation import prepare_passage


def main() -> None:
    repaired: list[tuple[int, str]] = []
    with SessionLocal.begin() as db:
        textbook = db.get(Textbook, "modern-spanish-1")
        if textbook is None or not textbook.current_version_id:
            raise SystemExit("尚无已确认教材")
        rows = list(db.execute(select(Lesson, Passage).join(Passage, Passage.lesson_id == Lesson.id).where(
            Lesson.conversion_version_id == textbook.current_version_id,
        ).order_by(Lesson.lesson_number, Passage.ordinal)))
        for lesson, passage in rows:
            lines = passage.content.splitlines()
            clean = [line for line in lines if not re.search(r"[\u3400-\u9fff]", line) and not re.fullmatch(r"\s*\d+\s*", line)]
            if len(clean) == len(lines):
                continue
            if db.scalar(select(ImitationRound.id).where(ImitationRound.passage_id == passage.id).limit(1)):
                raise SystemExit(f"第{lesson.lesson_number}课已有仿写记录，停止修改")
            passage.content = "\n".join(clean)
            for sentence in db.scalars(select(PassageSentence).where(PassageSentence.passage_id == passage.id)).all():
                db.delete(sentence)
            db.flush()
            prepare_passage(db, passage)
            repaired.append((lesson.lesson_number, passage.title))
    print(json.dumps({"repaired_passages": len(repaired), "titles": repaired}, ensure_ascii=True))


if __name__ == "__main__":
    main()
