from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.converters.fake import FakeConverter
from app.models import ConversionVersion, Lesson, VocabularyAttempt, VocabularyEntry, VocabularySession
from app.services.import_service import ImportService, ServiceError
from app.services.fake_lesson_extraction import fake_first_lesson
from app.services.pdf_validation import PdfMetadata
from app.services.source_storage import StoredSource
from app.services.vocabulary_study import VocabularyStudyService, accepted_spellings, normalized_spelling
from app.workers.import_worker import ImportWorker


def make_confirmed_lesson(factory, settings) -> VocabularyStudyService:
    importer = ImportService(factory, settings.storage_root)
    path = settings.storage_root / "textbooks/modern-spanish-1/originals/fake/source.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"pdf")
    source = importer.register_source(
        StoredSource(path, "book.pdf", 3, "f" * 64, False),
        PdfMetadata(2, 3, "f" * 64),
    )
    job = importer.create_import(source.id, "book.pdf")
    ImportWorker(factory, settings.storage_root, FakeConverter(), 60, lesson_extractor=fake_first_lesson).run_once()
    importer.confirm(job.id)
    with factory.begin() as db:
        lesson = db.scalar(select(Lesson))
        assert lesson is not None
        for ordinal, headword, meaning in [
            (3, "alumno, na", "学生"),
            (4, "estudiante", "学生"),
            (5, "niño", "孩子"),
        ]:
            db.add(VocabularyEntry(
                id=str(uuid4()), lesson_id=lesson.id, ordinal=ordinal,
                headword=headword, part_of_speech=None, meaning=meaning,
                source_page=2, raw_ocr=headword,
            ))
    return VocabularyStudyService(factory)


def answer(service, state, response, request_id=None):
    session = state["session"]
    return service.submit(session["id"], session["question"]["id"], response, request_id or str(uuid4()))


def correct_response(state):
    question = state["session"]["question"]
    if state["session"]["stage"] == "choice":
        return question["options"].index({
            "hola": "你好", "día": "天", "alumno, na": "学生",
            "estudiante": "学生", "niño": "孩子",
        }[question["lemma"]])
    return {
        "你好": "hola", "天": "dia", "学生": "alumno" if question["hint"] == "首字母 a" else "estudiante",
        "孩子": "niño",
    }[question["meaning"]]


def test_wrong_word_returns_after_remaining_words_and_pending_feedback_survives(session_factory, test_settings):
    service = make_confirmed_lesson(session_factory, test_settings)
    state = service.get_or_start()
    first_id = state["session"]["question"]["id"]
    options = state["session"]["question"]["options"]
    wrong = next(i for i in range(len(options)) if i != correct_response(state))
    state = answer(service, state, wrong)
    assert state["session"]["feedback"]["correct"] is False
    assert state["session"]["question"]["id"] == first_id
    assert service.get_or_start()["session"]["feedback"] == state["session"]["feedback"]
    with pytest.raises(ServiceError, match="下一题"):
        answer(service, state, correct_response(state))
    state = service.advance(state["session"]["id"])
    assert state["session"]["question"]["id"] != first_id
    for _ in range(4):
        state = answer(service, state, correct_response(state))
        state = service.advance(state["session"]["id"])
    assert state["session"]["question"]["id"] == first_id
    assert state["session"]["done"] == 4
    assert len(state["session"]["question"]["options"]) == 4
    assert len(set(state["session"]["question"]["options"])) == 4


def test_both_phases_and_review_pool_and_duplicate_request(session_factory, test_settings):
    service = make_confirmed_lesson(session_factory, test_settings)
    state = service.get_or_start()
    request_id = str(uuid4())
    state = answer(service, state, None, request_id)
    repeated = service.submit(state["session"]["id"], state["session"]["question"]["id"], None, request_id)
    assert repeated == state
    state = service.advance(state["session"]["id"])
    while state["session"]["stage"] == "choice":
        state = answer(service, state, correct_response(state))
        state = service.advance(state["session"]["id"])
    assert state["session"]["stage"] == "dictation"
    assert state["session"]["question"]["meaning"] == "你好"
    state = answer(service, state, "HOLA")
    assert state["session"]["feedback"]["correct"] is True
    state = service.advance(state["session"]["id"])
    while state["session"]["stage"] == "dictation":
        state = answer(service, state, correct_response(state))
        state = service.advance(state["session"]["id"])
    summary = state["session"]["summary"]
    assert state["session"]["stage"] == "complete"
    assert summary["learned"] == 5
    assert summary["review"] == 1
    assert summary["reviewWords"][0]["lemma"] == "hola"
    assert "释义错误 1 次" in summary["reviewWords"][0]["reason"]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(VocabularyAttempt)) == 11


def test_spelling_and_duplicate_meaning_hint(session_factory, test_settings):
    assert accepted_spellings("alumno, na") == ("alumno", "alumna")
    assert accepted_spellings("amigo, ga") == ("amigo", "amiga")
    assert accepted_spellings("español, la") == ("español", "española")
    assert accepted_spellings("profesor, ra") == ("profesor", "profesora")
    assert accepted_spellings("nuestro, tra") == ("nuestro", "nuestra")
    assert accepted_spellings("los, las") == ("los", "las")
    assert accepted_spellings("quién, es") == ("quién", "quiénes")
    assert accepted_spellings("esos, as") == ("esos", "esas")
    assert accepted_spellings("ellos, Ilas") == ("ellos", "ellas")
    assert accepted_spellings("novio, via") == ("novio", "novia")
    assert normalized_spelling("  DÍA ") == normalized_spelling("dia")
    assert normalized_spelling("niño") != normalized_spelling("nino")
    service = make_confirmed_lesson(session_factory, test_settings)
    state = service.get_or_start()
    while state["session"]["stage"] == "choice":
        state = service.advance(answer(service, state, correct_response(state))["session"]["id"])
    seen = set()
    while state["session"]["stage"] == "dictation":
        question = state["session"]["question"]
        if question["meaning"] == "学生":
            seen.add(question["hint"])
            response = "alumna" if question["hint"] == "首字母 a" else "estudiante"
        else:
            response = correct_response(state)
        state = answer(service, state, response)
        assert state["session"]["feedback"]["correct"] is True
        state = service.advance(state["session"]["id"])
    assert seen == {"首字母 a", "首字母 e"}
    assert state["session"]["summary"]["review"] == 0


def test_unconfirmed_version_cannot_start(session_factory):
    with pytest.raises(ServiceError) as error:
        VocabularyStudyService(session_factory).get_or_start()
    assert error.value.code == "TEXTBOOK_NOT_CONFIRMED"


def test_new_confirmed_version_gets_separate_session(session_factory, test_settings):
    service = make_confirmed_lesson(session_factory, test_settings)
    old_state = service.get_or_start()
    with session_factory() as db:
        old_version = db.scalar(select(ConversionVersion))
        assert old_version is not None
        old_job_id = old_version.job_id
    importer = ImportService(session_factory, test_settings.storage_root)
    new_job = importer.retry(old_job_id)
    ImportWorker(
        session_factory, test_settings.storage_root, FakeConverter(), 60,
        lesson_extractor=fake_first_lesson,
    ).run_once()
    importer.confirm(new_job.id)

    new_state = service.get_or_start()
    assert new_state["session"]["id"] != old_state["session"]["id"]
    assert new_state["overview"]["wordCount"] == 2
    with pytest.raises(ServiceError) as error:
        service.advance(old_state["session"]["id"])
    assert error.value.code == "SESSION_CHANGED"
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(VocabularySession)) == 2
