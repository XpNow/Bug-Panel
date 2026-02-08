from __future__ import annotations

import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_file",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("uri", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sha256"),
    )
    op.create_table(
        "upload_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("temp_path", sa.String(length=500), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ingest_job",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("progress_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("stats_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_file.id"]),
    )
    op.create_table(
        "raw_block",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uri", sa.String(length=500), nullable=False),
        sa.Column("codec", sa.String(length=20), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_file.id"]),
    )
    op.create_table(
        "dict_event_type",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "dict_item",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "dict_container",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("owner_player_id", sa.String(length=50), nullable=True),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "dict_player",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("player_id"),
    )
    op.create_table(
        "dict_alias",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["dict_player.id"]),
    )

    op.execute(
        """
        CREATE TABLE event (
            id UUID PRIMARY KEY,
            source_file_id UUID NOT NULL REFERENCES source_file(id),
            parser_id VARCHAR(50) NOT NULL,
            parser_version VARCHAR(20) NOT NULL,
            occurred_at TIMESTAMPTZ NULL,
            occurred_at_quality VARCHAR(20) NOT NULL,
            event_type_id INTEGER NOT NULL REFERENCES dict_event_type(id),
            src_player_id INTEGER NULL REFERENCES dict_player(id),
            dst_player_id INTEGER NULL REFERENCES dict_player(id),
            item_id INTEGER NULL REFERENCES dict_item(id),
            container_id INTEGER NULL REFERENCES dict_container(id),
            amount NUMERIC(20,2) NULL,
            qty NUMERIC(20,2) NULL,
            metadata JSONB NULL,
            raw_block_id UUID NOT NULL REFERENCES raw_block(id),
            raw_line_index INTEGER NOT NULL,
            dedupe_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        ) PARTITION BY RANGE (occurred_at);
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_event_dedupe ON event (dedupe_hash);")

    now = datetime.datetime.utcnow()
    start = datetime.datetime(now.year, now.month, 1)
    if now.month == 12:
        end = datetime.datetime(now.year + 1, 1, 1)
    else:
        end = datetime.datetime(now.year, now.month + 1, 1)
    op.execute(
        f"CREATE TABLE event_{start:%Y_%m} PARTITION OF event FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}');"
    )
    op.execute("CREATE TABLE event_notime PARTITION OF event DEFAULT;")

    op.create_table(
        "unknown_signature",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ingest_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signature", sa.String(length=400), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ingest_job_id"], ["ingest_job.id"]),
    )
    op.create_table(
        "report_pack",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("filter_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("uri", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("report_pack")
    op.drop_table("unknown_signature")
    op.execute("DROP TABLE IF EXISTS event_notime;")
    op.execute("DROP TABLE IF EXISTS event;")
    op.drop_table("dict_alias")
    op.drop_table("dict_player")
    op.drop_table("dict_container")
    op.drop_table("dict_item")
    op.drop_table("dict_event_type")
    op.drop_table("raw_block")
    op.drop_table("ingest_job")
    op.drop_table("upload_session")
    op.drop_table("source_file")
