from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.attempt import AttemptStatus, IncidentAttempt
from app.models.incident import Incident
from app.models.skill_profile import SkillProfile
from app.models.user import User
from app.schemas.coach import DashboardSummary, ReadinessReport
from app.services import readiness as readiness_service

router = APIRouter(tags=["dashboard"])

SKILL_TO_NEXT_INCIDENT_SLUG = {
    "layer1": "inc-002-interface-down",
    "layer2_switching": "inc-001-vlan-mismatch",
    "fundamentals": "inc-003-wrong-ip",
    "layer3_routing": "inc-004-missing-default-route",
    "network_services": "inc-004-missing-default-route",
    "security": "inc-004-missing-default-route",
    "monitoring": "inc-005-ospf-adjacency",
    "troubleshooting_methodology": "inc-005-ospf-adjacency",
}


def _skill_level_label(xp: int) -> str:
    if xp >= 1000:
        return "Advanced"
    if xp >= 400:
        return "Intermediate"
    return "Beginner"


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attempts = db.query(IncidentAttempt).filter(IncidentAttempt.user_id == current_user.id).all()
    resolved = [a for a in attempts if a.status == AttemptStatus.resolved]

    overall_skill = 0.0
    profile = db.query(SkillProfile).filter(SkillProfile.user_id == current_user.id).first()
    if profile:
        report = readiness_service.compute_readiness({
            "fundamentals": profile.fundamentals,
            "layer1": profile.layer1,
            "layer2_switching": profile.layer2_switching,
            "layer3_routing": profile.layer3_routing,
            "network_services": profile.network_services,
            "security": profile.security,
            "monitoring": profile.monitoring,
            "troubleshooting_methodology": profile.troubleshooting_methodology,
            "communication": profile.communication,
        })
        overall_skill = report["overall_readiness"]

    troubleshooting_scores = [a.score_overall for a in resolved if a.score_overall is not None]
    troubleshooting_avg = round(sum(troubleshooting_scores) / len(troubleshooting_scores), 1) if troubleshooting_scores else 0.0

    resolution_times = [a.resolution_seconds for a in resolved if a.resolution_seconds is not None]
    avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None

    hints_total = sum(a.hints_used for a in attempts)

    skill_fields = {
        "Fundamentals": profile.fundamentals if profile else 0,
        "Layer 1": profile.layer1 if profile else 0,
        "Switching": profile.layer2_switching if profile else 0,
        "Routing": profile.layer3_routing if profile else 0,
        "Network Services": profile.network_services if profile else 0,
        "Security": profile.security if profile else 0,
        "Monitoring": profile.monitoring if profile else 0,
    } if profile else {}
    nonzero = {k: v for k, v in skill_fields.items() if v > 0}
    strongest = max(nonzero, key=nonzero.get) if nonzero else None
    weakest = min(nonzero, key=nonzero.get) if nonzero else None

    recommended_slug = "inc-001-vlan-mismatch"
    if profile:
        weakest_key = min(
            ("fundamentals", "layer1", "layer2_switching", "layer3_routing", "network_services", "security", "monitoring", "troubleshooting_methodology"),
            key=lambda k: getattr(profile, k),
        )
        recommended_slug = SKILL_TO_NEXT_INCIDENT_SLUG.get(weakest_key, recommended_slug)
    recommended_incident = db.query(Incident).filter(Incident.slug == recommended_slug).first()

    return DashboardSummary(
        display_name=current_user.display_name,
        skill_level=_skill_level_label(current_user.xp),
        overall_skill_percent=overall_skill,
        troubleshooting_score_percent=troubleshooting_avg,
        incidents_completed=len(attempts),
        incidents_solved=len(resolved),
        average_resolution_seconds=avg_resolution,
        hints_used_total=hints_total,
        strongest_skill=strongest,
        weakest_skill=weakest,
        current_streak_days=current_user.current_streak_days,
        xp=current_user.xp,
        recommended_next=recommended_incident.title if recommended_incident else "Introduction to Networking",
    )


@router.get("/readiness", response_model=ReadinessReport)
def get_readiness(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(SkillProfile).filter(SkillProfile.user_id == current_user.id).first()
    profile_dict = {
        "fundamentals": profile.fundamentals if profile else 0.0,
        "layer1": profile.layer1 if profile else 0.0,
        "layer2_switching": profile.layer2_switching if profile else 0.0,
        "layer3_routing": profile.layer3_routing if profile else 0.0,
        "network_services": profile.network_services if profile else 0.0,
        "security": profile.security if profile else 0.0,
        "monitoring": profile.monitoring if profile else 0.0,
        "troubleshooting_methodology": profile.troubleshooting_methodology if profile else 0.0,
        "communication": profile.communication if profile else 0.0,
    }
    report = readiness_service.compute_readiness(profile_dict)
    return ReadinessReport(**report)
