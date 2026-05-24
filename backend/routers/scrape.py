from typing import Optional

from fastapi import APIRouter, HTTPException

from database import get_db, get_scrape_logs
from scrapers import SCRAPERS
from scheduler import _run_scraper

router = APIRouter()


@router.post("/scrape/{source_id}/trigger")
async def trigger_scrape(source_id: str) -> dict:
    if source_id not in SCRAPERS:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_id}")

    result = await _run_scraper(source_id)
    return {"source_id": source_id, "result": result}


@router.get("/scrape/sources")
def list_sources() -> list:
    db = get_db()
    rows = db.execute(
        "SELECT id, name, country, last_scraped_at, scrape_interval_hours FROM sources"
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/scrape/logs")
def list_logs(source_id: Optional[str] = None, limit: int = 20) -> list:
    return get_scrape_logs(source_id, limit)


@router.get("/policies/{policy_id}/trail")
def policy_trail(policy_id: str) -> dict:
    from database import get_db
    db = get_db()
    row = db.execute(
        "SELECT id, title, country, date, raw_json FROM policies WHERE id = ?",
        (policy_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="policy not found")

    r = dict(row)
    raw_json_str = r.get("raw_json", "{}")
    import json
    try:
        raw = json.loads(raw_json_str) if raw_json_str else {}
    except json.JSONDecodeError:
        raw = {}

    discovery = raw.get("_discovery", {}) if isinstance(raw, dict) else {}

    return {
        "policy": {
            "id": r["id"],
            "title": r["title"],
            "country": r["country"],
            "date": r["date"],
        },
        "source_trail": {
            "discovered_by": discovery.get("discovered_by", "manual"),
            "search_query": discovery.get("search_query"),
            "source_url": discovery.get("source_url"),
            "fetch_timestamp": discovery.get("fetch_timestamp"),
            "content_hash": discovery.get("content_hash"),
            "verified": discovery.get("verified", True),
        },
    }
