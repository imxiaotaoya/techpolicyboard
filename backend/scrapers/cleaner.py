"""Data cleaning, deduplication, and source verification pipeline."""

import hashlib
import re
from datetime import datetime
from typing import Optional

from .base import PolicyDict, _extract_summary, TECH_KEYWORDS


class PolicyCleaner:
    """Normalize, deduplicate, and verify raw policy data from any source."""

    @staticmethod
    def compute_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def normalize(raw: dict, source_id: str, discovery_info: Optional[dict] = None) -> PolicyDict:
        """Normalize fields from any source to our standard PolicyDict schema.

        Accepts both camelCase (API-style) and snake_case (DB-style) keys.
        """
        def _get(*keys: str, default: str = ""):
            for k in keys:
                val = raw.get(k)
                if val is not None and val != "":
                    return val
            return default

        title = _get("title", "policy_title", "name", default="Untitled")
        country = _get("country", "jurisdiction", "region", default="US")
        date_val = _get("date", "published_date", "publication_date", "pubDate", "introduced_date",
                        default=datetime.utcnow().strftime("%Y-%m-%d"))
        dept = _get("department", "agency", "issuing_body", "source_agency", default="Unknown")
        summary = _get("summary", "abstract", "description", "body_text", "content")

        # Normalize date to YYYY-MM-DD
        date_val = PolicyCleaner._norm_date(date_val)

        # Infer country from department/URL
        if country == "US" or not country:
            country = PolicyCleaner._infer_country(
                _get("source_url", "url", "link"),
                dept,
                title,
            )

        raw_json = dict(raw)
        if discovery_info:
            raw_json["_discovery"] = discovery_info

        full_text = _get("full_text", "fullText", "body", "text", "content")
        full_text_url = _get("full_text_url", "fullTextUrl", "url", "link", "source_url")
        summary_clean = _extract_summary(summary or full_text or title, 300)
        content_hash = PolicyCleaner.compute_hash(f"{title}{summary_clean}")

        return PolicyDict(
            id=f"discovered:{content_hash}",
            source_id=source_id,
            title=title[:500],
            title_en=title[:500] if re.search(r"[a-zA-Z]", title) else "",
            country=country,
            department=dept,
            department_label=dept,
            level=PolicyCleaner._infer_level(dept, country, title),
            date=date_val,
            summary=summary_clean,
            full_text=full_text or summary_clean,
            full_text_url=full_text_url,
            status="enacted",
            category=PolicyCleaner._infer_category(title, summary_clean),
            related_technologies=[],
            related_industries=[],
            market_reaction_days=None,
            raw_json=raw_json,
        )

    @staticmethod
    def deduplicate(policies: list[PolicyDict]) -> list[PolicyDict]:
        """Remove duplicates by content_hash and fuzzy title match."""
        seen_hashes: set[str] = set()
        seen_titles: set[str] = set()
        result: list[PolicyDict] = []

        for p in policies:
            h = PolicyCleaner.compute_hash(f"{p.title}{p.summary}")
            title_key = re.sub(r"\s+", " ", p.title.lower()).strip()[:80]

            if h in seen_hashes or title_key in seen_titles:
                continue

            seen_hashes.add(h)
            seen_titles.add(title_key)
            result.append(p)

        return result

    @staticmethod
    def verify(policy: PolicyDict) -> bool:
        """Verify a policy has minimum required fields and valid source."""
        if not policy.title or policy.title == "Untitled":
            return False
        if not policy.full_text_url and not policy.summary:
            return False
        if len(policy.title) < 5:
            return False
        return True

    @staticmethod
    def _norm_date(date_str: str) -> str:
        if not date_str:
            return datetime.utcnow().strftime("%Y-%m-%d")
        date_str = str(date_str).strip()[:19]
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
                     "%Y-%m-%dT%H:%M:%S", "%a, %d %b %Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(date_str[:len(fmt)], fmt).strftime("%Y-%m-%d")
            except (ValueError, IndexError):
                continue
        m = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", date_str)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return datetime.utcnow().strftime("%Y-%m-%d")

    @staticmethod
    def _infer_country(url: str, dept: str, title: str) -> str:
        combined = f"{url} {dept} {title}".lower()
        if any(kw in combined for kw in ["china", "chinese", "beijing", ".cn", "gov.cn", "most.cn"]):
            return "CN"
        if any(kw in combined for kw in ["europa.eu", "eur-lex", "european union", "european commission"]):
            return "EU"
        if any(kw in combined for kw in ["parliament.uk", ".gov.uk", "united kingdom"]):
            return "UK"
        if any(kw in combined for kw in [".go.jp", "japan"]):
            return "JP"
        if any(kw in combined for kw in [".go.kr", "korea"]):
            return "KR"
        return "US"

    @staticmethod
    def _infer_level(dept: str, country: str, title: str) -> str:
        combined = f"{dept} {title}".lower()
        if any(kw in combined for kw in ["state", "local", "city", "municipal"]):
            return "local"
        if any(kw in combined for kw in ["governor", "mayor", "county"]):
            return "local"
        if any(kw in combined for kw in ["minister", "agency", "department", "ministry"]):
            return "ministerial"
        if any(kw in combined for kw in ["congress", "parliament", "senate", "president",
                                          "executive order", "european commission",
                                          "council", "supreme", "constitutional"]):
            return "national"
        if country == "EU":
            return "supranational"
        return "national"

    @staticmethod
    def _infer_category(title: str, summary: str) -> str:
        combined = f"{title} {summary}".lower()
        if any(kw in combined for kw in ["executive order", "presidential"]):
            return "executive-order"
        if any(kw in combined for kw in ["regulation", "regulatory", "rule"]):
            return "regulation"
        if any(kw in combined for kw in ["appropriation", "budget", "funding"]):
            return "funding"
        if any(kw in combined for kw in ["act", "law", "statute", "legislation", "public law"]):
            return "legislation"
        if any(kw in combined for kw in ["directive", "decision"]):
            return "directive"
        if any(kw in combined for kw in ["strategy", "plan", "framework", "initiative", "agenda"]):
            return "strategy"
        return "other"
