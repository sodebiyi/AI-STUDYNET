"""
"Am I Job Ready?" readiness scoring (product spec section 10) and the
skill-profile update that runs after every resolved incident.
"""
from __future__ import annotations

CATEGORY_SKILL_MAP: dict[str, str] = {
    "VLAN": "layer2_switching",
    "Layer 1": "layer1",
    "Layer 3 - IP Addressing": "fundamentals",
    "Layer 3 - Routing": "layer3_routing",
    "Routing - OSPF": "layer3_routing",
    "Services": "network_services",
    "Security": "security",
    "Monitoring": "monitoring",
}

READINESS_WEIGHTS = {
    "fundamentals": 0.15,
    "layer1": 0.08,
    "layer2_switching": 0.12,
    "layer3_routing": 0.15,
    "network_services": 0.10,
    "security": 0.10,
    "monitoring": 0.08,
    "troubleshooting_methodology": 0.14,
    "communication": 0.08,
}

LEVELS = [
    (85, "Senior Network Engineer"),
    (70, "Mid-Level Network Engineer"),
    (50, "Junior Network Engineer"),
    (0, "Trainee / Entry Level"),
]


def update_skill_profile(current: dict, incident_category: str, score_overall: float, score_methodology: float) -> dict:
    """Exponential-moving-average update so recent performance matters more
    than ancient history, without a single bad attempt tanking the score."""
    alpha = 0.35
    skill_key = CATEGORY_SKILL_MAP.get(incident_category)
    updated = dict(current)

    if skill_key:
        updated[skill_key] = round((1 - alpha) * current.get(skill_key, 0.0) + alpha * score_overall, 1)

    updated["troubleshooting_methodology"] = round(
        (1 - alpha) * current.get("troubleshooting_methodology", 0.0) + alpha * score_methodology, 1
    )
    # Communication approximated from methodology + diagnosis quality until
    # a real interview-transcript grader (module 11) feeds this directly.
    updated["communication"] = round(
        (1 - alpha) * current.get("communication", 0.0) + alpha * ((score_overall + score_methodology) / 2), 1
    )
    updated["fundamentals"] = round((1 - alpha * 0.5) * current.get("fundamentals", 0.0) + (alpha * 0.5) * score_overall, 1)
    return updated


def compute_readiness(profile: dict) -> dict:
    overall = sum(profile.get(k, 0.0) * w for k, w in READINESS_WEIGHTS.items())
    overall = round(overall, 1)
    level = next(label for threshold, label in LEVELS if overall >= threshold)

    improvement_areas = sorted(
        ((k, profile.get(k, 0.0)) for k in READINESS_WEIGHTS if k not in ("fundamentals",)),
        key=lambda kv: kv[1],
    )[:3]

    return {
        **{k: profile.get(k, 0.0) for k in READINESS_WEIGHTS},
        "overall_readiness": overall,
        "level": level,
        "improvement_areas": [k.replace("_", " ").title() for k, _ in improvement_areas],
    }
