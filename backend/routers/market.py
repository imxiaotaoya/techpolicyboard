from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database import get_market_events, get_market_event
from scrapers.market_events_v2 import EnhancedMarketScraper

router = APIRouter()


@router.get("/market-events")
def list_market_events(
    technology_id: Optional[str] = None,
    industry_id: Optional[str] = None,
    event_type: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    items, total = get_market_events(
        technology_id=technology_id,
        industry_id=industry_id,
        event_type=event_type,
        country=country,
        limit=limit,
        offset=offset,
    )
    return {"events": items, "total": total, "limit": limit, "offset": offset}


@router.get("/market-events/stats")
def market_stats() -> dict:
    """Aggregate stats: total funding by industry/technology."""
    import json
    from database import get_db

    db = get_db()
    rows = db.execute(
        "SELECT industry_ids, technology_ids, amount_usd, event_type FROM market_events"
    ).fetchall()

    industry_totals: dict[str, float] = {}
    tech_totals: dict[str, float] = {}
    event_type_counts: dict[str, int] = {}
    total_funding = 0.0

    for r in rows:
        amount = r["amount_usd"] or 0
        total_funding += amount

        etype = r["event_type"] or "other"
        event_type_counts[etype] = event_type_counts.get(etype, 0) + 1

        try:
            inds = json.loads(r["industry_ids"]) if r["industry_ids"] else []
        except json.JSONDecodeError:
            inds = []
        for ind in inds:
            industry_totals[ind] = industry_totals.get(ind, 0) + amount

        try:
            techs = json.loads(r["technology_ids"]) if r["technology_ids"] else []
        except json.JSONDecodeError:
            techs = []
        for t in techs:
            tech_totals[t] = tech_totals.get(t, 0) + amount

    return {
        "total_funding_usd": total_funding,
        "total_events": sum(event_type_counts.values()),
        "by_industry": {k: round(v, 2) for k, v in sorted(industry_totals.items(), key=lambda x: -x[1])},
        "by_technology": {k: round(v, 2) for k, v in sorted(tech_totals.items(), key=lambda x: -x[1])},
        "by_event_type": event_type_counts,
    }


@router.post("/market-events/fetch")
async def trigger_market_fetch() -> dict:
    """Manually trigger market events scraping."""
    scraper = EnhancedMarketScraper()
    events = await scraper.fetch_events()

    from database import insert_market_event
    new_count = 0
    for e in events:
        if insert_market_event(e):
            new_count += 1

    return {"fetched": len(events), "new": new_count}


@router.get("/market-events/{event_id}")
def get_event(event_id: str) -> dict:
    event = get_market_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    return event
