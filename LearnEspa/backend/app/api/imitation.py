from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.textbook_imports import envelope
from app.schemas.imitation import AnswerRequest, DraftRequest, NextRequest, PreferenceRequest
from app.services.imitation import ImitationService


router = APIRouter(prefix="/api/imitation", tags=["imitation"])


def get_service(request: Request) -> ImitationService:
    return request.app.state.imitation_service


@router.get("/passages")
def list_passages(service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.get_passages())


@router.get("/history")
def all_history(service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.all_history())


@router.get("/preferences")
def get_preferences(service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.get_preferences())


@router.put("/preferences")
def set_preferences(payload: PreferenceRequest, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.set_preferences(payload.default_source_mode))


@router.post("/passages/{passage_id}/rounds")
def start_round(passage_id: str, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.start_or_resume(passage_id))


@router.get("/passages/{passage_id}/history")
def list_history(passage_id: str, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.history(passage_id))


@router.get("/rounds/{round_id}")
def get_round(round_id: str, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.get_round(round_id))


@router.put("/rounds/{round_id}/draft")
def save_draft(round_id: str, payload: DraftRequest, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.save_draft(round_id, payload.text))


@router.post("/rounds/{round_id}/answers")
def submit_answer(round_id: str, payload: AnswerRequest, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.submit_answer(
        round_id, payload.request_id, payload.answer, payload.source_mode, payload.hint_viewed,
    ))


@router.post("/rounds/{round_id}/next")
def next_sentence(round_id: str, payload: NextRequest, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.advance(round_id, payload.manual_pass))


@router.get("/rounds/{round_id}/report")
def get_report(round_id: str, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.get_report(round_id))


@router.post("/rounds/{round_id}/report/retry")
def retry_report(round_id: str, service: ImitationService = Depends(get_service)) -> dict:
    return envelope(service.retry_report(round_id))
