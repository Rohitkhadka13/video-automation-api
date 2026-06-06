# =============================================================================
# alembic/versions/001_initial_schema.py
# Initial database schema — all tables, ENUMs, indexes, triggers.
# Written to be fully idempotent: safe to run on a fresh or partially-migrated DB.
# =============================================================================
"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


# ---------------------------------------------------------------------------
# Helper — create ENUM type only if it doesn't already exist
# ---------------------------------------------------------------------------

def _create_enum_if_not_exists(name: str, *values: str) -> None:
    """
    Create a PostgreSQL ENUM type safely.
    Uses DO $$ ... EXCEPTION WHEN duplicate_object THEN null $$
    so re-running the migration on a partially-migrated DB never crashes.
    """
    values_sql = ", ".join(f"'{v}'" for v in values)
    op.execute(f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({values_sql});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)


def upgrade() -> None:

    # ------------------------------------------------------------------
    # Step 1 — ENUM types (idempotent)
    # ------------------------------------------------------------------
    _create_enum_if_not_exists("user_role", "admin", "user", "viewer")
    _create_enum_if_not_exists(
        "video_status",
        "pending", "uploading", "uploaded", "processing",
        "completed", "failed", "cancelled",
    )
    _create_enum_if_not_exists(
        "task_status",
        "pending", "started", "retry", "success", "failure", "revoked",
    )
    _create_enum_if_not_exists(
        "task_type",
        "video_process", "transcription", "tts", "thumbnail", "script_generate",
    )

    # ------------------------------------------------------------------
    # Step 2 — updated_at trigger function (idempotent — CREATE OR REPLACE)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ------------------------------------------------------------------
    # Step 3 — users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email",            sa.String(320),  nullable=False),
        sa.Column("full_name",        sa.String(255),  nullable=False),
        sa.Column("hashed_password",  sa.String(255),  nullable=False),
        sa.Column("is_active",        sa.Boolean(),    nullable=False, server_default="true"),
        sa.Column("is_verified",      sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column(
            "role",
            postgresql.ENUM(name="user_role", create_type=False),  # already created above
            nullable=False,
            server_default="user",
        ),
        sa.Column("avatar_url",             sa.Text(),           nullable=True),
        sa.Column("bio",                    sa.Text(),           nullable=True),
        sa.Column("refresh_token_family",   sa.String(36),       nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id",           "users", ["id"])
    op.create_index("ix_users_email",        "users", ["email"])
    op.create_index("ix_users_role",         "users", ["role"])
    op.create_index("ix_users_deleted_at",   "users", ["deleted_at"])
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])
    op.create_index("ix_users_role_active",  "users", ["role", "is_active"])
    op.execute("""
        CREATE TRIGGER users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # ------------------------------------------------------------------
    # Step 4 — projects
    # ------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name",        sa.String(255), nullable=False),
        sa.Column("slug",        sa.String(280), nullable=False),
        sa.Column("description", sa.Text(),      nullable=True),
        sa.Column("owner_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_voice_model", sa.String(120), nullable=False,
                  server_default="en_US-lessac-medium"),
        sa.Column("default_language",   sa.String(10),  nullable=False, server_default="en"),
        sa.Column("default_llm_model",  sa.String(120), nullable=False, server_default="llama3"),
        sa.Column("video_count",        sa.Integer(),   nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_projects_id",           "projects", ["id"])
    op.create_index("ix_projects_owner_id",     "projects", ["owner_id"])
    op.create_index("ix_projects_slug",         "projects", ["slug"])
    op.create_index("ix_projects_deleted_at",   "projects", ["deleted_at"])
    op.create_index("uix_projects_owner_slug",  "projects", ["owner_id", "slug"], unique=True)
    op.create_index("ix_projects_owner_created","projects", ["owner_id", "created_at"])
    op.execute("""
        CREATE TRIGGER projects_updated_at
        BEFORE UPDATE ON projects
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # ------------------------------------------------------------------
    # Step 5 — videos
    # ------------------------------------------------------------------
    op.create_table(
        "videos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title",       sa.String(500), nullable=False),
        sa.Column("slug",        sa.String(520), nullable=False),
        sa.Column("description", sa.Text(),      nullable=True),
        sa.Column("project_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="video_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message",           sa.Text(),         nullable=True),
        sa.Column("original_filename",       sa.String(500),    nullable=True),
        sa.Column("storage_key",             sa.String(1000),   nullable=True),
        sa.Column("mime_type",               sa.String(127),    nullable=True),
        sa.Column("file_size_bytes",         sa.BigInteger(),   nullable=True),
        sa.Column("output_storage_key",      sa.String(1000),   nullable=True),
        sa.Column("thumbnail_storage_key",   sa.String(1000),   nullable=True),
        sa.Column("duration_seconds",        sa.Float(),        nullable=True),
        sa.Column("width",                   sa.Integer(),      nullable=True),
        sa.Column("height",                  sa.Integer(),      nullable=True),
        sa.Column("fps",                     sa.Float(),        nullable=True),
        sa.Column("voice_model",             sa.String(120),    nullable=True),
        sa.Column("language",                sa.String(10),     nullable=True),
        sa.Column("script_prompt",           sa.Text(),         nullable=True),
        sa.Column("processing_metadata",     postgresql.JSONB(),nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"],   ["users.id"],    ondelete="CASCADE"),
    )
    op.create_index("ix_videos_id",           "videos", ["id"])
    op.create_index("ix_videos_project_id",   "videos", ["project_id"])
    op.create_index("ix_videos_owner_id",     "videos", ["owner_id"])
    op.create_index("ix_videos_status",       "videos", ["status"])
    op.create_index("ix_videos_deleted_at",   "videos", ["deleted_at"])
    op.create_index("ix_videos_project_status","videos", ["project_id", "status"])
    op.create_index("ix_videos_owner_status", "videos", ["owner_id",   "status"])
    op.create_index("ix_videos_project_slug", "videos", ["project_id", "slug"], unique=True)
    op.execute("""
        CREATE TRIGGER videos_updated_at
        BEFORE UPDATE ON videos
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # ------------------------------------------------------------------
    # Step 6 — video_tasks
    # ------------------------------------------------------------------
    op.create_table(
        "video_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("video_id",       postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column(
            "task_type",
            postgresql.ENUM(name="task_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="task_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("retry_count",      sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(),   nullable=True),
        sa.Column("progress",         sa.Float(),   nullable=False, server_default="0.0"),
        sa.Column("progress_message", sa.String(500), nullable=True),
        sa.Column("result_data",      postgresql.JSONB(), nullable=True),
        sa.Column("error_type",       sa.String(255), nullable=True),
        sa.Column("error_message",    sa.Text(),      nullable=True),
        sa.Column("error_traceback",  sa.Text(),      nullable=True),
        sa.Column(
            "log",
            postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("celery_task_id", name="uq_video_tasks_celery_id"),
    )
    op.create_index("ix_video_tasks_id",            "video_tasks", ["id"])
    op.create_index("ix_video_tasks_video_id",      "video_tasks", ["video_id"])
    op.create_index("ix_video_tasks_celery_task_id","video_tasks", ["celery_task_id"])
    op.create_index("ix_video_tasks_status",        "video_tasks", ["status"])
    op.create_index("ix_video_tasks_video_status",  "video_tasks", ["video_id", "status"])
    op.create_index("ix_video_tasks_video_type",    "video_tasks", ["video_id", "task_type"])
    op.create_index(
        "ix_video_tasks_celery_status",
        "video_tasks",
        ["celery_task_id", "status"],
    )
    op.execute("""
        CREATE TRIGGER video_tasks_updated_at
        BEFORE UPDATE ON video_tasks
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop triggers
    for tbl in ("video_tasks", "videos", "projects", "users"):
        op.execute(f"DROP TRIGGER IF EXISTS {tbl}_updated_at ON {tbl};")

    # Drop tables (reverse FK order)
    op.drop_table("video_tasks")
    op.drop_table("videos")
    op.drop_table("projects")
    op.drop_table("users")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop ENUM types
    for enum in ("task_type", "task_status", "video_status", "user_role"):
        op.execute(f"DROP TYPE IF EXISTS {enum};")