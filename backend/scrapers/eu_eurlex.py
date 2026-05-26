from datetime import datetime
from typing import Optional

import httpx

from .base import BaseScraper, PolicyDict, _is_tech_relevant, _extract_summary, _extract_date

SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"


class EurLexScraper(BaseScraper):
    source_id = "eu_eurlex"

    async def fetch(self, since: Optional[str] = None) -> list[PolicyDict]:
        policies = []

        # SPARQL query for recent EU legislation in tech-related domains
        query = self._build_sparql(since)

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.get(
                    SPARQL_ENDPOINT,
                    params={"query": query, "format": "application/json"},
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

                for binding in data.get("results", {}).get("bindings", []):
                    policy = self._binding_to_policy(binding)
                    if _is_tech_relevant(policy.title, policy.summary, policy.full_text):
                        policies.append(policy)
            except Exception:
                import logging
                logging.getLogger("techpolicy.scrapers").warning(
                    "eur_lex SPARQL query failed for %s", self.source_id
                )
                pass

        return policies

    def _build_sparql(self, since: Optional[str] = None) -> str:
        date_filter = ""
        if since:
            date_filter = f'FILTER(?date >= "{since[:10]}"^^xsd:date)'

        return f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?celex ?title ?date ?type ?url
        WHERE {{
          ?work a cdm:legislation_primary .
          ?work cdm:resource_legal_id_celex ?celex .
          ?work cdm:work_date_document ?date .
          ?work dc:title ?title .
          ?work cdm:resource_legal_type ?type_label .
          ?type_label cdm:authority-code ?type .
          OPTIONAL {{ ?work cdm:resource_legal_published_in_official-journal ?oj .
                      ?oj cdm:expression_belongs_to_work ?expr .
                      ?expr cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
                      ?expr cdm:expression_title ?url . }}

          {date_filter}

          FILTER(?type IN ("REG", "DIR", "DEC"))
          FILTER(lang(?title) = "en")
        }}
        ORDER BY DESC(?date)
        LIMIT 100
        """

    def _binding_to_policy(self, b: dict) -> PolicyDict:
        celex = b.get("celex", {}).get("value", "")
        title = b.get("title", {}).get("value", "")
        date_val = b.get("date", {}).get("value", "")[:10]
        doc_type = b.get("type", {}).get("value", "")
        url = b.get("url", {}).get("value", "")

        type_labels = {"REG": "Regulation", "DIR": "Directive", "DEC": "Decision"}
        doc_label = type_labels.get(doc_type, doc_type)

        return PolicyDict(
            id=f"eurlex:{celex}",
            source_id=self.source_id,
            title=title,
            title_en=title,
            country="EU",
            department="European Commission",
            department_label="EC",
            level="supranational",
            date=date_val,
            summary=_extract_summary(title, 300),
            full_text="",
            full_text_url=url or f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}",
            status="enacted",
            category=doc_label.lower(),
            related_technologies=[],
            related_industries=[],
            market_reaction_days=None,
            raw_json=b,
        )
