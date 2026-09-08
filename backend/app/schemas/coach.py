import uuid

from pydantic import BaseModel


class CoachMessageRequest(BaseModel):
    message: str


class CoachTurn(BaseModel):
    role: str  # "coach" | "student"
    text: str


class CoachMessageResponse(BaseModel):
    reply: str
    transcript: list[CoachTurn]
    hints_used: int


class HintRequest(BaseModel):
    pass


class DashboardSummary(BaseModel):
    display_name: str
    skill_level: str
    overall_skill_percent: float
    troubleshooting_score_percent: float
    incidents_completed: int
    incidents_solved: int
    average_resolution_seconds: float | None
    hints_used_total: int
    strongest_skill: str | None
    weakest_skill: str | None
    current_streak_days: int
    xp: int
    recommended_next: str


class ReadinessReport(BaseModel):
    fundamentals: float
    layer1: float
    layer2_switching: float
    layer3_routing: float
    network_services: float
    security: float
    monitoring: float
    troubleshooting_methodology: float
    communication: float
    overall_readiness: float
    level: str
    improvement_areas: list[str]
