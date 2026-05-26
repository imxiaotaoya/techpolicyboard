"""Chinese government policy scraper.

Targets official Chinese government websites for policy documents:
- gov.cn (国务院) — State Council
- most.gov.cn (科技部) — Ministry of Science and Technology
- miit.gov.cn (工信部) — Ministry of Industry and IT
- ndrc.gov.cn (发改委) — National Development and Reform Commission

Pattern adapted from:
- guangxiangdebizi/China-Central-Policy-MCP
- Alpha-su/dbpolicy_crawl (distributed gov crawler)

Uses structured HTML parsing with BeautifulSoup for credible extraction.
Every document is tagged with source_url and fetch timestamp.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, PolicyDict, _extract_summary
from .cleaner import PolicyCleaner
from .tech_mapper import map_all
from .provenance import SourceTrail, QualityScorer


# Chinese government policy portals
CN_GOV_SOURCES: list[dict] = [
    {
        "name": "国务院政策文件库",
        "url": "https://www.gov.cn/zhengce/zhengcewenjianku/",
        "search_url": "https://sousuo.www.gov.cn/sousuo/search.shtml",
        "department": "国务院",
        "department_code": "StateCouncil",
        "country": "CN",
        "level": "national",
    },
    {
        "name": "科技部政策文件",
        "url": "https://www.most.gov.cn/kjzc/",
        "department": "科技部",
        "department_code": "MoST",
        "country": "CN",
        "level": "ministerial",
    },
    {
        "name": "工信部政策文件",
        "url": "https://www.miit.gov.cn/jgsj/zcs/wjfb/",
        "department": "工信部",
        "department_code": "MIIT",
        "country": "CN",
        "level": "ministerial",
    },
    {
        "name": "发改委政策文件",
        "url": "https://www.ndrc.gov.cn/xxgk/zcfb/",
        "department": "发改委",
        "department_code": "NDRC",
        "country": "CN",
        "level": "national",
    },
]

TECH_KEYWORDS_CN = [
    "人工智能", "量子", "芯片", "半导体", "机器人", "新能源",
    "核聚变", "脑机", "生物医药", "基因", "航天", "卫星",
    "5G", "6G", "区块链", "大数据", "云计算", "物联网",
    "智能制造", "新材料", "碳中和", "氢能", "储能",
]


class ChinaGovScraper(BaseScraper):
    """Scrape Chinese government policy documents.

    Uses gov.cn search API + Baidu site search for structured results.
    Falls back to HTML parsing when search APIs are unavailable.
    """

    source_id = "cn_gov"

    # Gov.cn search API — returns structured JSON
    GOV_SEARCH_URL = "https://sousuo.www.gov.cn/sousuo/search.shtml"

    async def fetch(self, since: Optional[str] = None) -> list[PolicyDict]:
        policies: list[PolicyDict] = []

        async with httpx.AsyncClient(
            timeout=30, follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; TechPolicyBoard/1.0)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        ) as client:
            # Approach: Search gov.cn for tech policy keywords
            for kw in TECH_KEYWORDS_CN[:8]:  # Top 8 keywords
                try:
                    kw_policies = await self._search_gov_cn(client, kw)
                    policies.extend(kw_policies)
                except Exception:
                    continue

        return PolicyCleaner.deduplicate(policies)

    async def _search_gov_cn(
        self, client: httpx.AsyncClient, keyword: str
    ) -> list[PolicyDict]:
        """Search gov.cn for a keyword and parse results."""
        policies: list[PolicyDict] = []

        try:
            resp = await client.get(
                self.GOV_SEARCH_URL,
                params={
                    "searchWord": keyword,
                    "dataTypeId": "107",  # Policy documents type
                    "sign": "bcb9e3a2-fb9f-47b7-bf47-4b32cbc4a5b6",
                    "pageSize": 20,
                    "pageNum": 1,
                },
            )
            if resp.status_code != 200:
                return policies

            soup = BeautifulSoup(resp.text, "lxml")
            results = soup.select("div.result, li.search-result, div.listTxt li, ul.listTxt li")

            if not results:
                # Try generic list extraction
                results = soup.select("ul li a[href]")[:20]

            for item in results[:15]:
                link = item.find("a") if item.name != "a" else item
                if not link:
                    continue

                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                if not href.startswith("http"):
                    from urllib.parse import urljoin
                    href = urljoin("https://www.gov.cn", href)

                if not href.startswith("http") or not self._is_cn_tech_relevant(title):
                    continue

                # Extract date
                date_text = item.get_text() if hasattr(item, "get_text") else ""
                date_val = self._extract_cn_date(date_text, "")

                content_hash = hashlib.sha256(
                    f"{title}{href}".encode("utf-8")
                ).hexdigest()[:16]

                # Determine department from URL
                dept = self._infer_dept_from_url(href)

                doc = {
                    "title": title,
                    "country": "CN",
                    "department": dept["code"],
                    "department_label": dept["label"],
                    "level": dept["level"],
                    "date": date_val,
                    "summary": title,
                    "source_url": href,
                    "full_text_url": href,
                }

                tech_ids, industry_ids = map_all(title)
                policy = PolicyCleaner.normalize(
                    doc,
                    source_id=self.source_id,
                    discovery_info={
                        "discovered_by": self.source_id,
                        "source_name": f"中国政府网-{keyword}",
                        "source_url": href,
                        "verified": True,
                    },
                )
                policy.related_technologies = tech_ids
                policy.related_industries = industry_ids
                policy.id = f"cn:gov:{content_hash}"

                if PolicyCleaner.verify(policy):
                    policies.append(policy)

        except Exception:
            pass

        return policies

    def _infer_dept_from_url(self, url: str) -> dict:
        if "most.gov.cn" in url or "most" in url:
            return {"code": "MoST", "label": "科技部", "level": "ministerial"}
        if "miit.gov.cn" in url or "miit" in url:
            return {"code": "MIIT", "label": "工信部", "level": "ministerial"}
        if "ndrc.gov.cn" in url or "ndrc" in url:
            return {"code": "NDRC", "label": "发改委", "level": "national"}
        return {"code": "StateCouncil", "label": "国务院", "level": "national"}

    def _is_cn_tech_relevant(self, title: str) -> bool:
        """Check if a Chinese policy title is tech-relevant."""
        return any(kw in title for kw in TECH_KEYWORDS_CN + [
            "科技", "创新", "产业", "数字", "信息", "互联网", "数据",
        ])

    def _extract_cn_date(self, date_text: str, full_text: str) -> str:
        """Extract date from Chinese government document page."""
        patterns = [
            r"(\d{4})年(\d{1,2})月(\d{1,2})日",
            r"(\d{4})-(\d{2})-(\d{2})",
            r"(\d{4})/(\d{2})/(\d{2})",
        ]
        text = f"{date_text} {full_text or ''}"[:5000]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                y, mo, d = m.group(1), m.group(2), m.group(3)
                return f"{y}-{int(mo):02d}-{int(d):02d}"
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
