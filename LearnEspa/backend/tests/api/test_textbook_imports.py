import time
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.converters.fake import FakeConverter
from app.main import create_app


def pdf_bytes(pages: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_upload_process_confirm_and_refresh(test_settings):
    app = create_app(test_settings, FakeConverter())
    with TestClient(app) as client:
        empty = client.get("/api/textbooks/modern-spanish-1").json()["data"]
        assert empty["currentVersion"] is None

        response = client.post(
            "/api/textbooks/modern-spanish-1/imports",
            files={"file": ("改名教材.pdf", pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 202
        job_id = response.json()["data"]["id"]
        for _ in range(50):
            job = client.get(f"/api/textbook-imports/{job_id}").json()["data"]
            if job["status"] == "awaiting_confirmation":
                break
            time.sleep(0.02)
        assert job["status"] == "awaiting_confirmation"

        confirmed = client.post(f"/api/textbook-imports/{job_id}/confirm")
        assert confirmed.status_code == 200
        state = client.get("/api/textbooks/modern-spanish-1").json()["data"]
        assert state["currentVersion"]["displayFilename"] == "改名教材.pdf"


def test_rejects_non_pdf(test_settings):
    app = create_app(test_settings, FakeConverter())
    with TestClient(app) as client:
        response = client.post(
            "/api/textbooks/modern-spanish-1/imports",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_PDF"

