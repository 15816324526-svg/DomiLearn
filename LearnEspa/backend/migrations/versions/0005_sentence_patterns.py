"""Add traceable fixed patterns to prepared source sentences."""

from alembic import op
import sqlalchemy as sa


revision = "0005_sentence_patterns"
down_revision = "0004_imitation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("passage_sentences", sa.Column("core_pattern", sa.Text(), nullable=True))
    op.add_column("passage_sentences", sa.Column("fixed_collocations_json", sa.Text(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("passage_sentences", "fixed_collocations_json")
    op.drop_column("passage_sentences", "core_pattern")
