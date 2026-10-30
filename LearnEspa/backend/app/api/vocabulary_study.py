from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request

from app.api.textbook_imports import envelope
from app.schemas.vocabulary_study import AnswerRequest, NextRequest
from app.services.vocabulary_study import VocabularyStudyService


router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])


def get_service(request: Request) -> VocabularyStudyService:
    return request.app.state.vocabulary_study_service


@router.get("/lessons")
def list_lessons(service: VocabularyStudyService = Depends(get_service)) -> dict:
    return envelope(service.list_lessons())


@router.get("/lesson/{lesson_number}")
def get_study(lesson_number: int = Path(ge=1, le=16), service: VocabularyStudyService = Depends(get_service)) -> dict:
    return envelope(service.get_or_start(lesson_number))


@router.post("/lesson/{lesson_number}/answers")
def submit_answer(payload: AnswerRequest, lesson_number: int = Path(ge=1, le=16), service: VocabularyStudyService = Depends(get_service)) -> dict:
    return envelope(service.submit(payload.session_id, payload.question_id, payload.answer, payload.request_id, lesson_number))


@router.post("/lesson/{lesson_number}/next")
def next_question(payload: NextRequest, lesson_number: int = Path(ge=1, le=16), service: VocabularyStudyService = Depends(get_service)) -> dict:
    return envelope(service.advance(payload.session_id, lesson_number))


#vocabulary_study.py
#GET  /api/vocabulary/lessons
#GET  /api/vocabulary/lesson/{lesson_number}
#POST /api/vocabulary/lesson/{lesson_number}/answers
#POST /api/vocabulary/lesson/{lesson_number}/next
