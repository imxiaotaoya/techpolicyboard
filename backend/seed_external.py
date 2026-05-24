"""Import external curated policy datasets into SQLite.

Sources:
- ai-legislation-tracker: 28-entry JSON dataset of global AI laws
  https://github.com/delschlangen/ai-legislation-tracker
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import get_db, insert_policy, close_db
from scrapers.cleaner import PolicyCleaner

EXTERNAL_DIR = Path(__file__).resolve().parent / "data" / "external"


def ensure_cloned() -> None:
    """Clone external datasets if not already present."""
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)

    tracker_dir = EXTERNAL_DIR / "ai-legislation-tracker"
    if not tracker_dir.exists():
        print("Cloning ai-legislation-tracker...")
        os.system(
            f"git clone --depth 1 https://github.com/delschlangen/ai-legislation-tracker.git "
            f"{tracker_dir} 2>/dev/null"
        )


def import_ai_legislation_tracker() -> int:
    """Import all JSON files from the ai-legislation-tracker dataset."""
    tracker_dir = EXTERNAL_DIR / "ai-legislation-tracker"
    total = 0

    json_files = [
        ("US", "us_federal_actions.json"),
        ("US", "us_state_bills.json"),
        ("GLOBAL", "international_frameworks.json"),
    ]

    for default_country, filename in json_files:
        json_path = tracker_dir / "data" / filename
        if not json_path.exists():
            print(f"Skipping {filename} — not found")
            continue

        entries = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            entries = [entries]

        for entry in entries:
            # Map external schema to our fields
            raw_department = entry.get("issuing_body", entry.get("jurisdiction", ""))
            country = entry.get("country", entry.get("jurisdiction", default_country))

            policy = PolicyCleaner.normalize(
                {
                    "title": entry.get("title", ""),
                    "country": country,
                    "department": raw_department,
                    "date": entry.get("date_issued", entry.get("date", "")),
                    "summary": entry.get("summary", ""),
                    "full_text": entry.get("summary", ""),
                    "source_url": entry.get("source_url", ""),
                    "full_text_url": entry.get("source_url", ""),
                    "status": entry.get("status", "enacted"),
                    "category": entry.get("type", ""),
                    "raw_json": {
                        **entry,
                        "_discovery": {
                            "discovered_by": "external_dataset",
                            "dataset": "ai-legislation-tracker",
                            "dataset_url": "https://github.com/delschlangen/ai-legislation-tracker",
                            "fetch_timestamp": datetime.utcnow().isoformat(),
                            "verified": True,
                            "last_verified": entry.get("last_verified", ""),
                        },
                    },
                },
                source_id="external:ai-legislation-tracker",
            )

            # Use the dataset's own ID for stable references
            ext_id = entry.get("id", "")
            if ext_id:
                policy.id = f"ext:tracker:{ext_id}"

            # Add key provisions to summary
            provisions = entry.get("key_provisions", [])
            if provisions:
                policy.summary = policy.summary + "\nKey provisions: " + "; ".join(provisions[:5])

            if PolicyCleaner.verify(policy):
                if insert_policy(policy.to_dict()):
                    total += 1

        print(f"  Imported from {filename}")

    close_db()
    return total


if __name__ == "__main__":
    ensure_cloned()
    n = import_ai_legislation_tracker()
    print(f"Imported {n} policies from ai-legislation-tracker")
