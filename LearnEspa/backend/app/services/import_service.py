from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import ConversionVersion, ImportJob, ImportStatus, SourceFile, Textbook
from app.schemas.textbook_import import (
    CurrentVersionState,
    ImportJobState,
    TextbookState,
    elapsed_seconds,
)
from app.services.pdf_validation import PdfMetadata
from app.services.source_storage import StoredSource


class ServiceError(RuntimeError):
    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message


class ImportService:
    TEXTBOOK_ID = "modern-spanish-1"
    ACTIVE = (ImportStatus.QUEUED, ImportStatus.PROCESSING)

    def __init__(self, factory: sessionmaker[Session], storage_root: Path) -> None:
        self.factory = factory
        self.storage_root = storage_root

    def register_source(self, stored: StoredSource, metadata: PdfMetadata) -> SourceFile:
        with self.factory.begin() as session:
            source = session.scalar(select(SourceFile).where(SourceFile.sha256 == stored.sha256))
            if source is None:
                source = SourceFile(
                    id=str(uuid4()),
                    sha256=stored.sha256,
                    original_filename=stored.display_filename,
                    stored_path=self._relative(stored.path),
                    size_bytes=metadata.size_bytes,
                    page_count=metadata.page_count,
                )
                session.add(source)
                session.flush()
            session.expunge(source)
            return source

    def create_import(self, source_id: str, display_filename: str) -> ImportJob:
        with self.factory.begin() as session:
            active = session.scalar(select(ImportJob).where(ImportJob.status.in_(self.ACTIVE)))
            if active is not None:
                raise ServiceError("ACTIVE_JOB_EXISTS", 409, "已有教材正在解析")
            source = session.get(SourceFile, source_id)
            if source is None:
                raise ServiceError("SOURCE_NOT_FOUND", 404, "没有找到上传文件")
            job_id = str(uuid4())
            job = ImportJob(
                id=job_id,
                textbook_id=self.TEXTBOOK_ID,
                source_file_id=source.id,
                status=ImportStatus.QUEUED,
                display_filename=display_filename,
                total_pages=source.page_count,
                log_path=f"logs/jobs/{job_id}.log",
            )
            session.add(job)
            session.flush()
            session.expunge(job)
            return job

    def retry(self, job_id: str) -> ImportJob:
        with self.factory.begin() as session:
            job = session.get(ImportJob, job_id)
            if job is None:
                raise ServiceError("JOB_NOT_FOUND", 404, "没有找到解析任务")
            active = session.scalar(select(ImportJob).where(ImportJob.status.in_(self.ACTIVE)))
            if active is not None:
                raise ServiceError("ACTIVE_JOB_EXISTS", 409, "已有教材正在解析")
            if job.status not in (ImportStatus.FAILED, ImportStatus.AWAITING_CONFIRMATION, ImportStatus.CONFIRMED):
                raise ServiceError("INVALID_JOB_STATE", 409, "当前状态不能重新解析")
            new_id = str(uuid4())
            new_job = ImportJob(
                id=new_id,
                textbook_id=self.TEXTBOOK_ID,
                source_file_id=job.source_file_id,
                status=ImportStatus.QUEUED,
                display_filename=job.display_filename,
                total_pages=job.total_pages,
                log_path=f"logs/jobs/{new_id}.log",
            )
            session.add(new_job)
            session.flush()
            if job.status == ImportStatus.AWAITING_CONFIRMATION:
                job.status = ImportStatus.SUPERSEDED
                job.superseded_by_job_id = new_id
                job.updated_at = datetime.now(timezone.utc)
            session.flush()
            session.expunge(new_job)
            return new_job

    def confirm(self, job_id: str) -> ConversionVersion:
        with self.factory.begin() as session:
            job = session.get(ImportJob, job_id)
            if job is None:
                raise ServiceError("JOB_NOT_FOUND", 404, "没有找到解析任务")
            if job.status != ImportStatus.AWAITING_CONFIRMATION:
                raise ServiceError("INVALID_JOB_STATE", 409, "当前结果不能确认")
            version = session.scalar(select(ConversionVersion).where(ConversionVersion.job_id == job_id))
            if version is None:
                raise ServiceError("VERSION_NOT_FOUND", 409, "解析结果不完整")
            latest = session.scalar(
                select(ImportJob)
                .where(ImportJob.status == ImportStatus.AWAITING_CONFIRMATION)
                .order_by(ImportJob.created_at.desc())
            )
            if latest is None or latest.id != job.id:
                raise ServiceError("INVALID_JOB_STATE", 409, "该结果已被更新任务取代")
            now = datetime.now(timezone.utc)
            textbook = session.get(Textbook, self.TEXTBOOK_ID)
            assert textbook is not None
            textbook.current_version_id = version.id
            version.confirmed_at = now
            job.status = ImportStatus.CONFIRMED
            job.updated_at = now
            session.flush()
            session.expunge(version)
            return version

    def get_job(self, job_id: str) -> ImportJobState:
        with self.factory() as session:
            job = session.get(ImportJob, job_id)
            if job is None:
                raise ServiceError("JOB_NOT_FOUND", 404, "没有找到解析任务")
            return self._job_state(job)

    def get_textbook_state(self) -> TextbookState:
        with self.factory() as session:
            textbook = session.get(Textbook, self.TEXTBOOK_ID)
            assert textbook is not None
            latest = session.scalar(
                select(ImportJob).order_by(ImportJob.created_at.desc(), ImportJob.id.desc())
            )
            current = None
            if textbook.current_version_id:
                version = session.get(ConversionVersion, textbook.current_version_id)
                if version and version.confirmed_at:
                    current = CurrentVersionState(
                        id=version.id,
                        display_filename=version.display_filename,
                        page_count=version.page_count,
                        confirmed_at=version.confirmed_at,
                    )
            return TextbookState(
                id=textbook.id,
                title=textbook.title,
                current_version=current,
                latest_job=self._job_state(latest) if latest else None,
            )

    def _job_state(self, job: ImportJob) -> ImportJobState:
        return ImportJobState(
            id=job.id,
            status=job.status,
            display_filename=job.display_filename,
            total_pages=job.total_pages,
            processed_pages=job.processed_pages,
            elapsed_seconds=elapsed_seconds(job.started_at, job.finished_at),
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_code=job.error_code,
            error_message=job.error_message,
        )

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.storage_root.resolve()).as_posix()

