-- Market events schema: VC funding, M&A, IPOs, grants
-- Links each event to industries and technologies via keyword mapping

CREATE TABLE IF NOT EXISTS market_events (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    title TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'funding',
    company_name TEXT,
    amount_usd REAL,
    currency TEXT DEFAULT 'USD',
    round_stage TEXT,
    investors TEXT,
    valuation_usd REAL,
    country TEXT NOT NULL,
    date TEXT NOT NULL,
    summary TEXT,
    source_url TEXT,
    industry_ids TEXT,
    technology_ids TEXT,
    tags TEXT,
    raw_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_market_events_date ON market_events(date);
CREATE INDEX IF NOT EXISTS idx_market_events_type ON market_events(event_type);
CREATE INDEX IF NOT EXISTS idx_market_events_country ON market_events(country);
CREATE INDEX IF NOT EXISTS idx_market_events_source ON market_events(source_id);
CREATE INDEX IF NOT EXISTS idx_market_events_amount ON market_events(amount_usd);
