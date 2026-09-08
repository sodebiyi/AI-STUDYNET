from app.services import scoring


def test_perfect_run_scores_high():
    result = scoring.compute_full_score(
        root_cause_identified=True,
        diagnosis_text_matched=True,
        methodology_progress={s: True for s in scoring.EXPECTED_METHODOLOGY_STEPS},
        unnecessary_commands=0,
        hints_used=0,
        failed_attempts=0,
        remediation_applied=True,
        verification_passed=True,
    )
    assert result["overall"] == 100.0


def test_many_hints_and_failed_attempts_reduce_efficiency_and_overall():
    clean = scoring.compute_full_score(
        root_cause_identified=True, diagnosis_text_matched=True,
        methodology_progress={s: True for s in scoring.EXPECTED_METHODOLOGY_STEPS},
        unnecessary_commands=0, hints_used=0, failed_attempts=0,
        remediation_applied=True, verification_passed=True,
    )
    messy = scoring.compute_full_score(
        root_cause_identified=True, diagnosis_text_matched=True,
        methodology_progress={s: True for s in scoring.EXPECTED_METHODOLOGY_STEPS},
        unnecessary_commands=5, hints_used=3, failed_attempts=4,
        remediation_applied=True, verification_passed=True,
    )
    assert messy["efficiency"] < clean["efficiency"]
    assert messy["overall"] < clean["overall"]


def test_no_remediation_or_verification_caps_score():
    result = scoring.compute_full_score(
        root_cause_identified=True, diagnosis_text_matched=True,
        methodology_progress={}, unnecessary_commands=0, hints_used=0, failed_attempts=0,
        remediation_applied=False, verification_passed=False,
    )
    assert result["remediation"] == 0.0
    assert result["verification"] == 0.0
    assert result["overall"] < 70
