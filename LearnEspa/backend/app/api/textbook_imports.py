from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_import_service, get_source_storage, get_worker
from app.schemas.textbook_import import ImportJobState, TextbookState
from app.services.import_service import ImportService
from app.services.pdf_validation import validate_staged_pdf
from app.services.source_storage import SourceStorage, StagedUpload
from app.workers.import_worker import ImportWorker


router = APIRouter(prefix="/api", tags=["textbook-import"])


def envelope(data, message: str = "ok") -> dict:
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json", by_alias=True)
    return {"code": 0, "message": message, "data": data}


@router.get("/textbooks/modern-spanish-1")
def get_textbook(service: ImportService = Depends(get_import_service)) -> dict:
    return envelope(service.get_textbook_state())


@router.post("/textbooks/modern-spanish-1/imports", status_code=202)
async def import_textbook(
    file: UploadFile = File(...),
    storage: SourceStorage = Depends(get_source_storage),
    service: ImportService = Depends(get_import_service),
    worker: ImportWorker = Depends(get_worker),
) -> dict:
    staged: StagedUpload | None = None
    try:
        staged = await storage.stage_upload(file)
        metadata = validate_staged_pdf(
            staged.path,
            staged.display_filename,
            storage.max_bytes,
            known_sha256=staged.sha256,
        )
        stored = storage.finalize(staged, metadata)
        staged = None
        source = service.register_source(stored, metadata)
        job = service.create_import(source.id, stored.display_filename)
        worker.wake()
        return envelope(service.get_job(job.id), "已开始解析")
    finally:
        storage.cleanup(staged)
        await file.close()


@router.get("/textbook-imports/{job_id}")
def get_import(job_id: str, service: ImportService = Depends(get_import_service)) -> dict:
    return envelope(service.get_job(job_id))


@router.post("/textbook-imports/{job_id}/confirm")
def confirm_import(job_id: str, service: ImportService = Depends(get_import_service)) -> dict:
    service.confirm(job_id)
    return envelope(service.get_textbook_state(), "教材版本已确认")


@router.post("/textbook-imports/{job_id}/retry", status_code=202)
def retry_import(
    job_id: str,
    service: ImportService = Depends(get_import_service),
    worker: ImportWorker = Depends(get_worker),
) -> dict:
    job = service.retry(job_id)
    worker.wake()
    return envelope(service.get_job(job.id), "已重新开始解析")

#文件上传涉及等待输入和文件操作，因此使用异步方式。