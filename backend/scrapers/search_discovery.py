"""Search-driven policy discovery with source verification.

Uses DuckDuckGo (free, no API key) to search authoritative domains for policy documents.
Every result is verified by fetching the source URL and checking content.

This is the "Perplexity-like" verification layer — no data enters the system
without a traceable, verifiable source URL.
"""

import hashlib
import re
from datetime import datetime
from typing import Optional

import httpx

from .base import BaseScraper, PolicyDict, _is_tech_relevant, _extract_summary
from .cleaner import PolicyCleaner


SEARCH_QUERIES: list[tuple[str, str, str]] = [
    # (country, query_label, search_query)
    ("US", "White House AI/tech executive orders",
     'site:whitehouse.gov ("executive order" OR "memorandum") (artificial intelligence OR AI OR technology OR quantum OR semiconductor OR energy)'),
    ("US", "Congress AI/tech bills",
     'site:congress.gov ("artificial intelligence" OR "quantum" OR "semiconductor" OR "energy" OR "biotechnology") bill 2025'),
    ("US", "Federal Register tech rules",
     'site:federalregister.gov ("proposed rule" OR "final rule") (technology OR artificial intelligence OR AI OR cybersecurity)'),
    ("EU", "EU digital/tech regulations",
     'site:eur-lex.europa.eu ("regulation" OR "directive") (digital OR technology OR artificial intelligence OR AI OR data)'),
    ("CN", "中国科技政策",
     'site:gov.cn (人工智能 OR 量子计算 OR 芯片 OR 新能源 OR 脑机接口 OR 核聚变) 政策'),
]


class SearchDiscovery(BaseScraper):
    source_id = "search_discovery"

    async def fetch(self, since: Optional[str] = None) -> list[PolicyDict]:
        all_policies: list[PolicyDict] = []

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            for country, label, query in SEARCH_QUERIES:
                results = await self._search_and_fetch(client, country, label, query)
                all_policies.extend(results)

        return PolicyCleaner.deduplicate(all_policies)

    async def _search_and_fetch(self, client: httpx.AsyncClient, country: str,
                                 label: str, query: str) -> list[PolicyDict]:
        policies: list[PolicyDict] = []
        try:
            # Use DuckDuckGo HTML search (no API key needed)
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            resp = await client.get(search_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; TechPolicyBoard/1.0)",
            })
            if resp.status_code != 200:
                return []

            # Extract result URLs from HTML
            urls = re.findall(r'class="result__url"[^>]*>(.*?)<', resp.text)
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)<', resp.text)

            for i, url_raw in enumerate(urls[:15]):
                url = re.sub(r"<[^>]+>", "", url_raw).strip()
                if not url.startswith("http"):
                    continue

                snippet = re.sub(r"<[^>]+>", "", snippets[i] if i < len(snippets) else "").strip()

                # Verify by fetching the page
                verified = await self._verify_source(client, url, snippet)
                if verified:
                    policies.append(PolicyCleaner.normalize(
                        {
                            "title": verified.get("title", ""),
                            "country": country,
                            "date": verified.get("date", ""),
                            "summary": verified.get("summary", snippet),
                            "full_text": verified.get("text", snippet),
                            "source_url": url,
                            "full_text_url": url,
                            "raw_json": {
                                "search_query": query,
                                "search_label": label,
                                "source_url": url,
                                "fetch_timestamp": datetime.utcnow().isoformat(),
                                "page_title": verified.get("title", ""),
                            },
                        },
                        source_id=self.source_id,
                        discovery_info={
                            "discovered_by": "search_discovery",
                            "search_query": query,
                            "source_url": url,
                            "fetch_timestamp": datetime.utcnow().isoformat(),
                            "verified": True,
                        },
                    ))
        except Exception:
            import logging
            logging.getLogger("techpolicy.scrapers").warning(
                "search_discovery failed for query: %s", label
            )
            pass

        return [p for p in policies if PolicyCleaner.verify(p)]

    async def _verify_source(self, client: httpx.AsyncClient, url: str,
                              fallback_summary: str) -> Optional[dict]:
        """Fetch the source page and extract title, date, and text.

        Returns None if the source cannot be verified (non-200, empty content).
        """
        try:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; TechPolicyBoard/1.0)",
            })
            if resp.status_code != 200:
                return None

            html = resp.text[:500000]  # Limit to 500KB
            if len(html) < 200:
                return None

            # Extract title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""

            # Strip all HTML for text extraction
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()[:5000]

            # Extract date from meta tags or URL
            date_match = re.search(r'meta name="[Dd]ate"[^>]*content="([^"]+)"', html)
            if not date_match:
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", url + text[:1000])

            if not title and len(text) < 100:
                return None

            return {
                "title": title or fallback_summary[:200],
                "summary": _extract_summary(text[:2000] or fallback_summary, 300),
                "text": text[:5000],
                "date": date_match.group(1) if date_match else datetime.utcnow().strftime("%Y-%m-%d"),
            }
        except Exception:
            import logging
            logging.getLogger("techpolicy.scrapers").debug(
                "source verification failed for: %s", url
            )
            return None
