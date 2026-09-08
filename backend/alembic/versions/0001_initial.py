"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM("student", "instructor", "admin", name="userrole")
subscription_tier = postgresql.ENUM("free", "pro", "institution", name="subscriptiontier")
attempt_status = postgresql.ENUM("in_progress", "resolved", "abandoned", name="attemptstatus")

# create_type=False variants for use inside Column() definitions below — the
# type is created explicitly (once) at the top of upgrade() instead, since
# SQLAlchemy would otherwise try to auto-create it a second time during
# create_table() and fail with "type already exists".
user_role_col = postgresql.ENUM("student", "instructor", "admin", name="userrole", create_type=False)
subscription_tier_col = postgresql.ENUM("free", "pro", "institution", name="subscriptiontier", create_type=False)
attempt_status_col = postgresql.ENUM("in_progress", "resolved", "abandoned", name="attemptstatus", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    subscription_tier.create(bind, checkfirst=True)
    attempt_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("role", user_role_col, nullable=False, server_default="student"),
        sa.Column("subscription_tier", subscription_tier_col, nullable=False, server_default="free"),
        sa.Column("skill_level", sa.String(32), nullable=False, server_default="Beginner"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("difficulty", sa.String(32), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("priority", sa.String(8), nullable=False, server_default="P3"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("learning_objectives", sa.JSON(), nullable=False),
        sa.Column("topology", sa.JSON(), nullable=False),
        sa.Column("initial_state", sa.JSON(), nullable=False),
        sa.Column("answer_key", sa.JSON(), nullable=False),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_free_tier", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_incidents_slug", "incidents", ["slug"], unique=True)

    op.create_table(
        "skill_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("fundamentals", sa.Float(), nullable=False, server_default="0"),
        sa.Column("layer1", sa.Float(), nullable=False, server_default="0"),
        sa.Column("layer2_switching", sa.Float(), nullable=False, server_default="0"),
        sa.Column("layer3_routing", sa.Float(), nullable=False, server_default="0"),
        sa.Column("network_services", sa.Float(), nullable=False, server_default="0"),
        sa.Column("security", sa.Float(), nullable=False, server_default="0"),
        sa.Column("monitoring", sa.Float(), nullable=False, server_default="0"),
        sa.Column("troubleshooting_methodology", sa.Float(), nullable=False, server_default="0"),
        sa.Column("communication", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "incident_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("status", attempt_status_col, nullable=False, server_default="in_progress"),
        sa.Column("live_state", sa.JSON(), nullable=False),
        sa.Column("coach_transcript", sa.JSON(), nullable=False),
        sa.Column("methodology_progress", sa.JSON(), nullable=False),
        sa.Column("root_cause_identified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("remediation_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unnecessary_commands", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_diagnosis", sa.Float(), nullable=True),
        sa.Column("score_methodology", sa.Float(), nullable=True),
        sa.Column("score_efficiency", sa.Float(), nullable=True),
        sa.Column("score_remediation", sa.Float(), nullable=True),
        sa.Column("score_verification", sa.Float(), nullable=True),
        sa.Column("score_overall", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_seconds", sa.Integer(), nullable=True),
    )

    op.create_table(
        "command_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incident_attempts.id"), nullable=False),
        sa.Column("device", sa.String(64), nullable=False),
        sa.Column("command", sa.String(500), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("was_useful", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "hint_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incident_attempts.id"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("hint_logs")
    op.drop_table("command_logs")
    op.drop_table("incident_attempts")
    op.drop_table("skill_profiles")
    op.drop_table("incidents")
    op.drop_table("users")
    attempt_status.drop(op.get_bind(), checkfirst=True)
    subscription_tier.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
