from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent / "data"

_policies_cache: Optional[dict] = None
_technologies_cache: Optional[dict] = None
_industries_cache: Optional[dict] = None

_use_db: bool = True   # Set to False to force JSON mode


def _load_json(filename: str) -> dict:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def _db_row_to_policy(row: dict) -> dict:
    """Convert a SQLite row dict to the legacy JSON-compatible policy dict."""
    related_tech = json.loads(row.get("related_technologies", "[]") or "[]")
    related_ind = json.loads(row.get("related_industries", "[]") or "[]")
    return {
        "id": row["id"],
        "title": row["title"],
        "country": row["country"],
        "department": row.get("department", "International"),
        "departmentLabel": row.get("department_label", row.get("department", "")),
        "level": row.get("level", "national"),
        "date": row["date"],
        "summary": row.get("summary", ""),
        "fullTextUrl": row.get("full_text_url", ""),
        "relatedTechnologies": related_tech,
        "relatedIndustries": related_ind,
        "marketReactionDays": row.get("market_reaction_days"),
    }


def get_policies() -> list:
    if _use_db:
        try:
            from database import get_db
            db = get_db()
            rows = db.execute(
                "SELECT * FROM policies ORDER BY date DESC"
            ).fetchall()
            if rows:
                return [_db_row_to_policy(dict(r)) for r in rows]
        except Exception:
            import logging
            logging.getLogger("techpolicy").warning("DB read failed, falling back to JSON")
            pass

    # Fallback to JSON
    global _policies_cache
    if _policies_cache is None:
        _policies_cache = _load_json("policies.json")
    return list(_policies_cache.get("policies", []))


def use_json_mode() -> None:
    """Fall back to JSON data source."""
    global _use_db
    _use_db = False


def use_db_mode() -> None:
    """Use SQLite data source."""
    global _use_db
    _use_db = True
