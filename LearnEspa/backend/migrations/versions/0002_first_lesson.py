"""Store extracted lesson, vocabulary and passages by conversion version."""

from alembic import op
import sqlalchemy as sa


revision = "0002_first_lesson"
down_revision = "0001_textbook_import"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lessons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversion_version_id", sa.String(36), sa.ForeignKey("conversion_versions.id"), nullable=False),
        sa.Column("lesson_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("conversion_version_id", "lesson_number"),
    )
    op.create_index("ix_lessons_conversion_version_id", "lessons", ["conversion_version_id"])
    op.create_table(
        "vocabulary_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("headword", sa.String(300), nullable=False),
        sa.Column("part_of_speech", sa.String(100), nullable=True),
        sa.Column("meaning", sa.Text(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("raw_ocr", sa.Text(), nullable=False),
        sa.UniqueConstraint("lesson_id", "ordinal"),
    )
    op.create_index("ix_vocabulary_entries_lesson_id", "vocabulary_entries", ["lesson_id"])
    op.create_table(
        "passages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("lesson_id", sa.String(36), sa.ForeignKey("lessons.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_page_start", sa.Integer(), nullable=False),
        sa.Column("source_page_end", sa.Integer(), nullable=False),
        sa.Column("raw_ocr", sa.Text(), nullable=False),
        sa.UniqueConstraint("lesson_id", "ordinal"),
    )
    op.create_index("ix_passages_lesson_id", "passages", ["lesson_id"])


def downgrade() -> None:
    op.drop_table("passages")
    op.drop_table("vocabulary_entries")
    op.drop_table("lessons")
