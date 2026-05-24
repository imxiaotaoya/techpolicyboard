import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from scrapers import SCRAPERS

logger = logging.getLogger("techpolicy.scheduler")
scheduler = AsyncIOScheduler()


async def _run_scraper(source_id: str) -> dict:
    from database import get_db

    scraper = SCRAPERS.get(source_id)
    if scraper is None:
        logger.warning("Unknown scraper source: %s", source_id)
        return {"error": f"Unknown source: {source_id}"}

    # Inject API key from config
    if source_id == "us_congress" and settings.congress_api_key:
        scraper.API_KEY = settings.congress_api_key

    logger.info("Starting scraper: %s", source_id)
    result = await scraper.run(__import__("database", fromlist=["get_db"]))
    logger.info(
        "Scraper %s completed: fetched=%d new=%d error=%s",
        source_id,
        result.get("fetched", 0),
        result.get("new", 0),
        result.get("error"),
    )
    return result


def _sync_wrapper(source_id: str) -> None:
    """Bridge sync scheduler to async scraper."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run_scraper(source_id))
        loop.close()
    except Exception:
        logger.exception("Scheduler error running scraper: %s", source_id)


def start_scheduler() -> None:
    if scheduler.running or not settings.scheduler_enabled:
        return

    scheduler.add_job(
        lambda: _sync_wrapper("us_federal_register"),
        "interval", hours=24, id="us_federal_register",
        replace_existing=True, misfire_grace_time=3600, max_instances=1,
    )
    scheduler.add_job(
        lambda: _sync_wrapper("us_congress"),
        "interval", hours=24, id="us_congress",
        replace_existing=True, misfire_grace_time=3600, max_instances=1,
    )
    scheduler.add_job(
        lambda: _sync_wrapper("eu_eurlex"),
        "interval", hours=48, id="eu_eurlex",
        replace_existing=True, misfire_grace_time=7200, max_instances=1,
    )
    scheduler.add_job(
        lambda: _sync_wrapper("rss_discovery"),
        "interval", hours=12, id="rss_discovery",
        replace_existing=True, misfire_grace_time=1800, max_instances=1,
    )
    scheduler.add_job(
        lambda: _sync_wrapper("search_discovery"),
        "interval", hours=24, id="search_discovery",
        replace_existing=True, misfire_grace_time=3600, max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started: rss(12h), search(24h), us_fed_reg(24h), us_congress(24h), eu_eurlex(48h)")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
