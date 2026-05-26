from .base import BaseScraper, PolicyDict, TECH_KEYWORDS
from .us_federal_register import FederalRegisterScraper
from .us_congress import CongressScraper
from .eu_eurlex import EurLexScraper
from .rss_feeds import RSSDiscovery
from .search_discovery import SearchDiscovery
from .cn_gov import ChinaGovScraper
from .cleaner import PolicyCleaner
from .provenance import SourceTrail, QualityScorer

SCRAPERS: dict[str, BaseScraper] = {
    "us_federal_register": FederalRegisterScraper(),
    "us_congress": CongressScraper(),
    "eu_eurlex": EurLexScraper(),
    "rss_discovery": RSSDiscovery(),
    "search_discovery": SearchDiscovery(),
    "cn_gov": ChinaGovScraper(),
}
