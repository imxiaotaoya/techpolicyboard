import json
from datetime import datetime
from typing import Optional

import httpx

from .base import BaseScraper, PolicyDict, _is_tech_relevant, _extract_summary

BASE_URL = "https://www.federalregister.gov/api/v1"


class FederalRegisterScraper(BaseScraper):
    source_id = "us_federal_register"

    async def fetch(self, since: Optional[str] = None) -> list[PolicyDict]:
        policies = []

        # Fetch presidential documents (executive orders) first
        for doc_type in ["PRESDOCU", "RULE"]:
            params = {
                "per_page": 50,
                "order": "newest",
                "conditions[type][]": doc_type,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{BASE_URL}/documents", params=params)
                resp.raise_for_status()
                data = resp.json()

                for doc in data.get("results", []):
                    pub_date = doc.get("publication_date", "")[:10]
                    if since and pub_date <= since[:10]:
                        continue

                    title = doc.get("title", "")
                    summary = doc.get("abstract", "") or ""
                    full_text_url = doc.get("html_url", "")

                    policy = self._doc_to_policy(doc, doc_type)
                    if _is_tech_relevant(title, summary):
                        policies.append(policy)

        return policies

    def _doc_to_policy(self, doc: dict, doc_type: str) -> PolicyDict:
        title = doc.get("title", "") or ""
        pub_date = doc.get("publication_date", "")[:10]
        doc_id = f"fedreg:{doc.get('document_number', '')}"
        summary = doc.get("abstract", "") or ""
        full_text_url = doc.get("html_url", "")

        agencies = doc.get("agency_names", [])
        department = agencies[0] if agencies else "Executive Office"
        dept_label = department

        exec_order_num = doc.get("executive_order_number")
        if exec_order_num:
            title = f"Executive Order {exec_order_num}: {title}"

        return PolicyDict(
            id=doc_id,
            source_id=self.source_id,
            title=title,
            title_en=title,
            country="US",
            department=department,
            department_label=dept_label,
            level="national",
            date=pub_date,
            summary=_extract_summary(summary, 300),
            full_text=summary,
            full_text_url=full_text_url,
            status="proposed" if doc_type == "PRORULE" else "enacted",
            category="executive-order" if doc_type == "PRESDOCU" else "agency-rule",
            related_technologies=[],
            related_industries=[],
            market_reaction_days=None,
            raw_json=doc,
        )
