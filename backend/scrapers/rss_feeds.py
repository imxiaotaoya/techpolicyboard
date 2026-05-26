"""RSS/Atom feed discovery — stable, incremental, no API key needed."""

import asyncio
import hashlib
import re
from datetime import datetime
from typing import Optional

import feedparser
import httpx

from config import settings
from .base import BaseScraper, PolicyDict, _is_tech_relevant, _extract_summary
from .cleaner import PolicyCleaner

FEEDS: list[tuple[str, str, str]] = [
    # (country, source_name, rss_url)
    ("US", "Federal Register", "https://www.federalregister.gov/documents.rss"),
    ("US", "NSF News", "https://www.nsf.gov/news/rss.xml"),
    ("EU", "European Parliament News", "https://www.europarl.europa.eu/rss/doc/last-news/en.xml"),
    ("EU", "EU Digital Strategy", "https://digital-strategy.ec.europa.eu/en/rss.xml"),
    ("UK", "UK Parliament Publications", "https://www.parliament.uk/business/publications.rss"),
    ("UK", "GOV.UK Announcements", "https://www.gov.uk/government/announcements.atom"),
    ("UK", "GOV.UK Policy Papers", "https://www.gov.uk/government/publications.atom?publication_filter_option=policy-papers"),
    ("US", "DOE News", "https://www.energy.gov/rss/news.xml"),
    ("US", "NIST News", "https://www.nist.gov/news-events/news/rss.xml"),
    ("US", "OSTP News", "https://www.whitehouse.gov/ostp/feed.xml"),
    ("EU", "EU Research & Innovation", "https://ec.europa.eu/commission/presscorner/api/rss"),
    ("CN", "科技部", "https://www.most.gov.cn/tpxw/rss/rss.htm"),
]


class RSSDiscovery(BaseScraper):
    source_id = "rss_discovery"

    async def fetch(self, since: Optional[str] = None) -> list[PolicyDict]:
        policies: list[PolicyDict] = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for country, source_name, feed_url in FEEDS:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code != 200:
                        continue
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:30]:
                        policy = self._entry_to_policy(entry, country, source_name)
                        if policy and PolicyCleaner.verify(policy):
                            policies.append(policy)
                except Exception:
                    from .crash_handler import log_warn
                    log_warn("rss_discovery", source_name, f"feed failed: {feed_url}")
                    continue
                await asyncio.sleep(settings.scraper_delay_seconds)
        return PolicyCleaner.deduplicate(policies)

    def _entry_to_policy(self, entry, country: str, source_name: str) -> Optional[PolicyDict]:
        title = entry.get("title", "").strip()
        if not title:
            return None

        link = entry.get("link", "")
        if not link and hasattr(entry, "links"):
            for l in entry.links:
                if l.get("type", "").startswith("text/html"):
                    link = l.get("href", "")
                    break

        published = entry.get("published", "") or entry.get("updated", "") or ""
        summary_html = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
        summary_text = re.sub(r"<[^>]+>", " ", summary_html).strip()

        raw = {
            "title": title,
            "link": link,
            "published": published,
            "summary": summary_text,
            "source_name": source_name,
        }

        return PolicyCleaner.normalize(
            {
                "title": title,
                "country": country,
                "department": source_name,
                "date": published,
                "summary": summary_text,
                "full_text": summary_text,
                "source_url": link,
                "full_text_url": link,
                "raw_json": raw,
            },
            source_id=self.source_id,
        )
