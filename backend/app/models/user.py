import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    instructor = "instructor"
    admin = "admin"


class SubscriptionTier(str, enum.Enum):
    free = "free"
    pro = "pro"
    institution = "institution"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student, nullable=False)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.free, nullable=False
    )

    skill_level: Mapped[str] = mapped_column(String(32), default="Beginner", nullable=False)
    xp: Mapped[int] = mapped_column(default=0, nullable=False)
    current_streak_days: Mapped[int] = mapped_column(default=0, nullable=False)
    longest_streak_days: Mapped[int] = mapped_column(default=0, nullable=False)
    last_activity_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempts: Mapped[list["IncidentAttempt"]] = relationship(back_populates="user")
    skill_profile: Mapped["SkillProfile"] = relationship(back_populates="user", uselist=False)
