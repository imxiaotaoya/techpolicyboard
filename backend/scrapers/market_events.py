"""Primary market events scraper: VC funding, M&A, IPOs, grants.

Sources:
- RSS feeds: TechCrunch, VentureBeat, Sifted, Reuters Tech, 36Kr
- SEC EDGAR Form D: free, real-time US VC filings
- Search discovery: targeted queries for specific tech domains
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Optional

import feedparser
import httpx

from .base import BaseScraper, PolicyDict, _extract_summary, _is_tech_relevant
from .cleaner import PolicyCleaner
from .tech_mapper import (
    map_all, extract_amount_usd, extract_round_stage,
    map_to_technologies, map_to_industries,
)


FUNDING_RSS_FEEDS: list[tuple[str, str, str]] = [
    # (country, source_name, rss_url)
    ("US", "TechCrunch", "https://techcrunch.com/feed/"),
    ("US", "VentureBeat", "https://venturebeat.com/feed/"),
    ("EU", "Sifted", "https://sifted.eu/feed"),
    ("US", "Reuters Technology", "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best-topics-post"),
    ("CN", "36Kr", "https://36kr.com/feed"),
    ("CN", "IT桔子", "https://itjuzi.com/feed"),
    ("US", "CB Insights Research", "https://www.cbinsights.com/research/feed"),
    ("US", "Crunchbase News", "https://news.crunchbase.com/feed/"),
]


class MarketEventsScraper(BaseScraper):
    source_id = "market_events"

    async def fetch(self, since: Optional[str] = None) -> list:
        """Fetch market events from all sources."""
        return []  # Uses custom insert flow, not the base PolicyDict pipeline

    async def fetch_events(self, since: Optional[str] = None) -> list[dict]:
        """Fetch funding/market events as raw dicts for market_events table."""
        events: list[dict] = []

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Phase 1: RSS feeds
            for country, source_name, feed_url in FUNDING_RSS_FEEDS:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code != 200:
                        continue
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:30]:
                        event = self._parse_rss_entry(entry, country, source_name)
                        if event and self._is_funding_related(event):
                            events.append(event)
                except Exception:
                    continue

            # Phase 2: SEC EDGAR Form D (recent filings)
            try:
                sec_events = await self._fetch_sec_form_d(client)
                events.extend(sec_events)
            except Exception:
                pass

        return self._deduplicate(events)

    def _parse_rss_entry(self, entry, country: str, source_name: str) -> Optional[dict]:
        title = entry.get("title", "").strip()
        if not title or len(title) < 10:
            return None

        link = entry.get("link", "")
        if not link and hasattr(entry, "links"):
            for l in entry.links:
                if l.get("type", "").startswith("text/html"):
                    link = l.get("href", "")
                    break

        published = entry.get("published", "") or entry.get("updated", "")
        summary_html = entry.get("summary", "") or ""
        if hasattr(entry, "content") and entry.content:
            summary_html = entry.content[0].get("value", summary_html)
        summary = re.sub(r"<[^>]+>", " ", summary_html).strip()

        combined = f"{title} {summary}"
        amount = extract_amount_usd(combined)
        stage = extract_round_stage(combined)
        tech_ids, industry_ids = map_all(combined)
        company = self._extract_company(title, summary)

        content_hash = hashlib.sha256(
            f"{title}{link}".encode("utf-8")
        ).hexdigest()[:16]

        return {
            "id": f"market:{content_hash}",
            "source_id": self.source_id,
            "title": title[:500],
            "event_type": self._classify_event(title, summary, amount),
            "company_name": company,
            "amount_usd": amount,
            "currency": "USD",
            "round_stage": stage,
            "investors": self._extract_investors(summary),
            "valuation_usd": None,
            "country": country,
            "date": self._norm_date(published),
            "summary": _extract_summary(summary, 300),
            "source_url": link,
            "industry_ids": json.dumps(industry_ids),
            "technology_ids": json.dumps(tech_ids),
            "tags": json.dumps(self._extract_tags(title, summary)),
            "raw_json": json.dumps({
                "title": title,
                "link": link,
                "source": source_name,
                "fetched_at": datetime.utcnow().isoformat(),
                "_discovery": {
                    "discovered_by": "rss_feed",
                    "source_name": source_name,
                    "source_url": link,
                    "fetch_timestamp": datetime.utcnow().isoformat(),
                    "verified": True,
                },
            }, ensure_ascii=False),
        }

    async def _fetch_sec_form_d(self, client: httpx.AsyncClient) -> list[dict]:
        """Fetch recent SEC Form D filings via EDGAR RSS."""
        events = []
        try:
            resp = await client.get(
                "https://www.sec.gov/cgi-bin/browse-edgar"
                "?action=getcurrent&CIK=&type=D&company=&dateb=&owner=include&start=0&count=40&output=atom"
            )
            if resp.status_code != 200:
                return events

            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "")
                combined = f"{title} {summary}"
                tech_ids, industry_ids = map_all(combined)

                # Only include if tech-relevant
                if not tech_ids and not industry_ids:
                    continue

                amount = extract_amount_usd(combined)
                content_hash = hashlib.sha256(
                    f"{title}{entry.get('id', '')}".encode("utf-8")
                ).hexdigest()[:16]

                events.append({
                    "id": f"sec:{content_hash}",
                    "source_id": self.source_id,
                    "title": title[:500],
                    "event_type": "funding",
                    "company_name": self._extract_company(title, summary),
                    "amount_usd": amount,
                    "currency": "USD",
                    "round_stage": "form-d",
                    "investors": "[]",
                    "valuation_usd": None,
                    "country": "US",
                    "date": entry.get("updated", "")[:10] or datetime.utcnow().strftime("%Y-%m-%d"),
                    "summary": _extract_summary(summary, 200),
                    "source_url": entry.get("link", ""),
                    "industry_ids": json.dumps(industry_ids),
                    "technology_ids": json.dumps(tech_ids),
                    "tags": json.dumps(["sec", "form-d", "us"]),
                    "raw_json": json.dumps({
                        "title": title,
                        "source": "SEC EDGAR Form D",
                        "fetched_at": datetime.utcnow().isoformat(),
                        "_discovery": {
                            "discovered_by": "sec_edgar",
                            "source_url": entry.get("link", ""),
                            "fetch_timestamp": datetime.utcnow().isoformat(),
                            "verified": True,
                        },
                    }, ensure_ascii=False),
                })
        except Exception:
            pass
        return events

    def _classify_event(self, title: str, summary: str, amount: Optional[float]) -> str:
        combined = f"{title} {summary}".lower()
        if any(kw in combined for kw in ["acquired", "acquisition", "merger", "acqui-hire", "合并", "收购"]):
            return "acquisition"
        if any(kw in combined for kw in ["ipo", "went public", "initial public offering", "listed on", "上市"]):
            return "ipo"
        if any(kw in combined for kw in ["grant", "awarded", "contract", "sbir", "sttr", "拨款", "资助"]):
            return "grant"
        if amount and amount > 0:
            return "funding"
        if any(kw in combined for kw in ["raised", "funding", "series", "seed", "融资", "投资"]):
            return "funding"
        return "news"

    def _extract_company(self, title: str, summary: str) -> Optional[str]:
        """Extract company name from title or summary."""
        import re

        title_clean = title.replace("\n", " ").strip()
        STOP = {"the", "and", "for", "its", "has", "was", "new", "this",
                "what", "how", "why", "when", "strike", "nuclear", "smart",
                "a", "an", "in", "on", "at", "to", "of", "by", "is", "it"}

        # Pattern: [prefix like startup/company/firm/maker/chipmaker] + CompanyName + [verb like raises/said/files/IPO]
        PATTERNS = [
            # "startup Deep Fission says it is going public"
            r"(?:startup|company|firm|maker|platform|chipmaker)\s+"
            r"([A-Z][A-Za-z0-9\.\-]+(?:[\s]+[A-Z][A-Za-z0-9\.\-]+){0,3}?)"
            r"(?:[\x27’]s|[\s]+(?:raises?|secured|closes?|said|says|is|files?|has|target(?:ing)?|announced?|IPO))",

            # "SolarSquare in talks to raise"
            r"([A-Z][A-Za-z0-9\.\-]+(?:[\s]+[A-Z][A-Za-z0-9\.\-]+){0,3})"
            r"[\s]+(?:in[\s]+talks|is[\s]+in[\s]+talks)[\s]+(?:to|about)",

            # "[Oura] files for IPO" (single word, generic)
            r"([A-Z][A-Za-z0-9\.\-]{2,30})[\s]+(?:raises?|secured|closes?|files?|announces?|lands?|gets?)",
        ]

        for pat in PATTERNS:
            m = re.search(pat, title_clean, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                # Strip trailing noise words captured by greedy multi-word match
                name = re.sub(r"[\s]+(?:files|targets|announces|says|said|raises?|secured|closes?)$",
                             "", name, flags=re.IGNORECASE).strip()
                if name and name.lower() not in STOP:
                    return name

        # --- Chinese company names ---
        m = re.search(
            r"([一-鿿㐀-䶿A-Za-z0-9]{2,20}"
            r"(?:公司|科技|智能|机器人|半导体|量子|能源|材料|制药|医疗|芯片|数据|网络|软件|系统|航天|卫星))"
            r"[\s]*(?:完成|获得|获|宣布|实现|达成|签署|正式|成功|已)",
            title_clean
        )
        if m:
            name = m.group(1).strip()
            if len(name) >= 3 and name not in ("一季度", "今年", "近日", "国内首家"):
                return name

        return None

    def _extract_investors(self, text: str) -> str:
        """Extract investor names from text."""
        investors = set()
        patterns = [
            r"(?:led by|backed by|from|investors include|including)\s+([A-Z][A-Za-z0-9\s,\.&]+?)(?:\.|,|\s+and\s+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                names = re.split(r",|and", m.group(1))
                for n in names:
                    n = n.strip()
                    if 2 <= len(n) <= 50:
                        investors.add(n)
        return json.dumps(list(investors)[:10])

    def _extract_tags(self, title: str, summary: str) -> list[str]:
        """Extract relevant tags."""
        combined = f"{title} {summary}".lower()
        tags = set()
        tag_map = {
            "ai": ["artificial intelligence", "machine learning", "deep learning", "llm", "gpt", "transformer"],
            "semiconductor": ["chip", "semiconductor", "silicon", "fabrication", "wafer"],
            "robotics": ["robot", "autonomous", "drone", "ros"],
            "biotech": ["biotech", "gene", "cell therapy", "mrna", "crispr"],
            "energy": ["energy", "battery", "solar", "hydrogen", "renewable"],
            "cybersecurity": ["cyber", "security", "encryption", "zero trust"],
            "spacetech": ["space", "satellite", "launch", "orbit"],
            "fintech": ["fintech", "payment", "blockchain", "defi", "crypto"],
        }
        for tag, keywords in tag_map.items():
            for kw in keywords:
                if kw in combined:
                    tags.add(tag)
                    break
        return sorted(tags)

    def _is_funding_related(self, event: dict) -> bool:
        """Filter: must be funding-related AND tech-relevant (match >= 1 industry or technology)."""
        combined = f"{event.get('title', '')} {event.get('summary', '')}".lower()
        funding_kw = [
            "raised", "funding", "series", "seed", "invest", "valuation",
            "acquired", "acquisition", "merger", "ipo", "went public",
            "融资", "投资", "募资", "收购", "上市", "估值",
            "million", "billion", "$m", "$b",
        ]
        if not any(kw in combined for kw in funding_kw):
            return False

        # Must be tech-relevant: match at least one technology or industry
        tech_ids, industry_ids = map_all(f"{event.get('title', '')} {event.get('summary', '')}")
        has_tech = len(tech_ids) > 0 or len(industry_ids) > 0

        # Also check if it has company/amount info (strong signal of real event)
        has_financial = (
            event.get("amount_usd") is not None
            or event.get("company_name") is not None
            or any(kw in combined for kw in ["inc.", "ltd", "startup", "corp", "venture"])
        )

        return has_tech or has_financial

    def _deduplicate(self, events: list[dict]) -> list[dict]:
        seen_ids = set()
        seen_titles = set()
        result = []
        for e in events:
            eid = e.get("id", "")
            title_key = re.sub(r"\s+", " ", e.get("title", "").lower()).strip()[:80]
            if eid in seen_ids or title_key in seen_titles:
                continue
            seen_ids.add(eid)
            seen_titles.add(title_key)
            result.append(e)
        return result

    @staticmethod
    def _norm_date(date_str: str) -> str:
        if not date_str:
            return datetime.utcnow().strftime("%Y-%m-%d")
        date_str = str(date_str).strip()[:19]
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d",
                     "%a, %d %b %Y", "%d %b %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(date_str[:len(fmt)], fmt).strftime("%Y-%m-%d")
            except (ValueError, IndexError):
                continue
        m = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", date_str)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return datetime.utcnow().strftime("%Y-%m-%d")
