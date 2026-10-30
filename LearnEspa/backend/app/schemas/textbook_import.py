from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models import ImportStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CurrentVersionState(ApiModel):
    id: str
    display_filename: str
    page_count: int
    confirmed_at: datetime


class ImportJobState(ApiModel):
    id: str
    status: ImportStatus
    display_filename: str
    total_pages: int
    processed_pages: int | None = None
    elapsed_seconds: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class TextbookState(ApiModel):
    id: str
    title: str
    current_version: CurrentVersionState | None = None
    latest_job: ImportJobState | None = None


class ApiEnvelope(ApiModel):
    code: int = 0
    message: str = "ok"
    data: object | None = None


def elapsed_seconds(started_at: datetime | None, finished_at: datetime | None = None) -> int:
    if started_at is None:
        return 0
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    end = finished_at or datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0, int((end - started_at).total_seconds()))

