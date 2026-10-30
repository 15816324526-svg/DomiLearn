from __future__ import annotations

import json
import time
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.converters.fake import FakeConverter
from app.main import create_app
from app.services.imitation import ImitationService


class StubModel:
    def generate_structured(self, purpose, _system, prompt, _schema):
        data = json.loads(prompt)
        if purpose == "memory_open":
            return {"focus": [], "evidence_ids": []}, None
        if purpose == "imitation_plan":
            return {"items": [{"source_sentence_id": item["id"], "expected_pattern": "Hola",
                               "fixed_collocations": [], "scene_role": "问候"} for item in data["source"]]}, None
        if purpose in ("imitation_compose", "imitation_repair"):
            return {"background": "新同学在校园见面。", "items": [{
                "source_sentence_id": item["id"], "speaker": item["speaker"],
                "chinese_text": "你好。", "hint": "首次见面。",
            } for item in data["source"]]}, None
        if purpose == "imitation_audit":
            return {"approved": True, "issues": []}, None
        if purpose == "imitation_feedback":
            return {
                "verdict": "passed", "meaning_ok": True, "grammar_ok": True,
                "pattern_used": True, "pattern_attempted": True,
                "explanation": "表达正确", "revision": None,
            }, None
        if purpose == "memory_reflect":
            return {"summary": "完成", "evidence_ids": []}, None
        if purpose == "imitation_report":
            return {"summary": "用对问候句", "recurring_issues": [], "comparison": None,
                    "next_suggestions": [], "cited_attempt_ids": []}, None
        raise AssertionError(purpose)


def _pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_blank_page(width=100, height=100)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_imitation_http_flow_uses_persisted_backend_not_mock(test_settings):
    app = create_app(test_settings, FakeConverter())
    app.state.imitation_service = ImitationService(app.state.session_factory, StubModel())
    with TestClient(app) as client:
        missing = client.get("/api/imitation/passages")
        assert missing.status_code == 409
        job = client.post("/api/textbooks/modern-spanish-1/imports", files={
            "file": ("book.pdf", _pdf(), "application/pdf"),
        }).json()["data"]["id"]
        for _ in range(100):
            status = client.get(f"/api/textbook-imports/{job}").json()["data"]["status"]
            if status == "awaiting_confirmation":
                break
            time.sleep(0.02)
        assert status == "awaiting_confirmation"
        assert client.post(f"/api/textbook-imports/{job}/confirm").status_code == 200
        passages = client.get("/api/imitation/passages").json()["data"]
        first_id = passages[0]["id"]
        assert passages[0]["ready"] is True
        assert client.put("/api/imitation/preferences", json={"default_source_mode": "hidden"}).json()["data"]["default_source_mode"] == "hidden"
        practice = client.post(f"/api/imitation/passages/{first_id}/rounds").json()["data"]
        round_id = practice["id"]
        assert practice["default_source_mode"] == "hidden"
        assert client.post(f"/api/imitation/passages/{first_id}/rounds").json()["data"]["id"] == round_id
        assert client.put(f"/api/imitation/rounds/{round_id}/draft", json={"text": "Hola."}).json()["data"]["draft"] == "Hola."
        answered = client.post(f"/api/imitation/rounds/{round_id}/answers", json={
            "request_id": "same-answer", "answer": "Hola.", "source_mode": "hidden", "hint_viewed": False,
        }).json()["data"]
        assert answered["feedback"]["verdict"] == "passed"
        assert answered["can_next"]
        done = client.post(f"/api/imitation/rounds/{round_id}/next", json={"manual_pass": False}).json()["data"]
        assert done["status"] == "completed"
        assert client.get(f"/api/imitation/rounds/{round_id}/report").json()["data"]["status"] == "ready"
        assert client.get("/api/imitation/history").json()["data"][0]["id"] == round_id
        assert client.get("/api/model-settings").json()["data"]["has_api_key"] is False
