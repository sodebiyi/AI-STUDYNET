import copy
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.attempt import AttemptStatus, CommandLog, HintLog, IncidentAttempt
from app.models.incident import Incident
from app.models.skill_profile import SkillProfile
from app.models.user import User
from app.schemas.coach import CoachMessageRequest, CoachMessageResponse
from app.schemas.incident import (
    AttemptPublic,
    AttemptStart,
    CliCommandRequest,
    CliCommandResponse,
    DiagnosisSubmit,
    IncidentListItem,
    IncidentPublic,
    ResolutionSummary,
    VerifySubmit,
)
from app.simulation import cli as cli_engine
from app.simulation import engine as sim_engine
from app.services import coach as coach_service
from app.services import readiness as readiness_service
from app.services import scoring as scoring_service

router = APIRouter(prefix="/incidents", tags=["incidents"])

FREE_TIER_ATTEMPT_LIMIT = 3
ERROR_MARKERS = ("% Invalid", "% Incomplete", "% Unknown")


def _get_incident_or_404(db: Session, incident_id: uuid.UUID) -> Incident:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found.")
    return incident


def _get_attempt_or_404(db: Session, attempt_id: uuid.UUID, user: User) -> IncidentAttempt:
    attempt = db.get(IncidentAttempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found.")
    return attempt


@router.get("", response_model=list[IncidentListItem])
def list_incidents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Incident).order_by(Incident.xp_reward).all()


@router.get("/{incident_id}", response_model=IncidentPublic)
def get_incident(incident_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_incident_or_404(db, incident_id)


@router.post("/attempts", response_model=AttemptPublic, status_code=status.HTTP_201_CREATED)
def start_attempt(payload: AttemptStart, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    incident = _get_incident_or_404(db, payload.incident_id)

    if current_user.subscription_tier.value == "free" and not incident.is_free_tier:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "This incident requires a Pro subscription. Free tier includes 3 troubleshooting incidents.",
        )

    attempt = IncidentAttempt(
        user_id=current_user.id,
        incident_id=incident.id,
        live_state=copy.deepcopy(incident.initial_state),
        coach_transcript=[{"role": "coach", "text": coach_service.opening_message(incident.title)}],
        methodology_progress={"identify_problem": True},
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/attempts/{attempt_id}", response_model=AttemptPublic)
def get_attempt(attempt_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _get_attempt_or_404(db, attempt_id, current_user)


@router.get("/attempts/{attempt_id}/transcript")
def get_transcript(attempt_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attempt = _get_attempt_or_404(db, attempt_id, current_user)
    return {"transcript": attempt.coach_transcript}


@router.post("/attempts/{attempt_id}/cli", response_model=CliCommandResponse)
def run_cli_command(
    attempt_id: uuid.UUID,
    payload: CliCommandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = _get_attempt_or_404(db, attempt_id, current_user)
    if attempt.status != AttemptStatus.in_progress:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This attempt is already closed.")

    result = cli_engine.run_command(attempt.live_state, payload.device, payload.command)
    # cli_engine mutates attempt.live_state IN PLACE (both the simulated
    # device state and the per-device CLI mode/context tracker). SQLAlchemy
    # does not detect in-place mutation of JSON columns on its own, so we
    # must explicitly flag it dirty or the change (and CLI mode context,
    # e.g. "configure terminal" -> "interface X") would silently be lost
    # between requests.
    flag_modified(attempt, "live_state")

    was_useful = not any(result.output.startswith(m) for m in ERROR_MARKERS)
    log = CommandLog(attempt_id=attempt.id, device=payload.device, command=payload.command, output=result.output, was_useful=was_useful)
    db.add(log)

    if not was_useful:
        attempt.unnecessary_commands += 1

    # Update methodology tracking from the category of command just run.
    lower = payload.command.strip().lower()
    progress = dict(attempt.methodology_progress)
    if lower in coach_service.L1_COMMANDS or lower.startswith("show interfaces"):
        progress["check_layer1"] = True
    elif lower in coach_service.L2_COMMANDS:
        progress["check_layer2"] = True
    elif lower in coach_service.L3_COMMANDS or lower.startswith("ping") or lower.startswith("traceroute"):
        progress["check_layer3"] = True
    attempt.methodology_progress = progress

    if result.mutated:
        incident = db.get(Incident, attempt.incident_id)
        remediation_check = incident.answer_key.get("remediation_check", {})
        if _check_remediation(attempt.live_state, remediation_check):
            progress = dict(attempt.methodology_progress)
            progress["implement_fix"] = True
            attempt.methodology_progress = progress
            attempt.remediation_applied = True

    db.commit()
    db.refresh(attempt)
    return CliCommandResponse(device=payload.device, command=payload.command, output=result.output, was_useful=was_useful)


@router.post("/attempts/{attempt_id}/coach", response_model=CoachMessageResponse)
def coach_chat(
    attempt_id: uuid.UUID,
    payload: CoachMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = _get_attempt_or_404(db, attempt_id, current_user)
    incident = db.get(Incident, attempt.incident_id)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "message is required.")

    commands = [{"command": c.command} for c in attempt.commands]
    reply = coach_service.coach_reply(
        {"category": incident.category}, commands, attempt.failed_attempts, attempt.hints_used, message
    )

    transcript = list(attempt.coach_transcript)
    transcript.append({"role": "student", "text": message})
    transcript.append({"role": "coach", "text": reply})
    attempt.coach_transcript = transcript
    db.commit()
    return CoachMessageResponse(reply=reply, transcript=transcript, hints_used=attempt.hints_used)


@router.post("/attempts/{attempt_id}/hint")
def request_hint(attempt_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    attempt = _get_attempt_or_404(db, attempt_id, current_user)
    incident = db.get(Incident, attempt.incident_id)

    level = attempt.hints_used + 1
    if level > 3:
        level = 3
    text = coach_service.generate_hint({"category": incident.category, "answer_key": incident.answer_key}, level)

    db.add(HintLog(attempt_id=attempt.id, level=level, text=text))
    attempt.hints_used += 1
    transcript = list(attempt.coach_transcript)
    transcript.append({"role": "coach", "text": text})
    attempt.coach_transcript = transcript
    db.commit()
    return {"hint": text, "hints_used": attempt.hints_used}


@router.post("/attempts/{attempt_id}/diagnose")
def submit_diagnosis(
    attempt_id: uuid.UUID,
    payload: DiagnosisSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = _get_attempt_or_404(db, attempt_id, current_user)
    incident = db.get(Incident, attempt.incident_id)
    keywords = incident.answer_key.get("root_cause_keywords", [])

    text = payload.root_cause_statement.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text)
    matched = keywords and (matches / len(keywords)) >= 0.4

    progress = dict(attempt.methodology_progress)
    progress["form_hypothesis"] = True
    attempt.methodology_progress = progress

    if matched:
        attempt.root_cause_identified = True
    else:
        attempt.failed_attempts += 1

    db.commit()
    return {"matched": bool(matched), "keyword_matches": matches, "keyword_total": len(keywords), "failed_attempts": attempt.failed_attempts}


@router.post("/attempts/{attempt_id}/verify", response_model=ResolutionSummary)
def verify_and_resolve(
    attempt_id: uuid.UUID,
    payload: VerifySubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = _get_attempt_or_404(db, attempt_id, current_user)
    if attempt.status != AttemptStatus.in_progress:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This attempt is already closed.")
    incident = db.get(Incident, attempt.incident_id)

    verify_check = incident.answer_key.get("verify_check", {})
    result = sim_engine.attempt_ping(attempt.live_state, verify_check["device"], verify_check["dest_ip"])

    remediation_check = incident.answer_key.get("remediation_check", {})
    remediation_ok = _check_remediation(attempt.live_state, remediation_check)
    attempt.remediation_applied = attempt.remediation_applied or remediation_ok

    if not result.success:
        attempt.failed_attempts += 1
        db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Verification failed: {result.output.strip().splitlines()[-1] if result.output else 'ping failed'}. "
            f"{('Reason: ' + result.failure_reason) if result.failure_reason else ''}",
        )

    attempt.verification_passed = True
    progress = dict(attempt.methodology_progress)
    progress["verify_fix"] = True
    attempt.methodology_progress = progress

    attempt.status = AttemptStatus.resolved
    attempt.resolved_at = datetime.now(timezone.utc)
    started = attempt.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    attempt.resolution_seconds = int((attempt.resolved_at - started).total_seconds())

    scores = scoring_service.compute_full_score(
        root_cause_identified=attempt.root_cause_identified,
        diagnosis_text_matched=attempt.root_cause_identified,
        methodology_progress=attempt.methodology_progress,
        unnecessary_commands=attempt.unnecessary_commands,
        hints_used=attempt.hints_used,
        failed_attempts=attempt.failed_attempts,
        remediation_applied=attempt.remediation_applied,
        verification_passed=attempt.verification_passed,
    )
    attempt.score_diagnosis = scores["diagnosis"]
    attempt.score_methodology = scores["methodology"]
    attempt.score_efficiency = scores["efficiency"]
    attempt.score_remediation = scores["remediation"]
    attempt.score_verification = scores["verification"]
    attempt.score_overall = scores["overall"]

    # XP + streak + skill profile update
    current_user.xp += incident.xp_reward
    _update_streak(current_user)

    profile = db.query(SkillProfile).filter(SkillProfile.user_id == current_user.id).first()
    if profile is None:
        profile = SkillProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()
    profile_dict = {
        "fundamentals": profile.fundamentals,
        "layer1": profile.layer1,
        "layer2_switching": profile.layer2_switching,
        "layer3_routing": profile.layer3_routing,
        "network_services": profile.network_services,
        "security": profile.security,
        "monitoring": profile.monitoring,
        "troubleshooting_methodology": profile.troubleshooting_methodology,
        "communication": profile.communication,
    }
    updated = readiness_service.update_skill_profile(profile_dict, incident.category, scores["overall"], scores["methodology"])
    for k, v in updated.items():
        setattr(profile, k, v)

    db.commit()
    db.refresh(attempt)

    return ResolutionSummary(
        attempt=AttemptPublic.model_validate(attempt),
        root_cause=incident.answer_key["root_cause"],
        correct_remediation=incident.answer_key["correct_remediation"],
        verification_procedure=incident.answer_key["verification"],
        explanation=(
            f"Root cause: {incident.answer_key['root_cause']} "
            f"Fix applied: {incident.answer_key['correct_remediation']} "
            f"Verified via: {incident.answer_key['verification']}"
        ),
    )


def _check_remediation(live_state: dict, check: dict) -> bool:
    if not check:
        return False
    device = live_state.get("devices", {}).get(check.get("device"))
    if device is None:
        return False

    if "static_route" in check:
        target = check["static_route"]
        return any(
            r.get("network") == target.get("network") and r.get("mask") == target.get("mask") and r.get("next_hop") == target.get("next_hop")
            for r in device.get("static_routes", [])
        )

    iface = device.get("interfaces", {}).get(check.get("interface"))
    if iface is None:
        return False
    return iface.get(check.get("field")) == check.get("expected")


def _update_streak(user: User) -> None:
    now = datetime.now(timezone.utc)
    last = user.last_activity_date
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last is None:
        user.current_streak_days = 1
    else:
        delta_days = (now.date() - last.date()).days
        if delta_days == 0:
            pass  # already counted today
        elif delta_days == 1:
            user.current_streak_days += 1
        else:
            user.current_streak_days = 1
    user.longest_streak_days = max(user.longest_streak_days, user.current_streak_days)
    user.last_activity_date = now
