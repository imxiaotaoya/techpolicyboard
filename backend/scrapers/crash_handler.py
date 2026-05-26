"""Scraper error handling — ensures no scraper failure crashes the pipeline."""
import logging

logger = logging.getLogger("techpolicy.scrapers")


def safe_fetch(scraper_name: str, source: str, return_val=None):
    """Decorator/factory for wrapping scraper fetch logic with proper error logging.

    Usage:
        @safe_fetch("us_congress", "Congress.gov API", return_val=[])
        async def fetch_policies(): ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logger.exception(
                    "Scraper '%s' failed fetching from %s", scraper_name, source
                )
                return return_val
        return wrapper
    return decorator


def log_warn(scraper: str, source: str, detail: str = "") -> None:
    logger.warning("Scraper '%s' <source=%s> %s", scraper, source, detail)
