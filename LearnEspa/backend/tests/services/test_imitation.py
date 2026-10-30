from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import (
    ConversionVersion, ImitationAttempt, ImitationRound, ImportJob, ImportStatus,
    Lesson, Passage, SourceFile, Textbook,
)
from app.services.imitation import ImitationService
from app.services.import_service import ServiceError
from app.services.sentence_preparation import derive_units


class FakeGateway:
    def __init__(self) -> None:
        self.judgments: list[dict | Exception] = []
        self.audit_ok = True
        self.report_error_once = False
        self.memory_error_once = False
        self.purposes: list[str] = []

    def generate_structured(self, purpose: str, _system: str, prompt: str, _schema: dict):
        self.purposes.append(purpose)
        data = json.loads(prompt)
        if purpose == "memory_open":
            return {"focus": ["练习教材句式"], "evidence_ids": []}, None
        if purpose == "imitation_plan":
            return {"items": [{
                "source_sentence_id": item["id"],
                "expected_pattern": item["core_pattern"] or item["source_text"].strip("¿?.!"),
                "fixed_collocations": [], "scene_role": "保留对话轮次",
            } for item in data["source"]]}, None
        if purpose in ("imitation_compose", "imitation_repair"):
            return {"background": "两位新同学在校园相遇。", "items": [{
                "source_sentence_id": item["id"], "speaker": item["speaker"],
                "chinese_text": "请按教材句式介绍自己。", "hint": "两人刚认识。",
            } for item in data["source"]]}, None
        if purpose == "imitation_audit":
            return {"approved": self.audit_ok, "issues": [] if self.audit_ok else ["场景不合理"]}, None
        if purpose == "imitation_feedback":
            answer = self.judgments.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer, None
        if purpose == "memory_reflect":
            if self.memory_error_once:
                self.memory_error_once = False
                raise ServiceError("MODEL_TIMEOUT", 504, "模型超时")
            return {"summary": "本轮练习已完成", "evidence_ids": []}, None
        if purpose == "imitation_report":
            if self.report_error_once:
                self.report_error_once = False
                raise ServiceError("MODEL_TIMEOUT", 504, "模型超时")
            return {
                "summary": "第一句用对，第二句手动通过。", "recurring_issues": [],
                "comparison": None, "next_suggestions": ["下次再练第二句"],
                "cited_attempt_ids": [],
            }, None
        raise AssertionError(purpose)


def feedback(verdict: str) -> dict:
    return {
        "verdict": verdict,
        "meaning_ok": verdict != "rejected", "grammar_ok": verdict != "rejected",
        "pattern_used": verdict == "passed", "pattern_attempted": verdict != "alternative",
        "explanation": "请按教材句式修改" if verdict == "rejected" else "表达正确",
        "revision": "Me llamo Rosa." if verdict in ("alternative", "rejected") else None,
    }


def confirmed_passage(factory) -> str:
    with factory.begin() as db:
        source = SourceFile(id=str(uuid4()), sha256="b" * 64, original_filename="book.pdf",
                            stored_path="originals/book.pdf", size_bytes=10, page_count=305)
        db.add(source)
        db.flush()
        job = ImportJob(id=str(uuid4()), textbook_id="modern-spanish-1", source_file_id=source.id,
                        status=ImportStatus.CONFIRMED, display_filename="book.pdf", total_pages=305,
                        log_path="logs/job.log")
        db.add(job)
        db.flush()
        version = ConversionVersion(
            id=str(uuid4()), textbook_id="modern-spanish-1", source_file_id=source.id,
            job_id=job.id, display_filename="book.pdf", converter_name="docling",
            converter_version="test", configuration_version="test", markdown_path="document.md",
            docling_json_path="document.json", report_path="report.json", log_path="logs/job.log",
            page_count=305, duration_seconds=1.0, confirmed_at=datetime.now(timezone.utc),
        )
        db.add(version)
        db.flush()
        db.get(Textbook, "modern-spanish-1").current_version_id = version.id
        lesson = Lesson(id=str(uuid4()), conversion_version_id=version.id, lesson_number=1,
                        title="第一课", page_start=16, page_end=31)
        passage = Passage(id=str(uuid4()), lesson_id=lesson.id, ordinal=1,
                          title="认识新同学", content="Ana: Me llamo Ana. ¿Cómo te llamas?",
                          source_page_start=17, source_page_end=17,
                          raw_ocr="Ana: Me llamo Ana. ¿Cómo te llamas?")
        db.add_all([lesson, passage])
        return passage.id


def test_sentence_split_keeps_dialogue_speaker_and_source_line():
    units = derive_units("Ana: Me llamo Ana. ¿Cómo te llamas?\nSoy estudiante.")
    assert [(item.speaker, item.text, item.source_line) for item in units] == [
        ("Ana", "Me llamo Ana.", 1),
        ("Ana", "¿Cómo te llamas?", 1),
        (None, "Soy estudiante.", 2),
    ]
    assert derive_units("Ana: iEs cubano?")[0].text == "¿Es cubano?"


def test_round_resumes_after_model_error_and_manual_pass_is_neutral(session_factory):
    passage_id = confirmed_passage(session_factory)
    gateway = FakeGateway()
    service = ImitationService(session_factory, gateway)
    assert service.get_passages()[0]["sentence_count"] == 2
    practice = service.start_or_resume(passage_id)
    round_id = practice["id"]
    assert practice["total"] == 2
    assert service.start_or_resume(passage_id)["id"] == round_id

    service.save_draft(round_id, "Me llamo Rosa.")
    gateway.judgments = [ServiceError("MODEL_TIMEOUT", 504, "模型超时"), feedback("passed")]
    with pytest.raises(ServiceError, match="模型超时"):
        service.submit_answer(round_id, "request-one", "Me llamo Rosa.", "hidden", False)
    with session_factory() as db:
        pending = db.scalar(select(ImitationAttempt).where(ImitationAttempt.request_id == "request-one"))
        assert pending is not None and pending.status == "pending"
        assert pending.submitted_text == "Me llamo Rosa."
    assert service.get_round(round_id)["draft"] == "Me llamo Rosa."
    passed = service.submit_answer(round_id, "request-one", "Me llamo Rosa.", "hidden", False)
    assert passed["can_next"] is True
    assert service.submit_answer(round_id, "request-one", "Me llamo Rosa.", "hidden", False)["can_next"]

    practice = service.advance(round_id)
    assert practice["current_index"] == 1
    gateway.judgments = [feedback("rejected")] * 3
    for index in range(3):
        practice = service.submit_answer(round_id, f"request-{index + 2}", "No sé.", "masked", True)
    assert practice["rejection_count"] == 3
    assert practice["can_manual_pass"] is True
    practice = service.advance(round_id, manual_pass=True)
    assert practice["status"] == "completed"
    report = service.get_report(round_id)
    assert report["status"] == "ready"
    assert report["counts"] == {"first_pass": 1, "revised": 0, "alternative": 0, "manual_pass": 1}
    assert report["pattern_evidence"][1]["this_round"] is None

    fresh = service.start_or_resume(passage_id)
    assert fresh["id"] != round_id
    assert len(service.history(passage_id)) == 2


def test_failed_quality_audit_never_creates_round(session_factory):
    passage_id = confirmed_passage(session_factory)
    gateway = FakeGateway()
    gateway.audit_ok = False
    service = ImitationService(session_factory, gateway)
    with pytest.raises(ServiceError) as error:
        service.start_or_resume(passage_id)
    assert error.value.code == "COMPOSITION_AUDIT_FAILED"
    assert gateway.purposes.count("imitation_repair") == 1
    with session_factory() as db:
        assert list(db.scalars(select(ImitationRound))) == []


def test_correct_alternative_can_advance_after_optional_rewrite_fails(session_factory):
    passage_id = confirmed_passage(session_factory)
    gateway = FakeGateway()
    service = ImitationService(session_factory, gateway)
    round_id = service.start_or_resume(passage_id)["id"]
    gateway.judgments = [feedback("alternative"), feedback("rejected"), feedback("passed")]
    alternative = service.submit_answer(round_id, "alt", "Soy Rosa.", "normal", False)
    assert alternative["feedback"]["verdict"] == "alternative"
    assert alternative["can_next"]
    retry = service.submit_answer(round_id, "rewrite", "Me nombre Rosa.", "normal", False)
    assert retry["feedback"]["verdict"] == "rejected"
    assert retry["can_next"]  # A correct alternative cannot be revoked by an optional rewrite.
    service.advance(round_id)
    service.submit_answer(round_id, "second", "¿Y tú?", "hidden", False)
    service.advance(round_id)
    report = service.get_report(round_id)
    assert report["counts"]["alternative"] == 1
    assert report["counts"]["first_pass"] == 1
    assert report["pattern_evidence"][0]["this_round"] == 0.0
    assert report["weak_patterns"]


def test_report_failure_does_not_undo_completion_and_can_retry(session_factory):
    passage_id = confirmed_passage(session_factory)
    gateway = FakeGateway()
    gateway.report_error_once = True
    service = ImitationService(session_factory, gateway)
    round_id = service.start_or_resume(passage_id)["id"]
    gateway.judgments = [feedback("passed"), feedback("passed")]
    for index in range(2):
        service.submit_answer(round_id, f"answer-{index}", "Me llamo Rosa.", "masked", False)
        service.advance(round_id)
    assert service.get_round(round_id)["status"] == "completed"
    assert service.get_report(round_id)["status"] == "failed"
    assert service.retry_report(round_id)["status"] == "ready"


def test_memory_retry_keeps_already_ready_report(session_factory):
    passage_id = confirmed_passage(session_factory)
    gateway = FakeGateway()
    gateway.memory_error_once = True
    service = ImitationService(session_factory, gateway)
    round_id = service.start_or_resume(passage_id)["id"]
    gateway.judgments = [feedback("passed"), feedback("passed")]
    for index in range(2):
        service.submit_answer(round_id, f"answer-{index}", "Me llamo Rosa.", "hidden", False)
        service.advance(round_id)
    report = service.get_report(round_id)
    assert report["status"] == "ready" and report["memory_status"] == "pending"
    assert report["error"] == "模型超时"
    report_calls = gateway.purposes.count("imitation_report")
    retry = service.retry_report(round_id)
    assert retry["memory_status"] == "ready" and retry["error"] is None
    assert gateway.purposes.count("imitation_report") == report_calls
