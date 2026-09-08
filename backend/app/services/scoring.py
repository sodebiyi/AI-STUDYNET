"""
Troubleshooting score — grades engineering BEHAVIOUR, not just whether the
student eventually stumbled onto the fix (product spec section 7).
"""
from __future__ import annotations

EXPECTED_METHODOLOGY_STEPS = [
    "identify_problem",
    "check_layer1",
    "check_layer2",
    "check_layer3",
    "form_hypothesis",
    "implement_fix",
    "verify_fix",
]


def score_diagnosis(root_cause_identified: bool, diagnosis_text_matched: bool) -> float:
    if root_cause_identified and diagnosis_text_matched:
        return 100.0
    if root_cause_identified:
        return 75.0
    return 0.0


def score_methodology(methodology_progress: dict) -> float:
    if not EXPECTED_METHODOLOGY_STEPS:
        return 0.0
    completed = sum(1 for step in EXPECTED_METHODOLOGY_STEPS if methodology_progress.get(step))
    return round(100.0 * completed / len(EXPECTED_METHODOLOGY_STEPS), 1)


def score_efficiency(unnecessary_commands: int, hints_used: int, failed_attempts: int) -> float:
    penalty = unnecessary_commands * 4 + hints_used * 10 + failed_attempts * 8
    return max(0.0, round(100.0 - penalty, 1))


def score_remediation(remediation_applied: bool) -> float:
    return 100.0 if remediation_applied else 0.0


def score_verification(verification_passed: bool) -> float:
    return 100.0 if verification_passed else 0.0


def score_overall(diagnosis: float, methodology: float, efficiency: float, remediation: float, verification: float) -> float:
    # Weighted per spec emphasis: diagnosis and methodology matter most,
    # efficiency matters but shouldn't dominate, remediation/verification
    # are pass/fail gates that must both be hit for a strong overall score.
    weighted = (
        diagnosis * 0.30
        + methodology * 0.25
        + efficiency * 0.15
        + remediation * 0.15
        + verification * 0.15
    )
    return round(weighted, 1)


def compute_full_score(
    root_cause_identified: bool,
    diagnosis_text_matched: bool,
    methodology_progress: dict,
    unnecessary_commands: int,
    hints_used: int,
    failed_attempts: int,
    remediation_applied: bool,
    verification_passed: bool,
) -> dict:
    diagnosis = score_diagnosis(root_cause_identified, diagnosis_text_matched)
    methodology = score_methodology(methodology_progress)
    efficiency = score_efficiency(unnecessary_commands, hints_used, failed_attempts)
    remediation = score_remediation(remediation_applied)
    verification = score_verification(verification_passed)
    overall = score_overall(diagnosis, methodology, efficiency, remediation, verification)
    return {
        "diagnosis": diagnosis,
        "methodology": methodology,
        "efficiency": efficiency,
        "remediation": remediation,
        "verification": verification,
        "overall": overall,
    }
