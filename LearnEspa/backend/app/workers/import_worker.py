from __future__ import annotations

import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.converters.base import ConversionError, ConversionRequest, PdfConverter
from app.models import ConversionVersion, ImportJob, ImportStatus, SourceFile
from app.services.lesson_extraction import LessonExtraction
from app.services.book_extraction import ExtractedLesson, extract_book
from app.services.lesson_repository import save_book, save_first_lesson


class ImportWorker:
    def __init__(
        self,
        factory: sessionmaker[Session],
        storage_root: Path,
        converter: PdfConverter,
        timeout_seconds: int,
        poll_seconds: float = 1.0,
        lesson_extractor: Callable[[Path, Path], LessonExtraction | tuple[ExtractedLesson, ...]] = extract_book,
    ) -> None:
        self.factory = factory
        self.storage_root = storage_root
        self.converter = converter
        self.timeout_seconds = timeout_seconds
        self.poll_seconds = poll_seconds
        self.lesson_extractor = lesson_extractor
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="textbook-import-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=5)

    def wake(self) -> None:
        self._wake.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            processed = self.run_once()
            if not processed:
                self._wake.wait(self.poll_seconds)
                self._wake.clear()

    def run_once(self) -> bool:
        with self.factory.begin() as session:
            job = session.scalar(
                select(ImportJob)
                .where(ImportJob.status == ImportStatus.QUEUED)
                .order_by(ImportJob.created_at.asc())
            )
            if job is None:
                return False
            job.status = ImportStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            job.error_code = None
            job.error_message = None
            job_id = job.id
            source_id = job.source_file_id
            display_filename = job.display_filename
            total_pages = job.total_pages

        with self.factory() as session:
            source = session.get(SourceFile, source_id)
            assert source is not None
            source_path = self.storage_root / source.stored_path

        work_dir = self.storage_root / ".tmp" / "conversions" / job_id
        final_dir = self.storage_root / "textbooks" / "modern-spanish-1" / "conversions" / job_id
        log_path = self.storage_root / "logs" / "jobs" / f"{job_id}.log"
        shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        published = False
        try:
            result = self.converter.convert(
                ConversionRequest(job_id, source_path, work_dir, total_pages, self.timeout_seconds)
            )
            extraction = self.lesson_extractor(source_path, result.json_path)
            if isinstance(extraction, tuple):
                if len(extraction) != 16 or any(lesson.issues for lesson in extraction):
                    raise ValueError("教材未能完整解析 16 课")
            if final_dir.exists():
                raise RuntimeError("目标版本目录已存在")
            os.replace(work_dir, final_dir)
            published = True
            version_id = str(uuid4())
            with self.factory.begin() as session:
                job = session.get(ImportJob, job_id)
                assert job is not None
                version = ConversionVersion(
                    id=version_id,
                    textbook_id=job.textbook_id,
                    source_file_id=job.source_file_id,
                    job_id=job.id,
                    display_filename=display_filename,
                    converter_name=result.converter_name,
                    converter_version=result.converter_version,
                    configuration_version=result.configuration_version,
                    markdown_path=self._relative(final_dir / "document.md"),
                    docling_json_path=self._relative(final_dir / "document.json"),
                    report_path=self._relative(final_dir / "report.json"),
                    log_path=self._relative(log_path),
                    page_count=result.page_count,
                    duration_seconds=result.duration_seconds,
                )
                session.add(version)
                session.flush()
                if isinstance(extraction, tuple):
                    save_book(session, version_id, extraction)
                else:
                    save_first_lesson(session, version_id, extraction)
                job.status = ImportStatus.AWAITING_CONFIRMATION
                job.finished_at = datetime.now(timezone.utc)
                job.processed_pages = result.page_count
                job.updated_at = datetime.now(timezone.utc)
            passages = sum(len(lesson.passages) for lesson in extraction) if isinstance(extraction, tuple) else len(extraction.passages)
            words = sum(len(lesson.vocabulary) for lesson in extraction) if isinstance(extraction, tuple) else len(extraction.vocabulary)
            log_path.write_text(f"转换和分类成功：{passages} 篇课文、{words} 条单词\n", encoding="utf-8")
        except Exception as exc:
            code = exc.code if isinstance(exc, ConversionError) else "CONVERSION_FAILED"
            message = str(exc) if isinstance(exc, ConversionError) else "教材解析失败，请重新解析"
            log_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
            shutil.rmtree(work_dir, ignore_errors=True)
            if published:
                shutil.rmtree(final_dir, ignore_errors=True)
            with self.factory.begin() as session:
                job = session.get(ImportJob, job_id)
                assert job is not None
                job.status = ImportStatus.FAILED
                job.error_code = code
                job.error_message = message
                job.finished_at = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)
        return True

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.storage_root.resolve()).as_posix()

