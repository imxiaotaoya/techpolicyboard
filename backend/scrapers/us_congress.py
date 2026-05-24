import json
from datetime import datetime
from typing import Optional

import httpx

from .base import BaseScraper, PolicyDict, _is_tech_relevant, _extract_summary, _extract_date

BASE_URL = "https://api.congress.gov/v3"


class CongressScraper(BaseScraper):
    source_id = "us_congress"

    API_KEY: Optional[str] = None  # Set via CONGRESS_API_KEY env var

    async def fetch(self, since: Optional[str] = None) -> list[PolicyDict]:
        api_key = self.API_KEY or ""
        policies = []
        current_congress = 119  # 2025-2026 session

        async with httpx.AsyncClient(timeout=30) as client:
            for bill_type in ["hr", "s"]:
                url = f"{BASE_URL}/bill/{current_congress}/{bill_type}"
                params = {
                    "api_key": api_key,
                    "format": "json",
                    "limit": 50,
                    "sort": "updateDate+desc",
                }

                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    data = resp.json()

                    for bill in data.get("bills", []):
                        update_date = bill.get("updateDate", "")[:10]
                        if since and update_date <= since[:10]:
                            continue

                        title = bill.get("title", "")
                        summary = self._bill_summary(bill)

                        if _is_tech_relevant(title, summary):
                            policy = await self._bill_to_policy(client, bill, api_key)
                            if policy:
                                policies.append(policy)
                except httpx.HTTPError:
                    continue

        return policies

    def _bill_summary(self, bill: dict) -> str:
        """Extract best available summary from bill data."""
        # Try latest summary text
        summaries = bill.get("summaries", [])
        if summaries:
            texts = [s.get("text", "") for s in summaries if s.get("text")]
            if texts:
                return max(texts, key=len)
        return bill.get("latestAction", {}).get("text", "")

    async def _bill_to_policy(self, client: httpx.AsyncClient, bill: dict,
                               api_key: str) -> Optional[PolicyDict]:
        bill_type = bill.get("type", "").lower()
        bill_number = bill.get("number", "")
        congress = bill.get("congress", 119)
        bill_id = f"congress:{congress}:{bill_type}{bill_number}"

        title = bill.get("title", "")
        summary = self._bill_summary(bill)
        introduced_date = bill.get("introducedDate", "")[:10] or _extract_date(
            bill.get("updateDate", "")
        )

        # Fetch bill text URL
        text_url = ""
        try:
            text_resp = await client.get(
                f"{BASE_URL}/bill/{congress}/{bill_type}/{bill_number}/text",
                params={"api_key": api_key, "format": "json"},
            )
            text_data = text_resp.json()
            versions = text_data.get("textVersions", [])
            if versions:
                formats = versions[0].get("formats", [])
                for fmt in formats:
                    if fmt.get("type") == "PDF":
                        text_url = fmt.get("url", "")
                        break
                if not text_url and formats:
                    text_url = formats[0].get("url", "")
        except Exception:
            text_url = bill.get("url", "")

        return PolicyDict(
            id=bill_id,
            source_id=self.source_id,
            title=title,
            title_en=title,
            country="US",
            department="US Congress",
            department_label="Congress",
            level="national",
            date=introduced_date,
            summary=_extract_summary(summary, 300),
            full_text=summary,
            full_text_url=text_url,
            status="proposed",
            category=self._categorize_bill(title, summary),
            related_technologies=[],
            related_industries=[],
            market_reaction_days=None,
            raw_json=bill,
        )

    def _categorize_bill(self, title: str, summary: str) -> str:
        combined = f"{title} {summary}".lower()
        if any(kw in combined for kw in ["appropriation", "budget", "funding"]):
            return "funding"
        if any(kw in combined for kw in ["authorization", "reauthorization"]):
            return "authorization"
        return "legislation"
