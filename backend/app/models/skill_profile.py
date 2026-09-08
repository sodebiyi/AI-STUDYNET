import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SkillProfile(Base):
    """
    Rolling per-skill-area competency used by the dashboard and the
    "Am I Job Ready?" report. Updated after every resolved incident
    (see app/services/readiness.py).
    """

    __tablename__ = "skill_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    fundamentals: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    layer1: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    layer2_switching: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    layer3_routing: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    network_services: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    security: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    monitoring: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    troubleshooting_methodology: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    communication: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="skill_profile")  # noqa: F821
