-- Policy data schema for TechPolicyBoard
-- SQLite database

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    url TEXT,
    scraper_module TEXT,
    last_scraped_at TEXT,
    scrape_interval_hours INTEGER DEFAULT 24
);

CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    title TEXT NOT NULL,
    title_en TEXT,
    country TEXT NOT NULL,
    department TEXT,
    department_label TEXT,
    level TEXT,
    date TEXT NOT NULL,
    summary TEXT,
    full_text TEXT,
    full_text_url TEXT,
    status TEXT DEFAULT 'enacted',
    category TEXT,
    related_technologies TEXT,
    related_industries TEXT,
    market_reaction_days INTEGER,
    raw_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_policies_source ON policies(source_id);
CREATE INDEX IF NOT EXISTS idx_policies_date ON policies(date);
CREATE INDEX IF NOT EXISTS idx_policies_country ON policies(country);

CREATE TABLE IF NOT EXISTS scrape_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES sources(id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    items_fetched INTEGER DEFAULT 0,
    items_new INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_scrape_logs_source ON scrape_logs(source_id);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_started ON scrape_logs(started_at);
