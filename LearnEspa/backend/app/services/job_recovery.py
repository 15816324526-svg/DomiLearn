from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import ImportJob, ImportStatus


def recover_interrupted_jobs(session: Session) -> int:
    result = session.execute(
        update(ImportJob)
        .where(ImportJob.status.in_((ImportStatus.QUEUED, ImportStatus.PROCESSING)))
        .values(
            status=ImportStatus.FAILED,
            error_code="INTERRUPTED",
            error_message="上次解析被中断，请重新解析",
            finished_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    return int(result.rowcount or 0)

