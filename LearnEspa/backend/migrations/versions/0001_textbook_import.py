"""Create the textbook import schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001_textbook_import"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("stored_path", sa.String(1000), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("sha256"),
    )
    op.create_index("ix_source_files_sha256", "source_files", ["sha256"], unique=True)

    op.create_table(
        "textbooks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("current_version_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["current_version_id"], ["conversion_versions.id"]),
    )

    status_enum = sa.Enum(
        "QUEUED", "PROCESSING", "AWAITING_CONFIRMATION", "CONFIRMED", "FAILED", "SUPERSEDED",
        name="importstatus",
    )
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("textbook_id", sa.String(64), nullable=False),
        sa.Column("source_file_id", sa.String(36), nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("display_filename", sa.String(500), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_pages", sa.Integer(), nullable=True),
        sa.Column("total_pages", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("log_path", sa.String(1000), nullable=False),
        sa.Column("superseded_by_job_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["textbook_id"], ["textbooks.id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.ForeignKeyConstraint(["superseded_by_job_id"], ["import_jobs.id"]),
    )
    op.create_index("ix_import_jobs_textbook_id", "import_jobs", ["textbook_id"])
    op.create_index("ix_import_jobs_source_file_id", "import_jobs", ["source_file_id"])
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"])

    op.create_table(
        "conversion_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("textbook_id", sa.String(64), nullable=False),
        sa.Column("source_file_id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("display_filename", sa.String(500), nullable=False),
        sa.Column("converter_name", sa.String(100), nullable=False),
        sa.Column("converter_version", sa.String(100), nullable=False),
        sa.Column("configuration_version", sa.String(100), nullable=False),
        sa.Column("markdown_path", sa.String(1000), nullable=False),
        sa.Column("docling_json_path", sa.String(1000), nullable=False),
        sa.Column("report_path", sa.String(1000), nullable=False),
        sa.Column("log_path", sa.String(1000), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["textbook_id"], ["textbooks.id"]),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["import_jobs.id"]),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_conversion_versions_textbook_id", "conversion_versions", ["textbook_id"])
    op.create_index("ix_conversion_versions_source_file_id", "conversion_versions", ["source_file_id"])
    op.create_index("ix_conversion_versions_job_id", "conversion_versions", ["job_id"], unique=True)

    op.execute(
        sa.text(
            "INSERT INTO textbooks (id, title, current_version_id, created_at, updated_at) "
            "VALUES (:id, :title, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ).bindparams(id="modern-spanish-1", title="现代西班牙语1")
    )


def downgrade() -> None:
    op.drop_table("conversion_versions")
    op.drop_table("import_jobs")
    op.drop_table("textbooks")
    op.drop_table("source_files")
