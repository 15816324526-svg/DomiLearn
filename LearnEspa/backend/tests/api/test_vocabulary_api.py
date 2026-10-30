from __future__ import annotations

import time
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.converters.fake import FakeConverter
from app.main import create_app


def pdf_bytes() -> bytes:
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_vocabulary_api_requires_confirmed_book_and_persists_feedback(test_settings):
    app = create_app(test_settings, FakeConverter())
    with TestClient(app) as client:
        missing = client.get("/api/vocabulary/lesson/1")
        assert missing.status_code == 409
        assert missing.json()["code"] == "TEXTBOOK_NOT_CONFIRMED"

        uploaded = client.post(
            "/api/textbooks/modern-spanish-1/imports",
            files={"file": ("book.pdf", pdf_bytes(), "application/pdf")},
        )
        assert uploaded.status_code == 202
        job_id = uploaded.json()["data"]["id"]
        for _ in range(100):
            status = client.get(f"/api/textbook-imports/{job_id}").json()["data"]["status"]
            if status == "awaiting_confirmation":
                break
            time.sleep(0.02)
        assert status == "awaiting_confirmation"
        assert client.post(f"/api/textbook-imports/{job_id}/confirm").status_code == 200

        started = client.get("/api/vocabulary/lesson/1")
        assert started.status_code == 200
        state = started.json()["data"]
        assert state["overview"]["wordCount"] == 2
        current = state["session"]
        assert current["stage"] == "choice"
        assert "answer" not in current["question"]

        request_id = str(uuid4())
        payload = {
            "session_id": current["id"], "question_id": current["question"]["id"],
            "request_id": request_id, "answer": None,
        }
        answered = client.post("/api/vocabulary/lesson/1/answers", json=payload)
        assert answered.status_code == 200
        result = answered.json()["data"]["session"]
        assert result["feedback"]["correct"] is False
        assert result["feedback"]["correctAnswer"] == "你好"
        assert client.post("/api/vocabulary/lesson/1/answers", json=payload).json()["data"]["session"] == result
        assert client.get("/api/vocabulary/lesson/1").json()["data"]["session"] == result
        blocked = client.post("/api/vocabulary/lesson/1/answers", json={**payload, "request_id": str(uuid4())})
        assert blocked.status_code == 409
        next_state = client.post("/api/vocabulary/lesson/1/next", json={"session_id": current["id"]})
        assert next_state.status_code == 200
        next_question = next_state.json()["data"]["session"]["question"]
        assert next_question["id"] != current["question"]["id"]
        correct_index = next_question["options"].index("天")
        correct = client.post("/api/vocabulary/lesson/1/answers", json={
            "session_id": current["id"], "question_id": next_question["id"],
            "request_id": str(uuid4()), "answer": correct_index,
        })
        assert correct.status_code == 200
        assert correct.json()["data"]["session"]["feedback"]["correct"] is True
