from __future__ import annotations

import json
import random
import re
import unicodedata
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    ConversionVersion, Lesson, Textbook, VocabularyAttempt, VocabularyEntry, VocabularySession,
)
from app.services.import_service import ServiceError


def accepted_spellings(headword: str) -> tuple[str, ...]:
    """Expand textbook's compact gender suffix where its form is unambiguous."""
    value = headword.strip()
    match = re.fullmatch(r"([^,]+),\s*([a-záéíóúñü]+)", value, re.IGNORECASE)
    if not match:
        return (value,)
    base, suffix = match.group(1).strip(), match.group(2).lower()
    # The scan reads the compact "ellas" suffix as "Ilas" in this edition.
    if suffix == "ilas" and base == "ellos":
        return (base, "ellas")
    if suffix == "as" and base.endswith("os"):
        return (base, base[:-2] + "as")
    if suffix == "es" and base.endswith("n"):
        return (base, base + "es")
    first = suffix[0]
    position = base.lower().rfind(first)
    if position >= 0:
        return (base, base[:position] + suffix)
    if suffix == "a" and base.endswith("o"):
        return (base, base[:-1] + suffix)
    return (base,)


def normalized_spelling(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.strip().casefold())
    return "".join(char for char in decomposed if char != "\u0301")


def choice_options(word: VocabularyEntry, words: list[VocabularyEntry]) -> list[str]:
    other_meanings = sorted({item.meaning.strip() for item in words if item.meaning.strip() != word.meaning.strip()})
    rng = random.Random(word.id)
    options = [word.meaning.strip(), *rng.sample(other_meanings, min(3, len(other_meanings)))]
    rng.shuffle(options)
    return options


class VocabularyStudyService:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory

    def list_lessons(self) -> list[dict]:
        with self.factory() as db:
            textbook = db.get(Textbook, "modern-spanish-1")
            if textbook is None or textbook.current_version_id is None:
                return []
            lessons = list(db.scalars(select(Lesson).where(
                Lesson.conversion_version_id == textbook.current_version_id,
            ).order_by(Lesson.lesson_number)))
            return [{"number": lesson.lesson_number, "title": lesson.title} for lesson in lessons]

    def get_or_start(self, lesson_number: int = 1) -> dict:
        with self.factory.begin() as db:
            lesson = self._active_lesson(db, lesson_number)
            words = self._words(db, lesson.id)
            study = db.scalar(select(VocabularySession).where(VocabularySession.lesson_id == lesson.id))
            if study is None:
                ids = [word.id for word in words]
                state = {phase: {"active": ids.copy(), "retry": [], "done": []} for phase in ("choice", "dictation")}
                study = VocabularySession(id=str(uuid4()), lesson_id=lesson.id, stage="choice", state_json=json.dumps(state))
                db.add(study)
                db.flush()
            return self._present(db, lesson, study, words)

    def submit(self, session_id: str, question_id: str, answer: str | int | None, request_id: str, lesson_number: int = 1) -> dict:
        with self.factory.begin() as db:
            lesson, study, words = self._load_active_session(db, session_id, lesson_number)
            duplicate = db.scalar(select(VocabularyAttempt).where(
                VocabularyAttempt.session_id == study.id,
                VocabularyAttempt.request_id == request_id,
            ))
            if duplicate is not None:
                return self._present(db, lesson, study, words)
            if study.feedback_json or study.stage == "complete":
                raise ServiceError("ANSWER_PENDING", 409, "请先点击下一题")
            state = json.loads(study.state_json)
            phase = state[study.stage]
            if not phase["active"] or phase["active"][0] != question_id:
                raise ServiceError("QUESTION_CHANGED", 409, "题目已变化，请刷新后继续")
            by_id = {word.id: word for word in words}
            word = by_id[question_id]
            question = self._question(word, words, study.stage)
            skipped = answer is None
            if study.stage == "choice":
                options = question["options"]
                if not skipped and (type(answer) is not int or not 0 <= answer < len(options)):
                    raise ServiceError("INVALID_ANSWER", 400, "请选择一个释义选项")
                correct_index = options.index(word.meaning.strip())
                correct = not skipped and answer == correct_index
                correct_answer = word.meaning.strip()
            else:
                if not skipped and not isinstance(answer, str):
                    raise ServiceError("INVALID_ANSWER", 400, "请输入西语单词")
                if not skipped and not answer.strip():
                    raise ServiceError("INVALID_ANSWER", 400, "请输入西语单词，或点击暂时不会")
                correct_index = None
                correct = not skipped and normalized_spelling(answer) in {
                    normalized_spelling(form) for form in accepted_spellings(word.headword)
                }
                correct_answer = " / ".join(accepted_spellings(word.headword))
            phase["active"].pop(0)
            if correct:
                phase["done"].append(word.id)
            else:
                phase["retry"].append(word.id)
            if not phase["active"] and phase["retry"]:
                phase["active"], phase["retry"] = phase["retry"], []
            study.state_json = json.dumps(state)
            study.feedback_json = json.dumps({
                "question": question,
                "correct": correct,
                "skipped": skipped,
                "submittedAnswer": answer,
                "correctAnswer": correct_answer,
                "correctOptionIndex": correct_index,
            }, ensure_ascii=False)
            db.add(VocabularyAttempt(
                id=str(uuid4()), session_id=study.id, word_id=word.id, stage=study.stage,
                request_id=request_id,
                submitted_answer=None if skipped else str(answer), is_correct=correct,
            ))
            db.flush()
            return self._present(db, lesson, study, words)

    def advance(self, session_id: str, lesson_number: int = 1) -> dict:
        with self.factory.begin() as db:
            lesson, study, words = self._load_active_session(db, session_id, lesson_number)
            if not study.feedback_json:
                raise ServiceError("NO_FEEDBACK", 409, "请先回答当前题目")
            study.feedback_json = None
            state = json.loads(study.state_json)
            phase = state[study.stage]
            if not phase["active"]:
                study.stage = "dictation" if study.stage == "choice" else "complete"
            db.flush()
            return self._present(db, lesson, study, words)

    def _active_lesson(self, db: Session, lesson_number: int = 1) -> Lesson:
        textbook = db.get(Textbook, "modern-spanish-1")
        if textbook is None or textbook.current_version_id is None:
            raise ServiceError("TEXTBOOK_NOT_CONFIRMED", 409, "请先在教材目录确认解析成功的教材")
        version = db.get(ConversionVersion, textbook.current_version_id)
        if version is None or version.confirmed_at is None:
            raise ServiceError("TEXTBOOK_NOT_CONFIRMED", 409, "请先在教材目录确认解析成功的教材")
        lesson = db.scalar(select(Lesson).where(
            Lesson.conversion_version_id == version.id, Lesson.lesson_number == lesson_number,
        ))
        if lesson is None:
            raise ServiceError("LESSON_NOT_READY", 409, f"当前教材还没有第{lesson_number}课词表")
        return lesson

    def _load_active_session(self, db: Session, session_id: str, lesson_number: int = 1) -> tuple[Lesson, VocabularySession, list[VocabularyEntry]]:
        lesson = self._active_lesson(db, lesson_number)
        study = db.get(VocabularySession, session_id)
        if study is None or study.lesson_id != lesson.id:
            raise ServiceError("SESSION_CHANGED", 409, "教材版本已变化，请返回章节页继续")
        return lesson, study, self._words(db, lesson.id)

    def _words(self, db: Session, lesson_id: str) -> list[VocabularyEntry]:
        words = list(db.scalars(select(VocabularyEntry).where(
            VocabularyEntry.lesson_id == lesson_id,
        ).order_by(VocabularyEntry.ordinal)))
        if not words:
            raise ServiceError("LESSON_NOT_READY", 409, "当前课还没有词表")
        return words

    def _question(self, word: VocabularyEntry, words: list[VocabularyEntry], stage: str) -> dict:
        if stage == "choice":
            return {"id": word.id, "lemma": word.headword, "pos": word.part_of_speech or "", "options": choice_options(word, words)}
        same_meaning = sum(item.meaning.strip() == word.meaning.strip() for item in words) > 1
        first = accepted_spellings(word.headword)[0][:1].lower()
        return {"id": word.id, "meaning": word.meaning, "hint": f"首字母 {first}" if same_meaning else None}

    def _present(self, db: Session, lesson: Lesson, study: VocabularySession, words: list[VocabularyEntry]) -> dict:
        state = json.loads(study.state_json)
        phase = state[study.stage] if study.stage != "complete" else state["dictation"]
        feedback = json.loads(study.feedback_json) if study.feedback_json else None
        word_by_id = {word.id: word for word in words}
        question = feedback["question"] if feedback else (
            self._question(word_by_id[phase["active"][0]], words, study.stage)
            if study.stage != "complete" and phase["active"] else None
        )
        attempts = list(db.scalars(select(VocabularyAttempt).where(VocabularyAttempt.session_id == study.id)))
        errors = sum(not attempt.is_correct and attempt.stage == study.stage for attempt in attempts)
        wrong: dict[str, dict[str, int]] = {}
        for attempt in attempts:
            if not attempt.is_correct:
                counts = wrong.setdefault(attempt.word_id, {"choice": 0, "dictation": 0})
                counts[attempt.stage] += 1
        review_words = []
        stable_words = []
        for word in words:
            counts = wrong.get(word.id)
            item = {"id": word.id, "lemma": word.headword, "meaning": word.meaning}
            if counts:
                reasons = []
                if counts["choice"]:
                    reasons.append(f"释义错误 {counts['choice']} 次")
                if counts["dictation"]:
                    reasons.append(f"拼写错误 {counts['dictation']} 次")
                review_words.append({**item, "reason": "、".join(reasons)})
            else:
                stable_words.append(item)
        return {
            "overview": {
                "title": lesson.title,
                "description": "先看西语选中文，再根据中文拼出西语。每题完成后自动保存。",
                "wordCount": len(words),
                "estimatedMinutes": max(10, len(words)),
            },
            "session": {
                "id": study.id,
                "stage": study.stage,
                "total": len(words),
                "done": len(phase["done"]),
                "errors": errors,
                "question": question,
                "feedback": {key: value for key, value in feedback.items() if key != "question"} if feedback else None,
                "summary": {
                    "learned": len(words), "review": len(review_words), "stable": len(stable_words),
                    "attempts": len(attempts), "reviewWords": review_words, "stableWords": stable_words,
                } if study.stage == "complete" else None,
            },
        }
