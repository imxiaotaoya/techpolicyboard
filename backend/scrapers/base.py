from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PolicyDict:
    """Standardized policy dict that all scrapers produce."""
    id: str
    source_id: str
    title: str
    title_en: str
    country: str
    department: str
    department_label: str
    level: str
    date: str
    summary: str
    full_text: str
    full_text_url: str
    status: str
    category: str
    related_technologies: list[str]
    related_industries: list[str]
    market_reaction_days: Optional[int]
    raw_json: dict

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "title": self.title,
            "title_en": self.title_en,
            "country": self.country,
            "department": self.department,
            "departmentLabel": self.department_label,
            "level": self.level,
            "date": self.date,
            "summary": self.summary,
            "full_text": self.full_text,
            "fullTextUrl": self.full_text_url,
            "status": self.status,
            "category": self.category,
            "relatedTechnologies": self.related_technologies,
            "relatedIndustries": self.related_industries,
            "marketReactionDays": self.market_reaction_days,
            "raw_json": self.raw_json,
        }


TECH_KEYWORDS = [
    "artificial intelligence", "machine learning", "neural",
    "semiconductor", "chip", "quantum", "superconduct",
    "robot", "humanoid", "embodied", "autonomous",
    "brain-computer", "neural interface", "neurotech",
    "fusion", "nuclear", "plasma", "tokamak",
    "biotech", "genetic", "gene", "crispr",
    "cyber", "5g", "6g", "telecom", "broadband",
    "space", "satellite", "launch", "orbit",
    "battery", "solar", "hydrogen", "renewable", "clean energy",
    "computing", "data center", "cloud", "blockchain",
    "drone", "uav", "hypersonic", "advanced manufacturing",
]


def _is_tech_relevant(title: str, summary: str = "", full_text: str = "") -> bool:
    """Check if a policy is tech-relevant based on keyword matching."""
    combined = f"{title} {summary} {full_text or ''}".lower()
    return any(kw in combined for kw in TECH_KEYWORDS)


def _extract_summary(text: str, max_chars: int = 300) -> str:
    """Extract a short summary from longer text."""
    if not text:
        return ""
    clean = text.strip().replace("\n", " ").replace("\r", " ")
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rsplit(" ", 1)[0] + "..."


def _extract_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD format."""
    if not date_str:
        return datetime.utcnow().strftime("%Y-%m-%d")
    date_str = date_str.strip()[:10]
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT"]:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str[:10] if len(date_str) >= 10 else date_str


class BaseScraper(ABC):
    source_id: str

    @abstractmethod
    async def fetch(self, since: Optional[str] = None) -> list[PolicyDict]:
        """Fetch policies from the source, optionally filtering by date."""

    async def run(self, db_module) -> dict:
        """Full pipeline: fetch -> insert -> log. Returns summary dict."""
        db = db_module.get_db()
        since = self._get_last_scraped(db)
        log_id = db_module.log_scrape_start(self.source_id)
        result = {"fetched": 0, "new": 0, "error": None}

        try:
            policies = await self.fetch(since=since)
            result["fetched"] = len(policies)
            new_count = 0
            for p in policies:
                if db_module.insert_policy(p.to_dict()):
                    new_count += 1
            result["new"] = new_count
        except Exception as e:
            result["error"] = str(e)
        finally:
            db.execute(
                "UPDATE sources SET last_scraped_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), self.source_id),
            )
            db.commit()
            db_module.log_scrape_end(log_id, result["fetched"], result["new"], result["error"])

        return result

    def _get_last_scraped(self, db) -> Optional[str]:
        row = db.execute(
            "SELECT last_scraped_at FROM sources WHERE id = ?",
            (self.source_id,),
        ).fetchone()
        return row["last_scraped_at"] if row else None
