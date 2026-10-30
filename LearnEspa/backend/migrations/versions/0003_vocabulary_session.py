"""Persist first lesson vocabulary sessions and attempts."""

from alembic import op
import sqlalchemy as sa


revision = "0003_vocabulary_session"
down_revision = "0002_first_lesson"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vocabulary_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("feedback_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("lesson_id"),
    )
    op.create_index("ix_vocabulary_sessions_lesson_id", "vocabulary_sessions", ["lesson_id"])
    op.create_table(
        "vocabulary_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("vocabulary_sessions.id"), nullable=False),
        sa.Column("word_id", sa.String(36), sa.ForeignKey("vocabulary_entries.id"), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("submitted_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "request_id"),
    )
    op.create_index("ix_vocabulary_attempts_session_id", "vocabulary_attempts", ["session_id"])


def downgrade() -> None:
    op.drop_table("vocabulary_attempts")
    op.drop_table("vocabulary_sessions")
