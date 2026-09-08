"""
Seeds the `incidents` table from app/simulation/incidents.py.

Run with: python -m app.seed
Idempotent: existing incidents (matched by slug) are updated in place
rather than duplicated, so it's safe to re-run after editing incident data.
"""
from app.core.database import SessionLocal
from app.models.incident import Incident
from app.simulation.incidents import INCIDENTS


def seed() -> None:
    db = SessionLocal()
    try:
        for slug, data in INCIDENTS.items():
            incident = db.query(Incident).filter(Incident.slug == slug).first()
            if incident is None:
                incident = Incident(slug=slug)
                db.add(incident)

            incident.title = data["title"]
            incident.difficulty = data["difficulty"]
            incident.category = data["category"]
            incident.priority = data["priority"]
            incident.summary = data["summary"]
            incident.impact = data["impact"]
            incident.symptoms = data["symptoms"]
            incident.learning_objectives = data["learning_objectives"]
            incident.topology = data["topology"]
            incident.initial_state = data["initial_state"]
            incident.answer_key = data["answer_key"]
            incident.xp_reward = data["xp_reward"]
            incident.is_free_tier = data["is_free_tier"]

        db.commit()
        print(f"Seeded {len(INCIDENTS)} incidents.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
