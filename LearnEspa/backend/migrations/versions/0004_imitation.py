"""Persist textbook sentence practice, attempts, memory and reports."""

from alembic import op
import sqlalchemy as sa


revision = "0004_imitation"
down_revision = "0003_vocabulary_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "passage_sentences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("passage_id", sa.String(36), sa.ForeignKey("passages.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(100)),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("source_line", sa.Integer(), nullable=False),
        sa.Column("preparation_issue", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("passage_id", "ordinal"),
    )
    op.create_index("ix_passage_sentences_passage_id", "passage_sentences", ["passage_id"])
    op.create_table(
        "imitation_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("default_source_mode", sa.String(20), nullable=False),
    )
    op.create_table(
        "imitation_rounds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("passage_id", sa.String(36), sa.ForeignKey("passages.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("current_index", sa.Integer(), nullable=False),
        sa.Column("draft", sa.Text(), nullable=False),
        sa.Column("source_mode", sa.String(20), nullable=False),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_imitation_rounds_passage_id", "imitation_rounds", ["passage_id"])
    op.create_table(
        "planned_sentences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("round_id", sa.String(36), sa.ForeignKey("imitation_rounds.id"), nullable=False),
        sa.Column("source_sentence_id", sa.String(36), sa.ForeignKey("passage_sentences.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(100)),
        sa.Column("chinese_text", sa.Text(), nullable=False),
        sa.Column("hint", sa.Text()),
        sa.Column("expected_pattern", sa.Text(), nullable=False),
        sa.Column("fixed_collocations_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("round_id", "ordinal"),
    )
    op.create_index("ix_planned_sentences_round_id", "planned_sentences", ["round_id"])
    op.create_table(
        "imitation_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("round_id", sa.String(36), sa.ForeignKey("imitation_rounds.id"), nullable=False),
        sa.Column("planned_sentence_id", sa.String(36), sa.ForeignKey("planned_sentences.id"), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("submitted_text", sa.Text(), nullable=False),
        sa.Column("source_mode", sa.String(20), nullable=False),
        sa.Column("hint_viewed", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("feedback_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("round_id", "request_id"),
    )
    op.create_index("ix_imitation_attempts_round_id", "imitation_attempts", ["round_id"])
    op.create_table(
        "imitation_call_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("round_id", sa.String(36), sa.ForeignKey("imitation_rounds.id")),
        sa.Column("purpose", sa.String(60), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("total_tokens", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_imitation_call_usage_round_id", "imitation_call_usage", ["round_id"])
    op.create_table(
        "imitation_memory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("round_id", sa.String(36), sa.ForeignKey("imitation_rounds.id"), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("round_id"),
    )
    op.create_table(
        "imitation_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("round_id", sa.String(36), sa.ForeignKey("imitation_rounds.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("summary_json", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("round_id"),
    )


def downgrade() -> None:
    for table in (
        "imitation_reports", "imitation_memory", "imitation_call_usage",
        "imitation_attempts", "planned_sentences", "imitation_rounds",
        "imitation_preferences", "passage_sentences",
    ):
        op.drop_table(table)
