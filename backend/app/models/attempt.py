import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AttemptStatus(str, enum.Enum):
    in_progress = "in_progress"
    resolved = "resolved"
    abandoned = "abandoned"


class IncidentAttempt(Base):
    __tablename__ = "incident_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)

    status: Mapped[AttemptStatus] = mapped_column(default=AttemptStatus.in_progress, nullable=False)

    # Mutable simulated device state for THIS attempt (starts as a copy of
    # incident.initial_state; config commands mutate this, not the template).
    live_state: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Coach conversation transcript: [{"role": "coach"|"student", "text": ...}]
    coach_transcript: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Free-form tracking of which methodology steps the student has evidenced
    # (identify_problem, check_layer1, check_layer2, check_layer3, hypothesis,
    # test_hypothesis, implement_fix, verify_fix) -> bool
    methodology_progress: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    root_cause_identified: Mapped[bool] = mapped_column(default=False, nullable=False)
    remediation_applied: Mapped[bool] = mapped_column(default=False, nullable=False)
    verification_passed: Mapped[bool] = mapped_column(default=False, nullable=False)

    hints_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unnecessary_commands: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Score breakdown, populated on resolution (see app/services/scoring.py)
    score_diagnosis: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_methodology: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_remediation: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_verification: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_overall: Mapped[float | None] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="attempts")  # noqa: F821
    commands: Mapped[list["CommandLog"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")
    hints: Mapped[list["HintLog"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class CommandLog(Base):
    __tablename__ = "command_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incident_attempts.id"), nullable=False)
    device: Mapped[str] = mapped_column(String(64), nullable=False)
    command: Mapped[str] = mapped_column(String(500), nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    was_useful: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped["IncidentAttempt"] = relationship(back_populates="commands")


class HintLog(Base):
    __tablename__ = "hint_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incident_attempts.id"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = nudge, 2 = stronger, 3 = near-answer
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped["IncidentAttempt"] = relationship(back_populates="hints")
