"""Auto-tag orphan policies using tech_mapper keyword engine.

Scraped policies have empty relatedTechnologies/relatedIndustries.
This post-processing step runs the keyword mapper against each
policy's title + summary to auto-populate the relationship fields.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import get_db, close_db
from scrapers.tech_mapper import map_all


def tag_orphans() -> tuple[int, int]:
    """Tag all policies with empty relatedTechnologies. Returns (total, updated)."""
    db = get_db()
    rows = db.execute(
        "SELECT id, title, summary, related_technologies, related_industries FROM policies"
    ).fetchall()

    updated = 0
    total = len(rows)

    for r in rows:
        related_techs = r["related_technologies"] or ""
        related_inds = r["related_industries"] or ""

        # Skip if already has meaningful tags
        try:
            existing_techs = json.loads(related_techs) if related_techs else []
            existing_inds = json.loads(related_inds) if related_inds else []
        except json.JSONDecodeError:
            existing_techs = []
            existing_inds = []

        if len(existing_techs) > 0 and len(existing_inds) > 0:
            continue

        # Run keyword mapper on title + summary
        summary_val = r["summary"] or ""
        combined = f"{r['title']} {summary_val}"
        tech_ids, industry_ids = map_all(combined)

        # Only update if we found mappings
        if tech_ids or industry_ids:
            db.execute(
                "UPDATE policies SET related_technologies = ?, related_industries = ? WHERE id = ?",
                (json.dumps(tech_ids), json.dumps(industry_ids), r["id"]),
            )
            updated += 1
            if updated <= 10:
                print(f"  Tagged [{r['id']}]: techs={tech_ids}, inds={industry_ids}")

    db.commit()
    return total, updated


if __name__ == "__main__":
    total, updated = tag_orphans()
    close_db()
    print(f"\nTagged {updated}/{total} policies with tech/industry mappings")
