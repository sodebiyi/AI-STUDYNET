import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Incident(Base):
    """
    An incident's authoring content (topology, device configs, fault
    definition, root cause, remediation, verification) is server-side only.

    IMPORTANT: the `answer_key` column (root cause, correct remediation,
    verification steps, scoring rubric) is never serialized into any
    schema returned to students. Only app/schemas/incident.py's
    IncidentPublic model — which omits it — reaches the frontend. See
    app/api/incidents.py.
    """

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)  # Beginner/Intermediate/Advanced
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # VLAN, Layer1, Routing, OSPF...
    priority: Mapped[str] = mapped_column(String(8), default="P3", nullable=False)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    learning_objectives: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Topology diagram description consumed by the frontend renderer
    # (nodes/edges only — no fault information).
    topology: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Full simulated network state INCLUDING the injected fault. Server-side
    # only — used by app/simulation to answer CLI commands and evaluate fixes.
    initial_state: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Root cause, correct remediation, verification, scoring rubric. Never
    # sent to the client except post-completion inside a graded summary.
    answer_key: Mapped[dict] = mapped_column(JSON, nullable=False)

    xp_reward: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_free_tier: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
