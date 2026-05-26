import sqlite3
import json
import os
from pathlib import Path
from typing import Optional

DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "policies.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "policy_schema.sql"
MARKET_SCHEMA_PATH = Path(__file__).resolve().parent / "market_schema.sql"

_connection: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
        _init_schema(_connection)
        _seed_sources(_connection)
    return _connection


def _init_schema(db: sqlite3.Connection) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    db.executescript(schema_sql)
    market_sql = MARKET_SCHEMA_PATH.read_text(encoding="utf-8")
    db.executescript(market_sql)
    db.commit()


def _seed_sources(db: sqlite3.Connection) -> None:
    sources = [
        ("manual", "Hand-curated policy data", "GLOBAL",
         None, None, None),
        ("us_congress", "US Congress (Congress.gov)", "US",
         "https://api.congress.gov/v3/", "scrapers.us_congress", 24),
        ("us_federal_register", "US Federal Register", "US",
         "https://www.federalregister.gov/api/v1/", "scrapers.us_federal_register", 24),
        ("eu_eurlex", "EU EUR-Lex", "EU",
         "https://eur-lex.europa.eu/", "scrapers.eu_eurlex", 48),
        ("external:ai-legislation-tracker", "External: AI Legislation Tracker", "GLOBAL",
         "https://github.com/delschlangen/ai-legislation-tracker", None, None),
        ("rss_discovery", "RSS Feed Discovery", "GLOBAL",
         None, "scrapers.rss_feeds", 12),
        ("search_discovery", "Search Engine Discovery", "GLOBAL",
         None, "scrapers.search_discovery", 24),
        ("market_events", "Primary Market Events", "GLOBAL",
         None, "scrapers.market_events", 12),
        ("market_events_v2", "Enhanced Market Events (Provenance-tracked)", "GLOBAL",
         None, "scrapers.market_events_v2", 12),
        ("cn_gov", "China Government Policy (国务院/科技部/工信部/发改委)", "CN",
         None, "scrapers.cn_gov", 24),
    ]
    db.executemany(
        """INSERT OR IGNORE INTO sources (id, name, country, url, scraper_module, scrape_interval_hours)
           VALUES (?, ?, ?, ?, ?, ?)""",
        sources,
    )
    db.commit()


def close_db() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def insert_policy(policy: dict) -> bool:
    """Insert a policy, returns True if new, False if already exists (by id)."""
    db = get_db()
    related_tech = json.dumps(policy.get("relatedTechnologies", []))
    related_ind = json.dumps(policy.get("relatedIndustries", []))
    raw = json.dumps(policy.get("raw_json", policy), ensure_ascii=False)

    # Support both camelCase (from API/JSON) and snake_case (from DB/seed)
    def _get(key_snake: str, key_camel: str, default=""):
        return policy.get(key_snake) or policy.get(key_camel) or default

    try:
        db.execute(
            """INSERT INTO policies (id, source_id, title, title_en, country, department,
               department_label, level, date, summary, full_text, full_text_url, status,
               category, related_technologies, related_industries, market_reaction_days, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                policy["id"],
                policy.get("source_id") or policy.get("sourceId", "manual"),
                policy["title"],
                policy.get("title_en") or policy.get("titleEn"),
                policy["country"],
                policy.get("department"),
                _get("department_label", "departmentLabel"),
                policy.get("level"),
                policy["date"],
                policy.get("summary"),
                _get("full_text", "fullText"),
                _get("full_text_url", "fullTextUrl"),
                policy.get("status", "enacted"),
                policy.get("category"),
                related_tech,
                related_ind,
                policy.get("market_reaction_days") or policy.get("marketReactionDays"),
                raw,
            ),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def log_scrape_start(source_id: str) -> int:
    from datetime import datetime
    db = get_db()
    now = datetime.utcnow().isoformat()
    cur = db.execute(
        "INSERT INTO scrape_logs (source_id, started_at, status) VALUES (?, ?, 'running')",
        (source_id, now),
    )
    db.commit()
    return cur.lastrowid


def log_scrape_end(log_id: int, items_fetched: int, items_new: int,
                   error: Optional[str] = None) -> None:
    from datetime import datetime
    db = get_db()
    now = datetime.utcnow().isoformat()
    status = "error" if error else "success"
    db.execute(
        """UPDATE scrape_logs SET finished_at = ?, items_fetched = ?, items_new = ?,
           status = ?, error_message = ? WHERE id = ?""",
        (now, items_fetched, items_new, status, error, log_id),
    )
    db.commit()


def get_scrape_logs(source_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    db = get_db()
    if source_id:
        rows = db.execute(
            "SELECT * FROM scrape_logs WHERE source_id = ? ORDER BY started_at DESC LIMIT ?",
            (source_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM scrape_logs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Market Events CRUD ---

def insert_market_event(event: dict) -> bool:
    """Insert a market event. Returns True if new, False if duplicate."""
    db = get_db()
    try:
        db.execute(
            """INSERT INTO market_events (id, source_id, title, event_type, company_name,
               amount_usd, currency, round_stage, investors, valuation_usd,
               country, date, summary, source_url, industry_ids, technology_ids,
               tags, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event["id"],
                event.get("source_id", "market_events"),
                event["title"],
                event.get("event_type", "funding"),
                event.get("company_name"),
                event.get("amount_usd"),
                event.get("currency", "USD"),
                event.get("round_stage"),
                event.get("investors", "[]"),
                event.get("valuation_usd"),
                event.get("country", "US"),
                event["date"],
                event.get("summary", ""),
                event.get("source_url", ""),
                event.get("industry_ids", "[]"),
                event.get("technology_ids", "[]"),
                event.get("tags", "[]"),
                event.get("raw_json", "{}"),
            ),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_market_events(
    technology_id: Optional[str] = None,
    industry_id: Optional[str] = None,
    event_type: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Query market events with optional filters. Returns (items, total)."""
    db = get_db()
    where = []
    params: list = []

    if technology_id:
        where.append("technology_ids LIKE ?")
        params.append(f'%"{technology_id}"%')
    if industry_id:
        where.append("industry_ids LIKE ?")
        params.append(f'%"{industry_id}"%')
    if event_type:
        where.append("event_type = ?")
        params.append(event_type)
    if country:
        where.append("country = ?")
        params.append(country)

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    count_row = db.execute(
        f"SELECT COUNT(*) FROM market_events {where_clause}", params
    ).fetchone()
    total = count_row[0] if count_row else 0

    rows = db.execute(
        f"SELECT * FROM market_events {where_clause} ORDER BY date DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    ).fetchall()

    return [dict(r) for r in rows], total


def get_market_event(event_id: str) -> Optional[dict]:
    db = get_db()
    row = db.execute(
        "SELECT * FROM market_events WHERE id = ?", (event_id,)
    ).fetchone()
    return dict(row) if row else None

