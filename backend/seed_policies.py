"""Seed existing JSON policies into SQLite database."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import get_db, insert_policy, close_db
from data import get_policies as json_get_policies, use_json_mode


def seed() -> None:
    use_json_mode()
    policies = json_get_policies()
    print(f"Found {len(policies)} policies in JSON")

    new_count = 0
    skip_count = 0

    for p in policies:
        policy_dict = {
            "id": p['id'],
            "source_id": "manual",
            "title": p["title"],
            "title_en": "",
            "country": p["country"],
            "department": p.get("department", "International"),
            "department_label": p.get("departmentLabel", ""),
            "level": p.get("level", "national"),
            "date": p["date"],
            "summary": p.get("summary", ""),
            "full_text": p.get("summary", ""),
            "full_text_url": p.get("fullTextUrl", ""),
            "status": "enacted",
            "category": "",
            "related_technologies": p.get("relatedTechnologies", []),
            "related_industries": p.get("relatedIndustries", []),
            "market_reaction_days": p.get("marketReactionDays"),
            "raw_json": p,
        }
        if insert_policy(policy_dict):
            new_count += 1
        else:
            skip_count += 1

    close_db()
    print(f"Seeded: {new_count} new, {skip_count} skipped (already exist)")


if __name__ == "__main__":
    seed()
